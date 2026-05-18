//
//  GJLDigitalManager.m
//  GJLocalDigitalSDK
//
//  Created by guiji on 2023/12/12.
//

#import "GJLDigitalManager.h"
#import "DigitalHumanDriven.h"
#import "DIMetalView.h"
#import "GJLGCDTimer.h"
#import "GJLAudioPlayer.h"

#import <GJLDecry/GJLDecry.h>


#define DEBASEPATH @"DecryBasePath"
#define DEDIGITALPATH @"DecryDigitalPath"

#define FIRISTCONVAKEY @"FIRISTCONVAKEY"

static GJLDigitalManager * manager = nil;
@interface GJLDigitalManager ()
@property (nonatomic, strong) DIMetalView *mtkView;
@property (nonatomic, strong) NSString *digitalPath;
@property (nonatomic, strong) NSString *deDigitalPath;
@property (nonatomic, assign) NSInteger resultIndex;
@property (nonatomic, strong) dispatch_group_t playAudioGroup;

@property (nonatomic, strong) dispatch_queue_t digital_timer_queue;
@property (nonatomic, strong) dispatch_queue_t playImageQueue;
@property (nonatomic, assign) int playImageIndex;
@property (nonatomic, assign) int curentImageIndex;

//本地路径下的图片个数
@property (nonatomic, assign)NSInteger maxCount;
@property (nonatomic, assign) BOOL playSub;
@property (nonatomic, strong) NSString * bbgPath;
//数字人主计时器
@property (nonatomic, strong) GJLGCDTimer *digitalTimer;



//数字人主计时器
@property (nonatomic, strong) GJLGCDTimer *heartTimer;
@property (nonatomic, strong) dispatch_queue_t heart_timer_queue;

////播放wav音频文件计时器
//@property (nonatomic, strong) GJLGCDTimer *audioPathTimer;
//@property (nonatomic, strong) dispatch_queue_t audioPath_timer_queue;

//图片后缀名
@property (nonatomic, strong)NSString * pic_path_exten;


@property (nonatomic, assign) BOOL isInitSuscess;


//静默区间
@property (nonatomic, strong)DigitalRangeModel * silentRangeModel;
//动作区间
@property (nonatomic, strong)DigitalRangeModel * actRangeModel;

//静默区间
@property (nonatomic, strong)DigitalSpecialModel * silentSpecialModel;
//动作区间
@property (nonatomic, strong)DigitalSpecialModel * actSpecialModel;

@property (nonatomic, assign)NSInteger action_type;

@property (nonatomic, assign)NSInteger motionType;

@property (nonatomic, strong)NSMutableArray * range_act_arr;

@property (nonatomic, strong)NSMutableArray * range_silent_arr;



//播放中
@property (nonatomic, assign) BOOL isPlaying;
//需要继续播放
@property (nonatomic, assign) BOOL needPlay;

@property (nonatomic, strong)DigitalReverseModel * lastReverseModel;

@property (nonatomic, strong)DigitalReverseModel * lastReverseModel2;
//是否第一次随机
@property (nonatomic, assign)BOOL isFirstRandom;
//正序
@property (nonatomic, assign)NSInteger reverseRandomCount;

@property (nonatomic, assign)NSInteger reverseCount;
//0 正序 1 倒序
@property (nonatomic, assign)NSInteger sequence_type;
//uuid
@property (nonatomic, strong) NSString *uuid;

@property (nonatomic, assign)BOOL isAuth;

@end
@implementation GJLDigitalManager

+ (GJLDigitalManager *)manager
{
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        manager = [[GJLDigitalManager alloc] init];
    });
    return manager;
}
-(id)init
{
    self=[super init];
    if(self)
    {
        self.isAuth=NO;
        [self initQueue];
        
        self.pcmType=0;
        [DigitalHumanDriven manager].isStop=NO;
        
        self.isVoiceProcessingIO=YES;
        
        self.isFadeInOut=YES;
 

    }
    return self;
}
- (void)initQueue {
    
    self.digital_timer_queue = dispatch_queue_create("com.digitalsdk.digital_timer_queue", DISPATCH_QUEUE_CONCURRENT);
    
    self.playImageQueue= dispatch_queue_create("com.digitalsdk.playImageQueue", DISPATCH_QUEUE_CONCURRENT);
    
    
    self.playAudioGroup = dispatch_group_create();
    
    
    self.heart_timer_queue=dispatch_queue_create("com.digitalsdk.heart_timer_queue", DISPATCH_QUEUE_CONCURRENT);
 
}






