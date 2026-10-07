# 외부 접속 배포와 최초 로그인

## 현재 상태

프로그램 소스는 `dbalswns258-cyber/AI_PN2`에 반영할 수 있도록 준비했다. 개발 작업 공간은 `/workspace/AI_PN2`, 기존 개발 데이터는 `/workspace/ai-pn2-data`에 따로 있다. Git에는 코드·문서·합성 데이터 생성기만 올린다. DB·업로드·서명 키·생성 산출서는 올리지 않는다.

외부 호스팅 계정 연결은 확인되지 않았다. Render/Railway/Fly 등의 인증 변수와 CLI 인증 디렉터리가 없고, 클라우드 AWS 설정 파일도 비어 있다. GitHub Git HTTPS 접근은 사용하지만 GitHub API 접근은 현재 네트워크 정책에서 거부되었다. API 접근 실패를 Git 저장소 권한 부재로 판단하지 않는다.

**현재 공개 배포 완료나 실제 접속 URL이 발급되었다고 간주하면 안 된다.** 이 문서는 준비한 배포 구성과 사용자가 해야 할 계정 연결·비용 선택을 설명한다. 온보딩 환경의 Publish는 이 앱의 웹 배포와 별개다.

## 준비한 배포안: Render 웹 서비스 + 영구 디스크

첫 개인용 버전은 PostgreSQL/파일 스토리지/작업자 서비스를 따로 구매하는 대신, 하나의 Python 웹 서비스에서 Gunicorn 웹 서버와 단일 Python 작업자를 실행하고 SQLite·업로드·결과·서명 키를 같은 영구 디스크에 보관한다. 소수 사용자를 위한 한 인스턴스 구성이다.

| 항목 | 설정 |
|---|---|
| 저장소 / 브랜치 | `dbalswns258-cyber/AI_PN2` / `main` |
| 배포 명세 | 루트 `render.yaml` |
| 서버 | Python 3.12.14, Gunicorn 1 worker / 2 threads |
| 인스턴스 | Starter 1개 (사용자가 비용 확인 후 선택) |
| 지역 | Singapore (변경 시 기존 디스크 이동 조건 확인) |
| 영구 디스크 | `/var/data`, 초기 1 GB |
| 실제 DB·파일 경로 | `/var/data/ai-pn2` |
| 빌드 | `pip install --requirement requirements.txt` |
| 시작 | `python scripts/serve.py` |
| 상태 확인 | `/healthz/` (DB·파일 경로·작업자 상태) |
| 자동 배포 | 꺼짐; 검토한 커밋만 수동 배포 |

지속 디스크가 없는 무료/임시 파일시스템에 SQLite와 업로드를 두면 재배포·교체 때 자료가 사라질 수 있어 이 목적에 맞지 않는다. GitHub Pages 같은 정적 호스팅도 Django 인증/DB/작업자를 실행할 수 없다. 다른 유료 VPS/호스팅도 **Python 상시 실행 + 영구 쓰기 디스크 + HTTPS + 프로세스 재시작**을 제공하면 사용 가능하지만 현재 계정이 연결되어 있지 않다.

Render는 유료 서비스·디스크 선택이 필요한 배포안이다. 최신 금액은 이 환경에서 가격 페이지가 차단되어 확인하지 못했으므로 확정 가격을 적지 않는다. 배포 화면에서 웹 서비스와 디스크의 현재 합계 견적을 확인하고 직접 승인한다. 사용자의 동의 없이 유료 리소스를 만들거나 결제를 진행하지 않는다.

## 사용자가 해야 할 연결 절차

