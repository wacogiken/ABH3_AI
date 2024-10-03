"""
#CANの実行
ABH3_CAN.CanExe()
#CANの停止
ABH3_CAN.CanEnd():

#CANパケット送信内容の更新
ABH3_CAN.ApiPacketReload()

#AY軸指令セット
ABH3_CAN.ApiCmdAY_Set(cmdAY):  
#BX軸指令セット
ABH3_CAN.ApiCmdBX_Set(cmdBX):

#辞書型のdctCtrlFlgに登録されているフラグを指定し送信データに上書き
ABH3_CAN.ApiCtrlFlg_Set(cmdCtrlFlg:str=[]):
#辞書型のdctCtrlFlgに登録されているフラグを一つ指定し送信データにセットする
ABH3_CAN.ApiCtrlFlg_SetBit(cmdCtrlBit:str):    
辞書型のdctCtrlFlgに登録されているフラグを一つ指定し送信データからクリアする
ABH3_CAN.ApiCtrlFlg_ClaBit(cmdCtrlBit:str):

#内部データ AY軸の選択番号をセットする
ABH3_CAN.ApiCtrlFlg_SetSlectNoAY(selectNo:int):
#内部データ BX軸の選択番号をセットする
ABH3_CAN.ApiCtrlFlg_SetSlectNoBX(selectNo:int):

"""



from ctypes.wintypes import FLOAT, SHORT, UINT
from glob import glob
from os import execve
from pickletools import uint8
import struct

import can
import time
import threading

#CANID
canID_Host = 0x02
canID_ABH3 = 0x05
canID_ABH3_GNo = 0
#CANインターフェース
bus = can.ThreadSafeBus(channel='can0',interface='socketcan')

#スレッド用フラグ
trdExeFlg = False

#Gin
StatVC_AY_Gain = 0.2   #速度制御:0.2,電流制御0.01
StatVC_BX_Gain = 0.2   #速度制御:0.2,電流制御0.01

#操作用変数
apiPacketPn = 0     #更新のたびにカウントアップ
apiPacketPn_Old = 0     
apiCmd_AY:float = 0
apiCmd_BX:float = 0
apiCmd_CtrlFlg:str = []


flgSt_RxSuccess = False #受信成功状態 {T:成功}

#受信データ全体(辞書のキー名:値)
#ABH3_CAN.dctDataField["FbkAY"] のようにして取得
dctDataField = {
     'FbkAY'            :0  #A/Y帰還
    ,'FbkBX'            :0  #B\X帰還
    ,'CtrlFlg'          :""  #制御フラグ,dctCtrlFlgのkey名のリストが入る
    ,'ErrFlg'           :""  #異常フラグ,dctArmFlgkey名のリストが入る
    ,'ArmFlg'           :""  #警告フラグ,dctArmFlgkey名のリストが入る
    ,'IOFlg'            :0  #IOフラグ
    ,'InputFlg'         :0  #入力フラグ
    ,'VelCmdAY'         :0  #A/Y速度指令
    ,'VelCmdBX'         :0  #B/X速度指令
    ,'VelFbkAY'         :0  #A/Y速度帰還
    ,'VelFbkBX'         :0  #B/X速度帰還
    ,'CurCmdAY'         :0  #A/Y電流指令
    ,'CurCmdBX'         :0  #B/X電流指令
    ,'LoadA'            :0  #A負荷率
    ,'LoadB'            :0  #B負荷率
    ,'PosA'             :0  #Aパルス積算
    ,'PosB'             :0  #Bパルス積算
    ,'AnalogIn0'        :0  #アナログ入力0
    ,'AnalogIn1'        :0  #アナログ入力1
    ,'MainVolt'         :0  #主電源電圧
    ,'CntrlVol'         :0  #制御電源電圧
    ,'Moniter0'         :0  #モニター0データ
    ,'Moniter1'         :0  #モニター1データ
}

