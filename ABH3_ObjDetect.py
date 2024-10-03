

import cv2
import numpy as np
from math import sqrt
import ABH3_Camera

cm_w = ABH3_Camera.FRAME_W
cm_h = ABH3_Camera.FRAME_H
cm_S = cm_w * cm_h

#矢印の色範囲指定(範囲は色相Hが0~180度,彩度Sと明度Vが0~255)
arrowColor_H_Max = 105
arrowColor_H_Min = 60
arrowColor_S_Max = 245
arrowColor_S_Min = 20
arrowColor_V_Max = 245
arrowColor_V_Min = 20

class DetectedTarget:
    """AIにより検出した物体のサイズや適合率を正規化するためのデータクラス
    """
    def __init__(self,left=0,top=0,right=0,bottom=0,confidence=0,class_number=0):
        self.left = int(left)
        self.top = int(top)
        self.right = int(right)
        self.bottom = int(bottom)
        self.confidence =confidence
        self.class_number = int(class_number)

        self.center_x = int((self.right + self.left)/2)
        self.center_y = int((self.bottom + self.top)/2)
        self.width = self.right - self.left
        self.height = self.bottom -self.top
        self.area = self.width *self.height
        self.diagonal = sqrt(self.width*self.width + self.height*self.height)

class ClsTarget:
    """検出した物体用のデータクラス
    """
    dt = DetectedTarget()
    t_detect :bool  = False #検出状態 {T:検出}{F:未検出}
    t_img :np.ndarray = np.empty(0)  #ターゲットイメージ
    t_ArrowDir: str = "" #矢印方向{"":方向の未検出}

    rate_x: float  = 0.0 #左右位置 (左:-1 ~ 右:1)
    rate_y: float = 0.0 #上下位置 (下:-1 〜 上:1)
    rate_x_abs: float = 0.0 #中央からの左右距離 (0 ~ 1)
    rate_y_abs: float = 0.0 #中央からの上下距離 (0~1)

    distance = 0 #距離 (ターゲットの面積を利用した距離計算結果) 

    def __init__(self,dt:DetectedTarget=DetectedTarget() ,img=np.empty(0) ) -> None:
        self.dt = dt
        self.t_img = img
        self.rate_x  = (dt.center_x/cm_w -0.5) *2 #左右位置 (左:-1 ~ 右:1)
        self.rate_x_abs =  abs(self.rate_x)
        self.rate_y = (-dt.center_y /cm_h +0.5) *2 #上下位置 (下:-1 〜 上:1)
        self.rate_y_abs =  abs(self.rate_y)
        if(self.dt.diagonal > 1 ):
            self.distance = ABH3_Camera.DISTANCE_COEF / self.dt.diagonal  #距離 (ターゲットの面積を利用した距離計算結果) 
        else:
            self.distance = 999 #距離


#物体のleft, top, right, bottomを出力
def _getBoundingBox(result):
    """
        yolov5の推定結果を
        正規化しリスト化
    """
    data = []
    ndresult = result.xyxy[0]
    for v in ndresult:
        #v:xmin,ymin,xmax,ymax,confidence,class,name
        unit = DetectedTarget(left=int(v[0]),
                            top=int(v[1]),
                            right=int(v[2]),
                            bottom = int(v[3]),
                            confidence = float(v[4]),
                            class_number = int(v[5]))
        data.append(unit)
    return data

def _getBoxArro(data,img_org)->ClsTarget:
    """
        目的の矢印を取得する
    """
    imgAreaMax = 0
    imgAtMaxSize = ClsTarget()
    if len(data) == 0:
        return  ClsTarget()
    
    img_HSV = cv2.cvtColor(img_org, cv2.COLOR_BGR2HSV)
    img_HSV = cv2.medianBlur(img_HSV,5)
    cm_DitectMinSize = cm_S *0.25/ 100  #最小検出サイズ 

    dt:DetectedTarget
    for dt in data: 
        
        #選別:適合率が小さい場合スキップ
        if dt.confidence < 0.2 :
            continue
        #選別:サイズが小さい場合スキップ
        if(dt.area < cm_DitectMinSize ):
            continue

        #ステータス準備 矢印部分を取り出す
        img_t = img_HSV[dt.top:dt.bottom ,dt.left:dt.right]
        #縁を少し切り取る
        trm_w = int(dt.width * 0.2)
        trm_h = int(dt.height * 0.2)
        img_t = img_t[trm_h:dt.height-trm_h,trm_w:dt.width-trm_w]
        #1次化
        img_H,img_S,img_V = cv2.split(img_t)   
        img_trm_frat_H = np.array(img_H).flatten()
        img_trm_frat_S = np.array(img_S).flatten()    
        img_trm_frat_V = np.array(img_V).flatten()  
        img_len_Law = len(img_trm_frat_H)
        #色相による絞り込み
        area = (img_trm_frat_H > arrowColor_H_Min)&(img_trm_frat_H < arrowColor_H_Max)
        img_trm_frat_S = img_trm_frat_S[area]
        img_trm_frat_V = img_trm_frat_V[area]
        #彩度による絞り込み
        area = (img_trm_frat_S > arrowColor_S_Min)&(img_trm_frat_S < arrowColor_S_Max)
        img_trm_frat_V = img_trm_frat_V[area]
        #明度による絞り込み
        area = (img_trm_frat_V > arrowColor_V_Min)&(img_trm_frat_V < arrowColor_V_Max)

        #矢印色の割合が少ない場合無効
        if(len(area) < img_len_Law * 0.125): 
            continue

        #検出画像の取り出し
        targetUnit = ClsTarget(dt,img_org[dt.top:dt.bottom ,dt.left:dt.right])

        ##優先する矢印に更新する ---
        if imgAreaMax > 0 : 
            imgAtMaxXrate = imgAtMaxSize.rate_x
            targetXrate = targetUnit.rate_x
            imgAtMaxXrate_abs = abs(imgAtMaxXrate) 
            targetXrate_abs = abs(targetXrate) 
            outRangeXrate = 0.45     #設定値外は大きさにかかわらず中央に近い方を優先
            if (imgAreaMax*0.1 < dt.area ):
                if     (                        (imgAtMaxXrate_abs >= outRangeXrate )and( targetXrate_abs < outRangeXrate )) \
                    or ((imgAreaMax < dt.area )and(imgAtMaxXrate_abs >= outRangeXrate )and( targetXrate_abs >= outRangeXrate )) \
                    or ((imgAreaMax < dt.area )and(imgAtMaxXrate_abs < outRangeXrate )and( targetXrate_abs < outRangeXrate )) :
                    imgAreaMax = dt.area 
                    imgAtMaxSize = targetUnit
        else:
            imgAreaMax = dt.area 
            imgAtMaxSize = targetUnit
  
    if imgAreaMax > 0 :
        ImgUnit =  imgAtMaxSize
        ImgUnit.t_detect = True
        
        return ImgUnit
    else: #未検出
        ImgUnit = ClsTarget()
        ImgUnit.t_detect = False
        return ImgUnit


