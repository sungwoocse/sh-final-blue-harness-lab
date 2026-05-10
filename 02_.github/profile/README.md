<div align="center">

# SOFTBANK HACKATHON 2025 FINAL

> <h3>🎯 THEME</h3>
> <h3>"Run Your Functions Instantly over HTTP"</h3>
> EC2/Compute Engine 위에서 구현하는 차세대 Serverless 플랫폼

<img src="https://github.com/user-attachments/assets/8e0aef75-7f7f-4a87-995f-57fb19f9719a" width="80%">

</div>

---

## 팀 구성원

<table align="center" style="table-layout: fixed; width: 100%;">
  <tr>
    <td><img width="150" alt="최우수상-정호원" src="https://avatars.githubusercontent.com/u/76539118?v=4" /></td>
    <td><img width="150" alt="최우수상-최성우" src="https://avatars.githubusercontent.com/u/159869978?v=4" /></td>
    <td><img width="150" alt="최우수상-조현민" src="https://avatars.githubusercontent.com/u/120346964?v=4" /></td>
    <td><img width="150" alt="최우수상-조영빈" src="https://avatars.githubusercontent.com/u/150050751?v=4" /></td>
    <td><img width="150" alt="최우수상-이재준" src="https://avatars.githubusercontent.com/u/67398119?v=4" /></td>
  </tr>
  <tr>
    <td><a href="https://github.com/ONE0x393"><b>Howon Jeong</b></a><br><sub>DevOps</sub></td>
    <td><a href="https://github.com/sungwoocse"><b>Sungwoo Choi</b></a><br><sub>Fullstack</sub></td>
    <td><a href="https://github.com/galaxyhm"><b>Hyeonmin Cho</b></a><br><sub>Infra</sub></td>
    <td><a href="https://github.com/Joyeongbinnn"><b>Yeongbin Jo</b></a><br><sub>Infra</sub></td>
    <td><a href="https://github.com/LeeJaeJun-A"><b>Jaejun Lee</b></a><br><sub>Monitoring</sub></td>
  </tr>
</table>

</br></br>

---

## 🛠️ Tech Stack

<table align="center" style="table-layout: fixed; width="100%">
  <tr>
    <td width="150" align="center"><b>Infrastructure</b></td>
    <td>
      <img src="https://img.shields.io/badge/AWS-%23232F3E.svg?style=flat-square&logo=amazon-aws&logoColor=white"/>
      <img src="https://img.shields.io/badge/Kubernetes-%23326ce5.svg?style=flat-square&logo=kubernetes&logoColor=white"/>
      <img src="https://img.shields.io/badge/kOps-%23326ce5.svg?style=flat-square&logo=kubernetes&logoColor=white"/>
      <img src="https://img.shields.io/badge/Terraform-%235835CC.svg?style=flat-square&logo=terraform&logoColor=white"/>
    </td>
  </tr>
  <tr>
    <td align="center"><b>WASM Build</b></td>
    <td>
      <img src="https://img.shields.io/badge/SpinKube-654FF0?style=flat-square&logo=webassembly&logoColor=white"/>
      <img src="https://img.shields.io/badge/mypy-3670A0?style=flat-square&logo=python&logoColor=ffdd54"/>
    </td>
  </tr>
  <tr>
    <td align="center"><b>Back-End</b></td>
    <td>
      <img src="https://img.shields.io/badge/Python-3670A0?style=flat-square&logo=python&logoColor=ffdd54"/>
      <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white"/>
    </td>
  </tr>
  <tr>
    <td align="center"><b>Front-End</b></td>
    <td>
      <img src="https://img.shields.io/badge/React-%2320232a.svg?style=flat-square&logo=react&logoColor=%2361DAFB"/>
      <img src="https://img.shields.io/badge/node.js-6DA55F?style=flat-square&logo=node.js&logoColor=white"/>
    </td>
  </tr>
  <tr>
    <td align="center"><b>CI/CD</b></td>
    <td>
      <img src="https://img.shields.io/badge/Github%20Actions-%232671E5.svg?style=flat-square&logo=githubactions&logoColor=white"/>
      <img src="https://img.shields.io/badge/ArgoCD-%23EF7B4D.svg?style=flat-square&logo=argo&logoColor=white"/>
    </td>
  </tr>
  <tr>
    <td align="center"><b>Monitoring</b></td>
    <td>
      <img src="https://img.shields.io/badge/Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white"/>
      <img src="https://img.shields.io/badge/Grafana-%23F46800.svg?style=flat-square&logo=grafana&logoColor=white"/>
      <img src="https://img.shields.io/badge/Loki-E6522C?style=flat-square&logo=grafana&logoColor=white"/>
      <img src="https://img.shields.io/badge/Promtail-E6522C?style=flat-square&logo=grafana&logoColor=white"/>
    </td>
  </tr>
</table>

</br></br>

---

## 🚀 Project Overview
> **AWS Lambda보다 빠르고 Docker보다 안전한, 차세대 WASM 기반 서버리스 플랫폼**   

- **프로젝트 기간:** 2025.11.28 - 2025.12.07
- **프로젝트 목표:** 기존 VM/Container 기반 FaaS가 가진 **Cold Start 지연**과 **보안 취약점(Container Escape)** 문제를 해결

<br>

## ✨ Key Features

<div align="center">
  <img src="https://github.com/user-attachments/assets/69205483-75cd-4f33-9458-10bc449c2c43" width="60%" alt="Infrastructure Architecture" />
</div>

