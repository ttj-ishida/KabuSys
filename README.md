# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（発注〜約定のトレーサビリティ）、市場レジーム判定など、バックテスト／運用で必要となる基盤機能を提供します。

バージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主な API の例）
- 環境変数（.env 例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けのデータ基盤と研究／運用ユーティリティの集合です。主な設計方針は以下の通りです。

- Look-ahead bias を避ける（内部で現在時刻を直接参照しない関数設計）
- DuckDB を中心としたローカルデータベース管理（ETL の冪等性を重視）
- 外部 API 呼び出し（J-Quants / OpenAI 等）に対するリトライとレート制御
- ニュース収集・NLP はロバストに（SSRF 対策、XML パース安全対策、レスポンスサイズ制御）
- 監査ログ（signal → order_request → execution）で完全なトレーサビリティを確保

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / 環境変数の自動ロード（プロジェクトルート検出）
  - アプリケーション設定アクセス（settings）
- kabusys.data
  - jquants_client: J-Quants API クライアント（差分取得、ページネーション、保存関数）
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl 等）
  - news_collector: RSS から raw_news を収集（SSRF 対策・XML 防御）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定
  - audit: 監査ログスキーマ初期化・監査 DB ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM に投げて銘柄別センチメント（ai_scores）を作成
  - regime_detector.score_regime: ETF（1321）の MA200 とマクロ記事センチメントを合成して市場レジームを判定
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（研究支援ユーティリティ）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（| 演算子などの型注釈を使用）
- Git が利用できる環境

1. リポジトリをクローンする（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（最小セット）
   ```
   pip install duckdb openai defusedxml
   ```
   ※プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。

4. パッケージを editable インストール（開発時）
   ```
   pip install -e .
   ```
   （プロジェクトが packaging を提供している場合）

5. 環境変数を設定する
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数は次節を参照してください。

---

## 環境変数（.env 例）

config モジュールはプロジェクトルート（.git または pyproject.toml を起点）を探索して `.env`/.env.local を読み込みます。`.env.local` は `.env` をオーバーライドします。

最低限必要なキー（コードで参照されるものの抜粋）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot Token（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に参照）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

サンプル .env:
```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
OPENAI_API_KEY="sk-..."
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
SQLITE_PATH="data/monitoring.db"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主な例）

以下は簡単な対話的使用例です。スクリプトやジョブから呼び出して運用します。

- DuckDB 接続を作成する例
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースをスコアリングして ai_scores に書き込む
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026, 3, 20))  # OPENAI_API_KEY を環境変数/引数で指定可能
  ```

- 市場レジームを判定する（1321 の MA200 とマクロ記事センチメントの合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20))
  ```

- 監査ログ DB を初期化する（監査用専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests / executions 等に記録できます
  ```

- RSS を取得する（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, date(2026,3,20))
  ```

注意点:
- score_news / score_regime は OpenAI API を使用します。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- ETL / 保存処理は DuckDB テーブルが所定のスキーマで存在することを前提としています（スキーマ初期化ロジックは別途実装されている想定）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールと概要です（コードベースから抽出）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・settings 提供
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None)
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None)
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch_*, save_*）
    - pipeline.py
      - ETLResult dataclass, run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
    - news_collector.py
      - fetch_rss, RSS 前処理、SSRF 対策
    - calendar_management.py
      - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
    - quality.py
      - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
    - stats.py
      - zscore_normalize
    - audit.py
      - 監査ログスキーマ初期化（init_audit_schema, init_audit_db）
    - etl.py
      - ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank

---

## 運用上の注意 / ベストプラクティス

- 環境変数は secrets 管理（Vault 等）を推奨。`.env` は開発用に限定して管理してください。
- OpenAI / J-Quants の API キーやトークンは適切にローテーション・権限管理を行ってください。
- ETL はジョブとしてスケジュール（夜間）実行を想定しています。ETL 実行後に品質チェック（quality.run_all_checks）を行い、問題があればアラートを出す運用を推奨します。
- 監査ログは削除しない前提です。DB バックアップと容量監視を行ってください。
- テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化できます。

---

## 貢献 / ライセンス

本 README では割愛します。リポジトリの CONTRIBUTING / LICENSE ファイルを参照してください。

---

必要であれば、README に「起動スクリプト」「systemd / cron ジョブサンプル」「SQL スキーマ初期化スクリプト例」などの追加セクションを追記できます。どの部分を詳しく書くか指示ください。