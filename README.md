# KabuSys

日本株向けの自動売買・データプラットフォームのライブラリ群です。  
ETL（J-Quants からの株価 / 財務 / カレンダー取得）、ニュース収集と AI によるニュースセンチメント、研究用ファクター計算、監査ログ（発注→約定トレース）などをモジュール化して提供します。

---

## 概要

KabuSys は以下の主要機能を持つライブラリです。

- J-Quants API からの差分 ETL（株価日足 / 財務 / マーケットカレンダー）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（銘柄別）とマクロセンチメント統合による市場レジーム判定
- 研究（research）用のファクター計算（モメンタム / ボラティリティ / バリュー等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → executions）のテーブル定義と初期化ユーティリティ
- 環境変数・設定管理（.env 自動読み込み機能）

設計上の共通方針として、バックテストなどでルックアヘッドバイアスが生じないように
date.today()/datetime.today() を内部処理の基準に直接使わず、呼び出し側から任意の日付を与える形を採用しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（rate limit, retry, token refresh）
  - news_collector（RSS 収集、前処理、SSRF 対策）
  - quality（品質チェック：欠損 / スパイク / 重複 / 日付不整合）
  - calendar_management（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - audit（監査テーブルの初期化・DB 作成）
  - stats（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None) — 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None) — ETF (1321) の MA 差分とマクロセンチメントを合成して market_regime に保存
- research/
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラス（環境変数読み込み、.env 自動ロード、必須チェック）

---

## セットアップ手順

※ 以下は最小限の手順例です。プロジェクトに合わせて適宜調整してください。

1. Python バージョン
   - Python 3.9+ を推奨（型注釈や新しい標準機能を利用）

2. リポジトリをクローン / 取得
   - 例: git clone <repo-url>

3. 開発用インストール（ソースから editable インストール）
   - プロジェクトルートで:
     - pip install -e .

   もし setup 配置がない場合は必要ライブラリを個別にインストールしてください:

   - 主要依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込みます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限設定が必要な環境変数（Settings で必須とされるもの）:

   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
   - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（monitoring 用）
   - SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
   - KABU_API_PASSWORD — kabu ステーション API パスワード（実行モジュール用）
   - OPENAI_API_KEY — OpenAI 呼び出し（AI モジュール）※関数引数で明示的に渡すことも可能

   省略可能（デフォルトあり）:
   - KABUSYS_ENV (development|paper_trading|live) — デフォルトは development
   - LOG_LEVEL — DEBUG/INFO/...（デフォルト INFO）
   - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — SQLite パス（monitoring 用、デフォルト data/monitoring.db）

   .env 例（実際の値は秘匿してください）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxx...
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベースの準備（監査 DB 例）
   - 監査ログ専用 DB を初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL / analytics 用の DuckDB も必要に応じて `duckdb.connect("data/kabusys.duckdb")` で接続してテーブルを作成してください（スキーマ作成ユーティリティがある場合はそちらを使用）。

---

## 使い方（代表的な例）

- 簡単なインポートと設定参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- 日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコア付け（OpenAI API キーは環境変数または api_key 引数で指定）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- 監査テーブルの初期化（既存接続に追加）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注意:
- AI 関連関数（score_news, score_regime）は OpenAI API を呼び出します。API 呼び出し失敗時はフェイルセーフ（多くのケースで 0.0 を返す / スキップ）となるよう設計されていますが、API キー設定は必須です。
- J-Quants 関係の API 呼び出しは JQUANTS_REFRESH_TOKEN（または明示的な id_token 注入）を必要とします。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なモジュールと役割の一覧です。

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数・設定管理（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント解析（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py — ETL パイプライン / run_daily_etl（ETLResult 再エクスポート）
    - etl.py — ETLResult の公開
    - news_collector.py — RSS 収集と前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py — データ品質チェック
    - stats.py — zscore_normalize など統計ユーティリティ
    - audit.py — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（mom, volatility, value）
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
  - ai、data、research 内の多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り SQL と組み合わせて処理します。

---

## 注意点・運用上のヒント

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から実行ファイルを基準に検出します。テストや CI で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB は SQL 実行の互換性差分があるため（executemany の空リスト処理等）、関数内で互換性を配慮した実装になっています。DuckDB のバージョンに依存した問題が出る場合はバージョン揃えを検討してください。
- OpenAI API 呼び出しはリトライ・バックオフ・JSON 検証を行っていますが、レスポンス形式の変更や制限に注意してください（出力は JSON の厳密なフォーマットを要求しています）。
- J-Quants の API レート制限や 401 リフレッシュ処理については jquants_client.py に実装されています。認証エラー・レート制限はログで警告されます。

---

## さらに詳しく / 貢献

- 各モジュールの docstring に設計方針・処理フロー・注意点が記載されています。まずは該当ソースファイルの docstring を参照してください。
- バグ報告・機能追加は issue にて受け付けてください。プルリクエストではコードスタイル・テストを同梱してください。

---

この README はコードベースの主要機能と運用に必要な最小限の情報をまとめたものです。具体的な運用スクリプト（cron / Airflow 等）や CI/CD の設定はプロジェクト固有に合わせて作成してください。