##制御フラグ (辞書のキー名:ビット位置)
#svOnAYビットをセットしたいときは ABH3_CAN.ApiCtrlFlg_SetBit('svOnAY')
#svOnAYビットをクリアしたいときは ABH3_CAN.piCtrlFlg_ClaBit('svOnAY')
CtrlFlg_BAdd:int = 32
dctCtrlFlg = {
    'svOnAY'      : -CtrlFlg_BAdd + 32   #サーボON
    ,'stAY'        : -CtrlFlg_BAdd + 33   #スタート
    ,'invAY'       : -CtrlFlg_BAdd + 34   #指令極性
    ,'addStAY'     : -CtrlFlg_BAdd + 35   #補正加算
    ,'selDataAY0'  : -CtrlFlg_BAdd + 36   #選択データ0
    ,'selDataAY1'  : -CtrlFlg_BAdd + 37   #選択データ1
    ,'selDataAY2'  : -CtrlFlg_BAdd + 38   #選択データ2
    ,'addInvAY'    : -CtrlFlg_BAdd + 39   #補正極性
    ,'svOnBX'      : -CtrlFlg_BAdd + 40   #サーボON
    ,'stBX'        : -CtrlFlg_BAdd + 41   #スタート
    ,'invBX'       : -CtrlFlg_BAdd + 42   #指令極性
    ,'addStBX'     : -CtrlFlg_BAdd + 43   #補正加算
    ,'selDataBX0'   : -CtrlFlg_BAdd + 44   #選択データ0
    ,'selDataBX1'   : -CtrlFlg_BAdd + 45   #選択データ1
    ,'selDataBX2'   : -CtrlFlg_BAdd + 46   #選択データ2
    ,'addInvBX'    : -CtrlFlg_BAdd + 47   #補正極性
    ,'modeTrqAY'   : -CtrlFlg_BAdd + 48   #制御モード 速度:0,トルク:1      
    ,'modeTrqBX '  : -CtrlFlg_BAdd + 49   #制御モード 速度:0,トルク:1     
    ,'modeMasterSlave'   : -CtrlFlg_BAdd + 50 #マスタースレーブ　マスタースレーブ有効:1
    ,'brakeRelease' : -CtrlFlg_BAdd + 51 #ブレーキ開放
    ,'posClearA'   : -CtrlFlg_BAdd + 52 #位置積算クリア
    ,'posClearB'   : -CtrlFlg_BAdd + 53 #位置積算クリア
    ,'errReset'    : -CtrlFlg_BAdd + 54  #エラーリセット

    ,'ReadyAY': -CtrlFlg_BAdd + 57  #A/Y軸レディ
    ,'BusyAY': -CtrlFlg_BAdd + 58  #A/Y軸ビジー
    ,'ReadyBX': -CtrlFlg_BAdd + 59  #B/X軸レディ
    ,'BusyBX': -CtrlFlg_BAdd + 60  #B/X軸ビジー
    ,'ModelDrive': -CtrlFlg_BAdd + 61  #制御モデル モータ軸:0,走行軸:1
    ,'BrakeRelease': -CtrlFlg_BAdd + 62  #ブレーキ解除
    ,'ErrOcc': -CtrlFlg_BAdd + 63  #エラー発生 いずれかの異常が発生:1,異常なし:0
}

