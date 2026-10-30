# Noto-ridif

> 리디바탕(RIDIBatang)의 가독성과 Noto Serif CJK KR의 폭넓은 유니코드 커버리지를 결합한 합성 명조 폰트

![](demo.png)

## 소개

Noto-ridif는 전자책 및 고해상도 독서 환경에서 사랑받는 리디바탕의 유려한 글리프를 바탕으로, 글자 깨짐(Tofu, □) 현상을 방지하고자 Noto Serif CJK KR(본명조)을 결합한 오픈소스 폰트입니다.

- 뛰어난 가독성: 긴 문장에서도 눈의 피로를 덜어주는 리디바탕 고유의 조판 완성도를 유지합니다.
- 문자 깨짐 해결: 순수 리디바탕에서 지원하지 않는 확장 한자, 특수 부호, 다국어 문자(라틴 확장·키릴·그리스) 및 수학 기호를 Noto 글꼴 군으로 보완했습니다.
- 렌더링 최적화: 곡선을 정밀한 TrueType(Quadratic)으로 변환하고 TrueType 힌팅을 적용하여 데스크톱과 임베디드 단말기 모두에서 또렷하게 렌더링됩니다.


## 주요 특징

- 완성형 한글 및 CJK 지원: 한글 음절 11,172자 전체, 한글 호환 자모, CJK 통합 한자 8,138자, 일본어 가나 지원
- 다국어 및 기호 확장: 라틴 확장, 결합 발음 구별 기호, 키릴 문자, 통화 기호, 화살표, 수학 기호 완벽 지원
- 다양한 포맷 제공:
  - `TTF`: 데스크톱 및 모바일 기본 폰트
  - `WOFF` / `WOFF2`: 전자책(EPUB) 및 웹 환경을 위한 경량 압축 포맷
  - `.epdfont`: 전자종이(E-Paper) 단말기를 위한 1-bit / 2-bit 바이너리 폰트


## 보장 문자 범위

다음 영역은 빌드 시 무결성 검증(`--verify`)을 거쳐 누락 없이 생성됩니다.

| 범위 | 내용 |
|---|---|
| `U+0020–021F` | 기본 라틴 문자 (영문, 숫자, 기본 문장부호, 유럽 확장 문자) |
| `U+0300–036F` | 결합용 발음 구별 기호 |
| `U+0400–04FF` | 키릴 문자 |
| `U+1EA0–1EF9` | 베트남어 라틴 확장 문자 |
| `U+2000–2060` | 주요 문장부호 (`—`, `…`, `‘`, `’`, `“`, `”`, `※` 등) |
| `U+2070–20BF` | 위·아래 첨자 및 통화 기호 (`₩`, `€`, `₽` 등) |
| `U+2190–21EA` | 화살표 기호 |
| `U+2200–22EF` | 수학 연산자 및 기호 (`∑`, `√`, `∞`, `≠`, `≤`, `≥` 등) |
| `U+3000–301F` | 한중일 문장부호 (`「`, `」`, `『`, `』` 등) |
| `U+3131–318E` | 한글 호환 자모 (`ㄱ`~`ㅎ`, `ㅏ`~`ㅣ`) |
| `U+4E00–9FFF` | CJK 통합 한자 8,138자 |
| `U+AC00–D7A3` | 한글 음절 11,172자 전체 |

---

## 빠른 시작

이 프로젝트는 [uv](https://github.com/astral-sh/uv)를 사용하여 의존성 관리 및 빌드를 수행합니다.

### 폰트 빌드

기본 소스 폰트(`NotoSerifKR-Regular.ttf` + `RIDIBatang.otf`)를 병합하여 `noto-ridif.ttf`를 생성합니다.

```bash
# 의존성 설치
uv sync

# 기본 빌드 (출력: noto-ridif.ttf)
uv run noto-ridif

# 릴리스용 빌드 (힌팅 적용 및 문자 범위 검증)
uv run noto-ridif --hint --verify
```

> 사용자 정의 빌드: 베이스/오버레이 경로 변경 및 오차 허용치 조절은 `uv run noto-ridif --help`를 참고하세요.


## 유틸리티 스크립트

자세한 옵션과 상세 가이드는 [scripts/README.md](scripts/README.md)에 정리되어 있습니다.

- 데모 이미지 생성 (`scripts/render_demo.py`):
  ```bash
  uv run python scripts/render_demo.py -f demo.txt -o demo.png
  ```
- 전자종이 폰트 변환 (`scripts/font_to_epdfont.py`):
  ```bash
  # 본문용 28px (2-bit 그레이스케일)
  uv run python scripts/font_to_epdfont.py noto-ridif 28 noto-ridif.ttf -o noto-ridif_28_2bit.epdfont
  ```
- 웹 폰트 변환 (`scripts/font_to_woff.py`):
  ```bash
  # WOFF 및 WOFF2 동시 생성
  uv run python scripts/font_to_woff.py noto-ridif.ttf --output-dir .
  ```

---

## 라이선스

`Noto-ridif` 및 파생 폰트는 [SIL Open Font License 1.1](LICENSE)에 따라 배포됩니다.

- 상업적/비상업적 무료 이용 가능: 인쇄물, 웹사이트, 영상, 임베디드 기기, 앱 등 자유롭게 사용할 수 있습니다.
- 수정 및 재배포 허용: 글꼴을 자유롭게 수정·가공·병합하여 재배포할 수 있습니다 (단, 폰트 단독 유상 판매 불가 및 동일 OFL 라이선스 적용 필수).

### 기반 서체 저작권

- Noto Serif CJK KR: © Adobe
- Noto Serif / Noto Sans Symbols 2: © The Noto Project Authors
- Noto Sans Math: © Google LLC
- RIDIBatang (리디바탕): © RIDI Corporation & Sandoll Inc.