### 1. Zero Cold Start & Millisecond Execution
- **Problem:** 기존 VM/Container 기반 FaaS는 게스트 OS 부팅 및 라이브러리 로딩으로 인해 무겁고 느린 콜드 스타트(Cold Start) 문제가 발생합니다.
- **Solution:** **WebAssembly(WASM)** 기술을 도입하여 컨테이너 레이어를 제거했습니다. 무거운 가상머신 부팅 단계를 물리적으로 생략하고 단순 메모리 할당만으로 코드를 즉시 구동하여, **Docker Container 대비 10~100배 빠른 기동 시간**을 달성했습니다.

### 2. Enhanced Security (Memory Sandboxing)
- **Problem:** 컨테이너 환경은 호스트 OS와 커널을 공유하므로, 탈취 시 호스트까지 위험해지는 Container Escape 보안 이슈가 존재합니다.
- **Solution:** WASM은 **메모리 샌드박싱(Memory Sandboxing)** 환경에서 실행됩니다. 시스템 콜 접근을 원천적으로 제한하여 완벽한 격리 수준을 제공하며, 악의적인 코드 실행 및 해킹 위험을 최소화했습니다.

### 3. Native-Grade Performance
- 인터프리터 언어와 달리, WASM은 기계어에 가까운 바이너리 포맷을 사용하여 네이티브 코드 급의 처리 속도를 제공합니다. 특히 ARM 아키텍처와의 최적화를 통해 고성능 처리가 가능합니다.

<div align="center">
  <img src="https://github.com/user-attachments/assets/eb8a45cb-b44a-439b-b14e-e01aacfbbd04" width="60%" alt="Infrastructure Architecture" />
</div>

<br>

---

## 🏗️ System Architecture

### Infrastructure Design
> AWS Cloud 환경 위에 Terraform을 사용하여 인프라를 프로비저닝하였으며, **kOps**를 통해 Self-managed Kubernetes 클러스터를 구축했습니다.

<div align="center">
  <img src="https://github.com/user-attachments/assets/46457646-89cf-41f2-a084-71348ef53ecd" width="100%" alt="Infrastructure Architecture" />
</div>
<br>

- **High Availability (HA):** 이중화된 가용 영역(Multi-AZ) 구성을 통해 시스템 안정성을 확보했습니다.
- **Cost Optimization:**
    - **ARM Architecture:** 가성비가 뛰어난 ARM 기반 인스턴스를 적극 도입했습니다.
    - **Spot Instances:** 상태 저장이 필요 없는(Stateless) WASM 실행 노드는 **Spot Instance**를 활용하여 비용을 획기적으로 절감했습니다. 반면, 관리형 노드(Control Plane)는 On-Demand 인스턴스를 사용하여 안정성을 보장했습니다.
    - **CloudFront:** 정적 리소스에 대한 캐싱을 통해 트래픽 비용을 최적화했습니다.
- **Scalability:** WASM Build 노드와 Function 실행 노드를 분리하여 API 병목을 제거하고, Function 노드만 독립적으로 오토 스케일링 되도록 설계했습니다.

</br>

---

## 🔄 Service Workflow

### 1. Function Creation & Deploy
사용자가 코드를 제출하면 다음과 같은 파이프라인을 거쳐 배포됩니다:

<div align="center">
  <img src="https://github.com/user-attachments/assets/72a4176e-3968-4b52-a0ae-a7186736d175" width="80%" alt="Function Creation Flow" />
</div>

1.  **Code Validation:** `mypy` 등을 이용해 코드 문법 및 타입을 검증합니다.
2.  **WASM Build:** 검증된 코드는 `spin build` 프로세스를 통해 WASM 바이너리로 빌드됩니다.
3.  **OCI Registry Push:** 빌드된 아티팩트는 OCI 호환 레지스트리로 배포되어 실행 대기 상태가 됩니다.

<br>

### 2. Function Execution
WASM 런타임을 통해 즉시 함수가 실행되는 과정입니다:

<div align="center">
  <img src="https://github.com/user-attachments/assets/77d02de9-c359-44f5-80fa-3633db9531b7" width="80%" alt="Function Execution Flow" />
</div>

1.  **Request:** 클라이언트가 HTTP 요청을 통해 함수를 호출합니다.
2.  **SpinKube Execution:** Kubernetes 상의 **SpinKube**가 OCI 레지스트리에서 WASM 모듈을 페치(Fetch)합니다.
3.  **Instant Run:** 별도의 컨테이너 부팅 없이, 샌드박스 환경에서 함수가 즉시 실행되고 결과가 반환됩니다.

</br>

---

## 📊 Monitoring & Observability

- **Tools:** Prometheus, Grafana, Loki, Promtail
- **Implementation:** 각 실행 함수(Function)마다의 리소스 사용량과 로그 정보를 실시간으로 수집하여 관제할 수 있는 대시보드를 구축했습니다. 코드 작성부터 실행, 모니터링까지 이어지는 완전한 서버리스 파이프라인을 시각화했습니다.

<br>

---

## 🔮 Future Roadmap

현재 구현된 기능 외에, 더 고도화된 서버리스 플랫폼을 위해 다음과 같은 기능을 계획하고 있습니다.

- **Event-Driven Scaling (KEDA):** 현재 CPU 사용량 기반의 HPA를 넘어, **KEDA(Kubernetes Event-driven Autoscaling)**를 도입하여 실제 요청량(Request rate)에 따라 0에서 N까지 정밀하게 스케일링되는 구조로 발전시킬 예정입니다.
- **Advanced Observability:** **OpenTelemetry**와 **Grafana Tempo**를 도입하여 분산 트레이싱 환경을 구축, 각 함수의 호출 흐름과 병목 지점을 추적하는 고도화된 분석 환경을 제공할 계획입니다.
