# 기술 타당성 조사와 구현 결정

확인일: 2026-10-07. 공식 프로젝트 문서를 우선했다. 일반 문서 사이트 일부는 현재 클라우드 egress 정책에서 403이었으므로 접근 가능한 공식 GitHub 저장소의 문서 원문을 읽었다. 아래 근거는 해당 부분 기능을 지원한다는 증거이며 학교 기계설비 전체 업무의 무인 자동화 사례라는 뜻이 아니다.

| 확인한 공식 근거 | 확인 내용 | 개발 결정 |
|---|---|---|
| [ezdxf Introduction](https://github.com/mozman/ezdxf/blob/master/docs/source/introduction.rst) | DXF 읽기/쓰기 Python 도구, DWG 변환 도구와는 별개 | DWG 직접 입력을 약속하지 않고 AutoCAD DXF 저장부터 시작 |
| [ezdxf Units](https://github.com/mozman/ezdxf/blob/master/docs/source/concepts/units.rst) | 좌표 자체는 단위 없는 값, INSUNITS와 블록 단위/축척을 구분 | INSUNITS를 참고값으로 제시하고 사용자 확인 단위로 변환; 블록 내부는 보류 |
| [ezdxf LWPOLYLINE](https://github.com/mozman/ezdxf/blob/master/docs/source/dxfentities/lwpolyline.rst) | bulge의 부호·원호 정의·닫힘 구간 의미 | 곡선을 직선 현으로 잘못 계산하지 않고 원호 길이 검사 추가 |
| [Django 인증 공식 문서](https://github.com/django/django/blob/stable/5.2.x/docs/topics/auth/default.txt) | 사용자·비밀번호·세션·로그인/로그아웃과 접근 제어 | Django 인증 + 프로젝트 소유자별 서버 검사; 자체 비밀번호 암호 설계 안 함 |
| [IfcOpenShell 공식 README](https://github.com/IfcOpenShell/IfcOpenShell/tree/v0.8.0) | IFC 파싱·기하·Python API, Bonsai 저작 도구, ifc5d 비용 정보 도구 | 후속 IFC 후보. 실제 설비 연결/치수/물량은 별도 모델 검증 필요 |
| [Speckle 공식 README](https://github.com/specklesystems/speckle-server) | AEC 데이터 플랫폼, 데스크톱·Excel·각 도구 connector 구성 | 이종 도구 간 데이터 연결의 참고 사례. 첫 버전의 추가 필수 서비스로 도입하지 않음 |

문서의 최신 브랜치와 설치 버전은 별개다. 현재 실행은 `requirements.txt`의 ezdxf 1.4.2 / Django 5.2.18 / openpyxl 3.1.5에서 합성 테스트로 확인했다.

## 가능 범위와 조건

- DXF의 지원된 기본 객체 추출·확정 정보에 대한 길이 계산·엑셀 출력: 현재 환경에서 실행 확인.
- 단일 도면층에 혼재한 설비 의미 자동 판독: 현재 구현하지 않음. 레이어 규칙만으로 해결할 수 없음.
- 원본 CAD 완전 무손실 표준화: 특수 객체·외부참조·응용 데이터와 실제 AutoCAD 열기 검증 필요.
- IFC 생성: 라이브러리 후보는 있지만 높이·연결·분류·속성 모델을 먼저 확정해야 함. 아직 설치·연동 시험하지 않음.
- Revit 편집 모델, AutoCAD/LISP 연동: 사용자 PC 또는 지원되는 Autodesk 실행 서비스와 버전/라이선스 조건 검토 필요. 현재 클라우드에는 해당 실행 능력이 확인되지 않음.
- MQC: 제조사/제품/버전/입력 기능 미확정. API나 가져오기 지원을 주장하지 않음.

## 국내외 유사 제품·사례의 증거 수준

해외 공개 프로젝트로 확인한 IfcOpenShell/Bonsai/ifc5d는 IFC 편집·분석·비용 정보 도구, Speckle은 협업/데이터 교환 도구다. 원본 학교 DWG → 사용자 적산 기준 판독 → BIM MEP → MQC → 납품 자료 전부를 자동 수행한다는 근거는 확인하지 못했다.

국내 MQC 및 국내 유사 제품·특정 업체의 실제 운영 사례는 아직 검증하지 않았다. 사용자 제품 정보가 미확정이고 현재 환경의 일반 웹 공식 사이트 접근에도 제한이 있어, 근거 없는 제조사명·서울/특정 지역 업체 사례를 넣지 않았다. 후속 MQC/상용 제품 선정 전에 공식 설명서·제조사 연동 지원·실제 샘플 입력/출력을 확보하여 비교한다. 국내 사례 조사 완료로 보고하지 않는다.

초기 의사결정에 필요한 DXF·인증·계산 가능성은 위 근거와 실제 실행으로 확인했으므로 사례 조사 때문에 구현을 미루지 않았다.
