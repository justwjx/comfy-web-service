#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPv6连接测试脚本
注意：运行此脚本前请确保已激活虚拟环境
"""

import socket
import requests
import sys

def test_ipv6_support():
    """测试系统IPv6支持"""
    print("=== IPv6支持测试 ===")
    
    # 检查Python IPv6支持
    try:
        has_ipv6 = socket.has_ipv6
        print(f"Python IPv6支持: {'✓' if has_ipv6 else '✗'}")
    except Exception as e:
        print(f"Python IPv6支持检查失败: {e}")
        return False
    
    # 获取本地IPv6地址
    try:
        # 获取所有网络接口的IPv6地址
        for interface in socket.if_nameindex():
            try:
                addrinfo = socket.getaddrinfo(interface[1], None, socket.AF_INET6)
                for addr in addrinfo:
                    ipv6_addr = addr[4][0]
                    if not ipv6_addr.startswith('fe80:'):  # 排除链路本地地址
                        print(f"接口 {interface[1]} IPv6地址: {ipv6_addr}")
            except:
                continue
    except Exception as e:
        print(f"获取IPv6地址失败: {e}")
    
    return has_ipv6

def test_local_ipv6_connection(port=5000):
    """测试本地IPv6连接"""
    print(f"\n=== 本地IPv6连接测试 (端口 {port}) ===")
    
    # 测试IPv6地址
    ipv6_addresses = [
        '::1',  # IPv6 localhost
        '2409:8a20:8e25:a261:7656:3cff:feb3:26ed',  # 您的全局IPv6地址
        'fd27:392a:635d:e40:7656:3cff:feb3:26ed'   # 您的ULA地址
    ]
    
    for addr in ipv6_addresses:
        try:
            url = f"http://[{addr}]:{port}"
            print(f"测试连接: {url}")
            response = requests.get(url, timeout=5)
            print(f"✓ 连接成功: HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"✗ 连接失败: 无法连接到 {addr}:{port}")
        except requests.exceptions.Timeout:
            print(f"✗ 连接超时: {addr}:{port}")
        except Exception as e:
            print(f"✗ 连接错误: {e}")

def test_ipv4_fallback(port=5000):
    """测试IPv4回退连接"""
    print(f"\n=== IPv4回退连接测试 (端口 {port}) ===")
    
    ipv4_addresses = [
        '127.0.0.1',      # localhost
        '172.16.10.224',  # 您的IPv4地址
        '172.16.10.225'   # 您的另一个IPv4地址
    ]
    
    for addr in ipv4_addresses:
        try:
            url = f"http://{addr}:{port}"
            print(f"测试连接: {url}")
            response = requests.get(url, timeout=5)
            print(f"✓ 连接成功: HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"✗ 连接失败: 无法连接到 {addr}:{port}")
        except requests.exceptions.Timeout:
            print(f"✗ 连接超时: {addr}:{port}")
        except Exception as e:
            print(f"✗ 连接错误: {e}")

def main():
    """主函数"""
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("端口号必须是数字")
            return
    
    print("ComfyUI Web Service IPv6连接测试")
    print("=" * 50)
    
    # 测试IPv6支持
    if not test_ipv6_support():
        print("系统不支持IPv6，将只测试IPv4连接")
        test_ipv4_fallback(port)
        return
    
    # 测试IPv6连接
    test_local_ipv6_connection(port)
    
    # 测试IPv4回退
    test_ipv4_fallback(port)
    
    print("\n=== 测试完成 ===")
    print("如果IPv6连接失败，请确保:")
    print("1. 应用已使用IPv6地址启动 (HOST=::)")
    print("2. 防火墙允许IPv6连接")
    print("3. 网络配置正确")

if __name__ == '__main__':
    main() 