-(NSInteger)initBaseModel:(NSString*)basePath digitalModel:(NSString*)digitalPath showView:(UIView*)showView
{


 
    self.resultIndex= [[GJLDecryManager manager] initBaseModel:basePath digitalModel:digitalPath];
    if(self.resultIndex==-1)
    {
        return self.resultIndex;
    }
    
    

    //原始路径
    self.digitalPath=digitalPath;
    //解密之后路径
    self.deDigitalPath=[GJLDecryManager manager].decryDigitalPath;
    
    
    NSFileManager * filemager=[NSFileManager defaultManager];
    NSString *filePath =[NSString stringWithFormat:@"%@/raw_jpgs",self.digitalPath];
    NSArray *filelist= [filemager contentsOfDirectoryAtPath:filePath error:nil];
    
    NSInteger filesCount = [filelist count];
    self.maxCount=filesCount;
    if(self.maxCount<=0)
    {
        self.resultIndex=-1;
        return self.resultIndex;
    }
    
    
    self.playImageIndex=1;
    self.motionType=0;
    
    
    self.pic_path_exten=[[filelist.firstObject lastPathComponent] pathExtension];
    [self toStopHeartTimer];
    [self toStopDigitalTime];




    

    
//    [self.wavArr removeAllObjects];
    

    DigitalHumanDriven *manager = [DigitalHumanDriven manager];
    
    [self toJarphJson:[GJLDecryManager manager].configJson];
    
    [self toJarphSepicalJson:[GJLDecryManager manager].sepicalJson];
    
    [manager initGJStream];
    
    [manager initWenetWithPath:[GJLDecryManager manager].wenet_onnx_path];
    [manager initUnetPcmWithParamPath:[GJLDecryManager manager].paramPath binPath:[GJLDecryManager manager].binPath binPath2:[GJLDecryManager manager].weight_168u_path];
    
//    [manager initSession];
    
    
    [self toShow:showView];

  
    [GJLAudioPlayer manager].isMute=NO;
    //音频初始化回调
    [self toInitAudioPlayer];
    
    [self toInitHumanBlock];
    
    self.resultIndex=1;
    
    [DigitalHumanDriven manager].isStop=NO;
    self.isAuth=YES;
    self.isPlaying = YES;
    self.isInitSuscess=YES;
//                [DigitalHumanDriven manager].signSessionId=sessionId;
    [DigitalHumanDriven manager].isStartSuscess=YES;
    
    return  self.resultIndex;
    
}
-(void)toJarphSepicalJson:(NSString*)sepicalJson
{
    if([[NSFileManager defaultManager] fileExistsAtPath:sepicalJson])
    {
        NSData *data = [NSData dataWithContentsOfFile:sepicalJson];
        NSString *jsonString = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
        NSDictionary *sepical_dic=[self dictionaryWithJsonString:jsonString];
        if([sepical_dic isKindOfClass:[NSDictionary class]])
        {
            NSString *action_mode=[GJLGlobalFunc changeType:sepical_dic[@"action_mode"]];
            NSDictionary * padyarAppointInterval=[GJLGlobalFunc changeType:sepical_dic[@"padyarAppointInterval"]];
            if([padyarAppointInterval isKindOfClass:[NSDictionary class]])
            {
               NSArray * silences=[GJLGlobalFunc changeType:padyarAppointInterval[@"silences"]];
                if([silences isKindOfClass:[NSArray class]])
                {
                    NSMutableArray * range_mutal_arr=[[NSMutableArray alloc] init];
                    for (int i=0; i<silences.count; i++) {
                        DigitalSpecialModel * specialModel=[[DigitalSpecialModel alloc] init];
                        NSDictionary *dic=silences[i];
                        specialModel.name=[GJLGlobalFunc changeType:dic[@"name"]];
                        specialModel.cover=[GJLGlobalFunc changeType:dic[@"cover"]];
                        specialModel.duration=[GJLGlobalFunc changeType:dic[@"duration"]];
                        NSArray * actionArray=[GJLGlobalFunc changeType:dic[@"action"]];
                        if([actionArray isKindOfClass:[NSArray class]])
                        {
                            specialModel.min=[[GJLGlobalFunc changeType:actionArray.firstObject] integerValue];
                            specialModel.max=[[GJLGlobalFunc changeType:actionArray.lastObject] integerValue];
                        }
                        [range_mutal_arr addObject:specialModel];
                    }
                    
                    [DigitalHumanDriven manager].configModel.silences=range_mutal_arr;
             
                }
                
                
           
                NSArray * actions= [GJLGlobalFunc changeType:padyarAppointInterval[@"actions"]];
                if([actions isKindOfClass:[NSArray class]])
                {
                    NSMutableArray * range_mutal_arr=[[NSMutableArray alloc] init];
                    for (int i=0; i<actions.count; i++) {
                        DigitalSpecialModel * specialModel=[[DigitalSpecialModel alloc] init];
                        NSDictionary *dic=actions[i];
                        specialModel.name=[GJLGlobalFunc changeType:dic[@"name"]];
                        specialModel.cover=[GJLGlobalFunc changeType:dic[@"cover"]];
                        specialModel.duration=[GJLGlobalFunc changeType:dic[@"duration"]];
                        NSArray * actionArray=[GJLGlobalFunc changeType:dic[@"action"]];
                        if([actionArray isKindOfClass:[NSArray class]])
                        {
                            specialModel.min=[[GJLGlobalFunc changeType:actionArray.firstObject] integerValue];
                            specialModel.max=[[GJLGlobalFunc changeType:actionArray.lastObject] integerValue];
                        }
                        [range_mutal_arr addObject:specialModel];
                    }
                    
                    [DigitalHumanDriven manager].configModel.actions=range_mutal_arr;
             
                }
                
                if( [DigitalHumanDriven manager].configModel.silences.count>0 &&   [DigitalHumanDriven manager].configModel.actions.count>0)
                {
                    self.silentSpecialModel=[[DigitalSpecialModel alloc] init];
                    self.actSpecialModel=[[DigitalSpecialModel alloc] init];
                    int silent_random=arc4random()%[DigitalHumanDriven manager].configModel.silences.count;
                    self.silentSpecialModel=[DigitalHumanDriven manager].configModel.silences[silent_random];
                    
                    int act_random=arc4random()%[DigitalHumanDriven manager].configModel.actions.count;
                    self.actSpecialModel=[DigitalHumanDriven manager].configModel.actions[act_random];
                    
             
                }
             
            }
            
            
        }
        
        
        NSLog(@"config_dic:%@",sepical_dic);
    }
    
      
}
#pragma mark------------解析configJson文件-------------------------------
-(void)toJarphJson:(NSString*)configJson
{
    NSData *data = [NSData dataWithContentsOfFile:configJson];
    NSString *jsonString = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    NSDictionary *config_dic=[self dictionaryWithJsonString:jsonString];
    
    
    
    float width=[[config_dic valueForKey:@"width"] integerValue];
    float height=[[config_dic valueForKey:@"height"] integerValue];
    NSLog(@"config_dic:%@",config_dic);
    [DigitalHumanDriven manager].configModel.width=width>0?width:540;
    [DigitalHumanDriven manager].configModel.height=height>0?height:960;
    [DigitalHumanDriven manager].need_png=[[config_dic valueForKey:@"need_png"]?:@"" integerValue];
    if([config_dic.allKeys containsObject:@"modelkind"])
    {
        [DigitalHumanDriven manager].configModel.modelkind=[[config_dic valueForKey:@"modelkind"]?:@"" integerValue];
    }

    //NSDictionary *mydic=    @{@"ranges":@[@{ @"min": @"1",@"max": @"64", @"type": @"0"}, @{@"min": @"65",@"max": @"125", @"type": @"1"}]};
    
    [[DigitalHumanDriven manager].configModel.ranges removeAllObjects];
    NSArray * rangesArr=config_dic[@"ranges"];
//    NSArray * rangesArr=mydic[@"ranges"];
    if([rangesArr isKindOfClass:[NSArray class]])
    {
   
        NSMutableArray * range_mutal_arr=[[NSMutableArray alloc] init];
        self.range_silent_arr=[[NSMutableArray alloc] init];
        self.range_act_arr=[[NSMutableArray alloc] init];
        for (int i=0; i<rangesArr.count; i++) {
            NSDictionary * dic=rangesArr[i];
            DigitalRangeModel * rangeModel=[[DigitalRangeModel alloc] init];
            rangeModel.min=[dic[@"min"]?:@"" integerValue];
            rangeModel.max=[dic[@"max"]?:@"" integerValue];
            rangeModel.type=[dic[@"type"]?:@"" integerValue];
            [range_mutal_arr addObject:rangeModel];
            if(rangeModel.type==0)
            {
                [self.range_silent_arr addObject:rangeModel];
            }
            else
            {
                [self.range_act_arr addObject:rangeModel];
            }
            
            
        }
        
        if(self.range_silent_arr.count>0 &&self.range_act_arr.count>0&&range_mutal_arr.count>0)
        {
            self.silentRangeModel=[[DigitalRangeModel alloc] init];
            self.actRangeModel=[[DigitalRangeModel alloc] init];
            int silent_random=arc4random()%self.range_silent_arr.count;
            self.silentRangeModel=self.range_silent_arr[silent_random];
            
            int act_random=arc4random()%self.range_act_arr.count;
            self.actRangeModel=self.range_act_arr[act_random];
            
            [DigitalHumanDriven manager].configModel.ranges=range_mutal_arr;
        }
        
        
    }
    [[DigitalHumanDriven manager].configModel.reverses removeAllObjects];
    //可逆 不可逆
    NSArray * reverseArr=config_dic[@"reverse"];
    if([reverseArr isKindOfClass:[NSArray class]])
    {
        self.lastReverseModel=[[DigitalReverseModel alloc] init];
        self.lastReverseModel2=[[DigitalReverseModel alloc] init];
     
        NSMutableArray * reverse_mutal_arr=[[NSMutableArray alloc] init];
        for (int i=0; i<reverseArr.count; i++) {
            NSDictionary * dic=reverseArr[i];
            DigitalReverseModel * reverseModel=[[DigitalReverseModel alloc] init];
            reverseModel.min=[dic[@"min"]?:@"" integerValue];
            reverseModel.max=[dic[@"max"]?:@"" integerValue];
            reverseModel.type=[dic[@"type"]?:@"" integerValue];
            [reverse_mutal_arr addObject:reverseModel];
            
            
        }
        [DigitalHumanDriven manager].configModel.reverses=reverse_mutal_arr;
    }
    
}
-(void)initBaseModel:(NSString*)basePath
{
    [[DigitalHumanDriven manager] initWenetWithPath:basePath];
}
-(void)initDigitalModel:(NSString*)digitalPath
{
    
}
-(NSString *)getHistoryCachePath:(NSString*)pathName
{
    NSString* folderPath =[[self getFInalPath] stringByAppendingPathComponent:pathName];
    //创建文件管理器
    NSFileManager *fileManager = [NSFileManager defaultManager];
    //判断temp文件夹是否存在
    BOOL fileExists = [fileManager fileExistsAtPath:folderPath];
    //如果不存在说创建,因为下载时,不会自动创建文件夹
    if (!fileExists)
    {
        [fileManager createDirectoryAtPath:folderPath withIntermediateDirectories:YES attributes:nil error:nil];
    }
    return folderPath;
}

