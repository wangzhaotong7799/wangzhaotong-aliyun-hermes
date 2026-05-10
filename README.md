# Hermes Agent — 完整可部署环境

## 克隆

```bash
git clone --recurse-submodules git@github.com:wangzhaotong7799/hermes-Agent.git ~/.hermes
```

如果已经克隆了不带 submodule：

```bash
git submodule update --init --recursive
```

## 安装

```bash
cd ~/.hermes/hermes-agent
pip install -e .
```

## 启动

```bash
hermes
```

首次启动会自动初始化配置。
