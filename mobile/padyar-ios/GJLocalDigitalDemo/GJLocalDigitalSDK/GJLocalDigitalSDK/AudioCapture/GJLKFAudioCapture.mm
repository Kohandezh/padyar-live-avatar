


#import "GJLKFAudioCapture.h"
#import <AVFoundation/AVFoundation.h>
#import <mach/mach_time.h>
#import <zlib.h>

#import <AudioToolbox/AudioToolbox.h>
//#import "BZQWebRTC.h"
#import "GJLGCDTimer.h"
#import "DigitalHumanDriven.h"
@interface GJLKFAudioCapture ()
@property (nonatomic, assign) AudioComponentInstance audioCaptureInstance; // 音频采集实例。

@property (nonatomic, strong, readwrite) GJLKFAudioConfig *config;
@property (nonatomic, strong) dispatch_queue_t captureQueue;
@property (nonatomic, assign) BOOL isError;


//@property (strong, nonatomic) BZQWebRTC *webrtc;
@property(nonatomic,strong) NSMutableData *bufferedVoiceData;


//@property (nonatomic, strong)NSLock * lock;

@property (nonatomic, assign) float volume;
@property (nonatomic, strong) GJLGCDTimer *curentTimer;
@property (nonatomic, strong) dispatch_queue_t curent_timer_queue;
@property (nonatomic, strong) GJLGCDTimer *stopTimer;
@property (nonatomic, strong) dispatch_queue_t stop_timer_queue;
@property (nonatomic, assign) BOOL shouldRecord;
@end

@implementation GJLKFAudioCapture

#pragma mark - Lifecycle
- (instancetype)initWithConfig:(GJLKFAudioConfig *)config {
    self = [super init];
    if (self) {
        _config = config;
        _captureQueue = dispatch_queue_create("com.KeyFrameKit.audioCapture", DISPATCH_QUEUE_SERIAL);
//        self.webrtc = [[BZQWebRTC alloc] initWithSampleRate:16000 nsMode:BZQNSModeAggressive];
        _curent_timer_queue = dispatch_queue_create("com.KeyFrameKit.curent_timer_queue", DISPATCH_QUEUE_SERIAL);
        
        _stop_timer_queue = dispatch_queue_create("com.KeyFrameKit.stop_timer_queue", DISPATCH_QUEUE_SERIAL);
       // [self setupAudioCaptureInstance:nil];
//        self.lock=[NSLock new];
        self.volume=0;

    }
    
    return self;
}

- (void)dealloc {
    // 清理音频采集实例。
   // [self toFree];
}
-(void)toFree
{
    __weak typeof(self) weakSelf = self;
    dispatch_barrier_async(_captureQueue, ^{
        if (weakSelf.audioCaptureInstance) {
            [weakSelf toMuteRecord:NO];
            if(weakSelf.isRunning)
            {
                AudioOutputUnitStop(weakSelf.audioCaptureInstance);
            }
            AudioComponentInstanceDispose(weakSelf.audioCaptureInstance);
            weakSelf.audioCaptureInstance = nil;
     
        }
       });
   
    self.isError=NO;
}
#pragma mark - Action
- (void)startRunning {

    if(!self.isRunning)
    {
        self.shouldRecord=YES;
        self.isRunning=YES;
    //    AudioOutputUnitStart(self.audioCaptureInstance);
        __weak typeof(self) weakSelf = self;
        dispatch_async(_captureQueue, ^{
            if (!weakSelf.audioCaptureInstance) {
                NSError *error = nil;
                // 第一次 startRunning 时创建音频采集实例。
                [weakSelf setupAudioCaptureInstance:&error];
                if (error) {
                    // 捕捉并回调创建音频实例时的错误。
                   // [weakSelf callBackError:error];
                    return;
                }
            }
//
//            [weakSelf setupEchoCancellation];
            // 开始采集。
           AudioOutputUnitStart(weakSelf.audioCaptureInstance);

        });
    }
  
}
- (void)setupEchoCancellation{
    UInt32 echoCancellation = 0;
    UInt32 size = sizeof(echoCancellation);
    OSStatus status =  AudioUnitSetProperty(self.audioCaptureInstance,
                                    kAUVoiceIOProperty_BypassVoiceProcessing,
                                            kAudioUnitScope_Global,
                                    0,
                                    &echoCancellation,
                                    size);
    NSLog(@"status:%d",status);
    
}
- (void)stopRunning {

    self.shouldRecord=NO;
    self.isRunning=NO;
    __weak typeof(self) weakSelf = self;
    dispatch_async(_captureQueue, ^{
        if (weakSelf.audioCaptureInstance) {
            // 停止采集。
            OSStatus stopStatus = AudioOutputUnitStop(weakSelf.audioCaptureInstance);
            
          
            NSLog(@"stopStatus:%d",stopStatus);
//            if (stopStatus != noErr) {
//                // 捕捉并回调停止采集时的错误。
//                [weakSelf callBackError:[NSError errorWithDomain:NSStringFromClass([GJLKFAudioCapture class]) code:stopStatus userInfo:nil]];
//            }
        }
    
    });
}

