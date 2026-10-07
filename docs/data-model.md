# 표준 설비 데이터와 추적

## 식별과 현재 저장 구조

| 데이터 | 현재 필드/위치 | 의미 |
|---|---|---|
| Project | owner, name, client, trade, status, is_sample | 공사명·발주처·공종·상태·소유자·테스트 분류 |
| Drawing | UUID, project, previous, original_name, sha256, storage_name | 업로드마다 별도 원본 버전, 이전 파일 연결 |
| Extraction JSON | engine_version, insunits, suggested_unit, entities, warnings | 원본 속성 추출. 설비 의미가 확정된 것은 아님 |
| Entity | handle, type, layer, color, linetype, points, segments, text, block | 원본 객체 식별과 판독 참고 |
| Decision | drawing + handle 고유 키, data | 현재 사용자 확인 정보 |
| ReviewEvent | actor, before, after, revision, created_at | 누가 무엇을 바꿨는지 보관하는 추가 기록 |
| Job | UUID, kind, status, attempts, snapshot, request_key, result, artifact_dir | 실행 이력, 입력 사본, 결과 위치 |

객체 handle은 파일 전체에서 영구한 설비 ID가 아니다. **Drawing UUID + 파일 SHA-256 + handle**을 함께 사용한다. 다른 원본 버전의 handle이 같다고 동일 배관으로 자동 연결하지 않는다. 파일별 이전 버전은 명시적으로 연결하지만 객체 대응은 후속이다.

## 확인 정보 예시

```json
{
  "status": "confirmed",
  "system": "water",
  "diameter_mm": "20",
  "material": "",
  "floor": "1층",
  "zone": "동측 화장실",
  "work_category": "",
  "evidence": "실무자가 원본 범례와 관경 표기를 대조함"
}
```

`pending`은 미확정, `confirmed`는 첫 버전에서 길이 산출에 필요한 급수·관경·근거를 확인한 상태, `excluded`는 이유와 함께 산출에서 제외한 상태다. confirmed라고 해서 재질·높이·접속까지 모두 확인한 완전한 BIM 데이터가 되는 것은 아니다. 빈 문자열/결과의 null은 미확정이다. 기본값을 채워 사실처럼 표시하지 않는다.

웹은 수정을 저장할 때 기존 revision과 비교한다. 다른 화면에서 먼저 수정했으면 409로 충돌을 알리고 다시 확인하게 한다. 실행 요청에도 같은 수정 번호 검사를 적용한다.

## 계산 결과

각 행은 원본 handle·도면층·좌표, 선택 계통/관경/재질/층/구역/공사 구분, 판단 근거, 모델 길이, m 길이, 계산식, 결과 상태, 기준 버전을 포함한다. 상단 metadata에는 파일 해시, 확인 데이터 해시, 기준 전체와 해시, 엔진 버전, 단위 확인 근거가 있다. 웹 실행은 프로젝트 ID·Drawing UUID·원본 이름·검토 수정 번호를 추가한다.

계산에 넣은 양은 `drawing_direct`, 미확정/제외는 `unresolved_or_excluded`로 구분한다. `result.rows.status`는 중복 때문에 원래 confirmed 결정에서 pending으로 바뀔 수 있고 `decision_status`에 원래 확인 상태를 함께 보관한다. 사용자의 결정을 몰래 고치는 대신 해당 실행에서 계산을 보류한 이유를 남긴다.

## 후속 공통 설비 모델

현재 JSON을 확장하거나 검증된 `FacilityElement` 테이블로 이동할 때 다음을 추가한다.

- member_kind, 실제/호칭 치수, 재질 표준 코드, 공종·계통 표준 코드
- 필드별 값·상태·근거·사용자 승인·출처, AI 후보는 별도 제안 기록
- Z/층고/구배, 실제 연결 그래프, fitting 연결 방식, 원본/사용자/승인 기본값 구분
- 자료/실행/기준 버전 사이의 참조와 객체 대응 이력
- 직접 물량·기준 보완 물량·BIM 직접 물량을 구분하는 quantity_origin
- `physical_segment_id + scope`로 동일 입상/기구 연결 구간의 직접·보완 중복 방지

미지 높이와 연결은 빈 값으로 둔다. 현재 엔진은 보완 물량이나 BIM 물량을 생성하지 않으므로 이들의 이중 계산 방지 기능도 구현 완료로 간주하지 않는다.