#異常警告フラグ (辞書のキー名:ビット位置)
ArmFlg_BAdd:int = 32
dctArmFlg = {
    'MLockA'         :-ArmFlg_BAdd + 32   #A軸メカロック
    ,'MLockB'        :-ArmFlg_BAdd + 33   #B軸メカロック
    ,'DrHeat'        :-ArmFlg_BAdd + 34   #ドライバ加熱
    ,'BrkErr'        :-ArmFlg_BAdd + 35   #ブレーキ異常
    ,'ResErrA'       :-ArmFlg_BAdd + 36   #A軸レゾルバ
    ,'ResErrB'       :-ArmFlg_BAdd + 37   #B軸レゾルバ
    ,'CurOverA'      :-ArmFlg_BAdd + 38   #A軸過電流
    ,'CurOverB'      :-ArmFlg_BAdd + 39   #B軸過電流
    ,'CtrlVoltLow'   :-ArmFlg_BAdd + 40   #制御電源 電圧低下
    ,'ParaErr'       :-ArmFlg_BAdd + 41   #パラメータ
    ,'PduErrA'       :-ArmFlg_BAdd + 42   #A軸PDU
    ,'PduErrB'       :-ArmFlg_BAdd + 43   #B軸PDU
    ,'EThermalA'     :-ArmFlg_BAdd + 44   #A軸電子サーマル
    ,'EThermalB'     :-ArmFlg_BAdd + 45   #B軸電子サーマル
    ,'MainVoltLow'   :-ArmFlg_BAdd + 46   #主電源電圧低下
    ,'SorceVoltHi'   :-ArmFlg_BAdd + 47   #制御電源または主電源の過電圧
    ,'SpeedOverA'    :-ArmFlg_BAdd + 48   #A軸過速度
    ,'SpeedOverB'    :-ArmFlg_BAdd + 49   #B軸過速度
    ,'SpeedLimitA'   :-ArmFlg_BAdd + 50   #A軸速度リミット
    ,'SpeedLimitB'   :-ArmFlg_BAdd + 51   #B軸速度リミット
    ,'CurLimitA'     :-ArmFlg_BAdd + 52   #A軸電流リミット
    ,'CurLimitB'     :-ArmFlg_BAdd + 53   #B軸電流リミット
    ,'CanTimeOut'    :-ArmFlg_BAdd + 54   #CAN通信タイムアウト
    ,'CanTrafficOver':-ArmFlg_BAdd + 55   #CAN通信トラフィック過大

}
##===受信関係===
#フラグ解釈===
def interMsg_CtrlFlg(data):
    flgList = []
    for key in dctCtrlFlg:
        if (data & (1 << dctCtrlFlg[key])) != 0 :
            flgList.append(key)
    return flgList
def interMsg_ArmFlg(data):
    flgList = []
    for key in dctArmFlg:
        if (data & (1 << dctArmFlg[key])) != 0 :
            flgList.append(key)
    return flgList

#受信メッセージ解釈===
def interMsg(msg:can.Message):

    id = msg.arbitration_id
    data = msg.data
    id_PduFormt = (id & 0x00FF0000) >> 16
    id_SendFrom = (id & 0x000000FF)     #受信時はABH3のIDが入る
    id_Trget = (id & 0x0000FF00) >> 8   #ブロードキャストグループ番号などが入る

    if id_SendFrom != canID_ABH3:
        return
    
    if len(data) < 8:
        return
    #---パケット解釈---
    if id_PduFormt == 0xEF : 
        #シングルパケット受信
        values = struct.unpack('<h',data[0:2])
        dctDataField['FbkAY'] = values[0] *StatVC_AY_Gain
        values = struct.unpack('<h',data[2:4])
        dctDataField['FbkBX'] = values[0] *StatVC_BX_Gain
        values = struct.unpack('<L',(data[4:8]))
        dctDataField['CtrlFlg'] = interMsg_CtrlFlg(values[0])

    if (id_PduFormt == 0xFF)and(((id_Trget&0xF1)>>3) == canID_ABH3_GNo):
        #ブロードキャスト受信
        id_DNo = id_Trget& 0x07 
        
        if id_DNo == 0: #異常フラグ、警告フラグ
            values = struct.unpack('<L',(data[0:4]))
            dctDataField['ErrFlg'] = interMsg_ArmFlg(values[0])            
            values = struct.unpack('<L',(data[4:8]))
            dctDataField['ArmFlg'] = interMsg_ArmFlg(values[0])    
        elif id_DNo == 2 : #速度指令、速度帰還
            values = struct.unpack('<h',data[0:2])
            dctDataField['VelCmdAY'] = values[0] *0.2
            values = struct.unpack('<h',data[2:4])
            dctDataField['VelCmdBX'] = values[0] *0.2
            values = struct.unpack('<h',data[4:6])
            dctDataField['VelFbkAY'] = values[0] *0.2
            values = struct.unpack('<h',data[6:8])
            dctDataField['VelFbkBX'] = values[0] *0.2
        elif id_DNo == 3 : #電流指令、負荷率
            values = struct.unpack('<h',data[0:2])
            dctDataField['CurCmdAY'] = values[0] *0.01
            values = struct.unpack('<h',data[2:4])
            dctDataField['CurCmdBX'] = values[0] *0.01
            values = struct.unpack('<h',data[4:6])
            dctDataField['LoadA'] = values[0] * 1.0
            values = struct.unpack('<h',data[6:8])
            dctDataField['LoadB'] = values[0] * 1.0
        elif id_DNo == 4 : #パルス積算値
            values = struct.unpack('<l',(data[0:4]))
            dctDataField['PosA'] = values[0]               
            values = struct.unpack('<l',(data[4:8]))
            dctDataField['PosB'] = values[0]      

        elif id_DNo == 5 : #アナログ入力、電源電圧
            values = struct.unpack('<h',data[0:2])
            dctDataField['AnalogIn0'] = values[0] *0.01
            values = struct.unpack('<h',data[2:4])
            dctDataField['AnalogIn1'] = values[0] *0.01
            values = struct.unpack('<h',data[4:6])
            dctDataField['MainVolt'] = values[0] *0.1
            values = struct.unpack('<h',data[6:8])
            dctDataField['CntrlVol'] = values[0] *0.1