#pragma mark - Utility
- (void)setupAudioCaptureInstance:(NSError **)error {
    // 1、设置音频组件描述。


  
    
    AudioComponentDescription acd;
    acd.componentType = kAudioUnitType_Output;
    if([GJLAudioPlayer manager].isVoiceProcessingIO)
    {
        acd.componentSubType =kAudioUnitSubType_VoiceProcessingIO;
    }
    else
    {
        acd.componentSubType =kAudioUnitSubType_RemoteIO;
    }

    acd.componentManufacturer = kAudioUnitManufacturer_Apple;
    acd.componentFlags = 0;
    acd.componentFlagsMask = 0;

    // 2、查找符合指定描述的音频组件。
    AudioComponent component = AudioComponentFindNext(NULL, &acd);
    
    // 3、创建音频组件实例。
    OSStatus status = AudioComponentInstanceNew(component, &_audioCaptureInstance);
    if (status != noErr) {
        *error = [NSError errorWithDomain:NSStringFromClass(self.class) code:status userInfo:nil];
        return;
    }
        

    //默认启用录音功能

       if([GJLAudioPlayer manager].isEnableRecord)
       {
           UInt32 flagOne = 1;
           AudioUnitSetProperty(_audioCaptureInstance, kAudioOutputUnitProperty_EnableIO, kAudioUnitScope_Input, 1, &flagOne, sizeof(flagOne));
       }
  
    
    
  
        
//       [self toMuteRecord:![GJLAudioPlayer manager].isEnableRecord];

   

    
    UInt32 flag = 1;
    AudioUnitSetProperty(_audioCaptureInstance, kAudioOutputUnitProperty_EnableIO, kAudioUnitScope_Output, 0, &flag, sizeof(flag));
    
    
//    UInt32 enableAGC = 1; // 1 表示启用，0 表示禁用
//    status = AudioUnitSetProperty(_audioCaptureInstance,
//                                        kAUVoiceIOProperty_VoiceProcessingEnableAGC,
//                                        kAudioUnitScope_Global,
//                                        1,
//                                        &enableAGC,
//                                        sizeof(enableAGC));
//    
//    status = AudioUnitSetProperty(_audioCaptureInstance,
//                                        kAUVoiceIOProperty_VoiceProcessingEnableAGC,
//                                        kAudioUnitScope_Output,
//                                        0,
//                                        &enableAGC,
//                                        sizeof(enableAGC));
//      
    if (status != noErr) {
        // 处理错误
        NSLog(@"Error setting AGC: %ld", (long)status);
    }
//    
    
//    AudioUnitSetProperty(_audioCaptureInstance,kAUVoiceIOProperty_VoiceProcessingEnableAGC,kAudioUnitScope_Output,0,&flagOne,sizeof(flagOne));
    // 5、设置实例的属性：音频参数，如：数据格式、声道数、采样位深、采样率等。
    AudioStreamBasicDescription asbd = {0};
    asbd.mFormatID = kAudioFormatLinearPCM; // 原始数据为 PCM，采用声道交错格式。
    asbd.mFormatFlags = kAudioFormatFlagIsSignedInteger  | kAudioFormatFlagIsPacked | kAudioFormatFlagIsNonInterleaved;
    asbd.mChannelsPerFrame = (UInt32) self.config.channels; // 每帧的声道数
    asbd.mFramesPerPacket = 1; // 每个数据包帧数
    asbd.mBitsPerChannel = (UInt32) self.config.bitDepth; // 采样位深
    asbd.mBytesPerFrame = asbd.mChannelsPerFrame * asbd.mBitsPerChannel / 8; // 每帧字节数 (byte = bit / 8)
    asbd.mBytesPerPacket = asbd.mFramesPerPacket * asbd.mBytesPerFrame; // 每个包的字节数
    asbd.mSampleRate =self.config.sampleRate; // 采样率
    
//    AudioStreamBasicDescription playFormat =  asbd;
//    playFormat.mSampleRate =16000; // 采样率
    

    self.audioFormat = asbd;
    
//    if([GJLAudioPlayer manager].isEnableRecord)
//    {
        //设置录音的输出
          status = AudioUnitSetProperty(_audioCaptureInstance, kAudioUnitProperty_StreamFormat, kAudioUnitScope_Output, 1, &asbd, sizeof(asbd));
          if (status != noErr) {
              *error = [NSError errorWithDomain:NSStringFromClass(self.class) code:status userInfo:nil];
              return;
          }
//    }

    
        //设置播放的输入部分
        status = AudioUnitSetProperty(_audioCaptureInstance, kAudioUnitProperty_StreamFormat, kAudioUnitScope_Input, 0, &asbd, sizeof(asbd));
        if (status != noErr) {
            *error = [NSError errorWithDomain:NSStringFromClass(self.class) code:status userInfo:nil];
            return;
        }
    

//    UInt32 bypass = 1;
//    AudioUnitSetProperty(_audioCaptureInstance, kAudioUnitProperty_BypassEffect, kAudioUnitScope_Global, 0, &bypass, sizeof(bypass));
    



//    // 3. 启用即时启动模式
//    UInt32 instantStart = 1;
//    status = AudioUnitSetProperty(_audioCaptureInstance,
//                                  kAudioUnitProperty_RequestViewController,
//                                kAudioUnitScope_Global,
//                                0,
//                                &instantStart,
//                                sizeof(instantStart));
    

//    if([GJLAudioPlayer manager].isEnableRecord)
//    {
        // 录音 回调6、设置实例的属性：数据回调函数。
        AURenderCallbackStruct cb;
        cb.inputProcRefCon = (__bridge void *) self;
        cb.inputProc = recordingCallback;
        status = AudioUnitSetProperty(_audioCaptureInstance, kAudioOutputUnitProperty_SetInputCallback, kAudioUnitScope_Global, 1, &cb, sizeof(cb));
        if (status != noErr) {
            *error = [NSError errorWithDomain:NSStringFromClass(self.class) code:status userInfo:nil];
            return;
        }
//    }


    //播放回调
        AURenderCallbackStruct cb2;
        // 设置声音输出回调函数。当speaker需要数据时就会调用回调函数去获取数据。它是 "拉" 数据的概念。
        cb2.inputProc = audioRenderCallback;
        cb2.inputProcRefCon = (__bridge void *) self;
        status = AudioUnitSetProperty(_audioCaptureInstance,
                                      kAudioUnitProperty_SetRenderCallback,
                                      kAudioUnitScope_Global,
                                      0,
                                      &cb2,
                                      sizeof(cb2));
        if (status != noErr) {
            *error = [NSError errorWithDomain:NSStringFromClass(self.class) code:status userInfo:nil];
            return;
        }
    // 7、初始化实例。
    status = AudioUnitInitialize(_audioCaptureInstance);
    if (status != noErr) {
        *error = [NSError errorWithDomain:NSStringFromClass(self.class) code:status userInfo:nil];
        return;
    }
    

}
// 设置音量（范围0.0-1.0）
- (void)toSetVolume:(float)volume {



}
- (void)callBackError:(NSError *)error {
    self.isError = YES;
    if (error && self.errorCallBack) {
        dispatch_async(dispatch_get_main_queue(), ^{
            self.errorCallBack(error);
        });
    }
}