- (NSString *)getFInalPath
{
    NSString* folderPath =[[NSHomeDirectory() stringByAppendingPathComponent:@"Library"] stringByAppendingPathComponent:@"Cache"];
    //创建文件管理器
    NSFileManager *fileManager = [NSFileManager defaultManager];
    //判断temp文件夹是否存在
    BOOL fileExists = [fileManager fileExistsAtPath:folderPath];
    //如果不存在说创建,因为下载时,不会自动创建文件夹
    if (!fileExists) {
        [fileManager createDirectoryAtPath:folderPath withIntermediateDirectories:YES attributes:nil error:nil];
    }
    
    return folderPath;
}
-(NSInteger)getFileCounts:(NSString*)filePath
{
    NSFileManager *fm = [NSFileManager defaultManager];
    NSArray *filelist= [fm contentsOfDirectoryAtPath:filePath error:nil];
    NSInteger filesCount = [filelist count];
    return filesCount;
}

#pragma mark ************字符串转字典************************
-(NSDictionary *)dictionaryWithJsonString:(NSString *)jsonString {
    
    if (jsonString == nil) {
        return nil;
    }
    NSData *jsonData = [jsonString dataUsingEncoding:NSUTF8StringEncoding];
    NSError *err;
    NSDictionary *dic = [NSJSONSerialization JSONObjectWithData:jsonData
                                                        options:NSJSONReadingMutableContainers
                                                          error:&err];
    if(err)
    {
        NSLog(@"json解析失败：%@",err);
        return nil;
    }
    return dic;
}
-(void)toShow:(UIView*)view
{
    dispatch_async(dispatch_get_main_queue(), ^{
        [self toRemoveMtkView];
        self.mtkView = [[DIMetalView alloc] initWithFrame:CGRectMake(0, 0, view.frame.size.width, view.frame.size.height)];
        self.mtkView.backgroundColor = [UIColor clearColor];
        self.mtkView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
        [view addSubview:self.mtkView];
    });
    
}
-(void)toPlayNext:(NSInteger)playImageIndex audioIndex:(NSInteger)audioIndex bbgPath:(NSString*)bbgPath
{
    if (!self.isPlaying) {
        return;
    }
    if(playImageIndex==0)
    {
        return;
    }
    NSString *paramPath = [NSString stringWithFormat:@"%@/raw_jpgs/%ld.%@",   self.digitalPath,playImageIndex,self.pic_path_exten];
    NSString *jsonBbox = [NSString stringWithFormat:@"%@/bbox.json",  self.deDigitalPath] ;
    NSData *data = [NSData dataWithContentsOfFile:jsonBbox];
    NSString *jsonString = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    NSDictionary *bbox_dict=[self dictionaryWithJsonString:jsonString];
    NSArray *bbox = [bbox_dict objectForKey:[NSString stringWithFormat:@"%ld",playImageIndex]];
    NSString *maskkPath =[NSString stringWithFormat:@"%@/pha/%ld.%@",self.digitalPath,playImageIndex,self.pic_path_exten];
    NSString *bfgPath = [NSString stringWithFormat:@"%@/raw_sg/%ld.%@",self.digitalPath,playImageIndex,self.pic_path_exten];

    if([DigitalHumanDriven manager].need_png==0)
    {
        [[DigitalHumanDriven manager] maskrstPcmWithPath:paramPath index:(int)audioIndex array:bbox mskPath:maskkPath bfgPath:bfgPath bbgPath:bbgPath];
    }
    else
    {
        [[DigitalHumanDriven manager] simprstPcmWithPath:paramPath index:(int)audioIndex array:bbox];
    }
}
-(void)toStop
{
    self.isPlaying = NO;
    [self toStopDigitalTime];
    [self toStopHeartTimer];
    [DigitalHumanDriven manager].isStop=YES;
    [DigitalHumanDriven manager].audioIndex=0;
    self.playImageIndex=0;
    self.isInitSuscess=NO;

    self.motionType=0;
    [DigitalHumanDriven manager].isStartSuscess=NO;
    
    [[GJLAudioPlayer manager] stopPlaying:^(BOOL isSuccess) {
        
    }];
    [[GJLAudioPlayer manager] toStopRunning];

    [self clearAudioBuffer];

    [DigitalHumanDriven manager].wavframe=0;
    [self toFree];
    [[GJLAudioPlayer manager] toFree];
    [[DigitalHumanDriven manager].configModel.ranges removeAllObjects];
    //__weak typeof(self)weakSelf = self;
 
    
    
}
-(void)toStopRunning
{
    [[GJLAudioPlayer manager] toStopRunning];
}
/*
*播放
*/
-(void)toPlay {
    self.isPlaying = YES;
    if (self.needPlay) {
        [[GJLAudioPlayer manager] startPlaying];
        self.needPlay=NO;
    }
}

