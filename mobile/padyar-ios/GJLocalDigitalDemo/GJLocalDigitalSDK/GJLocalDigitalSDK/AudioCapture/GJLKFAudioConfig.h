
#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

@interface GJLKFAudioConfig : NSObject
+ (instancetype)defaultConfig;

@property (nonatomic, assign) NSUInteger sampleRate; // 采样率，default: 16000。
@property (nonatomic, assign) NSUInteger bitDepth; // 量化位深，default: 16。
@property (nonatomic, assign) NSUInteger channels; // 声道数，default: 1。
@end

NS_ASSUME_NONNULL_END