+ (CMSampleBufferRef)sampleBufferFromAudioBufferList:(AudioBufferList)buffers inTimeStamp:(const AudioTimeStamp *)inTimeStamp inNumberFrames:(UInt32)inNumberFrames description:(AudioStreamBasicDescription)description {
    CMSampleBufferRef sampleBuffer = NULL; // 待生成的 CMSampleBuffer 实例的引用。
    
    // 1、创建音频流的格式描述信息。
    CMFormatDescriptionRef format = NULL;
    OSStatus status = CMAudioFormatDescriptionCreate(kCFAllocatorDefault, &description, 0, NULL, 0, NULL, NULL, &format);
    if (status != noErr) {
        CFRelease(format);
        return nil;
    }
    
    // 2、处理音频帧的时间戳信息。
    mach_timebase_info_data_t info = {0, 0};
    mach_timebase_info(&info);
    uint64_t time = inTimeStamp->mHostTime;
    // 转换为纳秒。
    time *= info.numer;
    time /= info.denom;
    // PTS。
    CMTime presentationTime = CMTimeMake(time, 1000000000.0f);
    // 对于音频，PTS 和 DTS 是一样的。
    CMSampleTimingInfo timing = {CMTimeMake(1, description.mSampleRate), presentationTime, presentationTime};
    
    // 3、创建 CMSampleBuffer 实例。
    status = CMSampleBufferCreate(kCFAllocatorDefault, NULL, false, NULL, NULL, format, (CMItemCount) inNumberFrames, 1, &timing, 0, NULL, &sampleBuffer);
    if (status != noErr) {
        CFRelease(format);
        return nil;
    }
    
    // 4、创建 CMBlockBuffer 实例。其中数据拷贝自 AudioBufferList，并将 CMBlockBuffer 实例关联到 CMSampleBuffer 实例。
    status = CMSampleBufferSetDataBufferFromAudioBufferList(sampleBuffer, kCFAllocatorDefault, kCFAllocatorDefault, 0, &buffers);
    if (status != noErr) {
        CFRelease(format);
        return nil;
    }
    
    CFRelease(format);
    return sampleBuffer;
}

