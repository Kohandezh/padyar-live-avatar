package ai.guiji.padyar.test.ui.activity

import ai.guiji.padyar.sdk.client.Constant
import ai.guiji.padyar.sdk.client.PADYAR
import ai.guiji.padyar.sdk.client.loader.ModelInfo
import ai.guiji.padyar.sdk.client.render.PADYARRenderer
import ai.guiji.padyar.sdk.client.thread.RenderThread
import ai.guiji.padyar.test.R
import ai.guiji.padyar.test.databinding.ActivityCallBinding
import ai.guiji.padyar.test.ui.adapter.MotionAdapter
import ai.guiji.padyar.test.ui.dialog.AudioRecordDialog
import ai.guiji.padyar.test.util.StringUtils
import android.Manifest
import android.annotation.SuppressLint
import android.opengl.GLSurfaceView
import android.os.Bundle
import android.text.TextUtils
import android.util.Log
import android.view.View
import android.widget.CompoundButton
import android.widget.Toast
import com.bumptech.glide.Glide
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream


class CallActivity : BaseActivity() {

    companion object {
        const val GL_CONTEXT_VERSION = 2
    }

    private var modelUrl = ""
    private var debug = false
    private var mMessage = ""

    @SuppressLint("SetTextI18n")
    private fun applyMessage(msg: String){
        if (debug){
            runOnUiThread {
                binding.tvDebug.visibility = View.VISIBLE
                if (mMessage.length > 10000){
                    mMessage = ""
                }
                mMessage = "${StringUtils.dateToStringMS4()} $msg\n$mMessage"
                binding.tvDebug.text = mMessage
            }
        }

    }

    private lateinit var binding: ActivityCallBinding
    private var padyar: PADYAR? = null
    private var mPADYARRender: PADYARRenderer? = null
    private var mModelInfo: ModelInfo?=null     // 加载的模型信息

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        keepScreenOn()
//        val audioManager = mContext.getSystemService(AUDIO_SERVICE) as AudioManager
//        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
//        audioManager.isSpeakerphoneOn = true
        binding = ActivityCallBinding.inflate(layoutInflater)
        setContentView(binding.root)

        modelUrl = intent.getStringExtra("modelUrl") ?: ""
        debug = intent.getBooleanExtra("debug", false)

        Glide.with(mContext).load("file:///android_asset/bg/bg1.png").into(binding.ivBg)

        binding.glTextureView.setEGLContextClientVersion(GL_CONTEXT_VERSION)
        binding.glTextureView.setEGLConfigChooser(8, 8, 8, 8, 16, 0)
//        binding.glTextureView.preserveEGLContextOnPause = true
        binding.glTextureView.isOpaque = false

        binding.switchMute.setOnCheckedChangeListener(object : CompoundButton.OnCheckedChangeListener {
            override fun onCheckedChanged(
                buttonView: CompoundButton?,
                isChecked: Boolean,
            ) {
                if (isChecked) {
                    padyar?.setVolume(0.0F)
                } else {
                    padyar?.setVolume(1.0F)
                }
            }
        })

        binding.btnRecord.setOnClickListener {
            requestPermission(arrayOf(Manifest.permission.RECORD_AUDIO), 1)
        }

        binding.btnPlayPCM.setOnClickListener {
            applyMessage("start play pcm")
            playPCMStream()
        }

        binding.btnPlayWAV.setOnClickListener {
            applyMessage("start play wav")
            playWAVFile()
        }

        binding.btnRandomMotion.setOnClickListener {
            applyMessage("start random motion")
            padyar?.startRandomMotion(true)
        }
        binding.btnStopPlay.setOnClickListener {
            padyar?.stopAudio()
        }

        mPADYARRender =
            PADYARRenderer(
                mContext,
                binding.glTextureView
            )
        binding.glTextureView.setRenderer(mPADYARRender)
        binding.glTextureView.renderMode =
            GLSurfaceView.RENDERMODE_WHEN_DIRTY      // 一定要在设置完Render之后再调用

