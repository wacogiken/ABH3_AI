import cv2
#フレーム幅(物体検出に使う画像サイズ)
FRAME_W = 1280 
#フレーム高さ(物体検出に使う画像サイズ)
FRAME_H = 720 
#カメラで検出した矢印を四角で囲んだ際の対角線から距離を求める係数 
#実測して設定する必要あり "DISTANCE_COEF = 対角線[pixel] × 距離[m]"
DISTANCE_COEF = 374 

class Camera:
    #カメラの設定


    def __init__(self) -> None:

        self.cm = cv2.VideoCapture(0)                # カメラCh.(ここでは0)を指定
        self.cm.set(cv2.CAP_PROP_FPS,60)             #フレームレート    
        self.cm.set(cv2.CAP_PROP_FRAME_WIDTH,1920)   #フレームの幅(撮影サイズ) 1280x720[(1920, 1080),640x360
        self.cm.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)  #フレームの高さ(撮影サイズ)  ,

        if self.cm.isOpened() == False:
            print("NG:カメラの接続が確認できません,ソフトを終了してください")
            while(1):
                pass


    def read (self):
        ret,frame = self.cm.read()   #frame=[高さ,幅]
        frame = cv2.resize(frame,(FRAME_W,FRAME_H),cv2.INTER_LINEAR)
        return frame