##=====送信関係=======
#制御フラグのセット
def SingleCmd_CtrlCmd(data):
    ctrlFlg:UINT = 0
    for unit in data:
        bitshift = dctCtrlFlg.get(unit)
        if bitshift != None:
            ctrlFlg |= 1 << bitshift
        else:
            print("CtrlCmd Err : "+str(unit))

    return ctrlFlg


def makMsg_SingleCmd(cmdAY,cmdBX,ctrlFlg:str = []):
    data = [0] *8

    #制御フラグ 
    ctrlFlg = SingleCmd_CtrlCmd(ctrlFlg)

    #単位変換---
    cmdAY16bit = int(cmdAY / StatVC_AY_Gain) 
    cmdBX16bit = int(cmdBX / StatVC_BX_Gain) 
    # cmdAY16bit = int(cmdAY / 0.01) #電流指令[%](-327.68~327.67[%])の単位変換
    # cmdBX16bit = int(cmdBX / 0.01) #電流指令[%]の単位変換

    #送信データセット---
    #CmdAY
    data[0] = cmdAY16bit & 0xFF 
    data[1] = (cmdAY16bit >> 8) & 0xFF
    #CmdBX
    data[2] = cmdBX16bit & 0xFF 
    data[3] = (cmdBX16bit >> 8) & 0xFF

    #制御フラグ
    data[4] = 0xFF & ctrlFlg
    data[5] = 0xFF & (ctrlFlg >> 8)
    data[6] = 0xFF & (ctrlFlg >> 16)
    data[7] = 0xFF & (ctrlFlg >> 24)

    #メッセージ作成
    sendId:UINT = (0xef << 16) | (canID_ABH3 << 8) | (canID_Host) 
    msg = can.Message(arbitration_id= sendId,is_extended_id=True
                    ,dlc=8,data=data)

    return msg


##========スレッド========
#thr_lock = threading.Lock() #スレッドロック .acquire()でロック,.release()で解除
def Thr_send():
    global apiPacketPn_Old
    apiCmd_AY_Temp = apiCmd_AY
    apiCmd_BX_Temp = apiCmd_BX
    apiCmd_CtrlFlg_Temp = apiCmd_CtrlFlg
    time.sleep(0.2) #最初の送信を少し待つ(トラフィック警告対策)
    while(apiPacketPn == apiPacketPn_Old):
        time.sleep(0.2) #最初の指令が来るまで待つ

    while trdExeFlg:
        
        if apiPacketPn != apiPacketPn_Old:
            apiCmd_AY_Temp = apiCmd_AY
            apiCmd_BX_Temp = apiCmd_BX
            apiCmd_CtrlFlg_Temp = apiCmd_CtrlFlg
            apiPacketPn_Old = apiPacketPn
        else:
            time.sleep(0.01)
            continue

        msg = makMsg_SingleCmd(apiCmd_AY_Temp,apiCmd_BX_Temp,apiCmd_CtrlFlg_Temp)
        try:
            bus.send(msg,timeout=0.5)
        except Exception as e:
            #print('sendErr:'+str(e))  
            pass 
        
        time.sleep(0.02)

def Thr_recv():
    global flgSt_RxSuccess
    while trdExeFlg:
        msg:can.Message = bus.recv(0.5)
        if msg is None:
            flgSt_RxSuccess = False
            pass
        else:
            flgSt_RxSuccess = True
            interMsg(msg)
 
        

