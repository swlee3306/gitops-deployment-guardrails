# 5분 코드 리뷰: 배포 전에 확인하고 적용과 분리하기

## 해결하려는 문제

배포 설정을 검사할 때는 위험한 설정을 찾는 것뿐 아니라 검사하지 못한 범위를 드러내고,
보고서가 Secret 값을 다시 노출하지 않도록 해야 합니다.
이 공개 구현은 렌더링된 Kubernetes JSON의 정적 검사와 두 로컬 결과의 변경 계획을 제공합니다.

클러스터 접근이나 실제 배포는 하지 않습니다. 운영 장애 감소율이나 검사 성능을 측정한 자료는 없습니다.

## 먼저 실행하기

저장소 루트에서 Python 3.11 이상으로 실행합니다. 패키지 설치·클러스터 인증은 필요 없습니다.

```sh
python3 -m guardrails check examples/safe.json
python3 -m guardrails plan --before examples/safe.json --after examples/safe.json
python3 -m unittest discover -s tests -v
```

2026-09-14 실행에서 safe 예제는 검사 1개·위반 0개·미검사 0개였습니다.
동일 파일 비교는 `mode: plan-only`, `blocked: false`, `action: unchanged`를 반환했습니다.
25개 테스트가 통과했습니다. 예제의 이미지와 데이터는 합성이므로 배포할 수 있는 워크로드가 아닙니다.

위험 예제는 다음 명령으로 볼 수 있습니다. 예상 종료 코드는 **1**이므로 성공만 연결하는
`&&` 명령 체인에 넣으면 이후 명령이 실행되지 않습니다.

```sh
python3 -m guardrails check examples/unsafe.json
```

## 설계 선택을 코드와 함께 읽기

| 상황 | 구현에서 확인할 선택 | 검증 위치 |
| --- | --- | --- |
| 지원하지 않는 리소스 종류 | 조용히 승인하지 않고 `uninspected`로 표시 | `test_unknown_kind_visible`, `test_unsupported_kind_exit_1` |
| Secret 본문·환경변수 리터럴 | 정책 위반을 보고하되 비밀값 자체는 출력하지 않음 | `test_secret_values_never_in_report`, `test_secret_payload_redacted` |
| Secret 참조를 사용하는 workload | 값의 하드코딩과 참조를 구별 | `test_secret_reference_allowed` |
| init container·CronJob | 중첩된 실행 설정도 검사 | `test_privileged_init_container`, `test_nested_cronjob` |
| 변경 계획에 삭제 포함 | 명시적 확인 전 삭제 계획을 차단 | `test_delete_requires_ack` |
| 서버가 부여한 메타데이터 | 비교에서 제외해 의미 없는 변경을 줄임 | `test_server_metadata_ignored` |

검증은 [test_core.py](../tests/test_core.py), [test_cli.py](../tests/test_cli.py),
[test_plan.py](../tests/test_plan.py)에서 확인합니다.
구현은 [core.py](../guardrails/core.py)의 `check`와 [plan.py](../guardrails/plan.py)의 `plan` 순서로 읽으면 됩니다.

## 의도적으로 남긴 제약

- 입력은 렌더링된 JSON입니다. YAML·Helm 렌더링은 별도 단계의 책임입니다.
- 제한된 정책과 필드 형태를 검사합니다. Kubernetes 전체 스키마·취약점 검사가 아닙니다.
- 두 로컬 파일의 비교입니다. 실제 클러스터 상태와의 drift 비교를 제공하지 않습니다.
- 삭제 확인 플래그는 계획의 승인 조건일 뿐, 리소스를 삭제하지 않습니다.
- 정책 보고서에는 값을 출력하지 않지만 변경 계획에는 kind·namespace·name이 포함됩니다.
  운영 리소스 이름이 담긴 계획을 외부에 공유할 때는 별도 검토가 필요합니다.

## 면접에서 설명할 핵심

“검사할 수 없는 리소스를 성공으로 처리하지 않고, 비밀값을 보고서에 재노출하지 않는 정적 검사기를
구현했습니다. 실제 적용과 분리된 변경 계획에서 삭제에 대한 명시적 확인도 검증했습니다.”

이 설명은 공개 구현에 한정됩니다. 회사 배포 플랫폼 전체를 개발했거나 운영 사고를 예방한
실측 성과가 있다는 의미로 사용하지 않습니다.
