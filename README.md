# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリ群です。  
ETL、ニュース収集・NLP（LLM）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API 等から市場データ（株価・財務・カレンダー）を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と LLM（OpenAI）を用いたニュースセンチメント解析（銘柄別・マクロ）
- 市場レジーム（bull/neutral/bear）の判定（ETF の MA とマクロセンチメントを合成）
- ファクター（モメンタム／ボラティリティ／バリュー）計算と特徴量探索（IC・forward returns 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 取引監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化ユーティリティ

設計上の重要点:
- ルックアヘッドバイアスに配慮（内部で date.today() 等を直接参照しない設計が多い）
- DuckDB を中心としたオンプレ / ローカル DB 前提
- J-Quants / OpenAI 等外部 API 呼び出しはリトライ・レート制御・フォールバックを備える
- 冪等性を重視（DB への保存は ON CONFLICT や削除→挿入で上書き）

---

## 機能一覧（主要）

- data/
  - jquants_client: J-Quants API クライアント（差分取得、保存関数、トークン管理、レート制御）
  - pipeline: 日次 ETL 実行（run_daily_etl 等）
  - news_collector: RSS 取得と前処理、raw_news への保存ユーティリティ
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック群（欠損・スパイク・重複・日付整合性）
  - audit: 監査ログ用スキーマの初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）
- ai/
  - news_nlp.score_news: 銘柄別ニュースを LLM でスコア化して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM センチメントを合成し market_regime に保存
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config:
  - 環境変数管理（.env 自動読み込み機能、Settings オブジェクト）

---

## セットアップ手順

前提:
- Python 3.10+（PEP 604 の型記法（A | B）などを使用）
- DuckDB を利用可能な環境

1. リポジトリをチェックアウト
   - 例: git clone <repo>

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. インストール（プロジェクト配布形式に依存）
   - 開発時（プロジェクトルートに pyproject.toml 等がある前提）:
     ```
     pip install -e .
     ```
   - 必要なパッケージ（例）
     ```
     pip install duckdb openai defusedxml
     ```
   - その他実行環境に応じて urllib が使うライブラリ等を用意してください。

4. 環境変数の設定
   リポジトリのプロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の呼び出しで使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注系を使う場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知連携を使う場合
   任意・デフォルト:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/...
   - DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（代表的な例）

以下は Python スクリプトから各処理を呼ぶ簡単な例です。

- DuckDB 接続作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- ETL（日次パイプライン）を実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に保存:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数で設定するか api_key 引数を渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {n_written} scores")
  ```

- 市場レジームをスコアリング:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 必要に応じて audit_conn をアプリで利用
  ```

- ファクター計算（研究用途）:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  ```

注意点:
- OpenAI 呼び出しはネットワークやトークン切れに対するリトライ・フォールバックがあるものの、API キーは正しく設定してください。
- ETL / data モジュールは DuckDB スキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）に依存します。初期スキーマの作成やマイグレーションは別途管理してください（本コードは保存/更新用ロジックを提供します）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 配下にモジュールを配置しています。主なファイル一覧と説明:

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — 環境変数 / Settings 管理、.env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得/保存/認証/レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl ほか）
    - news_collector.py — RSS 取得・前処理
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - quality.py — データ品質チェック（各チェック関数・run_all_checks）
    - audit.py — 監査ログスキーマ定義・初期化
    - etl.py — ETLResult 型の再エクスポート
    - stats.py — zscore_normalize などの統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - research/*, ai/*, data/* にそれぞれの実装ファイルあり

---

## 注意事項 / 運用上のヒント

- .env 自動ロード
  - config._find_project_root() は __file__ を基準に `.git` または `pyproject.toml` を探索してプロジェクトルートを決めます。CWD に依存しないので、パッケージ配布後でも期待どおりに動作します。
  - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Look-ahead バイアス対策
  - 多くのモジュールは「対象日以前のデータのみを参照する」「内部で date.today() を直接使わない」といった設計方針を守っています。バックテストなどで使用する場合も、この設計に沿って使用してください。
- エラー・フォールバック
  - OpenAI / J-Quants API 呼び出しは一部エラーでフォールバック（例えば macro_sentiment=0.0）する設計です。処理が部分的に失敗しても全体を止めないようになっていますが、ログを監視してください。
- DuckDB の executemany 空リスト制約
  - DuckDB のバージョン依存で executemany に空リストを渡せない場合があるため、コード中で空チェックが行われています。DuckDB バージョンに注意してください。

---

以上が README の概要です。必要であれば、以下を追加で作成できます:
- 開発者向けセットアップ（テスト実行方法、linters）
- DuckDB スキーマ定義ファイルのサンプル（DDL）
- .env.example のテンプレート

どの追加情報が必要か教えてください。