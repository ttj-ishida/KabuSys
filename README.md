# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、市場レジーム判定、研究用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- 環境変数ベースの設定管理（自動でプロジェクトルートの .env/.env.local を読み込む）
- J-Quants API クライアント
  - 日足株価（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得（ページネーション対応）
  - レート制御・リトライ・401 リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン（run_daily_etl）
  - カレンダー・株価・財務の差分取得と保存、品質チェックの一括実行
  - 実行結果を ETLResult として返却
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキング除去、ID 発行）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメントを ai_scores に書き込む（score_news）
  - 市場マクロセンチメントと ETF MA を組み合わせた市場レジーム判定（score_regime）
- 研究用モジュール
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - クロスセクション Z スコア正規化ユーティリティ
- 監査ログ（audit schema）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ヘルパ
  - order_request_id による冪等性、UTC タイムスタンプ管理

---

## 要求事項・依存関係

- Python 3.10+
- 主要パッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリの urllib / json 等を使用

requirements.txt や pyproject.toml はプロジェクト側で管理してください。

---

## セットアップ手順

1. リポジトリをクローン / ソース取得

2. 仮想環境を作成・有効化（推奨）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要ライブラリをインストール（例）

   ```bash
   pip install duckdb openai defusedxml
   ```

4. パッケージをインストール（開発モード）

   ```bash
   pip install -e .
   ```

5. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと、モジュール import 時に自動で読み込まれます（テスト時などで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須と思われる環境変数（用途に応じて）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL / jquants_client）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等に使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で必要）

任意 / デフォルト値がある設定（Settings クラス参照）:

- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO

---

## 使い方（代表的な API）

以下はライブラリの主な利用例です。実行前に必要な環境変数（特に OpenAI / J-Quants トークン）を設定してください。

- 設定読み込み

  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行

  ```python
  from kabusys.data.pipeline import run_daily_etl

  # conn: duckdb connection を用意
  result = run_daily_etl(conn, target_date=None)  # target_date を指定しなければ today が使用される
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API 必須）

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（OpenAI API 必須）

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化（監査専用 DB を作る）

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算例

  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- ニュース RSS 取得（ニュース収集）

  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

注意:
- AI 関連関数（score_news / score_regime）は OpenAI の API を呼び出します。`OPENAI_API_KEY` を環境変数で設定するか、api_key 引数で明示的に渡してください。
- ETL/保存処理は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar 等）が期待されます。実行前に適切なスキーマ作成手順を用意してください（プロジェクトにスキーマ初期化スクリプトを配置するのが望ましいです）。

---

## 自動 .env 読み込みについて

- モジュール import 時にプロジェクトルートを探索して `.env` と `.env.local` を自動読み込みします（OS 環境変数を上書きしない / .env.local は上書き）。  
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env ファイルのパースは Bash ライクな `export KEY=val` / 引用符/コメントをサポートします。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主要ファイル群は以下のような構成です（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（OpenAI）
    - regime_detector.py            — 市場レジーム判定（ETF + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch / save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 他）
    - etl.py                        — ETLResult の再エクスポート
    - news_collector.py             — RSS 収集 / 前処理
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py        — 市場カレンダー管理 / 営業日判定
    - audit.py                      — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Value / Volatility 等
    - feature_exploration.py        — 将来リターン, IC, summary, rank

（その他、strategy / execution / monitoring 等のパッケージが想定されますが、このコードベースでは上記が主要実装となります）

---

## 開発・運用上の注意

- Look-ahead bias を避けるため、各モジュールは内部で `date.today()` を直接参照せず、引数で `target_date` を受け取る設計になっています。バッチ・バックテストを行う際は必ず `target_date` を明示的に渡してください。
- AI 呼び出し（OpenAI）は外部 API 呼び出しエラーに備えてフォールバックやリトライを行いますが、API キー・料金・レート制限に注意してください。
- DuckDB を用いた executemany の空リストバインド等に注意した実装上のワークアラウンドが入っています（DuckDB のバージョンに依存する挙動に気を付けてください）。
- news_collector は SSRF 対策・受信サイズ制限を実装しています。RSS ソースの追加時は信頼できる URL を登録してください。

---

## ライセンス / 貢献

（ライセンス表記やコントリビュート手順をここに記載してください）

---

必要であれば、README にサンプル .env.example、テーブルスキーマの初期化手順や運用用のコマンド例（cron / systemd / Airflow でのジョブ登録など）を追加します。どの部分を詳しく追記しましょうか？