# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ KabuSys のリポジトリ README（日本語）。

概要、主要機能、セットアップ、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、ETL、データ品質チェック、特徴量/ファクター計算、ニュースの NLP（LLM によるセンチメント評価）、市場レジーム判定、監査ログ（トレース）などを提供するモジュール群です。  
主にバックテスト／研究用途と運用（ETL・監視・発注監査）用途を想定したユーティリティを含みます。

設計上のポイント：
- Look-ahead bias を避ける設計（target_date を明示、datetime.now()/today() の無秩序な利用を避ける）
- DuckDB をデータ蓄積に利用
- J-Quants API / OpenAI API と統合（リトライ・レート制御・フェイルセーフを実装）
- 冪等保存（ON CONFLICT / upsert）や監査ログによるトレーサビリティ確保

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants から日次株価（OHLCV）、財務データ、上場情報、JPX カレンダーを差分取得・保存（duckdb）
  - ETL の質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL の統合エントリポイント（run_daily_etl）
- ニュース収集 / NLP
  - RSS から記事を収集・正規化して raw_news に保存（SSRF 対策、トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム・バリュー・ボラティリティ等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算 / IC（Information Coefficient） / 統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査 DB 初期化関数（init_audit_db / init_audit_schema）
- 設定管理
  - 環境変数 / .env 自動読み込み（config.Settings）
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## 前提・依存関係

- Python 3.10+
- 必須ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml

（実行環境によっては標準ライブラリ以外の追加パッケージが必要になる場合があります）

---

## 環境変数（主なもの）

config.Settings で参照される主要な環境変数（.env に設定する想定）：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で利用、必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携を行う場合）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用（任意）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用ファイルパス
- KABUSYS_ENV: environment ("development" | "paper_trading" | "live")
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

注意：
- config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動読み込みします。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートしてください。
   - 例（.env の一例）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

   - config モジュールが `.env` / `.env.local` を自動読み込みします。

5. データフォルダの作成（必要に応じて）
   - mkdir -p data

---

## 簡単な使い方（Python API）

以下は主要ユースケースのサンプルです。実行前に必要な環境変数を設定してください（特に OPENAI_API_KEY と JQUANTS_REFRESH_TOKEN）。

- DuckDB 接続を作って日次 ETL を実行する例：

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（score_news）を呼ぶ例：

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数に設定されている前提
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（score_regime）を呼ぶ例：

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化（監査専用 DuckDB を作る）：

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions が作成されます

注意点：
- score_news / score_regime は OpenAI API を呼びます（API キー必須）。API 呼び出しはリトライやフェイルセーフ処理がありますが、API 使用時のコスト・レート制限に注意してください。
- run_daily_etl は J-Quants API を呼びます（JQUANTS_REFRESH_TOKEN が必須）。API 呼び出しでのレート制御・リトライを備えています。

---

## よく使うモジュール／関数

- kabusys.config.settings — 環境設定オブジェクト
- kabusys.data.pipeline.run_daily_etl — 日次 ETL のエントリポイント（ETLResult を返す）
- kabusys.data.jquants_client.* — J-Quants との通信・保存ユーティリティ
- kabusys.data.news_collector.fetch_rss — RSS 取得・整形
- kabusys.ai.news_nlp.score_news — ニュースセンチメントの算出と ai_scores への書き込み
- kabusys.ai.regime_detector.score_regime — 市場レジームの算出と market_regime への書き込み
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査テーブル初期化
- kabusys.research.* — 研究/ファクター計算ユーティリティ

---

## 監視・運用に関するメモ

- config.Settings には PID ファイル・kill flag、CPU/メモリ/ディスク閾値等の監視設定が含まれています。環境変数で調整可能です。
- .env の自動読み込みはプロジェクトルートを .git/pyproject.toml で探索します。CI/テスト等で自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（主要ファイル／モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL 結果クラスの再エクスポート
    - news_collector.py      — RSS 取得・整形
    - calendar_management.py — 市場カレンダー管理
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - quality.py             — 品質チェック（check_missing_data 等）
    - audit.py               — 監査ログスキーマ・初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリー等

---

## テスト・開発

- 単体テストは pytest 等を利用して作成してください（このリポジトリにテストコードがある場合はそれに従います）。
- OpenAI / J-Quants の外部 API 呼び出し部分はモックしてテストすることを推奨します。実装はテスト時に差し替えやすいように設計されています（例: kabusys.ai.news_nlp._call_openai_api を patch）。

---

## ライセンス・貢献

（この README ではライセンス情報は含めていません。実際のリポジトリの LICENSE ファイルを参照してください。）  

貢献する場合は Pull Request / Issue を通じてお願いします。API キーやシークレットをコードや公開リポジトリに含めないでください。

---

必要があれば README にサンプル .env.example やコマンドライン用ラッパー、追加の運用ガイド（cron / systemd の例、監査ログの運用手順）を追記できます。どの情報を優先して追加したいか教えてください。