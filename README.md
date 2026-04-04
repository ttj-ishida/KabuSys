# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ管理などを提供します。

## 概要
KabuSys は以下の機能を持つモジュール群を含む Python パッケージです。

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）
- RSS ニュース収集と前処理（SSRF 防止・トラッキング除去）
- OpenAI を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）のスキーマ初期化ユーティリティ

設計方針として、バックテストにおけるルックアヘッドバイアス回避、ETL の冪等性、外部 API 呼び出しに対する堅牢なリトライ・スロットリング、SSRF 対策などが組み込まれています。

---

## 主な機能一覧
- data（ETL / jquants_client / news_collector / quality / calendar_management / audit / stats）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API クライアント（ページネーション・トークン自動更新・レート制御）
  - market_calendar の更新・営業日判定ユーティリティ
  - raw_news の収集・前処理（URL 正規化・ID 生成・SSRF 対策）
  - データ品質チェック（QualityIssue を返却）
  - 監査ログテーブル初期化（init_audit_schema / init_audit_db）
- ai
  - score_news(conn, target_date, api_key=None)：銘柄別ニュースセンチメントを ai_scores に書込
  - score_regime(conn, target_date, api_key=None)：市場レジーム（bull/neutral/bear）を market_regime に書込
- research
  - calc_momentum / calc_value / calc_volatility：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank：特徴量探索・IC 計算
- config
  - 環境変数自動ロード（プロジェクトルートの .env / .env.local ）と Settings オブジェクト

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン、仮想環境作成（任意）
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール（例）
   - 本リポジトリに requirements.txt がある想定で：
     ```bash
     pip install -r requirements.txt
     ```
   - 必須と思われるパッケージの一例：
     ```
     duckdb
     openai
     defusedxml
     ```
   ※ 実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

3. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先度：OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで利用）。
   - 例（.env）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # Kabuステーション API
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # OpenAI
     OPENAI_API_KEY=sk-...

     # DB paths
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 環境 / ログ
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は代表的な利用例です。すべて Python スクリプト内で DuckDB 接続を作成してモジュール関数を呼び出します。

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー・価格・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースに対する銘柄センチメントスコア付与（OpenAI 必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は env で読み込まれる
  print(f"written: {n_written}")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログテーブル初期化（専用 DuckDB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 研究用：ファクター計算・IC
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  target = date(2026,3,20)
  momentum = calc_momentum(conn, target)
  forward = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(momentum, forward, "mom_1m", "fwd_1d")
  ```

---

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD：kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL：kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY：OpenAI の API キー（ai.score_* を使う際に必要、各関数は api_key 引数でも渡せます）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID：LINE 通知用（任意）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH：実行監視用ファイルパス
- KABUSYS_ENV：実行環境（development / paper_trading / live）
- LOG_LEVEL：ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

注意: Settings クラスは未設定の必須キーに対して ValueError を投げます（例：JQUANTS_REFRESH_TOKEN）。

---

## 自動 .env ロード
- モジュール読み込み時にプロジェクトルート（.git または pyproject.toml を探索）を起点として `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先され、.env は既に設定されたキーを上書きしません（.env.local は上書き可能）。
- 自動ロードを無効化したい場合：
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     : 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  : 銘柄別ニュース NLP スコアリング（score_news）
    - regime_detector.py           : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            : J-Quants API クライアント（fetch/save 系）
    - pipeline.py                  : ETL パイプライン（run_daily_etl 等）
    - etl.py                       : ETL インターフェース再エクスポート
    - news_collector.py            : RSS 収集・前処理
    - calendar_management.py       : 市場カレンダー管理（is_trading_day 等）
    - quality.py                   : データ品質チェック
    - stats.py                     : 統計ユーティリティ（zscore_normalize）
    - audit.py                     : 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           : ファクター計算（momentum/value/volatility）
    - feature_exploration.py       : 将来リターン・IC・統計サマリ
  - monitoring/ (パッケージ想定)
  - strategy/ (パッケージ想定)
  - execution/ (パッケージ想定)

---

## 備考 / 運用上の注意
- OpenAI を呼び出すモジュールは API 失敗時にフェイルセーフとして 0.0 の中立スコアにフォールバックする設計です（例外を投げないケースあり）。
- J-Quants クライアントはレート制限（120 req/min）に準拠するため内部でスロットリングを行います。大量の同時実行は避けてください。
- ETL は差分更新とバックフィル（デフォルト 3 日）を組み合わせて API の後出し修正に対応します。
- DuckDB の executemany に関する制約や SQL 互換性を考慮した実装になっています（バージョン差異に注意）。
- テスト時は環境自動ロードを無効にしたり、OpenAI 呼び出しをモックすることを推奨します（モジュール内にテスト用差替えポイントあり）。

---

README は以上です。必要であれば「インストール手順の詳細」「example .env.example のテンプレート」「よくあるエラーと対処方法」などを追加します。どの情報を優先して追記しますか？