#pragma mark - Capture CallBack
static OSStatus recordingCallback(void *inRefCon,
                                    AudioUnitRenderActionFlags *ioActionFlags,
                                    const AudioTimeStamp *inTimeStamp,
                                    UInt32 inBusNumber,
                                    UInt32 inNumberFrames,
                                    AudioBufferList *ioData) {
    @autoreleasepool {
     
        GJLKFAudioCapture *capture = (__bridge GJLKFAudioCapture *) inRefCon;
        if (!capture) {
            return -1;
        }

        if(![GJLAudioPlayer manager].isEnableRecord)
        {
            return noErr;
        }
           AudioBuffer buffer;
           buffer.mDataByteSize = inNumberFrames * 2; // 16位PCM
           buffer.mNumberChannels = 1;
           buffer.mData = malloc(buffer.mDataByteSize);
           
           AudioBufferList bufferList;
           bufferList.mNumberBuffers = 1;
           bufferList.mBuffers[0] = buffer;
           
        OSStatus status =AudioUnitRender(capture.audioCaptureInstance, ioActionFlags, inTimeStamp, inBusNumber, inNumberFrames, &bufferList);
        

        // 3、数据封装及回调。
        if (status == noErr)
        {
            NSData *pcmData = [NSData dataWithBytes:buffer.mData length:buffer.mDataByteSize];
            [capture isQuite:pcmData];
            free(buffer.mData);
        
//            // 使用工具方法将数据封装为 CMSampleBuffer。
            CMSampleBufferRef sampleBuffer = [GJLKFAudioCapture sampleBufferFromAudioBufferList:bufferList inTimeStamp:inTimeStamp inNumberFrames:inNumberFrames description:capture.audioFormat];
            // 回调数据。
            if (capture.sampleBufferOutputCallBack) {
                capture.sampleBufferOutputCallBack(sampleBuffer,0);
            }
            if (sampleBuffer) {
                CFRelease(sampleBuffer);
            }
        }
        
        return status;
    }
}
//音频数据
-(NSData*)getAudioData:(CMSampleBufferRef)sampleBuffer
{
    
    CMBlockBufferRef blockBuffer = CMSampleBufferGetDataBuffer(sampleBuffer);
    size_t length = CMBlockBufferGetDataLength(blockBuffer);
    Byte buffer[length];
    CMBlockBufferCopyDataBytes(blockBuffer, 0, length, buffer);
    NSData *audioData = [NSData dataWithBytes:buffer length:length];

    return audioData;
}
- (void)isQuite:(NSData *)pcmData
{
    if (pcmData == nil)
    {
        return ;
    }
//    long long pcmAllLenght = 0;
//    short butterByte[pcmData.length/2];
//    memcpy(butterByte, pcmData.bytes, pcmData.length);//frame_size * sizeof(short)
//    
//    // 将 buffer 内容取出，进行平方和运算
//    for (int i = 0; i < pcmData.length/2; i++)
//    {
//        pcmAllLenght += butterByte[i] * butterByte[i];
//    }
//    // 平方和除以数据总长度，得到音量大小。
//    double mean = pcmAllLenght / (double)pcmData.length;
//    double volume =10*log10(mean);//volume为分贝数大小
   // NSLog(@"volume:%f",volume);
    if(self.audioPCMDataCallBack)
    {

        if (self.shouldRecord)
        {
 
                self.audioPCMDataCallBack(pcmData, 1.0);

        } 
     
    }

}
-(void)getCurrentTime
{
    [self toStopCurentTimer];
    __weak typeof(self) weakSelf = self;
    self.curentTimer =[GJLGCDTimer scheduledTimerWithTimeInterval:0.04 repeats:YES queue:self.curent_timer_queue block:^{
       
        NSTimeInterval currentPlayTime =  weakSelf.readedSize / (weakSelf.audioFormat.mSampleRate * weakSelf.audioFormat.mChannelsPerFrame * weakSelf.audioFormat.mBytesPerFrame);
        /// 回调进度
        //    UInt32 byteSize = ioData->mBuffers[0].mDataByteSize;
        if(weakSelf.playProgress)
        {
            weakSelf.playProgress(currentPlayTime, weakSelf.durationInSeconds);
        }
        if(currentPlayTime>weakSelf.durationInSeconds)
        {
            
//            weakSelf.readedSize = 0;
            [weakSelf toStopCurentTimer];
            if(weakSelf.playEnd)
            {
                weakSelf.playEnd();
            }
//            return noErr;
        }
    }];
}
-(void)getCurrentTimePCM
{
    [self toStopCurentTimer];
    __weak typeof(self) weakSelf = self;
    self.curentTimer =[GJLGCDTimer scheduledTimerWithTimeInterval:0.04 repeats:YES queue:self.curent_timer_queue block:^{
       
//        NSTimeInterval currentPlayTime =  weakSelf.readedSize / (weakSelf.audioFormat.mSampleRate * weakSelf.audioFormat.mChannelsPerFrame * weakSelf.audioFormat.mBytesPerFrame);
        /// 回调进度
        //    UInt32 byteSize = ioData->mBuffers[0].mDataByteSize;

        if(weakSelf.dataLengh>0&&weakSelf.isFinish)
        {
          
            if(weakSelf.playProgress)
            {
                weakSelf.playProgress(weakSelf.readedSize, weakSelf.dataLengh);
            }
            if(weakSelf.readedSize>=weakSelf.dataLengh)
            {


                weakSelf.isFinish=NO;

                if(weakSelf.playEnd)
                {
                    weakSelf.playEnd();
                }
            }
        }
        
       
    }];
}