        padyar = PADYAR(mContext, modelUrl, mPADYARRender) { event, msg, info ->
            when (event) {
                Constant.CALLBACK_EVENT_INIT_READY -> {
                    mModelInfo = info as ModelInfo
                    Log.i(TAG, "CALLBACK_EVENT_INIT_READY: $mModelInfo")
                    initOk()
                }

                Constant.CALLBACK_EVENT_INIT_ERROR -> {
                    runOnUiThread {
                        applyMessage("init error: $msg")
                        Log.e(TAG, "CALLBACK_EVENT_INIT_ERROR: $msg")
                        Toast.makeText(mContext, "Initialization exception: $msg", Toast.LENGTH_SHORT).show()
                    }
                }

                Constant.CALLBACK_EVENT_AUDIO_PLAY_START -> {
                    applyMessage("callback audio play start")
                    Log.i(TAG, "CALLBACK_EVENT_AUDIO_PLAY_START")
                }

                Constant.CALLBACK_EVENT_AUDIO_PLAY_END -> {
                    applyMessage("callback audio play end")
                    Log.i(TAG, "CALLBACK_EVENT_PLAY_END")
                }

                Constant.CALLBACK_EVENT_AUDIO_PLAY_ERROR -> {
                    applyMessage("callback audio play error: $msg")
                    Log.e(TAG, "CALLBACK_EVENT_PLAY_ERROR: $msg")
                }

                Constant.CALLBACK_EVENT_MOTION_START -> {
                    applyMessage("callback motion play start")
                    Log.e(TAG, "CALLBACK_EVENT_MOTION_START")
                }

                Constant.CALLBACK_EVENT_MOTION_END -> {
                    applyMessage("callback motion play end")
                    Log.e(TAG, "CALLBACK_EVENT_MOTION_END")
                }
            }
        }
        // Rendering status callback
//        padyar?.setReporter(object : RenderThread.Reporter {
//            override fun onRenderStat(
//                resultCode: Int,
//                isLip: Boolean,
//                useTime: Long,
//            ) {
//
//            }
//        })
        applyMessage("start init")
        padyar?.init()
    }

    private fun initOk() {
        Log.i(TAG, "init ok")
        applyMessage("init ok")
        runOnUiThread {
            binding.btnRecord.isEnabled = true
            binding.btnPlayPCM.isEnabled = true
            binding.btnPlayWAV.isEnabled = true
            binding.switchMute.isEnabled = true
            binding.btnStopPlay.isEnabled = true

            mModelInfo?.let { modelInfo ->
                if (modelInfo.motionRegions.isNotEmpty()) {
                    val names = ArrayList<String>()
                    for (motion in modelInfo.motionRegions){
                        if (!TextUtils.isEmpty(motion.name) && "unknown" != motion.name){
                            names.add(motion.name)
                        }
                    }
                    // Named action regions
                    if (names.isNotEmpty()){
                        val motionAdapter = MotionAdapter(names, object : MotionAdapter.Callback{
                            override fun onClick(name: String, now: Boolean) {
                                applyMessage("start [${name}] motion")
                                padyar?.startMotion(name, now)
                            }
                        })
                        binding.rvMotion.adapter = motionAdapter
                    }
                    binding.btnRandomMotion.visibility = View.VISIBLE
                    binding.tvMotionTips.visibility = View.VISIBLE
                }
            }
        }
    }


    override fun onDestroy() {
        super.onDestroy()
        padyar?.release()
    }

    private fun playPCMStream(){
        val thread = Thread {
            padyar?.startPush()
            val inputStream = assets.open("pcm/2.pcm")
            val buffer = ByteArray(320)
            var length = 0
            while (inputStream.read(buffer).also { length = it } > 0){
                val data = buffer.copyOfRange(0, length)
                padyar?.pushPcm(data)
            }
            padyar?.stopPush()
            inputStream.close()
        }
        thread.start()
    }

    private fun playWAVFile(){
        val thread = Thread {
            val wavName = "1.wav"
            val wavFile = File(mContext.externalCacheDir, wavName)
            if (!wavFile.exists()){
                // copy assets -> sd card
                val inputStream = assets.open("wav/$wavName")
                if (!mContext.externalCacheDir!!.exists()){
                    mContext.externalCacheDir!!.mkdirs()
                }
                val out = FileOutputStream(wavFile)
                val buffer = ByteArray(1024)
                var length = 0
                while ((inputStream.read(buffer).also { length = it }) > 0) {
                    out.write(buffer, 0, length)
                }
                out.close()
                inputStream.close()
            }
            padyar?.playAudio(wavFile.absolutePath)
        }
        thread.start()
    }

    override fun permissionsGet(get: Boolean, code: Int) {
        super.permissionsGet(get, code)
        if (get){
            showRecordDialog()
        } else {
            Toast.makeText(mContext, R.string.need_permission_continue, Toast.LENGTH_SHORT).show()
        }
    }

    private fun showRecordDialog(){
        val audioRecordDialog = AudioRecordDialog(mContext, object : AudioRecordDialog.Listener{
            override fun onFinish(path: String) {
                val thread = Thread {
                    padyar?.startPush()
                    val inputStream = FileInputStream(path)
                    val buffer = ByteArray(320)
                    var length = 0
                    while (inputStream.read(buffer).also { length = it } > 0){
                        val data = buffer.copyOfRange(0, length)
                        padyar?.pushPcm(data)
                    }
                    padyar?.stopPush()
                    inputStream.close()
                }
                thread.start()
            }
        })
        audioRecordDialog.show()
    }
}
