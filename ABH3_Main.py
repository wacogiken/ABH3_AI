print("Import")

import cv2
import torch
import copy
from ABH3_ObjDetect import DetectPanel
from ABH3_Ctrl import CtrlAGV
from ABH3_Camera import Camera
import ABH3_Can
import time
tm_start = time.time()

#デバイス選択(GPUorCPU)
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print( "device:" + str(device))
print("ReadModel")
model = torch.hub.load('yolov5', 'custom', path='last', source='local',device =device)
camera = Camera()
ctrl_agv = CtrlAGV()
print("---StartAGV---")

while True:
    
    #---キー入力---
    detectKey = cv2.waitKey(5) &0xff
    if detectKey  == ord("q"):#処理の終了
        print("--- Exit ---")    
        ctrl_agv.CtrlEnd()
        break
    if detectKey  == ord("r"):#エラーリセット
        flg_err_reset = True
        print("ABH3ErrorReset")
    else:
        flg_err_reset = False    


    #---物体検出によるAGV制御---
    #カメラから画像を取得
    frame = camera.read()
    #yolo物体検出
    model_results = model(frame)
    #矢印検出
    trget_obj = DetectPanel(frame,model_results)
    #AGV制御
    ctrl_agv.Exe(trget_obj,flg_err_reset)


    #---画面表示---
    img = copy.copy(frame)
    #検出対象を四角で囲む
    if trget_obj.t_detect == True :
        img = cv2.rectangle(img,(int(trget_obj.dt.left),int(trget_obj.dt.top)), (int(trget_obj.dt.right), int(trget_obj.dt.bottom))
                            , (0,255,0), 3)

    #メインウィンドウにテキスト表示
    textFScale = 0.8                #文字サイズ
    textFont = cv2.FONT_HERSHEY_DUPLEX #フォント #cv2.FONT_HERSHEY_TRIPLEX #cv2.FONT_HERSHEY_DUPLEX #cv2.FONT_HERSHEY_SIMPLEX 
    textThick:int = 1               #文字太さ
    textLineSpace = 32              #行間
    #色指定 (青,緑,赤) 範囲は0~255
    textColor = (50,200,50)         
    textColor_Arm = (0,200,200)     
    textColor_Err = (0,0,200)     
    textBackColor = (10,10,10)    
    
    text0 = "key:Func = {q:Exit},{r:ErrReset}"
    tm_start = time.time()
    cv2.putText(img,text0,(5,textLineSpace),textFont,fontScale=textFScale,thickness=textThick+1,color = textBackColor)
    cv2.putText(img,text0,(5,textLineSpace),textFont,fontScale=textFScale,thickness=textThick,color =textColor)

    text0 = "CAN="+str(ABH3_Can.flgSt_RxSuccess)+" ,Battery="+'{:.1f}'.format(ABH3_Can.dctDataField['CntrlVol'])+"[V]"+" ,Cycle:"+'{:.2f}'.format(time.time() - tm_start )+"[sec]"
    tm_start = time.time()
    cv2.putText(img,text0,(5,textLineSpace*2),textFont,fontScale=textFScale,thickness=textThick+1,color = textBackColor)
    cv2.putText(img,text0,(5,textLineSpace*2),textFont,fontScale=textFScale,thickness=textThick,color =textColor)
    
    text0 ="Trget_X="+'{:.2f}'.format(trget_obj.rate_x)+" ,Distance="+'{:.2f}'.format(trget_obj.distance)
    cv2.putText(img,text0,(5,textLineSpace*3),textFont,fontScale=textFScale,thickness=textThick+1,color = textBackColor)
    cv2.putText(img,text0,(5,textLineSpace*3),textFont,fontScale=textFScale,thickness=textThick,color =textColor)
        
    text0 = "Mode="+str(ctrl_agv.Drive.move_doc) 
    cv2.putText(img,text0,(5,textLineSpace*4),textFont,fontScale=textFScale,thickness=textThick+1,color = textBackColor)
    cv2.putText(img,text0,(5,textLineSpace*4),textFont,fontScale=textFScale,thickness=textThick,color =textColor)

    text0 = "Y{"+ str(ctrl_agv.Drive.move_doc_y) +"}   X{"+str(ctrl_agv.Drive.move_doc_x)+"}"  
    cv2.putText(img,text0,(5,textLineSpace*5),textFont,fontScale=textFScale,thickness=textThick+1,color = textBackColor)
    cv2.putText(img,text0,(5,textLineSpace*5),textFont,fontScale=textFScale,thickness=textThick,color =textColor)

    if len(ABH3_Can.dctDataField["ArmFlg"]) > 0:
        text0 = "Arm="+str(ABH3_Can.dctDataField["ArmFlg"] )
        cv2.putText(img,text0,(5,textLineSpace*6),textFont,fontScale=textFScale,thickness=textThick+1,color = textBackColor)
        cv2.putText(img,text0,(5,textLineSpace*6),textFont,fontScale=textFScale,thickness=textThick,color =textColor_Arm)
    if len(ABH3_Can.dctDataField["ErrFlg"]) > 0:
        text0 = "Err="+str(ABH3_Can.dctDataField["ErrFlg"] )
        cv2.putText(img,text0,(5,textLineSpace*7),textFont,fontScale=textFScale,thickness=textThick+1,color = textBackColor)
        cv2.putText(img,text0,(5,textLineSpace*7),textFont,fontScale=textFScale,thickness=textThick,color =textColor_Err)
    

    #画面に出力
    #小型モニターサイズ---
    img = cv2.resize(img,dsize=(1024,600))
    cv2.imshow("yolov5",img)


    