/*
*暂停
*/
-(void)toPause {
    self.isPlaying = NO;
    if ([GJLAudioPlayer manager].isPlaying) {
        self.needPlay = YES;
        [ [GJLAudioPlayer manager] pause];
    }
}

-(void)toFree
{
    
    dispatch_barrier_async(self.playImageQueue, ^{
          [[DigitalHumanDriven manager] free];
       });
    [self toRemoveMtkView];

}
-(void)toRemoveMtkView
{

        if(self.mtkView!=nil)
        {
            [self.mtkView removeFromSuperview];
            self.mtkView=nil;
        }
   
}


/*
 getDigitalSize 数字人模型的宽度 数字人模型的高度
 */
-(CGSize)getDigitalSize
{
    return  CGSizeMake([DigitalHumanDriven manager].configModel.width, [DigitalHumanDriven manager].configModel.height);
}
#pragma mark ----------------------播放音频流回调和录音音频流回调--------------------
-(void)toInitAudioPlayer
{
 

        __weak typeof(self)weakSelf = self;
//    [GJLAudioPlayer manager].playStatus = ^(NSInteger status) {
//            if(status==1)
//            {
//                
//                
//                //                NSLog(@"开始播放:%@",weakSelf.auidoPlayView.urlstr);
//                __strong __typeof(weakSelf) strongSelf = weakSelf;
//                if(strongSelf.isPlay)
//                {
//
//                   [[GJLAudioPlayer manager] startPlaying];
//                }
//                
//            }
//        };
    [GJLAudioPlayer manager].playFailed = ^{
            __strong __typeof(weakSelf) strongSelf = weakSelf;
//            if(strongSelf.isPlay)
//            {
                
                [strongSelf toPlayAudioEnd];
//            }
        };
    [GJLAudioPlayer manager].playEnd = ^{
            
            
            __strong __typeof(weakSelf) strongSelf = weakSelf;
//            if(strongSelf.isPlay)
//            {
//                NSLog(@"播放结束:%@",weakSelf.auidoPlayer.urlstr);
                [strongSelf toPlayAudioEnd];
//            }
            
            
        };
    [GJLAudioPlayer manager].playProgress = ^(float current, float total) {
            __strong __typeof(weakSelf) strongSelf = weakSelf;
            
            
            [strongSelf onProgressUpdate:current total:total];
            
        };
    [GJLAudioPlayer manager].sampleBufferOutputCallBack = ^(CMSampleBufferRef sample, NSInteger type) {
        __strong __typeof(weakSelf) strongSelf = weakSelf;
        if(strongSelf.sampleBufferOutputCallBack)
        {
            strongSelf.sampleBufferOutputCallBack(sample, type);
        }
    };
        


}
-(void)toInitHumanBlock
{
    __weak typeof(self)weakSelf = self;
    if([DigitalHumanDriven manager].metal_type==1)
    {
        if([DigitalHumanDriven manager].need_png==0)
        {
            [DigitalHumanDriven manager].uint8Block = ^(UInt8 *mat_uint8, UInt8 *maskMat_uint8, UInt8 *bfgMat_uint8, UInt8 *bbgMat_unit8, int width, int height) {
                dispatch_async(dispatch_get_main_queue(), ^{
                    if(weakSelf.mtkView!=nil &&[DigitalHumanDriven manager].isStartSuscess)
                    {
                        [weakSelf.mtkView renderWithUInt8:mat_uint8 :maskMat_uint8 :bfgMat_uint8 :bbgMat_unit8 :width :height];
                      
                    }
                    
                });
            };
        }
        else
        {
            [DigitalHumanDriven manager].uint8Block2 = ^(UInt8 *mat_uint8,int width, int height) {
                dispatch_async(dispatch_get_main_queue(), ^{
                    if(weakSelf.mtkView!=nil &&[DigitalHumanDriven manager].isStartSuscess)
                    {
                
                  
                        [weakSelf.mtkView renderWithMatUInt8:mat_uint8 :width :height];
                      
                    }
                    
                });
            };
        }
      
    }
    else
    {
        if([DigitalHumanDriven manager].need_png==0)
        {
            [DigitalHumanDriven manager].matBlock = ^(cv::Mat mat,cv::Mat maskMat,cv::Mat bfgMat,cv::Mat bbgMat) {
                dispatch_async(dispatch_get_main_queue(), ^{
                    if(weakSelf.mtkView!=nil &&[DigitalHumanDriven manager].isStartSuscess)
                    {
                        
                        [weakSelf.mtkView renderWithCVMat:mat :maskMat :bfgMat :bbgMat];
                    }
                    
                });
            };
        }
        else
        {
            [DigitalHumanDriven manager].matBlock2 = ^(cv::Mat mat) {
                dispatch_async(dispatch_get_main_queue(), ^{
                    if(weakSelf.mtkView!=nil &&[DigitalHumanDriven manager].isStartSuscess)
                    {
                        [weakSelf.mtkView renderWithSimCVMat:mat];
                    }
                    
                });
            };
        }
    
    }
    
    [DigitalHumanDriven manager].pcmReadyBlock = ^{
        if(weakSelf.pcmReadyBlock)
        {
            weakSelf.pcmReadyBlock();
        }
    };
    
    [DigitalHumanDriven manager].onRenderReportBlock = ^(int resultCode, BOOL isLip, float useTime) {
        if(weakSelf.onRenderReportBlock)
        {
            weakSelf.onRenderReportBlock(resultCode, isLip, useTime);
        }
    };
}
- (void)onProgressUpdate:(CGFloat)current total:(CGFloat)total
{
    if(self.audioPlayProgress)
    {

        self.audioPlayProgress(current, total);
    }
        int index = (int)(current/1280);
//            NSLog(@"音频帧index:%d",index);
        if (index <=  [DigitalHumanDriven manager].audioIndex) {
            return;
        }
      [DigitalHumanDriven manager].audioIndex=index;

}
-(void)toPlayAudioEnd
{
    //    [self.audi]
    
//    [self cancelAudioPlay];
//    [GJLAudioPlayer manager].isPlaying=NO;
    if(self.audioPlayEnd)
    {
        self.audioPlayEnd();
    }

}

