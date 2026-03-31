# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータ取得・品質管理・特徴量算出・ニュース NLP（LLM）・市場レジーム判定・監査ログなどを統合した自動売買／リサーチ基盤ライブラリです。DuckDB をデータ格納に用い、J-Quants API や RSS、OpenAI（gpt-4o-mini）を活用する設計になっています。

---

## プロジェクト概要

- データ取得（J-Quants）: 株価日足、上場銘柄情報、財務データ、JPX カレンダーを差分で取得し DuckDB に保存します（ETL）。
- データ品質チェック: 欠損、スパイク、重複、日付不整合などを自動検出します。
- ニュース処理 & NLP: RSS 取得 → 前処理 → OpenAI による銘柄別センチメント算出（ai_scores へ保存）。
- 市場レジーム判定: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して日次レジーム（bull/neutral/bear）を算出します。
- リサーチ用機能: モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC 計算、Z スコア正規化等。
- 監査ログ（audit）: シグナル → 発注 → 約定のトレーサビリティを担保する監査用テーブルの初期化ユーティリティ。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - ニュース収集（RSS の安全取得・前処理・raw_news への保存補助）
  - 品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを取得して ai_scores に書き込む
  - regime_detector.score_regime: 日次の市場レジームを算出して market_regime に書き込む
- research/
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数 / .env 読み込みと Settings オブジェクト（settings）を提供

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージをインストール）して、Python 仮想環境を作成・有効化します。

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要なパッケージをインストールします（プロジェクトに requirements.txt があればそれを使用してください）。主な依存例:

   ```bash
   pip install duckdb openai defusedxml
   ```

   - duckdb: データ格納・クエリ
   - openai: LLM 呼び出し（gpt-4o-mini を利用）
   - defusedxml: RSS パースの安全化
   - 標準ライブラリ以外の他ライブラリがある場合は適宜追加してください。

3. 環境変数を設定します。プロジェクトルート（.git または pyproject.toml を基準）に `.env` を置くと自動で読み込まれます（読み込み順: OS 環境 > .env.local > .env）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例 `.env`（必須項目はプロジェクトで実際に使う機能に応じて設定）:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=sk-...

   # kabuステーション（注文連携がある場合）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（通知がある場合）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...

   # DB/監視
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PID_FILE_PATH=data/execution.pid

   # 環境設定
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

4. データディレクトリなど（DuckDB パスの親ディレクトリ）を作成しておきます:

   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は基本的な利用例です。実行は任意の Python スクリプトや REPL から行えます。

- Settings (環境変数読み込み)

  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 環境変数が未設定なら例外
  ```

- DuckDB 接続を作って日次 ETL を実行

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（LLM）を計算して ai_scores テーブルへ保存

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written_count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print("書き込んだ銘柄数:", written_count)
  ```

- 市場レジーム判定

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査ログ用 DB の初期化

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # parent dir を自動作成
  ```

- リサーチ用ファクター計算

  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

- 市場カレンダー判定（営業日判定）

  ```python
  from kabusys.data.calendar_management import is_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  is_trading_day(conn, date(2026,3,20))
  ```

注意点:
- LLM / J-Quants を利用する機能は API キーが必要です。未設定の場合は ValueError が発生します。
- モジュールの関数はルックアヘッドバイアス対策として内部で date.today() を安易に参照しない設計になっています。target_date を明示して呼ぶことを推奨します。
- score_news / score_regime は OpenAI のレスポンスを JSON モードで扱いますが、失敗時は安全にフォールバックする設計です（例: スコア 0.0、またはスキップ）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（注文連携）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH: 実行監視用 PID ファイルパス（デフォルト data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 環境 ("development", "paper_trading", "live")
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化します。

---

## 自動 .env 読み込みについて

- config モジュールはパッケージの位置からプロジェクトルート（.git または pyproject.toml）を探索し、`.env` を読み込みます。
- 読み込み順は OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。
- 読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（主要ファイル/モジュールの一覧）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - etl.py (ETLResult エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research (exports zscore_normalize 等)
- README.md (このファイル)

各モジュールは概ね以下の責務を持ちます:
- data/*: データ取得・保存・品質・カレンダー・監査等の基盤機能
- ai/*: ニュース NLP と市場レジーム判定（OpenAI 呼び出し）
- research/*: ファクター・統計・特徴量解析

---

## 注意事項 / ベストプラクティス

- DuckDB のスキーマ（テーブル）がプロジェクトや ETL で期待される形になっていることを確認してください。初期スキーマ作成用のSQL は別途プロジェクト内にある想定です（必要に応じて init スクリプトを用意してください）。
- ETL を定期バッチで回す場合は J-Quants API のレート制限や OpenAI の利用制限に注意してください（モジュール内でレート制御・リトライ実装あり）。
- 本ライブラリは本番口座での発注処理システムと統合されうる構成を想定しています。実際の注文送信前に十分なテスト（paper_trading / sandbox）を行ってください。
- OpenAI 呼び出しをテストでモックする際には、内部の _call_openai_api をパッチすることを推奨します（news_nlp、regime_detector それぞれ独立実装を持ちます）。

---

質問や追加のドキュメント（例: スキーマ定義、運用手順、デプロイ手順）が必要であれば教えてください。必要に応じて README に含めるサンプルスキーマや運用チェックリストも作成します。