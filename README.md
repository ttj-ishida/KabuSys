# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、ファクター計算、データ品質チェック、監査ログ（order → execution トレーサビリティ）などの機能を提供します。

主な設計方針：
- バックテストに対するルックアヘッドバイアス回避（内部で date.today() を直接参照しない等）
- DuckDB ベースのローカルデータレイヤ
- J-Quants / OpenAI 呼び出しに対する堅牢なリトライ・レート制御
- 冪等（idempotent）なデータ保存（ON CONFLICT / UPDATE など）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API から日次株価、財務データ、JPX カレンダーを差分取得（ページネーション・認証トークン管理・レート制御）
  - ETL の結果を ETLResult で返却（ログ・品質検査情報含む）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出
- ニュース収集 / NLP
  - RSS 取得（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュース＋ETF（1321）MA200乖離を組み合わせた市場レジーム判定（score_regime）
- リサーチ（ファクター）
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を使用）
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリ
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティ
  - 夜間バッチで J-Quants から差分取得する calendar_update_job
- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブルの初期化（init_audit_schema / init_audit_db）
- ユーティリティ
  - クロスセクション Z スコア正規化等

---

## 必要条件（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの requirements.txt があればそちらを使用してください）

---

## 環境変数 / 設定

このパッケージは .env ファイルまたは環境変数を参照します。パッケージ起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し、`.env` と `.env.local` を自動で読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

主要な環境変数：
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出しで使用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB 等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

Settings は `kabusys.config.settings` から参照できます。

---

## セットアップ手順（例）

1. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール
   （プロジェクトに requirements.txt がある場合はそれを使用してください）
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成し、必要なキーを定義してください。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

4. DuckDB の初期スキーマ（監査ログなど）が必要な場合は初期化を行う（後述の使用例参照）。

---

## 使い方（代表的な API と使用例）

以下は Python からの呼び出し例です。実行前に必要な環境変数（特に API キー）を設定してください。

- DuckDB 接続の取得（ファイルパスは settings.duckdb_path を利用可能）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定しなければ今日
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に書き込む（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # target_date は評価対象日（date オブジェクト）
  num_written = score_news(conn, date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY から取得
  print(f"書き込み銘柄数: {num_written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, date(2026, 3, 20), api_key=None)
  ```

- 監査 DB の初期化（監査ログ専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブル等が作成される
  ```

- マーケットカレンダー関連ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
  ```

注意点：
- OpenAI を使う関数は api_key 引数にキーを渡すか、環境変数 OPENAI_API_KEY を設定してください。未設定だと ValueError を送出します。
- ETL / API 呼び出しはネットワーク・API レート・課金等に注意して実行してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py                -- ニュースセンチメント（score_news）
    - regime_detector.py         -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント、保存関数（save_*）
    - pipeline.py                -- ETL パイプライン（run_daily_etl など）
    - etl.py                     -- ETLResult の再エクスポート
    - calendar_management.py     -- マーケットカレンダー管理
    - news_collector.py          -- RSS ニュース収集（SSRF 対策等）
    - quality.py                 -- データ品質チェック
    - stats.py                   -- zscore_normalize 等ユーティリティ
    - audit.py                   -- 監査ログテーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py         -- momentum / value / volatility 等の計算
    - feature_exploration.py     -- 将来リターン, IC, rank, factor_summary
  - monitoring/ (パッケージ名が __all__ にあるが実装は省略されている場合あり)

各モジュールは README の説明にある責務（ETL、NLP、監査など）を分担しています。詳細は各モジュールの docstring を参照してください。

---

## 運用上のノート・設計上の注意

- 自動環境読み込み:
  - パッケージ import 時にプロジェクトルートを検出して `.env` / `.env.local` を自動で読み込みます。テストや明示的制御が必要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Look-ahead バイアス対策:
  - AI / リサーチ / ETL の多くの処理は「target_date より前のデータのみを参照する」実装になっています。バックテスト等ではこの設計方針を尊重してください。
- 冪等性:
  - ETL 保存関数は ON CONFLICT で既存データを更新する設計です。部分失敗や再実行に耐えるよう作られています。
- エラーハンドリング:
  - 外部 API 呼び出しにはリトライやフォールバック（例: OpenAI 失敗時は 0.0 スコア）を備えています。ログ出力を監視してください。
- ログレベルは環境変数 LOG_LEVEL で制御可能です。

---

README に記載されていない点や、実行時の具体的なスクリプト化（cron / Airflow / CI での ETL 実行等）については、運用環境に合わせたスクリプトやサービスラッパーの実装を推奨します。必要であればサンプルの CLI / systemd unit / Airflow DAG のテンプレートも作成しますのでご依頼ください。