1. [Render](https://dashboard.render.com/)에 로그인/가입한다.
2. GitHub 연결에서 이 저장소에 대한 접근을 허용한다. 비공개 저장소라면 해당 저장소 접근 권한을 선택한다. GitHub/Render 비밀번호나 API 키를 채팅에 보내지 않는다.
3. **New → Blueprint**에서 `dbalswns258-cyber/AI_PN2`와 `main`을 선택한다. `render.yaml`을 읽는지 확인한다. 또는 [이 저장소의 배포 시작](https://render.com/deploy?repo=https://github.com/dbalswns258-cyber/AI_PN2)을 이용한다. 이 링크는 프로그램 접속 주소가 아니라 배포 설정 시작 링크다.
4. 표시된 Starter 서버와 1 GB 영구 디스크의 비용을 검토하고 원하는 경우 생성한다. 무료 플랜으로 바꾸어 디스크를 없애지 않는다.
5. 배포가 Live가 되면 Render가 표시하는 실제 HTTPS 서비스 주소를 사용한다. 서비스 이름만으로 URL을 추측하지 않는다. 실제 주소가 나오면 로그인·프로젝트·업로드·재시작 보관 확인을 그 주소에서도 수행한다.

이 단계가 필요한 이유는 현재 Codex 작업에 사용자의 Render 계정·GitHub 연결 승인·결제 결정 권한이 제공되지 않았기 때문이다. 별도 도메인 구입은 필수가 아니다. 호스팅이 제공하는 HTTPS 주소로 시작할 수 있다.

## 최초 계정과 로그인

배포된 Render 웹 서비스의 **Shell**에서 다음을 실행한다.

```bash
python manage.py createsuperuser
```

원하는 사용자명·이메일·비밀번호를 대화형으로 입력한다. 비밀번호는 입력 중 화면에 표시되지 않는다. 이미 존재하는 사용자 이름을 자동 덮어쓰지 않는다. 서버가 쓰는 같은 `/var/data/ai-pn2` DB에 저장되므로 재시작에도 유지된다.

이후 Render가 표시한 HTTPS 주소의 `/accounts/login/`에서 방금 만든 사용자명·비밀번호로 로그인한다. 공개 회원가입과 공유 기본 비밀번호는 없다. 비밀번호를 잊으면 같은 Shell에서 `python manage.py changepassword 사용자명`을 실행한다.

첫 화면에서 프로젝트를 만든다. 실제 업무는 **테스트 프로젝트** 선택을 끄고, 연습 자료는 선택을 켠다. 현재 업로드 범위는 DXF·PDF·PNG·JPG이며 최대 10 MB다. DXF는 작업자가 객체를 추출하며 PDF·이미지는 검토용 원본으로 보관한다. 실제 업무 단위와 산출 기준은 나중에 확인하며, 파일 보관만 하려면 산출을 실행할 필요가 없다.

배포 스크립트는 합성 도면·테스트 계정·테스트 산출 결과를 운영 DB에 자동 등록하지 않는다. 테스트 프로젝트 표시가 자료 자체의 진위나 산출 정확도를 검증했다는 뜻은 아니다.

## 재배포와 보관

`scripts/serve.py`는 기존 키를 보존하고 DB 변경을 적용한 뒤 정적 파일을 모은다. 작업자 또는 웹 프로세스가 종료되면 부모 프로세스도 실패하여 호스팅의 재시작 대상이 된다. 한 서비스·한 디스크·한 작업자만 사용한다. 인스턴스를 늘리거나 디스크를 다른 서비스에 나눠 연결하지 않는다.

**서비스 재시작/재배포와 서비스·디스크 삭제는 다르다.** 영구 디스크를 삭제하면 보관 자료도 사라질 수 있다. 용량 1 GB는 초기값이며 사용량을 보고 늘려야 한다. 디스크는 백업 자체가 아니다.

같은 서비스 Shell에서 스냅샷을 만들 수 있다.

```bash
python scripts/backup.py --destination /var/data/backups/직접정한-새백업이름
```

이 명령은 SQLite의 일관된 사본과 그 DB가 참조하는 원본/결과, 서명 키, 파일 해시 목록을 별도 폴더에 저장한다. 백업도 비공개 자료다. 같은 디스크 밖의 안전한 저장소에 복사해야 디스크 삭제/장애에 대비할 수 있다. 공개 GitHub나 공개 파일 URL에 올리지 않는다. 외부 자동 백업은 별도 저장소 연결 후 추가할 항목이다.

복원은 서비스 중지 → 비어 있는 별도 디렉터리에 백업 복사 → `AI_PN2_DATA_DIR`를 복원 경로로 지정 → 재시작 → 로그인/원본/결과 확인 순서다. 기존 운영 데이터를 덮어쓰면서 복원하지 않는다.

## 검증 수준과 출처

로컬에서 운영 엔트리포인트와 실제 Gunicorn/WhiteNoise를 사용하여 브라우저 기능 및 같은 디스크 재시작·별도 백업 복원을 검증하는 명령:

```bash
python3 scripts/browser_smoke.py --python /workspace/ai-pn2-venv/bin/python --production
```

이 검사는 localhost에서 HTTP를 사용한다. HTTPS 전달 헤더·보안 쿠키·CSRF 검사는 `tests/test_deployment.py`로 별도 수행한다. 실제 Render TLS·디스크·서비스 재배포는 계정 연결 후 추가 검증해야 한다.

- 실제 읽은 공식 [Render Django 예제](https://github.com/render-examples/django), [배포 명세 예시](https://github.com/render-examples/django/blob/main/render.yaml), [빌드 명령 예시](https://github.com/render-examples/django/blob/main/build.sh)
- 호스팅 단계에서 확인할 [Render Django 배포](https://render.com/docs/deploy-django), [영구 디스크](https://render.com/docs/disks), [Blueprint 명세](https://render.com/docs/blueprint-spec), [가격](https://render.com/pricing)
- 뒤 네 개 일반 웹 페이지는 현재 네트워크 정책에서 직접 열리지 않았다. 현재 비용이나 실제 계정에서의 설정 검증 완료로 보고하지 않는다.