/*
*dataLength 音频buffer的长度
*isFinish 是否一句话结束或者整段话结束
*/
-(void)toBufferLength:(int)dataLength isFinish:(BOOL)isFinish
{
//    self.readedSize=0;
    self.dataLengh=dataLength;
    self.isFinish=isFinish;
}
-(void)toStopCurentTimer
{
    if(self.curentTimer!=nil)
    {
        [self.curentTimer invalidate];
        self.curentTimer=nil;
    }
}
-(void)pauseRunning:(BOOL)pause {
    
    self.shouldRecord = !pause;
}
-(void)toStartRecord
{
    self.shouldRecord=YES;
}
-(void)toStopRecord
{
    self.shouldRecord=NO;
}
static OSStatus audioRenderCallback(void *inRefCon, AudioUnitRenderActionFlags *ioActionFlags, const AudioTimeStamp *inTimeStamp, UInt32 inOutputBusNumber, UInt32 inNumberFrames, AudioBufferList *ioData)
{
 
    GJLKFAudioCapture *audioRender = (__bridge GJLKFAudioCapture *) inRefCon;

        // 淡出处理（20ms周期）
    // 检查静音标志避免无效处理
       if (*ioActionFlags & kAudioUnitRenderAction_OutputIsSilence) {
           memset(ioData->mBuffers[0].mData, 0, ioData->mBuffers[0].mDataByteSize);
           return noErr;
       }


    if([GJLAudioPlayer manager].pcmDataCache.length<ioData->mBuffers[0].mDataByteSize || [GJLAudioPlayer manager].isPlaying==NO || [DigitalHumanDriven manager].isAudioReady==0 ||   [GJLAudioPlayer manager].isMute==YES)
    {
    


        [GJLAudioPlayer manager].isPlayMutePcm=YES;

    
    
           if (audioRender.audioBufferInputCallBack) {
               audioRender.audioBufferInputCallBack(ioData);
           }
    


        
        // 获取当前音量设置
     
            if([GJLAudioPlayer manager].isFadeInOut)
            {
                [audioRender fadeOutAudioBuffer:ioData];
            }
      
        
           if([GJLAudioPlayer manager].pcmDataCache.length>0&&[GJLAudioPlayer manager].pcmDataCache.length<ioData->mBuffers[0].mDataByteSize)
           {
             audioRender.readedSize += ioData->mBuffers[0].mDataByteSize;
          }
        
    
 


    }
    else
    {

        [GJLAudioPlayer manager].isPlayMutePcm=NO;
//            *ioActionFlags &= ~kAudioUnitRenderAction_OutputIsSilence;
            if (audioRender.audioBufferInputCallBack) {
                audioRender.audioBufferInputCallBack(ioData);
            }
        if([GJLAudioPlayer manager].isFadeInOut)
        {
            [audioRender fadeInAudioBuffer:ioData];
        }
       
            audioRender.readedSize += ioData->mBuffers[0].mDataByteSize;


    }

    // 回调数据。
    if (audioRender.sampleBufferOutputCallBack) {
        // 使用工具方法将数据封装为 CMSampleBuffer。
        CMSampleBufferRef sampleBuffer = [GJLKFAudioCapture sampleBufferFromAudioBufferList:*ioData inTimeStamp:inTimeStamp inNumberFrames:inNumberFrames description:audioRender.audioFormat];
        audioRender.sampleBufferOutputCallBack(sampleBuffer,1);
        if (sampleBuffer) {
            CFRelease(sampleBuffer);
        }
    }
  
    
    return noErr;
}
-(void)fadeOutAudioBuffer:(AudioBufferList *)bufferList
{
    if (!bufferList)
    {
        return;
    }
    self.volume= self.volume-0.02;
    if(self.volume<0)
    {
        self.volume=0.0;
    }
    else
    {
        [self adjustVolumeOfAudioBufferList:bufferList];
    }
    


}
-(void)fadeInAudioBuffer:(AudioBufferList *)bufferList
{
    if (!bufferList)
    {
        return;
    }

    self.volume= self.volume+0.02;

    if(self.volume>[GJLAudioPlayer manager].volume)
    {
       
        self.volume=[GJLAudioPlayer manager].volume;
       
        
    }
    else
    {
   
    }
    [self adjustVolumeOfAudioBufferList:bufferList];
}
-(void)adjustVolumeOfAudioBufferList:(AudioBufferList *)bufferList
{
    
    for (UInt32 bufferIndex = 0; bufferIndex < bufferList->mNumberBuffers; bufferIndex++) {
        AudioBuffer *buffer = &bufferList->mBuffers[bufferIndex];
        // 对于整数样本，需要更谨慎地处理以避免溢出
        SInt16 *samples = (SInt16 *)buffer->mData;
        for (UInt32 i = 0; i < buffer->mDataByteSize / sizeof(SInt16); i++)
        {
            // 使用一个简单的方法来避免溢出：先转换为浮点数，乘以系数，然后转换回整数
            float sampleValue = (float)samples[i];
            sampleValue *=      self.volume;
            
            // 限制音量大小，避免溢出
            if (sampleValue > INT16_MAX) {
                sampleValue = INT16_MAX;
            } else if (sampleValue < INT16_MIN) {
                sampleValue = INT16_MIN;
            }
            
            samples[i] = (SInt16)sampleValue;
        }
    }
   
    
}



