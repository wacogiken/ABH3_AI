
import time #時間計測(time.time()で取得(1/60程度の精度)),(time.perf_counter()で取得(usの精度))

import ABH3_Can #CAN制御
from ABH3_ObjDetect import ClsTarget  #検出物体用データクラス

class CtrlAGV_M:

    def __init__(self) -> None:
        #パルス位置
        self.pos_rot_per_pulse = 1/256  #1回転あたりのパルス数
        self.pos_x = 0
        self.pos_y = 0

        #動作実行
        self.MoveFunc = self.__Move_FollowingPanel   #動作モード
        self.MoveFunc_Old = self.__Move_None #動作モード前回値   

        #動作コメント
        self.move_doc =''
        self.move_doc_x =''
        self.move_doc_y = ''

    def ClearPos(self,flg:bool=True):#位置積算クリア
        if flg == True:
            ABH3_Can.ApiCtrlFlg_SetBit('posClearA')
            ABH3_Can.ApiCtrlFlg_SetBit('posClearB')
        else:
            ABH3_Can.ApiCtrlFlg_ClaBit('posClearA')
            ABH3_Can.ApiCtrlFlg_ClaBit('posClearB')

    def Cmd_Y(self,select_no:int=7,cmd:float=0.0): 
        """進行速度"""
        ABH3_Can.ApiCtrlFlg_SetSlectNoAY(select_no) 
        ABH3_Can.ApiCmdAY_Set(cmd)
        self.move_doc_y ="Select:" +str(select_no)+",Cmd:"+'{:.2f}'.format(cmd)

    def Cmd_X(self,select_no:int=7,cmd:float=0.0):
        """旋回速度"""
        ABH3_Can.ApiCtrlFlg_SetSlectNoBX(select_no)          
        ABH3_Can.ApiCmdBX_Set(cmd)
        self.move_doc_x ="Select:" +str(select_no)+",Cmd:"+'{:.2f}'.format(cmd)


    def __Move_None(self,tg:ClsTarget): 
        self.move_doc = "None"
        self.Cmd_Y(0,0)     #減速停止
        self.Cmd_X(0,0)
        return    self.__Move_None

    def __Move_FollowingPanel(self,tg:ClsTarget): 
        """
        矢印追従走行
        """
        self.move_doc = "FollowingPanel"

        next_MoveFunc = self.__Move_FollowingPanel
        arrival     = False  #到着状態
        #初回判定
        if self.MoveFunc_Old != self.MoveFunc :
            pass

        #到着状態判定---
        if tg.distance <= 0.4: #近距離で到着判定
            arrival = True

        #矢印の見失った場合停止
        if tg.t_detect == False :#
            self.Cmd_Y(1,0)     #減速停止
            self.Cmd_X(0,0)
            return next_MoveFunc   #mode0継続

        #進行速度---  
        if arrival == True: #到着状態
            self.Cmd_Y(0,0)
        elif (tg.distance  > 1.25 )&(tg.rate_x_abs <= 0.60 ): #遠距離かつ中央付近にターゲット
            self.Cmd_Y(1,800)
        elif (tg.distance  > 0.65 ):  #通常低速走行 (到着判定との関係を注意)
            self.Cmd_Y(1,400)
        else:   #近距離状態
            self.Cmd_Y(1,100)
            
        #旋回速度---
        if arrival == True or ( tg.rate_x_abs < 0.1 ): #到着状態 or ターゲットが中央
            self.Cmd_X(0,0)
        elif ( tg.rate_x_abs > 0.1 ):
            self.Cmd_X(0,tg.rate_x * 100  +  (30 if tg.rate_x  > 0 else -30 ))
        else:
            self.Cmd_X(0,0)

        #到着状態であれば次のシーケンスへ
        if arrival == True : #到着状態
            next_MoveFunc = self.__Move_ArrivingPanel

        return next_MoveFunc


    move_ap_arrival_time_start = 0     #到達時の時間(到達からの時間計算用)
    move_ap_arrow_cunt = {"up":0,"dw":0,"r":0,"l":0}
    move_ap_detect_arrow =""   
    def __Move_ArrivingPanel(self,tg:ClsTarget):
        """
        矢印パネル到着時、矢印の向きを判定する
        """
        self.move_doc = "ArrivingPanel"
        next_MoveFunc = self.__Move_ArrivingPanel
        #初回判定
        if self.MoveFunc_Old != self.MoveFunc :
            self.move_ap_arrival_time_start = time.time() 
            self.move_ap_arrow_cunt = {}

        else: #初回以降
            if(tg.t_ArrowDir != ""):
                if tg.t_ArrowDir in self.move_ap_arrow_cunt:
                    self.move_ap_arrow_cunt[tg.t_ArrowDir] = self.move_ap_arrow_cunt[tg.t_ArrowDir] +1
                else:
                    self.move_ap_arrow_cunt[tg.t_ArrowDir] = 1
        
        #停止指令
        self.Cmd_X(0,0)
        self.Cmd_Y(0,0)

        #到着からの時間計算     
        arrivTime = time.time() - self.move_ap_arrival_time_start    
        self.move_doc += "->wait="+'{:.2f}'.format(arrivTime)

        if arrivTime > 1:
            if len(self.move_ap_arrow_cunt) > 0:
                self.move_ap_detect_arrow = max(self.move_ap_arrow_cunt, key=self.move_ap_arrow_cunt.get)
            else:
                self.move_ap_detect_arrow = ""
            next_MoveFunc = self.__Move_DepartingPanel

        elif tg.distance  > 0.8:
            #パネルが何かしらの理由で離れた場合
            next_MoveFunc = self.__Move_FollowingPanel

        return next_MoveFunc

    ##矢印の示す方向への旋回走行
    move_dp_pos_x_started = 0 #moveB
    move_dp_flg_turne_comp = False
    def __Move_DepartingPanel(self,tg:ClsTarget): 
        """
        矢印パネルから次のパネルに出発
        """
        self.move_doc = "DepartingPanel"
        next_MoveFunc = self.__Move_DepartingPanel
        #初回判定
        if self.MoveFunc_Old != self.MoveFunc :
            self.ClearPos(False)
            self.move_dp_pos_x_started = self.pos_x
            self.move_dp_flg_turne_comp = False

        #---ステータス準備---
        pos_x_rot_from_start = self.pos_rot_per_pulse * (self.pos_x - self.move_dp_pos_x_started ) #時計回りで+
        
        #旋回状態
        if self.move_ap_detect_arrow == "r" or self.move_ap_detect_arrow == "l":
            if abs( pos_x_rot_from_start) > 160 \
                    or (abs( pos_x_rot_from_start) > 70 and self.move_ap_detect_arrow == "r" and tg.rate_x > 0 and tg.rate_x_abs < 0.85) \
                    or (abs( pos_x_rot_from_start) > 70 and self.move_ap_detect_arrow == "l" and tg.rate_x < 0 and tg.rate_x_abs  < 0.85) :
                self.move_dp_flg_turne_comp = True
        else :
             if abs( pos_x_rot_from_start) > 210 : #180度/210pulse程度
                self.move_dp_flg_turne_comp = True       
        #
        if self.move_dp_flg_turne_comp == False :
            self.move_doc += "->Turne:" + str(self.move_ap_detect_arrow)
            if self.move_ap_detect_arrow == "r":
                self.Cmd_Y(1,300)
                self.Cmd_X(0,100)
                 
            elif self.move_ap_detect_arrow == "l":
                self.Cmd_Y(1,300)
                self.Cmd_X(0,-100)
            else : 
                self.Cmd_Y(1,300)
                self.Cmd_X(0,-250)
        else: 
            self.move_doc += "->SearchArrow"

            #矢印の見失った場合停止
            if tg.t_detect == False :#
                self.Cmd_Y(1,0)     #減速停止
                self.Cmd_X(0,0)
                return next_MoveFunc   #mode0継続

            self.Cmd_Y(1,300)
            x_cmd =  (tg.rate_x_abs) * 50 +50  #ターゲットの位置に合わせて旋回速度調整
            x_cmd =  100 if x_cmd > 100 else x_cmd  #上限
            if tg.rate_x < 0 :
                x_cmd = -x_cmd
            self.Cmd_X(0,x_cmd)

            if (tg.rate_x_abs < 0.1 ):
                #旋回完了
                self.ClearPos(True)
                self.Cmd_X(0,0)
                next_MoveFunc = self.__Move_FollowingPanel 

        return next_MoveFunc


    def Exe (self,tg:ClsTarget,flgDetectObstacle:bool):
        """走行制御実行
        """

        #CAN通信からのパルス位置の取得
        self.pos_x = ABH3_Can.dctDataField["PosA"] - ABH3_Can.dctDataField["PosB"] #時計回りで+
        self.pos_y = (ABH3_Can.dctDataField["PosA"] + ABH3_Can.dctDataField["PosB"]) / 2   #前進で+

        #障害物検出or 安全センサーによる停止
        if flgDetectObstacle== True:
            self.Cmd_Y(0,0)
            self.Cmd_X(0,0)  
            self.move_doc = "stop"
            return
        
        #移動モード分岐
        sqcMoveRequest = self.MoveFunc(tg)
        self.MoveFunc_Old = self.MoveFunc 
        self.MoveFunc = sqcMoveRequest