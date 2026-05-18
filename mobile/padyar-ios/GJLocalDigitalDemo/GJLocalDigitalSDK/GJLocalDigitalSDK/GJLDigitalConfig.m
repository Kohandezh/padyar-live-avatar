//
//  GJLDigitalConfig.m
//  GJLocalDigitalSDK
//
//  Created by guiji on 2025/5/15.
//

#import "GJLDigitalConfig.h"
#import "GJLOpenUDID.h"
@implementation GJLDigitalConfig
static GJLDigitalConfig *config;
+ (GJLDigitalConfig *)shareConfig
{
    static dispatch_once_t once;

    dispatch_once(&once, ^{
        config = [GJLDigitalConfig new];
    });
    return config;
}
- (id)init {
    if (self = [super init]) {
        [self defaultValue];
    }
    return self;
}
- (void)defaultValue {
    

    
    //默认sdk
    NSString *appName = [[NSBundle mainBundle] objectForInfoDictionaryKey:@"CFBundleDisplayName"];
    self.appName =appName;
    self.userId = [NSString stringWithFormat:@"sdk_%@",[GJLOpenUDID value]];
    
    

}
@end
