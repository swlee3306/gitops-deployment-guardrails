# GitOps 배포 사전 검사

렌더링된 Kubernetes JSON에서 위험한 배포 설정을 찾는 읽기 전용 도구입니다.
Python 3.11 이상이면 패키지 설치나 클러스터 인증 없이 실행할 수 있습니다.

```sh
python3 -m guardrails check examples/safe.json
python3 -m guardrails check examples/unsafe.json
python3 -m unittest discover -s tests -v
```

안전 예제는 exit 0, 위험 예제는 exit 1입니다. 출력에는 규칙 이름과 객체 위치만 담고,
Secret 본문이나 환경변수 값은 출력하지 않습니다. 예제 이미지·digest·값은 모두 합성 자료이며 배포용이 아닙니다.

주요 검사 항목은 Secret 본문, literal credential, 고정되지 않은 이미지, host 접근,
privileged/root 실행, 권한 상승, capabilities, resource budget, wildcard RBAC입니다.
일반 container뿐 아니라 init container와 CronJob의 중첩된 Pod 설정도 확인합니다.

정책이 모든 실제 서비스에 적합한 것은 아닙니다. 지원하지 않는 kind는 `uninspected`로 표시하고
성공 처리하지 않습니다. YAML 렌더링·Kubernetes 전체 스키마 검증·실제 배포 기능은 포함하지 않습니다.

입력 형식·규칙·종료 코드와 제한은 [영문 README](README.md)에 설명했습니다.
