# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームのライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、マーケットカレンダ管理、ファクター計算、監査ログ（オーディット）など、研究・モニタリング・実行層で必要となる機能を提供します。

バージョン: 0.1.0

---

## 主要機能（ハイライト）

- データ取得 / ETL
  - J-Quants API から株価（日次OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分取得して DuckDB に保存
  - 差分取得・バックフィル・品質チェックを組み合わせた日次 ETL パイプライン (`kabusys.data.pipeline.run_daily_etl`)
- ニュース収集 & NLP
  - RSS からニュース取得と前処理（SSRF 防御、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント集計と ai_scores への保存 (`kabusys.ai.news_nlp.score_news`)
  - マクロニュース + ETF 移動平均乖離を合成した市場レジーム判定 (`kabusys.ai.regime_detector.score_regime`)
- 研究用ユーティリティ
  - ファクター算出（モメンタム、ボラティリティ、バリュー等）および特徴量探索（IC、forward returns 等）
  - Z-score 正規化などの統計ユーティリティ
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合などのチェック (`kabusys.data.quality`)
- 監査ログ（トレーサビリティ）
  - 信号 → 発注 → 約定までの監査テーブルを初期化・管理する機能（冪等・UTC 保存） (`kabusys.data.audit.init_audit_db` / `init_audit_schema`)
- 環境管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と Settings オブジェクト経由の設定参照 (`kabusys.config.settings`)

---

## 必須要件（概況）

- Python 3.9+（型注釈等を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS ソース）
- J-Quants リフレッシュトークン、OpenAI API キー等の環境変数

（実際の requirements はプロジェクトの packaging / pyproject / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローンし、パッケージをインストールします（プロジェクト構成に応じて調整してください）:

   - 例（開発環境）:
     ```
     git clone <repo_url>
     cd <repo>
     python -m venv .venv
     source .venv/bin/activate
     pip install -e ".[dev]"   # または pip install -r requirements.txt
     ```

2. 環境変数を設定します（.env ファイルをプロジェクトルートに配置可能）。
   - 自動読み込みの優先順位:
     - OS 環境変数
     - .env.local（存在すれば OS より優先して上書き）
     - .env（上書きしない）
   - 自動読み込みを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（参考）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu API パスワード（必須）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH: 監視用ファイルパス
     - KILL_FLAG_CLEAR_ON_START: 起動時に kill flag をクリアするか (1/0)
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: モニタリング閾値
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
     - OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

3. DuckDB 用のディレクトリを作成します（例: data/）:
   ```
   mkdir -p data
   ```

---

## 使い方（サンプル）

以下は代表的な利用例です。Python スクリプトや Cron / Airflow 等から呼び出して運用できます。

- 共通: Settings と DuckDB 接続

  ```python
  import duckdb
  from kabusys.config import settings

  db_path = str(settings.duckdb_path)  # デフォルト data/kabusys.duckdb
  conn = duckdb.connect(db_path)
  ```

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）:

  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=None)  # target_date=None -> 今日
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（OpenAI 必須）:

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム（マクロ + ETF MA200）スコアリング:

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用 DuckDB を別 DB として初期化する例）:

  ```python
  from kabusys.data.audit import init_audit_db
  from pathlib import Path

  audit_db_path = Path("data/audit.duckdb")
  audit_conn = init_audit_db(audit_db_path)
  # これで signal_events, order_requests, executions テーブル等が作成されます
  ```

- 研究・ファクター計算の例:

  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

注意:
- AI 系関数（news_nlp / regime_detector）は OpenAI API キーが必要です。api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / save_* 関数は、テーブルスキーマ（raw_prices / raw_financials / market_calendar 等）が期待通り存在することを前提とします。スキーマ初期化スクリプトやマイグレーションが別にある場合はそちらを利用してください。監査テーブルに関しては `kabusys.data.audit.init_audit_schema` / `init_audit_db` が提供されます。

---

## 注意点・運用メモ

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を起点に行います。テストや CI で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは外部 API であり失敗する可能性があるため、各モジュールはフェイルセーフ（スコアに 0 を使う等）を採用しています。運用時はレートやコストに注意してください。
- J-Quants API はレート制限があり、クライアント側で固定間隔の RateLimiter を実装しています。ID トークンの自動リフレッシュや指数バックオフ等の耐障害設計が入っています。
- RSS 取得は SSRF 対策や受信サイズ制限を実装していますが、外部フィードの取り扱いは注意が必要です。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py — パッケージ初期化、エクスポート定義
  - config.py — 環境変数 / 設定読み込みと Settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの集約 / OpenAI を用いた銘柄センチメント集計
    - regime_detector.py — マクロ + ETF MA を合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存・認証）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得と raw_news 保存（SSRF 対策等）
    - calendar_management.py — JPX 市場カレンダー管理 / 営業日判定
    - stats.py — z-score 正規化などの統計ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログ（signal / order_request / executions）初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — forward returns / IC / summary / rank 等
  - monitoring, execution, strategy など（パッケージ公開名に含まれるが実装は別ファイル群）

各モジュールの docstring に処理フローと設計方針が詳述されています。実装詳細や API の使用方法は該当モジュールの docstring を参照してください。

---

## サポート / 開発メモ

- テストしやすさのため、OpenAI 呼び出しやネットワークアクセス部分はモックできるように設計されています（内部呼び出し関数をパッチする想定）。
- DuckDB のバージョン差異や executemany の挙動（空リスト不可等）に注意して実装されています。
- 監査ログは削除しない方針で設計されており、order_request_id を冪等キーとして二重発注防止をサポートします。

---

README はここまでです。必要であれば、具体的なセットアップ用 requirements.txt やスキーマ初期化スクリプト、運用用の systemd / service のテンプレート、サンプル .env.example を追加で作成できます。どれを用意しましょうか？