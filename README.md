# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）→ ETL → 品質チェック → 研究（ファクター計算）→ AI ニュースセンチメント → 市場レジーム判定 → 監査ログ・発注追跡、というワークフローを想定したモジュール群を提供します。

主な用途例:
- 日次 ETL による株価 / 財務 / カレンダーの収集・保存
- ニュースの収集と LLM を用いた銘柄センチメント評価
- ファクター計算・特徴量解析（リサーチ用途）
- 市場レジーム判定（MA + マクロニュースの合成）
- 監査ログ用スキーマ初期化（発注→約定のトレーサビリティ）

---

## 機能一覧

- data
  - jquants_client: J-Quants API からのデータ取得（株価 / 財務 / カレンダー等）、DuckDB への冪等保存
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）の実装（run_daily_etl 等）
  - news_collector: RSS 収集・前処理・raw_news への保存（SSRF 防御、gzip 上限等）
  - calendar_management: JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログ（signal_events / order_requests / executions）の DDL と初期化ヘルパ
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で評価し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA 乖離とマクロニュースセンチメントを合成して market_regime に保存
- research
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー、ランク変換 等
- config
  - 環境変数 / .env 読み込み（プロジェクトルートを自動検出）、必須設定の取得ユーティリティ

設計上の特徴:
- ルックアヘッドバイアスの排除を意識（内部で date.today() を盲目的に使わない等）
- DuckDB を中心としたローカル DB 設計（冪等保存パターン）
- API 呼び出しはリトライ・バックオフ・レートリミット対策済み
- 外部依存は最小限（標準ライブラリ + 必要パッケージ）

---

## 前提・動作環境

- Python 3.9+（型注釈は 3.10 以降の構文を一部使用しているため、3.10 推奨）
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース、OpenAI API）

プロジェクトに requirements.txt / pyproject.toml がある想定で、pip でインストールしてください。例:

python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml

（あるいはリポジトリ配布の setup/pyproject に従ってインストール）

---

## 環境変数（主要）

このライブラリはいくつかの必須・任意環境変数を参照します。`src/kabusys/config.py` が .env/.env.local をプロジェクトルートから自動読み込みします（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必要な場合）
- SLACK_CHANNEL_ID — Slack チャネル ID（必要な場合）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必要な場合）

任意（デフォルト値有り）:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合は 1
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime にも直接渡せます）

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567

---

## セットアップ手順（ローカル実行向け）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - pip install duckdb openai defusedxml

3. 環境変数を設定
   - 環境に合わせて .env を作成するか、シェルでエクスポートしてください。
   - プロジェクトルートに .env を置くと自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。

4. DuckDB 等の DB 用ディレクトリ作成（必要なら）
   - mkdir -p data

5. 監査 DB の初期化（任意）
   - Python REPL やスクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡単なコード例）

以下は代表的なユーティリティの呼び出し例です。すべて DuckDB 接続オブジェクト（duckdb.connect の戻り値）を渡します。

- 日次 ETL を実行する:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメント（LLM）でスコアを生成:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（MA200 + マクロニュース）:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査スキーマ初期化:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を監査ログの読み書きに使用

- 研究用ファクター計算:

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))

---

## 注意事項 / 運用メモ

- OpenAI や J-Quants の API キーは漏洩しないように管理してください。
- LLM 呼び出しはコストがかかるため、バッチ単位・レートに注意して実行してください。
- デフォルトで .env 自動読み込みを行いますが、テスト時などは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany の仕様（空リストを渡せない等）をコード内で考慮していますが、DB のバージョン差異には注意してください。
- run_daily_etl は各段階でエラーハンドリングを行い、処理を続行します。戻り値（ETLResult）で問題の有無を確認してください。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内部の主要モジュール構成（src/kabusys 配下）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
    - (その他研究用ユーティリティ)
  - research/factor_research.py
  - research/feature_exploration.py
  - data/audit.py
  - ...（その他モジュール）

上記以外にも、strategy / execution / monitoring 等のサブパッケージが参照される設計になっています（__all__ に含まれています）が、本リポジトリの提供するコアは上記モジュール群です。

---

## テストとモックについて

- ai モジュール内の OpenAI 呼び出しはテスト容易性のため単独関数（_call_openai_api）で切り出してあり、unittest.mock で差し替えてテスト可能です。
- news_collector はネットワーク部分（_urlopen）をモック可能な設計になっています。

---

## ライセンス / 貢献

本 README はリポジトリのドキュメントに合わせて更新してください。外部 API の利用規約（J-Quants / OpenAI）に従って運用してください。

もし README に追記したい項目（例: CI / テスト手順、より詳細な .env.example、実運用時の cron 設定例 等）があれば指示ください。