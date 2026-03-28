# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ。ETL、ニュース収集・NLP、ファクター計算、監査ログなどのユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム・データプラットフォームを構成する内部ライブラリ群です。主に以下を提供します。

- J-Quants API を使った市場データの差分 ETL（株価・財務・カレンダー）
- RSS ベースのニュース収集と前処理（SSRF対策、サイズ制限、ID生成）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（銘柄別）とマクロレジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）初期化ユーティリティ
- 環境変数 / .env の自動ロード設定

設計上、バックテストにおけるルックアヘッドバイアス防止や冪等性、外部 API のリトライ・レート制御、セキュリティ対策（SSRF、XML ディフェンス等）に配慮しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン自動更新、レートリミット）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS → raw_news、URL 正規化、SSRF 対策）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - 銘柄別ニュース NLP（score_news） — articles をまとめて LLM に投げて銘柄スコアを ai_scores に書き込む
  - マクロレジーム判定（score_regime） — ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime へ書き込み
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- 設定管理（kabusys.config.Settings）
  - .env 自動ロード（プロジェクトルート .git または pyproject.toml 基準）
  - 環境変数必須チェック

---

## セットアップ手順

前提: Python 3.9+ を推奨（typing で | を利用しているため少なくとも 3.10 を想定している実装もあります）。プロジェクト用途に応じて仮想環境を推奨します。

1. リポジトリをチェックアウト／コピー

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   pip で必要な外部依存を追加してください。主要な依存は次の通りです（プロジェクトに合わせて requirements を作成してください）:

   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

   （pip パッケージ名がプロジェクトに合わせて異なる場合があるので、実際の配布パッケージを確認してください）

4. パッケージを開発モードでインストール（プロジェクトルートに pyproject.toml / setup.py がある場合）
   ```
   pip install -e .
   ```

5. 環境変数設定
   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   必須の環境変数（少なくとも以下は設定してください）:
   - JQUANTS_REFRESH_TOKEN   — J-Quants リフレッシュトークン
   - SLACK_BOT_TOKEN         — （通知等を使う場合）Slack Bot Token
   - SLACK_CHANNEL_ID        — Slack の channel id
   - KABU_API_PASSWORD       — kabuステーション API を使用する場合のパスワード
   - OPENAI_API_KEY          — AI モジュールを利用するなら必要（score_news / score_regime で参照）
   オプション:
   - KABUSYS_ENV (development / paper_trading / live) — default: development
   - LOG_LEVEL (DEBUG/INFO/...) — default: INFO
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化
   - DUCKDB_PATH — デフォルト data/kabusys.duckdb
   - SQLITE_PATH — デフォルト data/monitoring.db
   - KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

   簡単な .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な呼び出し例）

以下は主要 API を Python REPL 等から呼ぶ最低限の例です。実運用ではログ設定や例外ハンドリングを適切に行ってください。

- DuckDB 接続を作成して日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai/news_nlp.score_news）を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数に設定しておくか、api_key を直接渡す
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"written: {written}")
  ```

- マクロレジーム判定（ai/regime_detector.score_regime）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を保持して以後の監査ログ書き込みに利用
  ```

- J-Quants API を直接利用する（例: 株価取得）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  from datetime import date

  records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,1))
  print(len(records))
  ```

注意点:
- AI 関連関数（score_news, score_regime）は OpenAI API を叩きます。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / API 呼び出しはネットワークアクセス・API レート制限（J-Quants）などを伴います。認証・トークン設定や rate-limit を遵守してください。

---

## 自動 .env ロードの動作

- 起点ファイルの場所（kabusys/config.py）から親ディレクトリを上へ探索し、.git もしくは pyproject.toml を見つけたディレクトリをプロジェクトルートと判断します。
- 読み込み順序:
  1. OS 環境変数（既存値を保護）
  2. .env（未設定のキーのみセット）
  3. .env.local（存在すれば上書き。ただし OS 環境変数は保護）

- 無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを行いません（テスト用途など）。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要モジュールとファイル一覧（src/kabusys 以下）:

- kabusys/
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
    - pipeline.py (ETLResult エクスポート)
    - etl.py (ETL helper re-export)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（上記はリポジトリに含まれる主要モジュールを抜粋したものです。詳細はソースツリーを参照してください。）

---

## 運用上の注意 / ベストプラクティス

- Look-ahead バイアス防止:
  - AI / ETL / リサーチ関数は内部で date.today() を不用意に使わない設計です。必ず target_date を明示して実行してください。
- リトライとフェイルセーフ:
  - J-Quants クライアントや OpenAI 呼び出しはリトライやフォールバック（デフォルトスコア 0 等）を持ちますが、長時間の障害時はアラート等で監視してください。
- DB スキーマ:
  - DuckDB テーブル名（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar, 等）に依存するため、既存 DB を使用する場合はスキーマ互換を確認してください。
- セキュリティ:
  - news_collector は SSRF 対策・defusedxml を導入していますが、運用中の RSS ソースやネットワーク構成による追加リスク評価を行ってください。
- テスト:
  - 外部 API 呼び出し部はモック可能（コード内で交換ポイントを用意）。ユニットテストで API 呼び出しを実行しないようにしてください。

---

## よく使う API 参照

- ETL 実行: kabusys.data.pipeline.run_daily_etl
- ニューススコア: kabusys.ai.news_nlp.score_news
- レジームスコア: kabusys.ai.regime_detector.score_regime
- 監査スキーマ初期化: kabusys.data.audit.init_audit_db / init_audit_schema
- J-Quants 取得: kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar

---

## 補足

- 本 README はコードベースから読み取れる仕様・使い方をまとめたものです。実運用では追加の設定（ロギング設定、プロセス監視、CI/CD、マイグレーション等）が必要になります。
- 問題や機能追加を行う場合は、コードコメントにある設計方針（ルックアヘッド防止、冪等性、セキュリティ等）を尊重してください。

--- 

必要であれば、README に記載する具体的な .env.example や簡易のスキーマ（DuckDB の CREATE TABLE 文の抜粋）、あるいはよく使う CLI スクリプト例を追加で作成します。どの情報を優先して追記しますか？