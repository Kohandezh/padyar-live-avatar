//
//  DigitalHumanDriven.m
//  Digital
//
//  Created by cunzhi on 2023/11/9.
//

#import "DigitalHumanDriven.h"
#import <UIKit/UIKit.h>

//#import "gjpadyar.h"
#include <stdio.h>
#include "jmat.h"
#import "gjsimp.h"
#import "GJLAudioPlayer.h"
//#import "MHCVPixelBuffer.h"
static DigitalHumanDriven *manager = nil;


@interface DigitalHumanDriven () {
//    gjdigit_t* gjdigit;
//    dhmfcc_s* gjmfcc;
//    dhunet_s *gjunet;
    
    dhpadyar_s *  gjpadyar_s;

//    int pcmsize;
//    int bnfsize;
//    char* bnf;
//    char* pcm;
}


@end
@implementation DigitalHumanDriven


+ (instancetype)manager {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        manager = [[DigitalHumanDriven alloc] init];
       // [manager initGJDigital];
    });
    return manager;
}
-(id)init
{
    self=[super init];
    if(self)
    {
        self.configModel=[[DigitalConfigModel alloc] init];
        self.metal_type=0;
        self.back_type=0;
        self.audio_ready_timer_queue=dispatch_queue_create("com.digitalsdk.audio_ready_timer_queue", DISPATCH_QUEUE_SERIAL);
        self.playAuidoQueue= dispatch_queue_create("com.digitalsdk.playAuidoQueue", DISPATCH_QUEUE_SERIAL);
   
//        self.mat_type=0;
    }
    return self;
}
- (int)initGJStream{
//    self.isStop=YES;
    // 在这里实现对应的功能
    dhpadyar_s* dg = NULL;
    int rst = 0;
    rst = dhpadyar_alloc(&dg,100,(int)self.configModel.width,(int)self.configModel.height);
    rst = dhpadyar_initPcmex(dg,0,10,20,50,0);

    gjpadyar_s = dg;
   
    return rst;
}

-(void)newSession
{
    [self toStopAudioReadyTimer];
    
    self.sessid = dhpadyar_newsession(gjpadyar_s);
//    NSLog(@"sessid:%llu",sessid);

    __weak typeof(self)weakSelf = self;
  
    
    self.audioReadyTimer =[GJLGCDTimer scheduledTimerWithTimeInterval:0.04 repeats:YES queue:self.audio_ready_timer_queue block:^{
        [weakSelf toFirstReady];
    }];


}
-(void)toFirstReady
{
    __weak typeof(self)weakSelf = self;
    dispatch_async(weakSelf.playAuidoQueue, ^{
        weakSelf.isAudioReady = dhpadyar_readycnt(self->gjpadyar_s,weakSelf.sessid);
//                NSLog(@"isAudioReady:%d",self.isAudioReady);
        if(weakSelf.isAudioReady>0)
        {
            [weakSelf toStopAudioReadyTimer];
            if(weakSelf.pcmReadyBlock)
            {
                weakSelf.pcmReadyBlock();
            }
        }
        
    });
    //
}
 

-(void)toStopAudioReadyTimer
{
    if(self.audioReadyTimer!=nil) {
        [self.audioReadyTimer invalidate];
        self.audioReadyTimer = nil;
    }
}


- (int)initWenetWithPath:(NSString*)path {
    
    int rst = 0;
    const char *cStr = [path UTF8String];
    char *charStr = (char *)cStr;
    rst = dhpadyar_initWenet(gjpadyar_s,charStr);
    return rst;
}
  

- (int)initUnetPcmWithParamPath:(NSString*)paramPath binPath:(NSString*)binPath binPath2:(NSString*)binPath2
{
    int rst = 0;
    const char *cParamPath = [paramPath UTF8String];
    char *paramPathStr = (char *)cParamPath;
    
    const char *cBinPath = [binPath UTF8String];
    char *binPathStr = (char *)cBinPath;
    
    const char *cBinPath2 = [binPath2 UTF8String];
    char *binPathStr2 = (char *)cBinPath2;
    
    rst = dhpadyar_initMunetex(gjpadyar_s,paramPathStr,binPathStr,binPathStr2,(int)self.configModel.modelkind);
    return rst;
}



