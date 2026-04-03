# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。ETL・ニュース収集・AI（LLM）によるニュースセンチメント評価・市場レジーム判定・ファクター計算・監査ログなど、取引システムの主要機能群を提供します。

---

## 概要

KabuSys は以下の目的で設計された Python モジュール群です。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL
- RSS を用いたニュース収集と記事前処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別 / マクロ）評価
- ETF（1321）200日移動平均乖離などを組み合わせた市場レジーム判定
- ファクター（モメンタム／バリュー／ボラティリティ等）と研究用ユーティリティ
- 監査ログ（signal → order_request → execution のトレース）用スキーマ初期化
- データ品質チェック（欠損／重複／スパイク／日付不整合）など

設計上の特徴：
- ルックアヘッドバイアス回避（内部で date.today() などを直接参照しない実装）
- DuckDB を主な永続化ストアとして利用
- API 呼び出しに対するリトライ・レート制御・フェイルセーフを実装
- 環境変数ベースの設定管理（.env 自動ロード機能あり）

---

## 主な機能一覧

- data（kabusys.data）
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）、レート制御、認証
  - market_calendar 管理、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

- ai（kabusys.ai）
  - ニュースNLP（score_news: 銘柄別ニュースセンチメント）
  - レジーム判定（score_regime: MA200 とマクロニュースセンチメント合成）

- research（kabusys.research）
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
  - z-score 正規化ユーティリティ（kabusys.data.stats.zscore_normalize）

- config（kabusys.config）
  - .env/環境変数の読み込みロジック、settings オブジェクト（プロパティ経由で設定取得）
  - .env 自動読み込み（OS環境変数 > .env.local > .env）。自動ロード無効化フラグあり。

---

## 要件

- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai （OpenAI Python SDK）
  - defusedxml
（プロジェクトが配布される際の requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン（またはソースを取得）

   ```bash
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（requirements.txt がある場合）

   ```bash
   pip install -r requirements.txt
   ```

   または最低限：

   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定

   プロジェクトルートに `.env` として必要な環境変数を配置できます。自動ロードの優先順は以下の通りです：

   - OS 環境変数（最優先）
   - .env.local
   - .env

   自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（代表例）：
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 用）
   - KABU_API_PASSWORD     : kabu ステーション API パスワード
   - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用 LINE 設定（任意）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START : 実行監視用
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視閾値
   - KABUSYS_ENV           : 動作環境 (development / paper_trading / live)
   - LOG_LEVEL             : ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)

   settings オブジェクトから Python 側で取得可能です（例: `from kabusys.config import settings`）。

---

## 使い方（代表的な例）

以下は Python セッション / スクリプトからライブラリを呼ぶ簡単な例です。日付は datetime.date を使用します。

- DuckDB 接続の準備

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコア化して ai_scores に保存

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)
  ```

  - OpenAI API キーを明示する場合:

    ```python
    score_news(conn, date(2026,3,20), api_key="sk-...")
    ```

- 市場レジーム（ETF 1321 の MA200 とマクロニュースの合成）を評価

  ```python
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DuckDB ファイルを生成）

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 市場カレンダーの判定ユーティリティ例

  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print("次の営業日:", next_trading_day(conn, d))
  ```

- ファクター計算（研究用途）

  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  m = calc_momentum(conn, date(2026,3,20))
  v = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

注意点：
- score_news / score_regime は OpenAI を呼びます。API クォータやレイテンシ、費用に注意してください。API エラー時は内部でフェイルセーフ（スコアを 0 にする等）を採用していますが、キー未設定時は ValueError が発生します。
- ETL は J-Quants API を呼びます。`JQUANTS_REFRESH_TOKEN` を設定してください。get_id_token が自動的にトークンを取得・キャッシュします。

---

## .env の自動ロードについて

- 自動ロードはデフォルトで有効です（kabusys.config がプロジェクトルートを探して `.env` / `.env.local` を読みます）。
- 優先順位: OS 環境変数 > .env.local > .env
- テストや特殊環境で自動読み込みを無効にするには環境変数を設定します:

  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- .env のパースはシェル形式（`export KEY=val` やクォート・コメント対応）に対応しています。

---

## 主要なディレクトリ構成

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / settings 管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（銘柄別）
    - regime_detector.py           — マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - pipeline.py                  — ETL パイプライン / run_daily_etl 等
    - etl.py                       — ETLResult の再エクスポート
    - news_collector.py            — RSS 収集・前処理
    - calendar_management.py       — マーケットカレンダー管理 / 営業日ロジック
    - quality.py                   — データ品質チェック群
    - stats.py                     — zscore_normalize 等ユーティリティ
    - audit.py                     — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Value / Volatility 等
    - feature_exploration.py       — forward returns, IC, factor_summary, rank
  - research/*, ai/*, data/* の各モジュールに詳細実装（SQL/ロジック）あり

---

## 開発・運用上の注意

- DuckDB の SQL 実行は `duckdb.DuckDBPyConnection` を前提にしているため、接続オブジェクトをそのまま渡してください。
- ETL/保存系は基本的に冪等（ON CONFLICT / DO UPDATE）を前提とした実装です。
- API 呼び出しはレート制御およびリトライを実装していますが、運用時には API キー／クォータ管理を注意してください。
- OpenAI の呼び出しは JSON Mode を利用し、応答のバリデーションを行っています。テスト用に内部の _call_openai_api をモックする設計です。
- ログは settings.log_level に従います。運用環境では適切に設定してください。

---

何か特定の機能についての詳しいドキュメント（関数の使い方、SQL スキーマ、例外挙動、テスト方法など）が必要であれば教えてください。必要に応じてサンプルスクリプトや具体的な .env.example を作成します。