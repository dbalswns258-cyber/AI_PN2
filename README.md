# AI PN2 — 설비 산출 작업실

학교 기계설비 적산을 위한 Python 개발 프로젝트입니다. 첫 버전은 **한 층 또는 화장실 구간의 급수 DXF를 사람이 확인하고 평면 길이를 계산하는 검증용 프로그램**입니다. 실제 공사 도면, LISP, 기존 산출서, MQC 자료는 아직 제공되지 않았습니다. 합성 도면의 테스트 통과는 실제 업무 정확도 검증을 의미하지 않습니다.

기존 `index.html` 시장 동향 대시보드는 그대로 보존했습니다. 새 웹 프로그램은 Django로 실행하며 외부 CDN이나 런타임 AI API가 필요하지 않습니다.

외부에서 접속하는 배포는 [배포·최초 로그인 안내](docs/deployment.md)를 따릅니다. `render.yaml`과 운영 실행 스크립트를 준비했으며, 호스팅 계정 연결과 유료 영구 디스크 선택은 사용자가 해야 합니다. 공개 접속 URL은 호스팅 서비스가 실제 생성한 뒤에만 확정됩니다.

## 구현한 흐름

1. 실제 비밀번호 인증으로 로그인합니다. 프로젝트와 파일은 소유자만 접근할 수 있습니다.
2. 프로젝트를 만들고 DXF 또는 PDF·PNG·JPG 참고 자료를 등록합니다.
3. 별도 Python 작업자가 DXF의 객체 번호(handle), 선·폴리선·문자·블록 정보를 추출합니다.
4. 원본 CAD의 객체와 좌표를 대조하여 급수·관경·판독 근거를 직접 확정하거나 제외합니다.
5. 모델 공간 단위, 근거, 반올림 방식을 직접 지정해 계산을 요청합니다.
6. 관경별 집계, 미확정·제외 내역, 객체별 계산식을 확인하고 DXF·엑셀·JSON을 받습니다.

원본은 덮어쓰지 않습니다. 실행 시점의 확인 정보와 계산 기준을 따로 보관하므로 나중에 검토 내용을 바꾸어도 과거 결과는 유지됩니다.

## 설치와 실행 (검증 환경: Linux / Python 3.12)

```bash
cd /workspace/AI_PN2
bash scripts/install.sh
```

설치 위치 기본값:

| 내용 | 경로 |
|---|---|
| Python 가상환경 (프로젝트 전용 도구 모음) | `/workspace/ai-pn2-venv` |
| 사용자·프로젝트·작업 DB | `/workspace/ai-pn2-data/db.sqlite3` |
| 원본과 결과 파일 | `/workspace/ai-pn2-data/files` |
| 자동 생성한 로컬 서버 서명 키 | `/workspace/ai-pn2-data/django-secret-key` |

`AI_PN2_DATA_DIR`, `AI_PN2_VENV`로 변경할 수 있습니다. 자료 경로는 Git 저장소 밖이어야 합니다. 비밀값·실제 도면·사용자 DB를 Git에 추가하지 마세요. 설치 스크립트는 기존 DB와 키를 초기화하지 않습니다.

첫 계정은 본인이 안전한 터미널에서 생성하세요. 공유 기본 계정이나 기본 비밀번호는 없습니다.

```bash
/workspace/ai-pn2-venv/bin/python manage.py createsuperuser
```

비밀번호는 명령행 인자나 채팅에 넣지 않고 대화형 입력란에 입력합니다. 일반 사용자 계정도 향후 관리자 절차로 추가할 수 있지만 현재 프로젝트 공유 권한 UI는 없습니다. Django 관리자 권한이 있어도 웹 프로젝트 접근은 소유자 조건을 따릅니다.

터미널 두 개에서 각각 실행합니다.

```bash
bash scripts/dev.sh web
```

```bash
bash scripts/dev.sh worker
```

