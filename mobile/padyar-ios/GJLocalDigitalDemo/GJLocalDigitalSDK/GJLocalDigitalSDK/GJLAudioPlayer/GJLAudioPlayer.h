//
//  GJLAudioPlayer.h
//  GJLocalDigitalSDK
//
//  Created by guiji on 2024/5/21.
//

#import <Foundation/Foundation.h>
#import <AVFoundation/AVFoundation.h>

@interface GJLAudioPlayer : NSObject
//播放状态回调
@property (nonatomic, copy) void (^playStatus)(NSInteger status);
////播放状态回调
@property (nonatomic, copy) void (^playFailed)(void);
//播放结束回调
@property (nonatomic, copy) void (^playEnd)(void);

//推流结束回调
@property (nonatomic, copy) void (^pushPcmEnd)(void);
//播放进度回调
@property (nonatomic, copy) void (^playProgress)(float current,float total);
@property (nonatomic, copy) void (^audioPCMDataCallBack)(NSData * data,NSInteger level); // 音频采集数据回调。
@property (nonatomic, copy) void (^sampleBufferOutputCallBack)(CMSampleBufferRef sample,NSInteger type); // 音频采集数据回调。
@property (nonatomic, assign) BOOL isPlaying;
@property (nonatomic, strong) NSMutableData *pcmDataCache; // 解码数据缓冲区。
// 是否允许讲话
@property (nonatomic, assign)BOOL isMute;

// 是否允许录音
@property (nonatomic, assign)BOOL isEnableRecord;

@property (nonatomic, assign)float volume;

@property (nonatomic, assign) BOOL isPlayMutePcm;


@property (nonatomic, assign) BOOL isVoiceProcessingIO;
/*
 isFadeInOut YES 启用音量淡入淡出 NO 关闭音量淡入淡出  默认为YES
 */
@property (nonatomic, assign) BOOL isFadeInOut;

+ (GJLAudioPlayer*)manager;
//本地音频 要求音频格式 wav 通道1 采样率16000 深度16
- (void)speakWavPath:(NSString *)wavPath;
- (void)startPlaying; // 开始渲染。
- (void)stopPlaying:(void (^)( BOOL isSuccess))success;  // 结束渲染。

-(void)pause;
-(void)toFree;
-(void)pauseRunning:(BOOL)pause; //暂停采集;

-(void)toStartRunning;
-(void)wavPCM:(uint8_t*)pcm size:(int)size;

-(void)toWavPcmData:(NSData*)audioData;
-(void)toStopRunning;
/*
*dataLength 音频buffer的长度
*isFinish 是否一句话结束或者整段话结束
*/
-(void)toBufferLength:(int)dataLength isFinish:(BOOL)isFinish;

-(void)clearAudioBuffer;



-(void)toMuteRecord:(BOOL)isMute;

-(void)toEnableRecord:(BOOL)isEnable;


@end


