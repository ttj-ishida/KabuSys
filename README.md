# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。データ取得（J-Quants）、ETL、ニュース NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム開発のためのユーティリティ群です。主に以下を目的としています。

- J-Quants API からの株価 / 財務 / 市場カレンダー等の差分取得と DuckDB への保存（ETL）
- RSS ニュース収集と前処理、安全対策（SSRF 対策、サイズ制限等）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別）とマクロセンチメント評価
- ETF とマクロセンチメントを合成した市場レジーム判定（bull / neutral / bear）
- ファクター計算（Momentum / Volatility / Value 等）と特徴量探索ユーティリティ
- 監査ログ（signal → order_request → execution）用のスキーマ生成・初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上の特徴：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を不用意に参照しない）
- ETL・保存処理は冪等（ON CONFLICT）で安全
- API 呼び出しはリトライ / バックオフ / レート制御を備える
- ネットワーク周りに対する安全対策（SSRF、レスポンスサイズ制限、gzip扱い等）
- テストしやすいよう依存注入・モック差し替え箇所を確保

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・ページネーション・レート制御）
  - pipeline: 日次 ETL パイプライン（run_daily_etl / run_prices_etl / ...）
  - news_collector: RSS 収集、前処理、raw_news への保存ロジック（SSRF 対策、gzip 対応）
  - calendar_management: JPX カレンダー管理、営業日判定、夜間更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit: 監査ログスキーマの初期化と監査 DB 作成補助
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 記事を銘柄ごとに集約し OpenAI でセンチメント評価、ai_scores へ書き込み
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースの LLM センチメントを合成して market_regime を書き込み
- research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数読み込み・管理（.env 自動ロード、必須チェック、settings オブジェクト）

---

## セットアップ手順

（以下は一般的な Python 開発環境構築手順です。プロジェクトの packaging/依存管理に合わせて調整してください。）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 本コードベースで想定される主な依存：
     - duckdb
     - openai
     - defusedxml
   例：
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実際の requirements.txt や pyproject.toml がある場合はそちらを使用してください（例: pip install -r requirements.txt）。

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を作成すると、自動でロードされます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（.env に記述する例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development         # development | paper_trading | live
   LOG_LEVEL=INFO                  # DEBUG | INFO | WARNING | ERROR | CRITICAL
   ```

---

## 使い方（主要ワークフローと例）

以下は代表的な利用方法の一例です。DuckDB を使った ETL 実行や AI スコアリング、監査 DB 初期化のスニペットを示します。

- DuckDB 接続を用意して ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect('data/kabusys.duckdb')  # settings.duckdb_path でも可
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄ごと）を計算して ai_scores テーブルに書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect('data/kabusys.duckdb')
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

  - OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定します。

- 市場レジームを判定して market_regime テーブルへ保存する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect('data/kabusys.duckdb')
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DuckDB を初期化する（監査ログ専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db('data/audit.duckdb')
  # これで signal_events, order_requests, executions 等のテーブルが作成されます。
  ```

- データ品質チェックを走らせる
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

- 設定参照（settings）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## 環境変数と設定（主要項目）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: メイン DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: モニタリング用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 動作モード（development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

config.Settings にプロパティとしてアクセスできます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成

以下は主要なファイル・モジュールの構成（src/kabusys 以下）です。README の作成時点のコードベースに基づきます。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント解析（銘柄別）
    - regime_detector.py            — 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 / 保存 / 認証）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult 再エクスポート
    - news_collector.py             — RSS 収集 / 前処理 / 保存
    - calendar_management.py        — 市場カレンダー管理 / 営業日判定
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility 等
    - feature_exploration.py        — 将来リターン計算 / IC / 統計サマリー
  - research/__init__.py
  - ほか（将来的に strategy / execution / monitoring などが想定される）

---

## 設計上の注意点（運用時ガイド）

- OpenAI / J-Quants など外部 API 呼び出しはネットワーク/料金に依存します。API キーの管理・呼び出し頻度には注意してください。
- run_daily_etl は複数ステップで独立してエラーハンドリングします。欄外の問題は ETLResult に集約されます。
- DuckDB に対する executemany/バルク操作はバージョンによって挙動差があるため、pipeline/news_nlp 内で空パラメータを渡さない等の配慮があります。
- ニュース収集は RSS の内容サイズ・エンコーディング・gzip に注意。SSRF 等の対策は実装されていますが、運用ポリシーに従ってホワイトリスト管理を行ってください。
- 本ライブラリの関数はバックテストでのルックアヘッドバイアス防止を意識して設計されています。バックテスト内で利用する際は、取得済みデータのみを参照する等の運用を徹底してください。

---

## 貢献・拡張のヒント

- news_nlp / regime_detector の OpenAI 呼び出しはクライアント関数をモック可能に実装しているため、テストを書きやすくなっています。ユニットテストでは _call_openai_api を patch してください。
- jquants_client は rate limiter やトークンリフレッシュを備えています。追加の API エンドポイントが必要な場合は同様の設計を踏襲してください。
- audit.init_audit_schema はトランザクションオプションを持ちます。監査データの初期化・移行スクリプトを作成する際に活用してください。

---

もし README に追記してほしい使用例（たとえば Docker での実行、CI ワークフロー、より詳細な .env.example のサンプルなど）があれば教えてください。必要に応じて実行コマンドやサンプル .env.example ファイルを追加します。