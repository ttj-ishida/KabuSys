# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得・保存）、ニュース NLP（OpenAI を用いたセンチメント解析）、市場レジーム判定、研究用ファクター計算、監査ログ管理など、トレーディングシステムの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のような用途を想定したモジュール群を含みます。

- J-Quants API を使った株価・財務・マーケットカレンダーの差分 ETL（保存は DuckDB）
- RSS からのニュース収集と記事前処理（SSRF 対策等を実装）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント／マクロセンチメント評価
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
- 研究用途のファクター計算・特徴量探索ユーティリティ
- データ品質チェック（欠損／スパイク／重複／日付整合性）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 環境変数管理（.env 自動読み込み機能あり）

設計方針として、ルックアヘッドバイアス防止、冪等性、外部 API のリトライ／バックオフ、安全な RSS 取得などを重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days 等）
  - ニュース収集（RSS 取得・正規化・保存）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄ごとのセンチメントを ai_scores に保存）
  - レジーム判定（score_regime: ETF 1321 の MA とマクロセンチメントで 'bull'/'neutral'/'bear' を判定）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数 / 設定の読み込みと accessor（settings）

---

## 必要な環境変数

以下は本プロジェクトで参照する主な環境変数です（必須／任意を示します）。実運用前に .env をプロジェクトルートに置くことを推奨します。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY (必須 for AI 機能)
  - OpenAI API キー。ai.score_news / ai.score_regime はこれを参照します（api_key 引数で上書き可）
- KABU_API_PASSWORD (必須 for 発注連携)
  - kabu ステーション（kabusapi）連携パスワード
- KABU_API_BASE_URL (任意)
  - kabu API のエンドポイント（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 for Slack 通知)
- SLACK_CHANNEL_ID (必須 for Slack 通知)
- DUCKDB_PATH (任意)
  - デフォルト DuckDB ファイルパス: data/kabusys.duckdb
- SQLITE_PATH (任意)
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意)
  - 開発環境フラグ: development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意)
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

自動 .env 読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml）が見つかれば自動で `.env` → `.env.local` を読み込みます。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローン（任意）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境の作成と有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必須ライブラリのインストール（例）
   - 本リポジトリはパッケージ化された前提で動作します。最低限必要な依存:
     - duckdb
     - openai
     - defusedxml
   - 開発環境ではさらにテスト・ロギング等が必要かもしれません。

   例:
   ```
   pip install duckdb openai defusedxml
   # またはパッケージを編集可能インストール
   pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env`（と任意で `.env.local`）を作成し、前節の必須変数を設定してください。
   - `.env.example` を用意している場合は参考にしてください（本コードベースでは参照メッセージがあります）。

5. データベース初期化（監査ログ用など）
   - 監査用 DuckDB を初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（主要な実行例）

以下はライブラリの主要な関数の呼び出し例です。実行前に環境変数を設定し、DuckDB 接続等を準備してください。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア付与（ai_scores へ書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  m = calc_momentum(conn, target_date=date(2026,3,20))
  v = calc_value(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  ```

- カレンダー系ユーティリティ
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026,3,20)))
  print(next_trading_day(conn, date(2026,3,20)))
  ```

- 監査テーブル初期化（既存接続に対して）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意:
- AI 系（score_news / score_regime）は OpenAI API キー（OPENAI_API_KEY）を参照します。引数 `api_key` で直接渡すことも可能です。
- J-Quants への API 呼び出しはレート制限とリトライを内包していますが、実 API 実行時は J-Quants 側のレートに注意してください。

---

## ディレクトリ構成

主要ファイル・モジュールのツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン / run_daily_etl 等
    - etl.py                 — ETL インターフェース再エクスポート
    - news_collector.py      — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー管理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ（テーブル DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py     — momentum/value/volatility 等
    - feature_exploration.py — forward returns / IC / summary / rank

この README では主要な API を抜粋しています。詳細は各モジュールの docstring を参照してください。

---

## 注意点 / 運用上のヒント

- ルックアヘッドバイアス対策として、本ライブラリの多くの関数は内部で現在時刻を参照せず、呼び出し元が target_date を明示する設計です。バックテスト時は必ず適切な過去日付を指定してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、モジュール内で空チェックを行っています。運用時の DuckDB バージョンに注意してください。
- RSS 取得は SSRF や XML Bomb 対策を施していますが、カスタムソースを追加する際は URL の正当性とホストの確認を行ってください。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI やテストで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

もし README に追加してほしい内容（セットアップスクリプト、CI 設定、詳しい API リファレンス、実運用チェックリスト など）があれば教えてください。必要に応じて追記します。