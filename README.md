# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ。  
ETL（J-Quants→DuckDB）、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、ファクター研究、監査ログ等のユーティリティ群を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数
- ディレクトリ構成（主要ファイル）

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームと自動売買の基盤を想定した Python パッケージです。J-Quants API からデータを取り込み、DuckDB に保存・品質チェックを行い、ニュースのセンチメント（OpenAI）を用いた AI スコアや市場レジーム判定、因子計算・研究用ユーティリティ、監査ログ（注文→約定のトレーサビリティ）などを提供します。

設計上の特徴:
- Look-ahead bias を避ける（関数内部で date.today()/datetime.today() を直接参照しない）
- DuckDB を中心としたローカル DB 設計
- 冪等性を意識した保存ロジック（ON CONFLICT / DELETE→INSERT）
- API 呼び出しにはリトライ・バックオフ・レート制御を実装
- セキュリティ/安全策（RSS の SSRF 対策、XML の defusedxml 使用 等）

---

## 機能一覧

主要な機能（モジュール別）:

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出），設定アクセス用 Settings
- kabusys.data
  - jquants_client: J-Quants API 取得／保存（株価、財務、マーケットカレンダー等）
  - pipeline: 日次 ETL（run_daily_etl）／個別 ETL
  - news_collector: RSS 収集・前処理・raw_news 保存支援（SSRF対策）
  - calendar_management: 営業日判定・next/prev trading day 等
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - stats: z-score 正規化ユーティリティ
  - audit: 監査ログ（signal_events, order_requests, executions）スキーマ初期化
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM（gpt-4o-mini）で銘柄別センチメント取得→ai_scores 保存
  - regime_detector.score_regime: ETF (1321) の MA200 とマクロニュースセンチメントを合成して市場レジーム判定
- kabusys.research
  - factor_research: momentum/volatility/value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（情報係数）など

---

## セットアップ手順

前提: Python 3.10+（型注釈で | を使用しているため）、DuckDB 等の依存をインストールしてください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実運用では追加の依存やバージョンを requirements.txt / pyproject.toml に記載してください。

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（設定の競合解決あり）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
   - 必須の環境変数は後述の「環境変数」セクション参照。

5. DuckDB 初期化（監査ログ用の DB を作る例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   - `init_audit_db` は親ディレクトリを自動作成します。

---

## 簡単な使い方（例）

- DuckDB 接続を作成して日次 ETL を実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアを生成する例（OpenAI API キーが必要）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム判定（OpenAI API キーが必要）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査スキーマ初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

注意:
- OpenAI の呼び出しは gpt-4o-mini を使用する想定（モデル名はモジュール内定義）。API レートやコストに注意してください。
- ETL / API 呼び出しはネットワーク/認証の失敗に対するリトライを含みますが、適切な環境変数とトークンが必要です。

---

## 環境変数

主要な環境変数（config.py, 各モジュールで参照）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注周りで使用）
- SLACK_BOT_TOKEN: Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）

任意（デフォルト値あり）:
- KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL: "DEBUG"/"INFO"/...
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default data/monitoring.db）
- PID_FILE_PATH: 実行監視用 PID ファイルパス
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効にする

.env ファイルを用意する際はプロジェクトルート（.git または pyproject.toml があるディレクトリ）に置きます。ファイルのパースは一般的な .env 形式（export を含む行やコメント、クォート形式）に対応しています。

---

## 注意点 / 運用上の補足

- DuckDB への insert/update は冪等性を重視していますが、ETL を運用する際はバックアップや監査ログを併用してください。
- OpenAI 呼び出しは JSON Mode を使い厳格に構造化レスポンスを期待しますが、万一のパース失敗はフェイルセーフ（0.0にフォールバック等）で設計されています。
- news_collector の RSS 取得は SSRF 対策（プライベートIP拒否、リダイレクト検査、最大レスポンスサイズ制限）を実装しています。外部入力 URL を直接実行する場合は注意してください。
- テスト時は環境変数自動ロードを無効化したり、OpenAI／ネットワーク呼び出し箇所をモックすることを推奨します（モジュール内に差し替えポイントあり）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールと説明）

- __init__.py
  - パッケージメタ情報（バージョン、公開モジュール）

- config.py
  - 環境変数ロードと Settings クラス（アプリ設定）

- ai/
  - __init__.py
  - news_nlp.py            : ニュースの LLM スコアリング、ai_scores への書き込み
  - regime_detector.py     : ETF MA200 とマクロニュースを合成する市場レジーム判定

- data/
  - __init__.py
  - jquants_client.py      : J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py            : ETL パイプライン（run_daily_etl 等）
  - etl.py                 : ETLResult の再エクスポート
  - news_collector.py      : RSS 収集・前処理（SSRF 対策含む）
  - calendar_management.py : JPX カレンダー管理・営業日判定
  - quality.py             : データ品質チェック群
  - stats.py               : 統計ユーティリティ（zscore_normalize）
  - audit.py               : 監査ログテーブル定義・初期化

- research/
  - __init__.py
  - factor_research.py     : Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py : 将来リターン・IC・統計サマリー等

---

必要に応じて README に含める追加のコマンド（例: マイグレーション、スキーマ初期化、cron/ジョブ設定、監視手順等）を追記できます。README の補足や特定の使い方サンプル（ETL スケジュール例、バックテストでの使用注意など）が必要であれば教えてください。