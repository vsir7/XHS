#!/usr/bin/env python3
"""
创建测试视频文件
"""

import numpy as np
import wave
import os

def create_test_audio(duration=5, sample_rate=16000):
    """
    创建测试音频文件
    """
    print(f"正在创建测试音频文件，时长：{duration}秒...")
    
    # 生成简单的音频数据（正弦波）
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(2 * np.pi * 440 * t)  # 440Hz的正弦波
    
    # 转换为16位整数
    audio_data = (audio_data * 32767).astype(np.int16)
    
    # 保存为WAV文件
    with wave.open('test_audio.wav', 'wb') as wav_file:
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16位
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    print(f"✅ 测试音频文件创建完成：test_audio.wav")
    return 'test_audio.wav'

def create_test_video_with_audio():
    """
    创建包含音频的测试视频
    """
    try:
        import cv2
        
        print("正在创建测试视频文件...")
        
        # 创建测试音频
        audio_file = create_test_audio(duration=5)
        
        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter('test_video.mp4', fourcc, 30.0, (640, 480))
        
        # 生成视频帧
        for i in range(150):  # 5秒，30fps
            # 创建一个简单的渐变背景
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:, :] = [i % 256, (i * 2) % 256, (i * 3) % 256]
            
            # 添加文字
            cv2.putText(frame, f'Frame {i}', (50, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            out.write(frame)
        
        out.release()
        print(f"✅ 测试视频文件创建完成：test_video.mp4")
        
        # 注意：OpenCV创建的视频没有音频，但librosa可以处理视频文件
        # 实际的语音识别可能需要真实的音频内容
        
        return 'test_video.mp4'
        
    except ImportError:
        print("❌ 未安装OpenCV，无法创建测试视频")
        print("   可以使用以下命令安装：pip install opencv-python")
        return None
    except Exception as e:
        print(f"❌ 创建测试视频失败：{str(e)}")
        return None

def main():
    """
    主函数
    """
    print("="*60)
    print("创建测试视频文件")
    print("="*60)
    print()
    
    # 创建测试视频
    video_file = create_test_video_with_audio()
    
    if video_file and os.path.exists(video_file):
        file_size = os.path.getsize(video_file)
        print(f"\n📁 视频文件信息：")
        print(f"   文件名：{video_file}")
        print(f"   文件大小：{file_size / (1024 * 1024):.2f}MB")
        print(f"\n✅ 测试视频文件创建成功！")
        print("   可以使用以下命令测试：")
        print("   python test_upload_video.py")
        return 0
    else:
        print(f"\n❌ 测试视频文件创建失败")
        print("   请手动准备一个测试视频文件（MP4格式）")
        return 1

if __name__ == "__main__":
    exit(main())