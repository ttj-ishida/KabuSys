# KabuSys

日本株向け自動売買・データプラットフォームライブラリ

短い概要:
KabuSys は日本株のデータ ETL、データ品質チェック、特徴量（ファクター）計算、ニュース NLP（LLM を用いたセンチメント）、市場レジーム判定、監査ログ（発注〜約定のトレース）などを提供するモジュール群です。DuckDB をデータレイク／分析 DB として利用し、J-Quants API からデータ取得、OpenAI（gpt-4o-mini）でニュース評価を行う設計になっています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local / OS 環境変数読み込み（自動ロード、無効化フラグあり）
  - 必須環境変数チェック

- データ取得・ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダー取得（ページネーション・リトライ・レート制御）
  - 差分更新・バックフィル・冪等保存（DuckDB の ON CONFLICT 相当）
  - 日次 ETL エントリポイント（run_daily_etl）

- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合検出
  - QualityIssue オブジェクトで問題を集約

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化、前処理、SSRF/サイズ制限対策、raw_news 保存準備

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義・初期化
  - 発注から約定までのトレーサビリティ（UUID ベース、冪等キー対応）

- 研究用ツール（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z スコア正規化

- ニュース NLP / 市場レジーム判定（kabusys.ai）
  - ニュースを銘柄単位に集約し OpenAI（JSON Mode）でセンチメントを評価して ai_scores に保存
  - ETF（1321）200日移動平均乖離とマクロニュース LLM スコアを合成し market_regime を判定

- 汎用ユーティリティ
  - クロスセクション Z-score 正規化（kabusys.data.stats）
  - マーケットカレンダー管理（営業日判定・next/prev/get_trading_days）

設計上の注記:
- ルックアヘッドバイアス対策（内部で date.today()/datetime.today() を不用意に参照しない設計）
- API 呼び出しに対するリトライ・フォールバック（LLM/API 失敗時のフェイルセーフ）
- 冪等性（DB 書き込みは既存データに対して上書き等で保護）

---

## セットアップ手順

前提:
- Python 3.10+（型注釈に Union | 型を使用）
- pip が使えること

1. リポジトリをクローン／配置し、パッケージをインストール（開発モード推奨）
   - 例:
     ```
     git clone <repo-url>
     cd <repo>
     pip install -e .
     ```

2. 必要な追加依存パッケージ（主なもの）
   - duckdb
   - openai
   - defusedxml
   - （HTTP/SSL 標準ライブラリは別途不要）
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただしプロジェクトルートは .git または pyproject.toml で検出されます）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視等）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視設定）

   - 例の .env（README 用サンプル）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     KABUSYS_ENV=development
     ```

4. データベースの初期化（監査ログ用）
   - 監査ログ専用 DB を初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - または既存の DuckDB 接続にテーブルを追加:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn)
     ```

---

## 使い方（簡単な例）

以下はライブラリの代表的な呼び出し例です。実行前に環境変数（JQUANTS_REFRESH_TOKEN・OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続を作って日次 ETL を実行:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI キーが環境変数にあること）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  mom = calc_momentum(conn, d)
  val = calc_value(conn, d)
  vol = calc_volatility(conn, d)
  ```

- データ品質チェックを走らせる:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

注意点:
- OpenAI へのリクエストは API レート・料金が発生します。テスト時は関数内部の _call_openai_api をモックしてください。
- ETL / AI 関数は Look-ahead バイアスを防ぐため内部で日付扱いに注意して実装されています（target_date を明示的に渡すことを推奨）。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py — パッケージ定義（バージョンなど）
- config.py — 環境変数・設定管理（.env 自動ロード、settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメントの集約・OpenAI 呼び出し・ai_scores 書込みロジック
  - regime_detector.py — ETF MA200 とマクロニュースを統合した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — マーケットカレンダー管理（営業日判定・更新ジョブ）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py — 監査ログテーブル定義・初期化・index
  - news_collector.py — RSS 取得・前処理・SSRF 対策
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー・ランク関数
- research 等から参照される data.stats などのユーティリティが同梱

---

## 運用上の注意・設計上のポイント

- 自動ロードされる .env の優先順: OS 環境 > .env.local > .env。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API はレート制限（120 req/min）に注意。jquants_client は内部で固定間隔スロットリングを実装しています。
- LLM（OpenAI）呼び出しは JSON Mode の利用を想定、レスポンスのバリデーションやリトライ処理が組み込まれていますが、API 変更に対して脆弱な点があり得ます。テスト時は _call_openai_api をモックしてください。
- DuckDB への書き込みは冪等を意識した実装（ON CONFLICT）になっています。ETL は部分失敗時でも既存データを不必要に上書きしない工夫をしています。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）。order_request_id を冪等キーとして二重発注防止を容易にします。

---

必要であれば、README に以下を追加できます:
- 開発用のテスト手順（ユニットテストの実行方法、モックの例）
- .env.example のサンプルファイル
- CI/CD / cron による日次バッチの実行例（systemd / cron / GitHub Actions）
- API レートや課金見積もりに関する運用ガイド

追加してほしい項目や、重点的に説明して欲しい箇所があれば教えてください。