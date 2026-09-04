# DevOps / 运维学习路线(用户主攻方向)

> 来源:[roadmap.sh/devops](https://roadmap.sh/devops)(357K★) + [bregman-arie/devops-exercises](https://github.com/bregman-arie/devops-exercises)(67.9K★)
> 用户当前进度基于 profile.yml 标注:✅已掌握 / 🟡学习中 / 🔴待补

## 路线图(从基础到进阶)

```
阶段 1: 基础(运维地基)
├── ✅ Linux 基础(文件系统/权限/进程)
├── ✅ Shell/Bash 脚本
├── ✅ Git 版本控制
├── 🟡 网络(TCP/IP/DNS/HTTP)
└── 🔴 系统服务(systemd)
          ↓
阶段 2: 容器与部署
├── ✅ Docker(用户已熟练)
├── 🟡 Kubernetes(用户学习中)
├── 🔴 Helm
└── 🔴 服务网格(Istio,进阶)
          ↓
阶段 3: CI/CD 与自动化
├── 🟡 CI/CD(用户学习中)
├── 🔴 Jenkins / GitHub Actions
├── 🔴 Ansible(配置管理)
└── 🔴 Terraform(IaC)
          ↓
阶段 4: 监控与可观测性
├── 🔴 Prometheus + Grafana
├── 🔴 ELK/EFK 日志栈
└── 🔴 告警系统(Alertmanager)
          ↓
阶段 5: 云平台
├── ✅ AWS IoT(用户掌握)
├── 🔴 阿里云/腾讯云(国内主流)
└── 🔴 多云管理(进阶)
```

## 用户优先级建议(基于 profile.yml)

1. **第 1 优先(立即补):** systemd + 网络深入 + Kubernetes 基础 → 应聘运维岗硬性要求
2. **第 2 优先(1-2 个月):** CI/CD(GitHub Actions 入门快)+ Ansible → 简历加分
3. **第 3 优先(面试前):** Prometheus + Grafana 基础概念 → 面试常问

## 练习资源(高星)

- [bregman-arie/devops-exercises](https://github.com/bregman-arie/devops-exercises):**67.9K★**,2600+ 道题,覆盖 Linux/Docker/K8s/AWS,**面试前必刷**

## skill 调用提示

- `career-self-assessment` 差距分析模块:读取本文件,对比 profile.yml,输出"缺什么 + 学多久"
- `career-learning-path`(待建):作为主路线图