- (void)startPlaying
{

    __weak typeof(self) weakSelf = self;
    [self toStopTimer];
    dispatch_barrier_async(_captureQueue, ^{


        
//        weakSelf.volume=1.0;
        [weakSelf getCurrentTimePCM];


       });
   
}
- (void)stopPlaying:(void (^)( BOOL isSuccess))success
{

    __weak typeof(self) weakSelf = self;
    [self toStopTimer];

    
//            weakSelf.readedSize=0;
    [weakSelf toStopCurentTimer];
    [weakSelf toStopTimer];
    success(YES);



}
-(void)toStopTimer
{
    if(self.stopTimer!=nil)
    {
        [self.stopTimer invalidate];
        self.stopTimer=nil;
    }
    
}


// 淡出处理（中断时调用）
- (void)fadeOutBuffer:(AudioBufferList *)bufferList {
    const int fadeSamples = 320; // 16kHz采样率下20ms淡出
    SInt16 *pcmData = (SInt16 *)bufferList->mBuffers[0].mData;
    
    for(int i=0; i<fadeSamples && i<bufferList->mBuffers[0].mDataByteSize/2; i++) {
        float factor = 1.0 - (i/(float)fadeSamples);
        pcmData[i] = (SInt16)(pcmData[i] * factor);
    }
}

// 重置AudioUnit状态
- (void)resetAudioUnit
{

    self.volume=0.0;
    
}
-(void)toMuteRecord:(BOOL)isMute
{
    if(self.audioCaptureInstance)
    {
        UInt32 mute =isMute?1:0; // 1静音，0取消静音
        AudioUnitSetProperty(_audioCaptureInstance,
                            kAUVoiceIOProperty_MuteOutput,
                            kAudioUnitScope_Global,
                            0, // 主输出
                            &mute,
                            sizeof(mute));
    }

    

}


@end

