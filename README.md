# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants（株価・財務・カレンダー）や RSS ニュース、OpenAI を活用してデータ取得、品質チェック、ニュース NLP、マーケットレジーム判定、ファクター計算、監査ログなどを一貫して提供します。

主な用途:
- データプラットフォーム（株価 / 財務 / カレンダーの ETL と品質チェック）
- ニュース収集・NLP による銘柄別センチメント生成
- マーケットレジーム判定（MA200 とマクロニュースの合成）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 取引監査ログ（signal → order_request → execution のトレーサビリティ）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理（.env の自動ロード、必須環境変数チェック）
- J-Quants API クライアント（ページネーション・トークン自動更新・レート制御・リトライ）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（JPX カレンダーの差分更新、営業日判定ユーティリティ）
- ニュース収集（RSS 収集、SSRF 対策、トラッキングパラメータ除去、前処理）
- OpenAI を用いたニュース NLP（銘柄ごとのセンチメントスコアを生成）
- マーケットレジーム判定（ETF 1321 の MA200 乖離 + マクロニュース）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- 統計ユーティリティ（Z-score 正規化など）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ初期化（signal, order_request, executions 等のテーブル定義・インデックス）

---

## セットアップ手順

前提
- Python 3.9+（typing の一部機能が使われています）
- DuckDB を利用（ローカルファイル or :memory:）

推奨インストール例（プロジェクトルートで）:

1. 仮想環境作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージのインストール（例）
   必要な主要パッケージ：
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外の依存がある場合は requirements.txt を用意してください）

   例:
   ```bash
   pip install duckdb openai defusedxml
   # プロジェクトを編集可能モードでインストールする場合
   pip install -e .
   ```

3. 環境変数設定
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（読み込みはプロジェクトルート判定に .git または pyproject.toml を使用）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（関数・機能に応じて必要になります）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に必要）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注等を行う場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知宛先チャンネル
   任意（デフォルトあり）:
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: duckdb データベースパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   例 `.env`（一部）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. データベース初期化（監査ログなど）
   監査ログ用の DuckDB を初期化する例:
   ```python
   from pathlib import Path
   import duckdb
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db

   db_path = settings.duckdb_path  # Path オブジェクト
   conn = init_audit_db(db_path)   # テーブルとインデックスを作成して接続を返す
   ```

---

## 使い方（主要機能の例）

以下は最小限の利用例です。実行前に必ず設定（.env / 環境変数）を行ってください。

- DuckDB 接続を作る:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別スコア）を実行する:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API key は環境変数 OPENAI_API_KEY か引数で指定
  print("written:", written)
  ```

- 市場レジーム判定を実行する:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマを初期化する（既存 DB に付与する場合）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算 / リサーチ:
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- カレンダー更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from datetime import date

  saved = calendar_update_job(conn, lookahead_days=90)
  print("saved calendar records:", saved)
  ```

注意:
- OpenAI を利用する関数（score_news, score_regime）は API 呼び出しを行います。テストやモックを使う場合は内部の _call_openai_api をパッチする設計になっています。
- DuckDB に対する INSERT は多くが冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装されています。
- ETL / スコアリング関数は内部で日付の扱いに注意（ルックアヘッド回避）して実装されています。

---

## ディレクトリ構成

主要なファイル・モジュール（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # ニュース NLP（銘柄別スコア）
    - regime_detector.py    # マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント（取得・保存）
    - pipeline.py           # ETL パイプラインの実装（run_daily_etl 等）
    - etl.py                # ETLResult 再エクスポート
    - calendar_management.py# 市場カレンダー管理（営業日判定等）
    - news_collector.py     # RSS ニュース収集
    - quality.py            # データ品質チェック
    - stats.py              # 統計ユーティリティ（zscore_normalize 等）
    - audit.py              # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    # ファクター計算（momentum/value/volatility）
    - feature_exploration.py# 将来リターン・IC・統計サマリー等
  - monitoring/ (存在する場合、監視系コード)
  - execution/  (発注実装、kabuステーション接続等)
  - strategy/   (取引戦略定義。StrategyModel 等)

（上記はコードベースに含まれる主要モジュールの一覧です。実際のリポジトリには他の補助モジュールや CLI、テスト等が存在する場合があります）

---

## 設定と運用上の注意

- 環境変数は .env/.env.local から自動で読み込まれます（プロジェクトルートが .git または pyproject.toml によって検出されます）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI・J-Quants 呼び出し部分は外部 API なのでレート制限や課金に注意してください。テスト時は関数をモックする設計になっています。
- DuckDB によるデータ保存は多くの場合冪等化されていますが、運用スクリプトではバックアップやトランザクションの扱いに留意してください（init_audit_schema の transactional オプション等）。
- ログレベル・環境切替（development / paper_trading / live）は環境変数 `KABUSYS_ENV` / `LOG_LEVEL` で制御します。`KABUSYS_ENV` の有効値は development, paper_trading, live です。

---

もし README に追加したい具体的な使い方（例: ETL をスケジューラで回す手順、kabuステーションとの接続設定、Slack 通知の例、あるいは Docker 化手順など）があれば、必要な想定環境や要件を教えてください。それに合わせて追記します。