def _ImagLineDetect(objTrget:ClsTarget):
    """
        矢印の方向を検出する
    """
    #img:[高さ,幅,色]
    img = objTrget.t_img.copy() 
    #ブラーによるノイズ除去と白黒化
    img = cv2.GaussianBlur(img,(9, 9),3)
    img  ,img_gray= _ImageColorMask(img)
    img_gray = cv2.medianBlur(img_gray,5)
    #輪郭の検出
    contours, hierarchy = cv2.findContours(img_gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) > 0 :
        #検出した輪郭の中で最大の輪郭を取り出す
        cnt = max(contours, key=lambda x: cv2.contourArea(x))
        #輪郭の周囲の長さを計算
        arclen = cv2.arcLength(cnt, True)
        #余分な輪郭点を削除(輪郭を少ない点で近似する)
        contour = cv2.approxPolyDP(cnt, epsilon=0.025 * arclen, closed=True)
        #輪郭点7個が矢印
        if len(contour) == 7:        
            # 重心の計算
            m = cv2.moments(contour)
            cx,cy= m['m10']/m['m00'] , m['m01']/m['m00']
            # 重心座標を四捨五入
            cx, cy = round(cx), round(cy)

            #矢印の方向を検出
            dir = {"up":0,"dw":0,"r":0,"l":0}
            for point in contour:
                #輪郭点の位置と重心を比較しカウント
                px = point[0][0]
                py = point[0][1]
                if(cx < px):
                    dir['r'] += 1
                else:
                    dir['l'] += 1

                if(cy < py):
                    dir['dw'] += 1
                else:
                    dir['up'] += 1
            
            #輪郭点のカウントから矢印の方向をセット
            if dir['r'] == 5 and dir['l'] == 2:
                dir_result ='r'
            elif dir['l'] == 5 and dir['r'] == 2:
                dir_result ='l'
            elif dir['dw'] == 5 and dir['up'] == 2:
                dir_result ='dw'
            elif dir['up'] == 5 and dir['dw'] == 2:
                dir_result ='up'
            else:#方向未検出
                dir_result =''
        else:#サイズが小さい
            dir_result =''
    else:#輪郭が検出できない
        dir_result =''
        
    objTrget.t_ArrowDir = dir_result   
    return img

def _ImageColorMask(img):
    """
        目的の色以外をマスクする
    """
    img_target = img

    # マスク作成用の画像をHSVに変換
    img_HSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    #色を抽出(Opencvは色相Hが180度,彩度S明度Vが255)
    hsv_min = np.array([(arrowColor_H_Min),(arrowColor_S_Min),(arrowColor_V_Min)])
    hsv_max = np.array([(arrowColor_H_Max),(arrowColor_S_Max),(arrowColor_V_Max)])

    #画像の2値化
    hsv_mask = cv2.inRange(img_HSV,hsv_min,hsv_max)

    ##---画像のマスク（合成）---
    img_masked = cv2.bitwise_and(img_target,img_target, mask = hsv_mask)

    return img_masked,hsv_mask



def DetectPanel(img,results) -> ClsTarget:
    """
        yolov5の推定結果をもとに対象となる矢印とその向きを求める
    """

    #検出結果をリスト化
    results_List = _getBoundingBox(results)
    # #色やサイズから検出対象を絞る
    objTrget = _getBoxArro(results_List,img)

    #矢印方向検出---
    if objTrget.t_detect == True :
        _ImagLineDetect(objTrget)

    return objTrget