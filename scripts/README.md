# Scripts Guide

이 디렉토리는 폰트 합성, E-Paper 디스플레이용 바이너리 폰트(`.epdfont`) 변환, 데모 프리뷰 이미지 렌더링에 사용되는 유틸리티 스크립트들을 포함합니다.

모든 스크립트는 [`click`](https://click.palletsprojects.com/) 라이브러리를 기반으로 CLI 인터페이스가 구축되어 있으며, 프로젝트 루트에서 `uv run`을 통해 가상환경 및 의존성을 자동으로 불러와 실행할 수 있습니다. 각 스크립트의 상세 도움말은 `--help` 옵션으로 언제든지 확인할 수 있습니다.


## 1. `render_demo.py` (데모 이미지 생성)

`noto-ridif` 폰트를 사용하여 텍스트나 문서를 실제 A5 책(148mm × 210mm) 규격의 조판 문서처럼 자동 줄바꿈(Word wrap)하여 이미지(`demo.png` 등)로 렌더링합니다.

### 사용법

```bash
# 기본 실행: demo.txt 사용
uv run python scripts/render_demo.py

# 특정 텍스트 파일 지정 (-f, --file)
uv run python scripts/render_demo.py -f demo.txt -o preview.png

# 직접 문장 입력 (--text)
uv run python scripts/render_demo.py --text "다람쥐 헌 쳇바퀴에 타고파." -o sample.png
```

### 주요 옵션
| 옵션 | 설명 | 기본값 |
|---|---|---|
| `--font` | 렌더링에 사용할 폰트 파일 경로 | `noto-ridif.ttf` |
| `-o`, `--output` | 출력 이미지 파일 경로 | `demo.png` |
| `-f`, `--file` | 렌더링할 텍스트 파일 경로 | (기본적으로 `demo.txt` 탐색) |
| `--text` | 직접 지정할 텍스트 문자열 | (지정되지 않으면 파일 또는 기본 텍스트) |
| `--size` | 폰트 크기 (pt) | `22` (A5 본문 최적) |
| `--width` | 페이지 가로 폭 (px) | `874` (A5 150DPI 기준) |
| `--height` | 페이지 세로 높이 (px) | `1240` (A5 150DPI 기준) |
| `--auto-height` | 텍스트가 1페이지를 초과할 경우 세로 길이를 자동 연장 | `False` |

---

## 2. `font_to_epdfont.py` (E-Paper 폰트 바이너리 변환기)

TTF 및 OTF(OpenType) 글꼴을 전자책(E-Reader) 및 전자종이(E-Paper) 단말기에서 바로 읽을 수 있는 컴팩트한 `.epdfont` 바이너리 포맷으로 변환합니다. 다중 폰트 폴백(Fallback Stack), 자간, 장평, 베이스라인 오프셋, 1비트 모노크롬 및 2비트 그레이스케일 모드를 지원합니다.

> [!TIP]
> **권장 폰트 크기:**
> - **본문용**: `28` (가독성과 정보량 균형에 최적)
> - **UI용**: `20` (메뉴, 상태 표시줄, 헤더/푸터 등 작은 인터페이스에 최적)

### 사용법
```bash
# 본문용 28px, 2-bit 그레이스케일
uv run python scripts/font_to_epdfont.py noto-ridif 28 fonts/noto-ridif.ttf -o noto-ridif_28_2bit.epdfont

# UI용 20px, 2-bit 그레이스케일
uv run python scripts/font_to_epdfont.py noto-ridif 20 fonts/noto-ridif.ttf -o noto-ridif_20_2bit.epdfont

# 전자종이에서 획을 조금 더 진하게 (gamma < 1)
uv run python scripts/font_to_epdfont.py noto-ridif 28 fonts/noto-ridif.ttf --gamma 0.85 -o noto-ridif_28_dark.epdfont

# 1-bit 모노크롬 모드 (--1bit)
uv run python scripts/font_to_epdfont.py noto-ridif 20 fonts/noto-ridif.ttf --1bit -o noto-ridif_20_1bit.epdfont

# 자간(letter-spacing) 및 장평(width-scale), 줄간격(line-height) 조정
uv run python scripts/font_to_epdfont.py noto-ridif 18 fonts/noto-ridif.ttf \
  --line-height 1.25 \
  --letter-spacing 1 \
  --width-scale 0.95 \
  -o noto-ridif_18.epdfont

# 다중 폰트 폴백 스택 지정 (우선순위 순서대로 나열)
uv run python scripts/font_to_epdfont.py merged 16 fonts/primary.ttf fonts/fallback.ttf -o merged_16.epdfont
```

### 주요 옵션
| 옵션 | 설명 | 기본값 |
|---|---|---|
| `name` | 폰트 식별자 이름 | (필수) |
| `size` | 폰트 픽셀 크기 (px, 본문용 28, UI용 20 추천) | (필수) |
| `fontfiles` | 폰트 파일 경로들 (우선순위 순) | (필수) |
| `-o`, `--output` | 출력 바이너리 파일 경로 | `<name>_<size>.epdfont` |
| `--2bit / --1bit` | 2-bit 그레이스케일 비트맵(기본) 또는 1-bit 흑백 모노크롬 생성 | `--2bit` (기본값) |
| `--line-height` | 줄 간격(Line Height) 배율 | `1.2` (120%) |
| `--letter-spacing`| 글자 사이 추가 간격(px) | `0` |
| `--width-scale` | 장평(너비 비율) 배율 | `1.0` (100%) |
| `--baseline-offset` | 베이스라인 수직 오프셋(px, 양수=위로) | `0` |
| `--gamma` | 2-bit 그레이스케일 감마 (<1은 중간톤을 진하게, >1은 연하게) | `1.0` |
| `--additional-intervals` | 추가 포함할 유니코드 범위 (`MIN,MAX`) | - |