개발 서버는 `127.0.0.1:8000`에 바인딩됩니다. 온보딩 화면은 로컬 미리보기 링크를 제공하지 않습니다. 클라우드의 Python은 사용자 PC의 AutoCAD·Revit·MQC를 직접 실행하지 않습니다. 웹에서 작업이 계속 대기하면 작업자 프로세스와 프로젝트 화면의 연결 상태를 확인하세요.

이 설정은 개발·개인 검증용입니다. 공개 서비스 배포 시에는 별도 Python 서버, HTTPS, 비공개 파일 저장소, 백업·복구, 운영 프로세스 관리, 업로드 격리 검토가 필요합니다. Django 개발 서버를 인터넷 운영 서버로 사용하지 않습니다. 정적 호스팅만 지원하는 서비스에는 Python 계산·인증·작업자를 함께 배포할 수 없습니다.

## 웹 없이 엔진 검증

다음 예시는 **합성 도면 전용**이며 실제 업무의 mm 단위나 소수 3자리 기준을 승인한 것이 아닙니다. 출력 폴더는 새 경로를 사용하세요.

```bash
source /workspace/ai-pn2-venv/bin/activate
export XDG_CACHE_HOME=/workspace/ai-pn2-data/cache
python -m takeoff.cli sample /tmp/pn2-example
python -m takeoff.cli inspect /tmp/pn2-example/sample.dxf /tmp/pn2-example/extracted.json
python -m takeoff.cli run /tmp/pn2-example/sample.dxf \
  /tmp/pn2-example/decisions.json /tmp/pn2-example/output \
  --unit mm --unit-evidence '합성 명세: 3-4-5 삼각형의 5000 mm 길이'
```

예상: DN20 `8.142 m` (5 m 직선 + 반지름 1 m 반원), DN25 `3.000 m`. 확정 3, 제외 1, 미확정 5개입니다. 출력은 `standardized.dxf`, `takeoff.xlsx`, `result.json`입니다. 엑셀은 MQC의 가져오기 형식으로 검증된 파일이 아닙니다.

기존 산출을 비교하려면 `handle,diameter_mm,length_m` 열의 CSV를 준비하고 `--baseline 경로.csv`를 추가합니다. 객체 번호 대응은 사용자가 검증해야 합니다. 행별 차이와 대응이 없는 항목을 내보내며 합격 허용오차를 임의로 판정하지 않습니다. 현재 비교 기능은 CLI에만 있습니다.

## 검사

```bash
source /workspace/ai-pn2-venv/bin/activate
python manage.py check
python manage.py test
```

브라우저 전체 흐름 검사는 별도 Playwright/Chromium 도구가 있을 때 실행합니다. 이 클라우드에는 둘 다 미리 설치되어 있습니다. 아래 `python3`는 Playwright가 설치된 기본 인터프리터입니다. 가상환경 활성화 상태라면 먼저 `deactivate` 하세요.

```bash
python3 scripts/browser_smoke.py --python /workspace/ai-pn2-venv/bin/python
```

브라우저 검사는 임시 DB·임시 계정·합성 도면으로 실행하고 종료 후 정리합니다. 운영용 자료나 기존 계정을 바꾸지 않습니다.

## 문서와 현재 한계

- [요구사항과 미확정 사항](docs/requirements.md)
- [구성요소와 실행 환경](docs/architecture.md)
- [표준 설비 데이터](docs/data-model.md)
- [산출 기준과 처리 범위](docs/takeoff-rules.md)
- [단계별 계획](docs/roadmap.md)
- [검증 기록](docs/validation.md)
- [공식 근거와 기술 조사](docs/research.md)
- [외부 배포·자료 보존·최초 로그인](docs/deployment.md)

DWG 직접 처리, 블록 내부 물량, 입상·기구 연결 보완, AI 판독, BIM 생성, MQC 자동 입력은 구현하지 않았습니다. 단위·반올림 등 실제 업무 기준과 MQC 제품 정보는 사용자 지시에 따라 미확정으로 유지합니다.