- (void)maskrstPcmWithPath:(NSString *)imagePath index:(int)index array:(NSArray *)array mskPath:(NSString*)maskPath bfgPath:(NSString*)bfgPath bbgPath:(NSString*)bbgPath  {

       
        double time1=[[NSDate date] timeIntervalSince1970];
          JMat mat;
          int mat_result=mat.load([imagePath UTF8String]);
          JMat maskMat;
          int mask_result=maskMat.load([maskPath UTF8String]);
          JMat bfgMat;
          int bfg_result=bfgMat.load([bfgPath UTF8String]);

        if(mat_result<0 || mask_result<0 || bfg_result<0 )
        {
           return;
        }
    
       JMat bbgMat;
       if(bbgPath!=nil&&bbgPath.length>0)
       {
          int bbg_result=bbgMat.load([bbgPath UTF8String]);
          if(bbg_result<0 )
          {
             return;
          }
       }
        
        int boxs[4];
        if (array.count == 4) {
            boxs[0]= [[NSString stringWithFormat:@"%@",[array objectAtIndex:0]] intValue];
            boxs[2]= [[NSString stringWithFormat:@"%@",[array objectAtIndex:1]] intValue];
            boxs[1]= [[NSString stringWithFormat:@"%@",[array objectAtIndex:2]] intValue];
            boxs[3]= [[NSString stringWithFormat:@"%@",[array objectAtIndex:3]] intValue];
        }
//        self.isStop=NO;
        
        int rst=0;
        BOOL isLip=NO;
        if(![GJLAudioPlayer manager].isMute&&index>0&&[GJLAudioPlayer manager].isPlayMutePcm==NO)
       {
  
//          double time1=[[NSDate date] timeIntervalSince1970];

           
      
      
               rst = dhpadyar_simpinx(self->gjpadyar_s,self.sessid,mat.udata(),mat.width(),mat.height(),boxs,maskMat.udata(),bfgMat.udata(),index);
           
              isLip=YES;
          
     
      
      }
       double time2=[[NSDate date] timeIntervalSince1970];
       float useTime=time2-time1;
       if(self.onRenderReportBlock)
       {
          self.onRenderReportBlock(rst, isLip, useTime);
       }

     
       

         
            if(self.metal_type==0)
            {
                
                if(self.matBlock)
                {
                   self.matBlock(mat.cvmat().clone(),maskMat.cvmat().clone(),bfgMat.cvmat().clone(),bbgMat.cvmat().clone());
                    mat.cvmat().release();
                    maskMat.cvmat().release();
                    bfgMat.cvmat().release();
                    bbgMat.cvmat().release();
                }
            }
            else
            {
               
                if(self.uint8Block)
                {
                    cv::Mat reuslt_mat=mat.cvmat().clone();
                    cv::Mat reuslt_maskMat=maskMat.cvmat().clone();
                    cv::Mat reuslt_bfgMat=bfgMat.cvmat().clone();
                    cv::Mat reuslt_bbgMat=bbgMat.cvmat().clone();
                    
                    UInt8 * reuslt_mat_uint8=nil;
                    if(!reuslt_mat.empty())
                    {
                        reuslt_mat_uint8=[self convertedRawImage:reuslt_mat];
                    }
                    
                    UInt8 * reuslt_maskMat_uint8=nil;
                    if(!reuslt_maskMat.empty())
                    {
                        reuslt_maskMat_uint8=[self convertedRawImage:reuslt_maskMat];
                    }
                  
                    
                    UInt8 * reuslt_bfgMat_uint8=nil;
                    if(!reuslt_bfgMat.empty())
                    {
                        reuslt_bfgMat_uint8=[self convertedRawImage:reuslt_bfgMat];
                    }
                  
                    UInt8 * reuslt_bbg_uint8=nil;
                    if (!reuslt_bbgMat.empty())
                    {
                        reuslt_bbg_uint8 =[self convertedRawImage:reuslt_bbgMat];
                    }
            
                    self.uint8Block(reuslt_mat_uint8, reuslt_maskMat_uint8, reuslt_bfgMat_uint8, reuslt_bbg_uint8, mat.width(), mat.height());
                    reuslt_mat.release();
                    reuslt_maskMat.release();
                    reuslt_bfgMat.release();
                    reuslt_bbgMat.release();
                    mat.cvmat().release();
                    maskMat.cvmat().release();
                    bfgMat.cvmat().release();
                    bbgMat.cvmat().release();
                }
            }
         
            

    
  

}
- (void)simprstPcmWithPath:(NSString *)imagePath index:(int)index array:(NSArray *)array
{
       double time1=[[NSDate date] timeIntervalSince1970];
        JMat mat;
        int mat_result=mat.load([imagePath UTF8String]);
        


        if(mat_result<0)
        {
           return;
        }
    

        
        int boxs[4];
        if (array.count == 4) {
            boxs[0]= [[NSString stringWithFormat:@"%@",[array objectAtIndex:0]] intValue];
            boxs[2]= [[NSString stringWithFormat:@"%@",[array objectAtIndex:1]] intValue];
            boxs[1]= [[NSString stringWithFormat:@"%@",[array objectAtIndex:2]] intValue];
            boxs[3]= [[NSString stringWithFormat:@"%@",[array objectAtIndex:3]] intValue];
        }
//        self.isStop=NO;
        
        int rst=0;
         BOOL isLip=NO;
        if (![GJLAudioPlayer manager].isMute&&index>0&&[GJLAudioPlayer manager].isPlayMutePcm==NO) {
     
     
            rst = dhpadyar_simpinx(self->gjpadyar_s,self.sessid,mat.udata(),mat.width(),mat.height(),boxs,NULL,NULL,index);
            isLip=YES;
//            NSLog(@"isAudioReady:%d,index:%d,rst:%d",self.isAudioReady,index,rst);
//            double time2=[[NSDate date] timeIntervalSince1970];
          
        }
          double time2=[[NSDate date] timeIntervalSince1970];
          float useTime=time2-time1;
          if(self.onRenderReportBlock)
          {
             self.onRenderReportBlock(rst, isLip, useTime);
          }
            if(self.metal_type==0)
            {
                
                if(self.matBlock2)
                {
            
                    self.matBlock2(mat.cvmat().clone());
                    mat.cvmat().release();
                }
            }
            else
            {
               
                if(self.uint8Block2)
                {
             
                    cv::Mat reuslt_mat=mat.cvmat().clone();
                
                    
                    UInt8 * reuslt_mat_uint8=nil;
                    if(!reuslt_mat.empty())
                    {
                        reuslt_mat_uint8=[self convertedRawImage:reuslt_mat];
                    }
                
                    self.uint8Block2(reuslt_mat_uint8, mat.width(), mat.height());
                    reuslt_mat.release();
                    mat.cvmat().release();
                }
            }
         
            
            
     
    
  

}
- (UInt8 *)convertedRawImage:(cv::Mat)image {
  //  double time1=[[NSDate date] timeIntervalSince1970];
    cv::Mat dst;
    cv::cvtColor(image, dst,  cv::COLOR_BGR2BGRA);

    int   m_bit =1;
    int  m_width = dst.cols;
    int m_height = dst.rows;
    int m_channel = 4;//image.channels();
    //printf("===channels %d\n",m_channel);
    int m_stride = m_width*m_channel;
    int   m_size = m_bit*m_stride*m_height;
    UInt8 *convertedRawImage = (UInt8*)calloc(m_size, sizeof(UInt8));
    //int m_ref = 0;
    memcpy(convertedRawImage,dst.data,m_size);
    image.release();
    dst.release();
   // double time2=[[NSDate date] timeIntervalSince1970];
//    NSLog(@"cvtColor:%f",time2-time1);
    return convertedRawImage;
    

}
-(void)wavPCM:(uint8_t*)pcm size:(int)size
{
//    NSLog(@"wavPCM:%d",size);
    if(self.sessid>0&&size>0)
    {
     
            uint64_t rst = dhpadyar_pushpcm(gjpadyar_s, self.sessid, (char*)pcm, size, 0);
       
       
      
        
    }
}
-(void)finishSession
{
    if(self.sessid>0)
    {
        dhpadyar_finsession(gjpadyar_s, self.sessid);
    }

}
//finishSession 结束后调用续上continueSession
-(void)continueSession
{
    if(self.sessid>0)
    {
        dhpadyar_consession(gjpadyar_s, self.sessid);
    }
}
- (void)free
{
    
    [self toStopAudioReadyTimer];
    if(gjpadyar_s!=nil)
    {
        dhpadyar_free(gjpadyar_s);
        gjpadyar_s=nil;
    }
 

}


/*
*生成一个新的问答会话id
*/
- (NSString *)getNewChatSessionId
{
    CFUUIDRef uuid_ref = CFUUIDCreate(NULL);
    CFStringRef uuid_string_ref= CFUUIDCreateString(NULL, uuid_ref);
    NSString *uuid = [NSString stringWithString:(__bridge NSString *)uuid_string_ref];
    CFRelease(uuid_ref);
    CFRelease(uuid_string_ref);
    return [uuid lowercaseString];
}






@end
