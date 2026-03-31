# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL、ニュースのNLPスコアリング、マーケットレジーム判定、ファクター研究、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL と DuckDB への保存
- RSS ニュース収集と OpenAI を用いたニュースセンチメント（ai_score）生成
- マーケットレジーム判定（ETF の MA とマクロニュースの LLM センチメントの合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（シグナル → 注文 → 約定のトレーサビリティ）用のスキーマ初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上、ルックアヘッドバイアスを避ける実装指針が各所に組み込まれています（関数は現在時刻を直接参照しないなど）。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存・トークン自動リフレッシュ・レート制御）
  - カレンダー管理（営業日判定、next/prev/trading days）
  - ニュース収集（RSS → raw_news、SSRF対策、トラッキングパラメータ除去）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news：ニュースの銘柄別センチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime：ETF(1321) MA とマクロニュース LLM を合成して market_regime を更新
- research/
  - factor_research（calc_momentum / calc_value / calc_volatility）
  - feature_exploration（forward returns / IC / summary / rank）
- config：.env 自動読み込み・設定アクセス（settings オブジェクト）

---

## 必要環境・依存

- Python >= 3.10（型ヒントの | 演算子などを使用）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリと urllib, json 等を使用）

プロジェクトの実行環境によって追加パッケージが必要になる場合があります。実運用では仮想環境（venv / virtualenv / poetry など）を推奨します。

---

## 環境変数（主な必須項目）

以下はコード中で必須または推奨されている環境変数の一覧（.env に定義して使用する想定）。

必須（Settings._require で要求されるもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション（発注用）パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

OpenAI 関連（ai モジュールで使用）:
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の api_key 引数で上書き可能）

その他（任意・デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

.env 自動ロード:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を手がかり）から `.env` と `.env.local` を自動読み込みします。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。

例 `.env`（README 用サンプル）:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb

注意: 実運用では秘密情報は安全に管理してください（Vault / CI secrets 等）。

---

## セットアップ手順（開発向け）

1. リポジトリをクローン / コピー
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （必要に応じて開発用パッケージを追加）
4. パッケージを editable インストール（開発）
   - pip install -e .
5. .env を作成して 必須環境変数 を設定
   - 例: .env に前節のサンプル値を記述

---

## 使い方（代表的な操作例）

下記は Python REPL / スクリプト内から呼び出す例です。各例は DuckDB 接続を作成して該当関数を呼ぶスタイルです。

1) DuckDB 接続を用意する:
- Python 内で:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

2) 日次 ETL を実行する（run_daily_etl）:
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

3) ニュースの NLP スコアを生成して ai_scores に保存（score_news）:
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"written: {n_written}")

  - OPENAI_API_KEY は環境変数で読み込まれます。api_key 引数で明示的に渡すことも可能です。

4) 市場レジーム判定（score_regime）:
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))

5) 監査ログ DB の初期化:
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # 以後 conn を使って監査テーブルにアクセス可能

6) ファクター計算（例: モメンタム）:
  - from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    recs = calc_momentum(conn, date(2026,3,20))
    # recs は dict のリスト

7) 設定値にアクセスする:
  - from kabusys.config import settings
    print(settings.duckdb_path, settings.is_live)

ログのレベルは環境変数 LOG_LEVEL で制御できます。

---

## 注意点 / 実装上のポイント

- ルックアヘッドバイアス防止: many 関数は date 引数を受け取り、内部で date.today() を参照しない設計です。バックテスト等では過去日付を指定してください。
- OpenAI 呼び出しは retry/backoff を実装していますが、API 料金とレートを考慮してください。
- J-Quants API のレート制御とトークンリフレッシュを組み込んでいます。JQUANTS_REFRESH_TOKEN を必ず設定してください。
- news_collector は SSRF 対策やレスポンスサイズ制限、XML パースの安全化（defusedxml）などを行っています。
- DuckDB に対する executemany の空リストに関する注意点を内部で考慮しています（空の場合は実行しない）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys をルートとした主要モジュール一覧）

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
    - etl.py (ETLResult re-export)
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - その他（strategy / execution / monitoring 等の公開名を想定）

パッケージ公開時は top-level から "kabusys.data", "kabusys.ai", "kabusys.research" などをインポートして利用します。

---

## テスト / 開発支援

- 環境変数の自動ロードを無効化してテストしたい場合は:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しやネットワーク I/O はテストでモック可能なように設計されています
  - 例: kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で差し替え

---

## 最後に

本 README はコードベースから抽出した主要ポイントをまとめたものです。  
詳細な使い方や運用手順は実運用の要件に合わせて補足してください。質問や追加のドキュメント生成が必要であればお知らせください。