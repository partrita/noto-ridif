# Noto-ridif

> [!NOTE]
> **리디바탕(RIDIBatang)의 미려한 본문 활자감과 Noto Serif CJK KR의 압도적인 유니코드 글리프 커버리지를 결합한 합성 명조 폰트**

![](demo.png)

## 📖 서체 소개

**Noto-ridif**는 전자책(E-Book Reader) 및 고해상도 독서 환경에서 널리 사랑받는 **리디바탕(RIDIBatang)**의 유려한 글리프를 기본으로 하고, 누락된 문자나 특수 기호로 인해 발생하는 **Tofu(□, 글자 깨짐)** 현상을 방지하기 위해 **Google Noto Serif CJK KR (본명조)**을 폴백 베이스로 오버레이 병합한 오픈소스 한글 폰트입니다.

### 왜 만들었나요?
- **리디바탕의 뛰어난 가독성**: 긴 문장과 전자책 화면에서 눈의 피로를 덜어주는 특유의 획 구조와 조판 완성도를 제공합니다.
- **Tofu 현상 해결**: 순수 리디바탕 서체에서 지원하지 않는 확장 한자, 특수 부호, 다국어 문자(라틴 확장, 키릴, 그리스 문자 등) 및 수학/도형 기호를 Noto Serif CJK KR의 23,000여 개 글리프로 빈틈없이 채워 넣었습니다.
- **최적화된 글리프 변환**: Cubic(PostScript) 곡선 글리프를 높은 정밀도의 Quadratic(TrueType) 곡선으로 변환하여 임베디드 단말기와 데스크톱 모두에서 빠른 렌더링을 보장합니다.

## ✨ 주요 특징

1. **완벽에 가까운 한글 및 다국어 지원**:
   - 완성형 한글 11,172자 및 고어/옛한글 부호 지원
   - 한자(CJK 통합 한자 및 인명용 한자), 일본어 가나(히라가나/가타카나)
   - 다양한 문장 부호, 단위 기호, 통화 기호($·€·£·¥·₩·₹·₽), 수학 연산자, 기하학 도형
2. **전자종이(E-Paper / E-Reader) 최적화**:
   - 전자책 리더기 단말기에서 바로 사용할 수 있는 바이너리 폰트(`.epdfont`) 변환 스크립트 제공 (1-bit / 2-bit 그레이스케일 지원)
3. **표준 오픈 TTF 포맷**:
   - 모바일, 전자책 뷰어, macOS, Windows, Linux 어디서나 기본 폰트로 즉시 사용 가능


## 🛠️ 빠른 시작 (빌드 및 사용법)

이 프로젝트는 [uv](https://github.com/astral-sh/uv) 패키지 매니저를 사용하여 의존성 설치 및 빌드를 간편하게 수행할 수 있습니다.

### 1. 폰트 직접 빌드하기
기본 소스 폰트(`fonts/NotoSerifKR-Regular.ttf` + `fonts/RIDIBatang.otf`)를 병합하여 새로운 `noto-ridif.ttf`를 생성합니다.

```bash
# 의존성 설치
uv sync

# 폰트 병합 실행 (기본 출력: noto-ridif.ttf)
uv run noto-ridif
```

### 2. 옵션별 사용자 정의 빌드
```bash
uv run noto-ridif \
  --base fonts/NotoSerifKR-Regular.ttf \
  --overlay fonts/RIDIBatang.otf \
  --output custom-noto-ridif.ttf \
  --name "noto-ridif" \
  --max-err 0.5
```

## 📜 포함된 유틸리티 스크립트

자세한 옵션과 고급 사용법은 [scripts/README.md](scripts/README.md)를 참고하세요.

### A5 도서 판형 데모 렌더러 (`scripts/render_demo.py`)
`noto-ridif.ttf`를 사용하여 실제 A5 책 조판 규격의 고품질 데모 이미지(`demo.png`)를 생성합니다.
```bash
uv run python scripts/render_demo.py -f demo.txt -o demo.png
```

### E-Paper 바이너리 폰트 변환기 (`scripts/font_to_epdfont.py`)
E-Reader 단말기(Kindle, Kobo, ESP32 기반 전자종이 등)용 초경량 `.epdfont` 파일로 변환합니다.
```bash
# 2-bit 그레이스케일 (기본값)
uv run python scripts/font_to_epdfont.py noto-ridif 16 noto-ridif.ttf -o noto-ridif_16.epdfont

# 1-bit 모노크롬 모드 (--1bit)
uv run python scripts/font_to_epdfont.py noto-ridif 16 noto-ridif.ttf --1bit -o noto-ridif_16_1bit.epdfont
```


## 🧪 테스트 및 품질 검사

코드 스타일, 린트 및 타입 안전성은 프로젝트 내 자동화 도구를 통해 항상 검사됩니다.

```bash
# 테스트 및 린터/타입 일괄 실행
uv run pytest

# Ruff 코드 스타일 검사
uv run ruff check .

# Ty 정적 타입 검사
ty check .
```

## 📄 라이선스 (License)

`noto-ridif` 글꼴 및 파생 폰트 소프트웨어는 [SIL Open Font License 1.1](LICENSE)에 따라 배포됩니다.

- **개인 및 상업적 이용 무료**: 인쇄물, 웹사이트, 영상, 임베디드 기기, 앱 등 모든 상업적/비상업적 용도로 자유롭게 사용할 수 있습니다.
- **수정 및 재배포 허용**: 글꼴을 자유롭게 수정, 가공, 병합 및 재배포할 수 있습니다.
- **제한 사항**: 
  - 본 폰트 소프트웨어 자체를 단독으로 유상 판매할 수 없습니다.
  - 수정되거나 파생된 모든 폰트 역시 동일한 SIL Open Font License 1.1 조건으로 배포되어야 합니다.
- **기반 서체 저작권**:
  - **Noto Serif CJK KR**: © 2017-2024 Adobe (Licensed under SIL OFL 1.1)
  - **RIDIBatang (리디바탕)**: © 2019 RIDI Corporation & Sandoll Inc. (Licensed under SIL OFL 1.1)
