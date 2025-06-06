from pydub import AudioSegment
import os
from app.lib.logger import logger


def merge_audio_files(audio_files, output_path):
    """
    Ghép nhiều file âm thanh thành một file duy nhất.

    :param audio_files: Danh sách đường dẫn đến các file âm thanh cần ghép
    :param output_path: Đường dẫn để lưu file âm thanh đã ghép
    :return: Đường dẫn đến file âm thanh đã ghép
    """
    try:
        if not audio_files:
            logger.error("No audio files provided for merging")
            return None

        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Khởi tạo audio segment đầu tiên
        combined = AudioSegment.from_file(audio_files[0])

        # Ghép các file còn lại
        for audio_file in audio_files[1:]:
            try:
                next_segment = AudioSegment.from_file(audio_file)
                combined += next_segment
            except Exception as e:
                logger.error(f"Error processing audio file {audio_file}: {str(e)}")
                continue

        # Xuất file đã ghép
        combined.export(output_path, format="mp3")
        logger.info(
            f"Successfully merged {len(audio_files)} audio files to {output_path}"
        )
        return output_path

    except Exception as e:
        logger.error(f"Error merging audio files: {str(e)}")
        return None


def merge_audio_files_with_silence(audio_files, output_path, silence_duration=500):
    """
    Ghép nhiều file âm thanh thành một file duy nhất, thêm khoảng lặng giữa các file.

    :param audio_files: Danh sách đường dẫn đến các file âm thanh cần ghép
    :param output_path: Đường dẫn để lưu file âm thanh đã ghép
    :param silence_duration: Thời gian khoảng lặng giữa các file (milliseconds)
    :return: Đường dẫn đến file âm thanh đã ghép
    """
    try:
        if not audio_files:
            logger.error("No audio files provided for merging")
            return None

        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Tạo khoảng lặng
        silence = AudioSegment.silent(duration=silence_duration)

        # Khởi tạo audio segment đầu tiên
        combined = AudioSegment.from_file(audio_files[0])

        # Ghép các file còn lại với khoảng lặng
        for audio_file in audio_files[1:]:
            try:
                next_segment = AudioSegment.from_file(audio_file)
                combined += silence + next_segment
            except Exception as e:
                logger.error(f"Error processing audio file {audio_file}: {str(e)}")
                continue

        # Xuất file đã ghép
        combined.export(output_path, format="mp3")
        logger.info(
            f"Successfully merged {len(audio_files)} audio files to {output_path}"
        )
        return output_path

    except Exception as e:
        logger.error(f"Error merging audio files: {str(e)}")
        return None