-(void)toStart:(void (^) (BOOL isSuccess, NSString *errorMsg))block
{
        __weak typeof(self)weakSelf = self;
       self.playImageIndex=1;
    [self toStopDigitalTime];
    [self playNext];
    self.digitalTimer =[GJLGCDTimer scheduledTimerWithTimeInterval:0.04 repeats:YES queue:self.digital_timer_queue block:^{
            [weakSelf playNext];
        }];
    block(YES,@"开始成功");

    
}
-(void)toStopHeartTimer
{
    if(self.heartTimer!=nil) {
        [self.heartTimer invalidate];
        self.heartTimer = nil;
    }
}
- (void)toStopDigitalTime {
    
    if(self.digitalTimer!=nil) {
        [self.digitalTimer invalidate];
        self.digitalTimer = nil;
    }
}
- (void)playNext {
    //    NSString *localPath = [filePath.absoluteString stringByReplacingOccurrencesOfString:@"file://" withString:@""];

    if(!self.isInitSuscess)
    {
        return;
    }
    if(![DigitalHumanDriven manager].isStartSuscess)
    {
        
        return;
    }
    if([DigitalHumanDriven manager].isStop)
    {
        return;
    }
    
//    if([DigitalHumanDriven manager].isAudioReady>0)
//    {
//        [DigitalHumanDriven manager].audioIndex+=1;
//    }
    __weak typeof(self)weakSelf = self;
    dispatch_async(self.playImageQueue, ^{
        if([DigitalHumanDriven manager].configModel.ranges.count>0&&[DigitalHumanDriven manager].configModel.reverses.count==0)
        {
            
            [weakSelf toPlayNextByRanges];
        }
        else if([DigitalHumanDriven manager].configModel.silences.count>0&&[DigitalHumanDriven manager].configModel.actions.count>0)
        {
            [weakSelf toPlayNextBySpecial];
        }
        else if([DigitalHumanDriven manager].configModel.reverses.count>0)
        {
            [weakSelf toPlayNextByReverses];
        }
        else
        {
            [weakSelf toPlayNextDefaults];
        }
        
    });
    
}
-(NSInteger)isGetAuth
{
    
    if(!self.isAuth)
    {
        return 0;
    }
    if([DigitalHumanDriven manager].isStop)
    {
        return 0;
    }

    if(!self.isInitSuscess)
    {
        if(self.playFailed)
        {
            self.playFailed(-1, @"未初始化");
        }
        return 0;
    }
    if(![DigitalHumanDriven manager].isStartSuscess)
    {
     
        return 0;
    }
    return 1;
}
#pragma mark ------------根据动作区间播放静默和动作---------------------
-(void)toPlayNextByRanges
{
    
    if([DigitalHumanDriven manager].isStop)
    {
        return;
    }
   // NSLog(@"playImageIndex:%d",  self.playImageIndex);
    //    NSLog(@"音频帧图片index:%d",self.audioIndex);
    [self toPlayNext:self.playImageIndex audioIndex:[DigitalHumanDriven manager].audioIndex bbgPath:self.bbgPath];
    if(self.motionType==1)
    {
        //动作
        self.action_type=1;
        [self toGetPlayImageIndex:self.actRangeModel.min :self.actRangeModel.max];
    }
    else  if(self.motionType==2)
    {
        int distance1=(int)abs(self.playImageIndex-self.actRangeModel.min);
        int distance2=(int)abs(self.playImageIndex-self.actRangeModel.max);
        if(distance1<=distance2)
        {
            
            if(self.actRangeModel.min==self.playImageIndex)
            {
                self.action_type=0;
                self.motionType=0;
                [self toGetPlayImageIndex:self.silentRangeModel.min  :self.silentRangeModel.max];
                
            }
            else
            {
                self.playSub=YES;
                [self toGetPlayImageIndex:self.actRangeModel.min :self.playImageIndex];
            }
        }
        else
        {
            
            if(self.actRangeModel.max==self.playImageIndex)
            {
                self.action_type=0;
                self.motionType=0;
                [self toGetPlayImageIndex:self.silentRangeModel.min  :self.silentRangeModel.max];
            }
            else
            {
                self.playSub=NO;
                [self toGetPlayImageIndex:self.actRangeModel.min :self.actRangeModel.max];
            }
            
            
        }
    }
    else
    {
    
        
        [self toGetPlayImageIndex:self.silentRangeModel.min  :self.silentRangeModel.max];
        
        
        
        
    }

    
    
}
-(BOOL)toMotionByName:(NSString*)name
{
    BOOL isMacth=NO;
    if(name.length==0)
    {
        return isMacth;
    }
    for (int i=0; i<[DigitalHumanDriven manager].configModel.actions.count; i++) {
        DigitalSpecialModel * specialModel=[DigitalHumanDriven manager].configModel.actions[i];
        if([name containsString:specialModel.name])
        {
            self.actSpecialModel=specialModel;
            isMacth=YES;
            break;
        }
    }
    return isMacth;
    
        
}
#pragma mark ------------根据多动作区间播放静默和动作---------------------
-(void)toPlayNextBySpecial
{
    
    if([DigitalHumanDriven manager].isStop)
    {
        return;
    }
//    NSLog(@"playImageIndex:%d",  self.playImageIndex);
    //    NSLog(@"音频帧图片index:%d",self.audioIndex);
    [self toPlayNext:self.playImageIndex audioIndex:[DigitalHumanDriven manager].audioIndex bbgPath:self.bbgPath];
    if(self.motionType==1)
    {
        //动作
        self.action_type=1;
        if(self.playImageIndex==self.actSpecialModel.max)
        {
            self.action_type=0;
            self.motionType=0;
            [self toGetPlayImageIndex:self.silentSpecialModel.min  :self.silentSpecialModel.max];
        }
        else
        {
            [self toGetPlayImageIndex:self.actSpecialModel.min :self.actSpecialModel.max];
        }
      
    }
    else  if(self.motionType==2)
    {
        if(self.playImageIndex==self.actSpecialModel.max || self.playImageIndex==self.actSpecialModel.min)
        {
            self.action_type=0;
            self.motionType=0;
            [self toGetPlayImageIndex:self.silentSpecialModel.min  :self.silentSpecialModel.max];
        }
        else
        {
            [self toGetPlayImageIndex:self.actSpecialModel.min :self.actSpecialModel.max];
        }
    }
    else
    {
    
        
        [self toGetPlayImageIndex:self.silentSpecialModel.min  :self.silentSpecialModel.max];
        
        
        
        
    }

    
    
}
-(void)toGetPlayImageIndex:(NSInteger)minImageCount :(NSInteger)maxImageCount
{
    if (self.playImageIndex == maxImageCount)
    {
        self.playSub = YES;
        
    } else if (self.playImageIndex == minImageCount)
    {
        self.playSub = NO;
    }
    if (self.playSub) {

         self.playImageIndex --;


    } else {

            self.playImageIndex ++;

    
    }
    
    if(self.playImageIndex<minImageCount)
    {
        self.playImageIndex=(int)minImageCount;
        self.playSub = NO;
    }
    else if(self.playImageIndex>maxImageCount)
    {
        self.playImageIndex=(int)maxImageCount;
        self.playSub = YES;
    }
}

