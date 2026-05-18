#ifndef GJSIMP
#define GJSIMP

#include <stdint.h>
#ifdef __cplusplus
extern "C"{
#endif


typedef struct dhpadyar_s dhpadyar_t;

int dhpadyar_alloc(dhpadyar_t** pdg,int mincalc,int width,int height);
int dhpadyar_initPcmex(dhpadyar_t* dg,int maxsize,int minoff ,int minblock ,int maxblock,int rgb);
int dhpadyar_initWenet(dhpadyar_t* dg,char* fnwenet); 
int dhpadyar_initMunet(dhpadyar_t* dg,char* fnparam,char* fnbin,char* fnmsk);
int dhpadyar_initMunetex(dhpadyar_t* dg,char* fnparam,char* fnbin,char* fnmsk,int rect);

uint64_t dhpadyar_newsession(dhpadyar_t* dg);

int dhpadyar_pushpcm(dhpadyar_t* dg,uint64_t sessid,char* buf,int size,int kind);
int dhpadyar_readpcm(dhpadyar_t* dg,uint64_t sessid,char* pcmbuf,int pcmlen,char* bnfbuf,int bnflen);
int dhpadyar_simprst(dhpadyar_t* dg,uint64_t sessid,uint8_t* bpic,int width,int height,int* box,uint8_t* bmsk,uint8_t* bfg,uint8_t* bnfbuf,int bnflen);

int dhpadyar_allcnt(dhpadyar_t* dg,uint64_t sessid);
int dhpadyar_readycnt(dhpadyar_t* dg,uint64_t sessid);
int dhpadyar_simpinx(dhpadyar_t* dg,uint64_t sessid,uint8_t* bpic,int width,int height,int* box,uint8_t* bmsk,uint8_t* bfg,int bnfinx);
int dhpadyar_fileinx(dhpadyar_t* dg,uint64_t sessid,char* fnpic,int* box,char* fnmsk,char* fnfg,int bnfinx,char* bimg,char* mskbuf,int imgsize);
int dhpadyar_simpblend(dhpadyar_t* dg,uint64_t sessid,uint8_t* bpic,int width,int height,uint8_t* bmsk,uint8_t* bfg);

int dhpadyar_simppcm(dhpadyar_t* dg,char* buf,int size,char* pre,int presize,char* bnf,int bnfsize);


int dhpadyar_finsession(dhpadyar_t* dg,uint64_t sessid);
int dhpadyar_consession(dhpadyar_t* dg,uint64_t sessid);



int dhpadyar_free(dhpadyar_t* dg);








#ifdef __cplusplus
}
#endif


#endif