#====外部からのセット===
def ApiCmdAY_Set(cmdAY):#速度の場合rpm,電流の場合%で指定
    """
        AY軸指令セット
        cmdAY:AY軸指令(速度の場合rpm,電流の場合%で指定)
    """
    global apiCmd_AY 
    apiCmd_AY = cmdAY

def ApiCmdBX_Set(cmdBX):#速度の場合rpm,電流の場合%で指定
    """
        BX軸指令セット
        cmdBY:BY軸指令(速度の場合rpm,電流の場合%で指定)
    """
    global apiCmd_BX 
    apiCmd_BX = cmdBX

def ApiCtrlFlg_Set(cmdCtrlFlg:str=[]):
    """
        辞書型のdctCtrlFlgに登録されているフラグを指定し送信データに上書き
        cmdCtrlFlg:辞書のキー名のリスト
    """
    global apiCmd_CtrlFlg #
    apiCmd_CtrlFlg = cmdCtrlFlg

def ApiCtrlFlg_SetBit(cmdCtrlBit:str):
    """
        辞書型のdctCtrlFlgに登録されているフラグを一つ指定し送信データにセットする
        cmdCtrlBit:辞書のキー名
    """
    global apiCmd_CtrlFlg 
    if cmdCtrlBit not in apiCmd_CtrlFlg:
        apiCmd_CtrlFlg.append(cmdCtrlBit)    

def ApiCtrlFlg_ClaBit(cmdCtrlBit:str):
    """
        辞書型のdctCtrlFlgに登録されているフラグを一つ指定し送信データからクリアする
        cmdCtrlBit:辞書のキー名
    """    
    global apiCmd_CtrlFlg 
    
    if cmdCtrlBit in apiCmd_CtrlFlg:
        apiCmd_CtrlFlg.remove(cmdCtrlBit)

def ApiCtrlFlg_SetSlectNoAY(selectNo:int):
    """
        内部データ AY軸の選択番号をセットする
        selectNo:選択番号
    """    
    global apiCmd_CtrlFlg 

    if selectNo & 0x01 :
        ApiCtrlFlg_SetBit('selDataAY0')
    else:
        ApiCtrlFlg_ClaBit('selDataAY0')

    if selectNo & 0x02 :
        ApiCtrlFlg_SetBit('selDataAY1')
    else:
        ApiCtrlFlg_ClaBit('selDataAY1')

    if selectNo & 0x04 :
        ApiCtrlFlg_SetBit('selDataAY2')
    else:
        ApiCtrlFlg_ClaBit('selDataAY2')

def ApiCtrlFlg_SetSlectNoBX(selectNo:int):
    """
        内部データ BY軸の選択番号をセットする
        selectNo:選択番号
    """ 
    global apiCmd_CtrlFlg 

    if selectNo & 0x01 :
        ApiCtrlFlg_SetBit('selDataBX0')
    else:
        ApiCtrlFlg_ClaBit('selDataBX0')

    if selectNo & 0x02 :
        ApiCtrlFlg_SetBit('selDataBX1')
    else:
        ApiCtrlFlg_ClaBit('selDataBX1')

    if selectNo & 0x04 :
        ApiCtrlFlg_SetBit('selDataBX2')
    else:
        ApiCtrlFlg_ClaBit('selDataBX2')


def ApiPacketReload():
    """
        送信データ確定後にコールすることで送信が開始される
    """
    global apiPacketPn
    apiPacketPn +=1

def ApiPacketIsSendDone():
    """
        送信完了状態を返す
        return:送信完了状態(T:送信完了)
    """
    return(apiPacketPn == apiPacketPn_Old)


thr_send_1 = threading.Thread(target=Thr_send)
thr_recv_1 = threading.Thread(target=Thr_recv)
def CanExe():
    global trdExeFlg
    global thr_send_1
    global thr_recv_1
    ##=====実行=====
    trdExeFlg = True
    thr_send_1.start()
    thr_recv_1.start()

#while True:
def CanEnd():
    global trdExeFlg
    global thr_send_1
    global thr_recv_1

    trdExeFlg = False
    thr_send_1.join()
    thr_recv_1.join()
    bus.shutdown()