#pragma mark ---------------------播放可逆不可逆-------------------------------
-(void)toPlayNextByReverses
{
    //NSLog(@"playImageIndex:%d",  self.playImageIndex);
    //   NSLog(@"音频帧图片index:%d",self.audioIndex);
    [self toPlayNext:self.playImageIndex audioIndex: [DigitalHumanDriven manager].audioIndex bbgPath:self.bbgPath];
    if([DigitalHumanDriven manager].configModel.reverses.count>0)
    {
        for (DigitalReverseModel * reverseModel in [DigitalHumanDriven manager].configModel.reverses)
        {
            if(self.playImageIndex>=reverseModel.min&&self.playImageIndex<=reverseModel.max)
            {
            
                self.lastReverseModel=reverseModel;
              //  NSLog(@"type:%ld",self.lastReverseModel.type);
                break;
            }
            
            
        }
      
        if(self.lastReverseModel!= self.lastReverseModel2)
        {
            self.isFirstRandom=NO;
            self.reverseCount=0;
        }
        self.lastReverseModel2=self.lastReverseModel;
     
        if(self.lastReverseModel.type==1)
        {
            if(!self.isFirstRandom)
            {
                self.reverseRandomCount=arc4random()%5+1;

                self.isFirstRandom=YES;
            }
            if(self.lastReverseModel.min==self.playImageIndex)
            {
              

                if(self.reverseCount<self.reverseRandomCount)
                {
               
                 
                   [self toGetPlayImageIndex:self.lastReverseModel.min :self.lastReverseModel.max];
                  
                 
                }
                else
                {
                    if(self.playImageIndex<=1)
                    {
                        self.sequence_type=0;
    
                    }
                    if(self.sequence_type==0)
                    {
                        self.playSub=NO;
                    }
                
                
//                    self.reverseCount=0;
                    [self toGetPlayImageIndex:1 :self.maxCount];
                   
                
                }
                
            }
            else if(self.lastReverseModel.max==self.playImageIndex)
            {
                
            
                self.reverseCount++;
                if(self.reverseCount<self.reverseRandomCount)
                {
               
                 
                   [self toGetPlayImageIndex:self.lastReverseModel.min :self.lastReverseModel.max];
                  
                 
                }
                else
                {
//                    self.playSub=NO;
                    if(self.playImageIndex>=self.maxCount)
                    {
                        self.sequence_type=1;
                       
                    }
                    if(self.sequence_type==1)
                    {
                        self.playSub=YES;
                    }
              
         
//                    self.reverseCount=0;
                    [self toGetPlayImageIndex:1 :self.maxCount];
                   
                
                }
         
            
            }
            else
            {
                [self toGetPlayImageIndex:1 :self.maxCount];
            }
        }
        else
        {
//            self.playSub=NO;
            self.isFirstRandom=NO;
            self.reverseCount=0;
            if(self.playImageIndex<=1)
            {
                self.sequence_type=0;
                self.playSub=NO;
            }
       
            [self toGetPlayImageIndex:1 :self.maxCount];
        
          
        }
       
        
    }
    else
    {
        self.isFirstRandom=NO;
        [self toGetPlayImageIndex:1 :self.maxCount];
     
    }

//    NSLog(@"reverseRandomCount:%ld,playImageIndex:%d,type:%ld,sequence_type:%ld",self.reverseRandomCount,self.playImageIndex,self.lastReverseModel.type,self.sequence_type);
//    [self toGetPlayImageIndex:1 :self.maxCount];
}
  
