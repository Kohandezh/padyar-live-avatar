

#import "GJLKFAudioConfig.h"

@implementation GJLKFAudioConfig

+ (instancetype)defaultConfig {
    GJLKFAudioConfig *config = [[self alloc] init];
    config.sampleRate = 16000;
    config.bitDepth = 16;
    config.channels = 1;

    return config;
}

@end
