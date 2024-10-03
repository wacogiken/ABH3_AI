
from math import sqrt
import time #時間計測(time.time()で取得(1/60程度の精度)),(time.perf_counter()で取得(usの精度))
import ABH3_Can #CAN制御
from ABH3_Ctrl_Drive import  CtrlAGV_M 

#検出物体用データクラス
from ABH3_ObjDetect import ClsTarget

class CtrlAGV:

    err_reset_hold = 0

    def __init__(self) -> None:

        #CANの実行
        ABH3_Can.CanExe()

        ##初期化
        self.Drive = CtrlAGV_M()

    def RestErr(self,flg:bool = True):
        
        if flg == True:
            ABH3_Can.ApiCtrlFlg_SetBit('errReset')
            self.err_reset_hold = 5
            
        else:
            if (self.err_reset_hold <= 0):
                ABH3_Can.ApiCtrlFlg_ClaBit('errReset') 
            else:
                self.err_reset_hold -=1
    #安全センサー
    stop_hold = False
    stop_restart_timer = 0
    def SafeSensor(self):

        #受信した操作フラグをカンマ区切りでまとめる
        ctrl_flgs =  ','.join(ABH3_Can.dctDataField['CtrlFlg'])
        #サーボ状態
        servo_on = ("svOnAY" in ctrl_flgs) or ("svOnBX" in ctrl_flgs)

        if servo_on  == False: 
            #サーボOFFで衝突状態クリア
            self.stop_hold = False
        elif  ("stAY" not in ctrl_flgs): 
            #制御フラグのAY軸スタートのストップ状態を安全センサー衝突判定として利用する
            self.stop_hold = True

        #障害物による停止から一定時間開けてスタートする     
        if servo_on == False:
            self.stop_restart_timer = time.time() + 5
        elif self.stop_hold == True:    
            self.stop_restart_timer = time.time() + 1.5

        #停止判定
        stop_request = True
        if (time.time() - self.stop_restart_timer) > 0 and self.stop_hold == False:
            stop_request = False
            self.stop_restart_timer = time.time() - 10

        return stop_request

    ##===AGV制御実行===
    def Exe(self,tg:ClsTarget,flgErrReset:bool = True)-> None:  

        if ABH3_Can.ApiPacketIsSendDone == False:
            print("CtrlSkip_CanSendErr")
            return

        #安全センサー
        stop_request = self.SafeSensor()
        
        #走行制御
        self.Drive.Exe(tg,stop_request)

        #エラーリセット
        self.RestErr(flgErrReset)

        # #CANパケットの更新
        ABH3_Can.ApiPacketReload()
        
        return

    def CtrlEnd(self):
        ABH3_Can.CanEnd()
 