#pragma mark ---------------------播放默认不带动作区间-------------------------------
-(void)toPlayNextDefaults
{
    //NSLog(@"playImageIndex:%d",  self.playImageIndex);
    //   NSLog(@"音频帧图片index:%d",self.audioIndex);
    [self toPlayNext:self.playImageIndex audioIndex:[DigitalHumanDriven manager].audioIndex bbgPath:self.bbgPath];
    [self toGetPlayImageIndex:1 :self.maxCount];
}



-(void)setBackType:(NSInteger)backType
{
    _backType=backType;
    [DigitalHumanDriven manager].back_type=backType;
}
/*
 bbgPath 替换背景
 */
-(void)toChangeBBGWithPath:(NSString*)bbgPath
{
   
    self.bbgPath=bbgPath;
    [self playNext];
}
/*
 取消播放音频
 */
-(void)cancelAudioPlay
{
   
    [DigitalHumanDriven manager].audioIndex=0;
    //    self.audi

    [[GJLAudioPlayer manager] stopPlaying:^(BOOL isSuccess) {
        
    }];
    [DigitalHumanDriven manager].wavframe=0;
}



/*
* 开始动作 （一段文字包含多个音频，第一个音频开始时设置）
* return 0  数字人模型不支持开始动作 1  数字人模型支持开始动作
*/
-(NSInteger)toStartMotion
{
    if([DigitalHumanDriven manager].configModel.ranges.count>0&&[DigitalHumanDriven manager].configModel.reverses.count==0&&[DigitalHumanDriven manager].configModel.silences.count==0&&[DigitalHumanDriven manager].configModel.actions.count==0)
    {
        if(self.range_silent_arr.count>1)
        {
            int silent_random=arc4random()%self.range_silent_arr.count;
            self.silentRangeModel=self.range_silent_arr[silent_random];
            NSLog(@"min:%ld,max:%ld", self.silentRangeModel.min,self.silentRangeModel.max);
        }
        [self toMotionType:1];
        return 1;
    }
    
    else  if([DigitalHumanDriven manager].configModel.silences.count>0&&[DigitalHumanDriven manager].configModel.actions.count>0)
    {
        if([DigitalHumanDriven manager].configModel.silences.count>1)
        {
            int silent_random=arc4random()%[DigitalHumanDriven manager].configModel.silences.count;
            self.silentSpecialModel=[DigitalHumanDriven manager].configModel.silences[silent_random];
            NSLog(@"min:%ld,max:%ld", self.silentSpecialModel.min,self.silentSpecialModel.max);
        }
        [self toMotionType:1];
        return 1;
    }
    
    return 0;

}

