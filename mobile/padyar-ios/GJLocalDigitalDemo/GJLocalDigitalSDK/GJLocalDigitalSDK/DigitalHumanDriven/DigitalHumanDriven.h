//
//  DigitalHumanDriven.h
//  Digital
//
//  Created by cunzhi on 2023/11/9.
//

#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#import <opencv2/opencv.hpp>
#import <opencv2/imgproc/types_c.h>
#import <AVFoundation/AVFoundation.h>
#import "DigitalConfigModel.h"
#import "GJLGCDTimer.h"
@interface DigitalHumanDriven : NSObject

+ (instancetype)manager;
@property (nonatomic, assign) NSInteger metal_type;
//0 透明 1有背景
@property (nonatomic, assign) NSInteger back_type;
@property (nonatomic, assign) int wavframe;
@property (nonatomic, strong) DigitalConfigModel * configModel;
//@property (nonatomic, assign) NSInteger width;
//@property (nonatomic, assign) NSInteger height;

@property (nonatomic, assign) BOOL isStartSuscess;

//客户端创建的会话SessionId
@property (nonatomic, strong) NSString *chatSessionId;

//控制并发的SessionId
@property (nonatomic, strong)NSString *signSessionId;
//是否结束
@property (nonatomic, assign) BOOL isStop;

@property (nonatomic, assign)NSInteger need_png;
//@property (nonatomic, assign) int mat_type;
//@property (nonatomic, assign)BOOL isStop;

@property (nonatomic, strong)NSString * appId;

@property (nonatomic, strong)NSString * appSign;

@property (nonatomic, strong)NSString * conversationId;
//查询第一帧音频是否准备好
@property (nonatomic, strong) GJLGCDTimer *audioReadyTimer;
//查询第一帧音频是否准备好的线程
@property (nonatomic, strong) dispatch_queue_t audio_ready_timer_queue;
//音频播放的线程
@property (nonatomic, strong) dispatch_queue_t playAuidoQueue;

@property (nonatomic, assign) int isAudioReady;

@property (nonatomic, assign) int audioIndex;

@property (nonatomic, assign) uint64_t sessid;

@property (nonatomic, copy) void (^imageBlock)(UIImage *image);
@property (nonatomic, copy) void (^pixerBlock)(CVPixelBufferRef cvPixelBuffer);
@property (nonatomic, copy) void (^uint8Block)(UInt8*mat_uint8,UInt8*maskMat_uint8 ,UInt8*bfgMat_uint8,UInt8*bbgMat_unit8,int width ,int height);
@property (nonatomic, copy) void (^matBlock)(cv::Mat mat,cv::Mat maskMat,cv::Mat bfgMat,cv::Mat bbgMat);
//非绿幕
@property (nonatomic, copy) void (^uint8Block2)(UInt8*mat_uint8,int width ,int height);
@property (nonatomic, copy) void (^matBlock2)(cv::Mat mat);
/*
* pcm是否准备好
*/
@property (nonatomic, copy)void (^pcmReadyBlock)(void);
/*
* 帧渲染计算统计
* @param resultCode 是否正常返回帧数据, <0 则说明帧数据异常
* @param isLip      是否计算唇形
* @param useTime    帧计算消耗的时间
*/
@property (nonatomic, copy)void (^onRenderReportBlock)(int resultCode, BOOL isLip, float useTime);


@property (nonatomic, strong)AVURLAsset *audioAsset;

- (int)initWenetWithPath:(NSString*)path;
- (int)initUnetPcmWithParamPath:(NSString*)paramPath binPath:(NSString*)binPath binPath2:(NSString*)binPath2;
- (void)maskrstPcmWithPath:(NSString *)imagePath index:(int)index array:(NSArray *)array mskPath:(NSString*)maskPath bfgPath:(NSString*)bfgPath bbgPath:(NSString*)bbgPath ;
- (void)simprstPcmWithPath:(NSString *)imagePath index:(int)index array:(NSArray *)array;

//初始化音频mfcc和推理模型
- (int)initGJStream;
//初始化session
-(void)newSession;
//结束session
-(void)finishSession;
//finishSession 结束后调用续上continueSession
-(void)continueSession;

- (void)free;

-(void)wavPCM:(uint8_t*)pcm size:(int)size;

/*
*生成一个新的问答会话id
*/
- (NSString *)getNewChatSessionId;
@end

