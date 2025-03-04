import pytest
import struct
import time
from unittest.mock import patch, MagicMock

import sys
import os
# 将父目录添加到路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Absolute import since parent has no __init__.py (namespace package)
from communication import (
    get_timestamp,
    create_command_packet,
    send_command,
    VESSEL_CODES
)

def test_get_timestamp():
    """测试时间戳函数返回值是否有效"""
    timestamp = get_timestamp()
    assert isinstance(timestamp, int)
    
    # 一天的0.1ms单位数量 = 24h * 60m * 60s * 10000
    assert 0 <= timestamp < 864000000
    print(f"当前时间戳: {timestamp}")

def test_create_command_packet():
    """测试数据包结构是否正确"""
    seq_num = 5
    vessel_id = 3
    speed = 10.5  # 10.5节
    direction = 45.0  # 45度
    
    packet = create_command_packet(seq_num, vessel_id, speed, direction)
    
    # 检查数据包是否为字节类型
    assert isinstance(packet, bytes)
    
    # 检查数据包长度是否为28字节
    assert len(packet) == 28
    
    # 解析数据包检查字段值
    unpacked = struct.unpack('>BBHIHHHBBHHHIH', packet)
    
    # 检查关键字段
    assert unpacked[0] == seq_num  # 序列号
    assert unpacked[1] == 0x01     # 信息单元标识
    assert unpacked[2] == 0x001C   # 信息单元长度
    assert unpacked[4] == 0x0701   # 发送节点编码
    assert unpacked[5] == 0x0340   # 二级信息单元标识
    assert unpacked[6] == 0x5003   # 接收节点编码(无人艇3)
    assert unpacked[7] == 0x01     # 数据来源标识
    assert unpacked[8] == 0x07     # 参数扩展标识
    assert unpacked[9] == 105      # 航速值(10.5节 -> 105)
    assert unpacked[10] == 450     # 航向值(45度 -> 450)
    assert unpacked[13] == 0x5003  # 平台编码
    print(f"数据包: {packet}")

def test_vessel_code_mapping():
    """测试无人艇ID到编码的映射"""
    for vessel_id in range(1, 6):
        packet = create_command_packet(1, vessel_id, 5.0, 90.0)
        unpacked = struct.unpack('>BBHIHHHBBHHHIH', packet)
        assert unpacked[6] == VESSEL_CODES[vessel_id]
        assert unpacked[13] == VESSEL_CODES[vessel_id]
    
    # 测试无效ID的默认值
    packet = create_command_packet(1, 99, 5.0, 90.0)
    unpacked = struct.unpack('>BBHIHHHBBHHHIH', packet)
    assert unpacked[6] == 0x5001  # 默认使用1号艇编码

@patch('socket.socket')
def test_send_command_success(mock_socket):
    """测试成功发送命令数据包"""
    # 创建模拟Socket对象
    mock_socket_instance = MagicMock()
    mock_socket.return_value = mock_socket_instance
    
    # 测试数据包
    packet = create_command_packet(1, 1, 5.0, 90.0)
    
    # 调用发送函数
    result = send_command(packet)
    
    # 验证sendto被调用并传入正确参数
    mock_socket_instance.sendto.assert_called_once()
    args = mock_socket_instance.sendto.call_args[0]
    assert args[0] == packet
    
    # 验证Socket被关闭
    mock_socket_instance.close.assert_called_once()
    
    # 验证函数返回True表示成功
    assert result is True

@patch('socket.socket')
def test_send_command_failure(mock_socket):
    """测试发送命令失败情况处理"""
    # 创建模拟Socket对象，发送时抛出异常
    mock_socket_instance = MagicMock()
    mock_socket.return_value = mock_socket_instance
    mock_socket_instance.sendto.side_effect = Exception("测试异常")
    
    # 测试数据包
    packet = create_command_packet(1, 1, 5.0, 90.0)
    
    # 调用发送函数
    result = send_command(packet)
    
    # 验证异常情况下Socket仍被关闭
    mock_socket_instance.close.assert_called_once()
    
    # 验证函数返回False表示失败
    assert result is False