/*
* 结束动作 （一段文字包含多个音频，最后一个音频播放结束时设置）
*isQuickly YES 立即结束动作   NO 等待动作播放完成再静默
*return 0 数字人模型不支持结束动作  1 数字人模型支持结束动作
*/
-(NSInteger)toSopMotion:(BOOL)isQuickly
{
    if([DigitalHumanDriven manager].configModel.ranges.count>0&&[DigitalHumanDriven manager].configModel.reverses.count==0)
    {
      
  
        if(isQuickly)
        {
            [self toMotionType:0];
            
        }
        else
        {
            [self toMotionType:2];
        }
        return 1;
    }
    else  if([DigitalHumanDriven manager].configModel.silences.count>0&&[DigitalHumanDriven manager].configModel.actions.count>0)
    {
        if(isQuickly)
        {
            [self toMotionType:0];
            
        }
        else
        {
            [self toMotionType:2];
        }
        return 1;
    }
    return 0;
   
}

/*
* motion_type 0 静默或语音播放完成立即结束动作  1 保持动作  2 一段文字包含多个音频，最后一句音频播放完成后等待动作播放完成再静默
* 默认为0
*/
-(void)toMotionType:(NSInteger)motion_type
{
    
    self.motionType=motion_type;
}

/*
* 随机动作（一段文字包含多个音频，第一个音频开始时设置）
* 1 数字人模型支持随机动作 0 数字人模型不支持随机动作
*/
-(NSInteger)toRandomMotion
{
    if([DigitalHumanDriven manager].configModel.ranges.count>0&&self.range_act_arr.count>1&&[DigitalHumanDriven manager].configModel.reverses.count==0)
    {
        int act_random=arc4random()%self.range_act_arr.count;
        self.actRangeModel=self.range_act_arr[act_random];
    
        return 1;
    }
    else
    {
        return 0;
    }
    

}
/*
* 动作区间来回震荡
* 1 数字人模型支持随机动作 0 数字人模型不支持随机动作
*/
-(NSInteger)toActRangeMinAndMax
{
    if([DigitalHumanDriven manager].configModel.ranges.count>0&&self.range_act_arr.count>1&&[DigitalHumanDriven manager].configModel.reverses.count==0)
    {
        if( self.playImageIndex<self.actRangeModel.min || self.playImageIndex>self.actRangeModel.max)
        {
            self.playImageIndex=(int)self.actRangeModel.min;
                
        }
        return 1;
    }
    return 0;
}
-(void)toMute:(BOOL)isMute
{

//    [[GJLAudioPlayer manager] toEnablePlay:isMute];
    [GJLAudioPlayer manager].isMute=isMute;
}

-(void)toStartRuning
{

    
    [[GJLAudioPlayer manager] toStartRunning];
    
    [[GJLAudioPlayer manager] startPlaying];
}
//一句话或一段话的初始化session
-(void)newSession
{
    if(![self isGetAuth])
    {
        return;
    }
    [GJLAudioPlayer manager].isPlaying=YES;
    [self clearAudioBuffer];
    [[DigitalHumanDriven manager] newSession];



}
//一句话或一段话的推流结束 调用finishSession
-(void)finishSession
{
    
    [[DigitalHumanDriven manager] finishSession];
}
//finishSession 结束后调用续上continueSession
-(void)continueSession
{
    [[DigitalHumanDriven manager] continueSession];
}
/*
*pcm
*size
*/
-(void)wavPCM:(uint8_t*)pcm size:(int)size
{
    [[GJLAudioPlayer manager] wavPCM:pcm size:size];
}
-(void)clearAudioBuffer
{
//    self.audioIndex=0;
    [DigitalHumanDriven manager].sessid=0;
    [DigitalHumanDriven manager].audioIndex=0;
    [[GJLAudioPlayer manager] clearAudioBuffer];
//    [self toMute:YES];


}
/*
*dataLength 音频buffer的长度
*isFinish 是否一句话结束或者整段话结束
*/
-(void)toBufferLength:(int)dataLength isFinish:(BOOL)isFinish
{
    [[GJLAudioPlayer manager] toBufferLength:dataLength isFinish:isFinish];
}

/*
*暂停播放音频流
*/
-(void)toPausePcm
{
    if ([GJLAudioPlayer manager].isPlaying) {
        self.needPlay = YES;
        [ [GJLAudioPlayer manager] pause];
    }
}

/*
*恢复播放音频流
*/
-(void)toResumePcm
{
    if (self.needPlay) {
        [[GJLAudioPlayer manager] startPlaying];
        self.needPlay=NO;
    }
}
/*
* 是否启用录音
 */
-(void)toEnableRecord:(BOOL)isEnable
{

    [[GJLAudioPlayer manager] toEnableRecord:isEnable];
}
-(void)toMuteRecord:(BOOL)isMute
{
    [[GJLAudioPlayer manager] toMuteRecord:isMute];
}
/*
* 开始音频流播放
*/
- (void)startPlaying
{
    [[GJLAudioPlayer manager] startPlaying];
}
/*
* 结束音频流播放
 */
- (void)stopPlaying:(void (^)( BOOL isSuccess))success
{
    [[GJLAudioPlayer manager] stopPlaying:^(BOOL isSuccess) {
   
    
        success(isSuccess);
    }];
}

-(void)toWavPcmData:(NSData*)audioData
{
    
    [[GJLAudioPlayer manager] toWavPcmData:audioData];
    

}
-(void)toSetVolume:(float)volume
{
    [GJLAudioPlayer manager].volume=volume;
}
-(void)setIsVoiceProcessingIO:(BOOL)isVoiceProcessingIO
{
    [GJLAudioPlayer manager].isVoiceProcessingIO=isVoiceProcessingIO;
}
-(void)setIsFadeInOut:(BOOL)isFadeInOut
{
    [GJLAudioPlayer manager].isFadeInOut=isFadeInOut;
}
@end
