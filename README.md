# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。ETL、ニュースNLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ等のユーティリティをまとめて提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの差分 ETL（株価 / 財務 / 市場カレンダー）
- raw_news を収集・前処理し OpenAI による銘柄別センチメント評価（ニュースNLP）
- ETF とマクロニュースを組み合わせた市場レジーム（bull/neutral/bear）判定
- ファクター（モメンタム/バリュー/ボラティリティ等）計算、特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（信号→発注→約定のトレーサビリティ）用スキーマ初期化
- DuckDB を中心としたローカルデータプラットフォーム設計

設計上の特徴として「ルックアヘッドバイアスの回避」「冪等（idempotent）保存」「API リトライとレート制御」「フェイルセーフ（API エラー時はスキップ or デフォールト値）」を重視しています。

---

## 主な機能一覧

- ETL
  - run_daily_etl: 日次の差分 ETL（カレンダー→株価→財務 → 品質チェック）
  - Individual jobs: run_prices_etl / run_financials_etl / run_calendar_etl
- データ取得（J-Quants）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - save_* 系: DuckDB へ冪等保存
- ニュース収集
  - fetch_rss（SSRF 対策、トラッキング除去、前処理）
- ニュース NLP（OpenAI）
  - score_news: 銘柄ごとのセンチメントを ai_scores テーブルへ書き込み
- 市場レジーム判定（AI + MA）
  - score_regime: ETF(1321)の200日MA乖離 + マクロニュースセンチメントで daily regime を生成
- リサーチ / ファクター
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ
  - init_audit_db / init_audit_schema（監査テーブルおよびインデックスを冪等に作成）
- 設定管理
  - kabusys.config.Settings: .env と環境変数から設定を読み込み（自動ロード機構あり）

---

## 前提条件 / 必要ソフトウェア

- Python 3.10 以上（タイプヒントで `X | Y` を使用）
- 依存パッケージ（例、インストールが必要なもの）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外が必要な部分のみ列挙。実際の requirements.txt を用意してください）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）
   - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードは無効化されます）。

必須（利用する機能に応じて）:
- JQUANTS_REFRESH_TOKEN=...   （J-Quants 用リフレッシュトークン）
- OPENAI_API_KEY=...          （OpenAI API キー、score_news / score_regime で使用）
- KABU_API_PASSWORD=...       （kabuステーション API を使う場合）
- その他（任意）:
  - KABUSYS_ENV=development|paper_trading|live
  - LOG_LEVEL=DEBUG|INFO|...
  - DUCKDB_PATH=（例: data/kabusys.duckdb）
  - SQLITE_PATH=（監視用 DB）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用途）

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要な例）

以下は Python スクリプトや REPL での利用例です。各例では既に必要なパッケージと環境変数が設定されている前提です。

- DuckDB 接続の生成（設定値を使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（OpenAI を使用して ai_scores テーブルへ保存）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# APIキーは環境変数 OPENAI_API_KEY を設定するか、引数 api_key に渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに結果が書き込まれます
```

- 監査ログ DB 初期化（専用ファイル）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/monitoring_audit.duckdb")
# audit_conn は初期化済み接続
```

- ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

- データ品質チェックを実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意:
- OpenAI 呼び出し部分はリトライやフォールバックが実装されていますが、API コストとレート制限に注意してください。
- ETL 系は J-Quants API に依存します。J-Quants のトークン・レート制限に従ってください。

---

## 自動 .env 読み込みについて

- kabusys.config モジュールは、パッケージ import 時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に `.env` と `.env.local` を自動読み込みします。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには、環境変数を設定します:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースはシェルライクな形式（export KEY=val、コメントやクォートを扱う）をサポートします。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュース NPL（score_news）
    - regime_detector.py            # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント（fetch / save）
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - etl.py                        # ETL の公開 API（ETLResult 再エクスポート）
    - news_collector.py             # RSS 収集（SSRF 対策、前処理）
    - calendar_management.py        # 市場カレンダー管理（営業日判定等）
    - quality.py                    # データ品質チェック
    - stats.py                      # 統計ユーティリティ（zscore_normalize 等）
    - audit.py                      # 監査ログスキーマ初期化 / DB 作成
  - research/
    - __init__.py
    - factor_research.py            # ファクター計算（momentum/value/volatility）
    - feature_exploration.py        # 将来リターン / IC / 統計サマリー
  - research/* (他モジュール)
  - ai/* (他モジュール)

---

## 注意点 / 実運用上のヒント

- DuckDB ファイルパスは Settings.duckdb_path（環境変数 DUCKDB_PATH）で指定します。バックアップ・ロールバック運用を検討してください。
- OpenAI 利用はコストが発生します。モデルやバッチサイズは ai.news_nlp の定数で調整可能です（_MODEL/_BATCH_SIZE 等）。
- J-Quants API 利用はレート制限と認証（refresh token）に注意。jquants_client は内部でレート制御とトークン自動更新を行います。
- run_daily_etl は各ステップで例外を捕捉し続行します。戻り値 ETLResult から quality_issues / errors を確認してください。
- テスト時は各種外部呼び出し（OpenAI / HTTP / jquants_client._request など）をモックしてください。モジュール内でテスト用差し替えポイント（例えば _call_openai_api）を用意しています。

---

必要であれば、README に以下を追加できます:
- 開発用のセットアップ（pre-commit, lint, pytest の設定）
- 具体的な SQL スキーマ定義（raw_prices, raw_financials, ai_scores, market_regime など）
- 実行スクリプト（cron / systemd 用の例）
- サンプル .env.example

追加希望があれば教えてください。