"""
流式缓冲区状态机 - 处理 SSE 流式响应
支持分块传输、缓冲区管理、状态追踪
"""
import logging
from enum import Enum
from typing import Dict, Optional, List, Generator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class StreamState(Enum):
    """流式状态"""
    IDLE = "idle"
    RECEIVING = "receiving"
    BUFFERING = "buffering"
    FLUSHING = "flushing"
    DONE = "done"
    ERROR = "error"


@dataclass
class StreamChunk:
    """流式数据块"""
    event: str
    data: str
    raw: str
    index: int


class StreamBuffer:
    """流式缓冲区状态机"""

    def __init__(self, buffer_size: int = 4096):
        self.buffer_size = buffer_size
        self.state = StreamState.IDLE
        self.buffer: List[str] = []
        self.chunks: List[StreamChunk] = []
        self.current_index = 0
        self.mappings: Dict[str, str] = {}

    def reset(self):
        """重置缓冲区"""
        self.state = StreamState.IDLE
        self.buffer.clear()
        self.chunks.clear()
        self.current_index = 0
        self.mappings.clear()

    def set_mappings(self, mappings: Dict[str, str]):
        """设置还原映射"""
        self.mappings = mappings

    def feed(self, data: str) -> List[StreamChunk]:
        """
        输入数据流，解析并返回数据块
        """
        self.state = StreamState.RECEIVING
        self.buffer.append(data)

        # 解析 SSE 格式
        chunks = self._parse_sse(data)
        self.chunks.extend(chunks)

        return chunks

    def _parse_sse(self, data: str) -> List[StreamChunk]:
        """解析 SSE 格式数据"""
        chunks = []
        lines = data.split('\n')

        for line in lines:
            if not line:
                continue

            if line.startswith('data: '):
                raw_data = line[6:]
                if raw_data == '[DONE]':
                    self.state = StreamState.DONE
                    chunks.append(StreamChunk(
                        event='done',
                        data='[DONE]',
                        raw=line,
                        index=self.current_index
                    ))
                else:
                    chunks.append(StreamChunk(
                        event='message',
                        data=raw_data,
                        raw=line,
                        index=self.current_index
                    ))
                    self.current_index += 1
            elif line.startswith('event: '):
                # 事件类型行
                pass
            elif line.startswith(':'):
                # 注释行，忽略
                pass
            else:
                # 其他数据
                chunks.append(StreamChunk(
                    event='raw',
                    data=line,
                    raw=line,
                    index=self.current_index
                ))

        return chunks

    def process_chunk(self, chunk: StreamChunk, unmask_func) -> StreamChunk:
        """
        处理单个数据块，执行还原
        """
        if chunk.event == 'done':
            return chunk

        # 还原敏感信息
        unmasked_data = unmask_func(chunk.data, self.mappings)

        return StreamChunk(
            event=chunk.event,
            data=unmasked_data,
            raw=chunk.raw,
            index=chunk.index
        )

    def flush(self) -> str:
        """
        刷新缓冲区，返回完整数据
        """
        self.state = StreamState.FLUSHING
        result = '\n'.join([chunk.raw for chunk in self.chunks])
        self.state = StreamState.DONE
        return result

    def is_done(self) -> bool:
        """检查是否完成"""
        return self.state == StreamState.DONE

    def is_error(self) -> bool:
        """检查是否出错"""
        return self.state == StreamState.ERROR

    def set_error(self, error_msg: str):
        """设置错误状态"""
        self.state = StreamState.ERROR
        logger.error(f"[流式错误] {error_msg}")


class StreamProcessor:
    """流式处理器"""

    def __init__(self, unmask_func):
        self.unmask_func = unmask_func
        self.buffer = StreamBuffer()

    def process_stream(self, stream: Generator[str, None, None]) -> Generator[str, None, None]:
        """
        处理流式数据
        """
        self.buffer.reset()

        for data in stream:
            chunks = self.buffer.feed(data)

            for chunk in chunks:
                processed = self.buffer.process_chunk(chunk, self.unmask_func)

                if processed.event == 'done':
                    yield 'data: [DONE]\n\n'
                elif processed.event == 'message':
                    yield f'data: {processed.data}\n\n'
                else:
                    yield f'{processed.raw}\n'

            if self.buffer.is_done():
                break

            if self.buffer.is_error():
                yield 'data: {"error": "stream processing error"}\n\n'
                break


def create_stream_processor(unmask_func) -> StreamProcessor:
    """创建流式处理器"""
    return StreamProcessor(unmask_func)