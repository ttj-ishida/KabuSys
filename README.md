# KabuSys

日本株のデータ取得・前処理・研究・AIスコアリング・監査ログを備えた自動売買システム用ライブラリ（モジュール群）。  
このリポジトリは、データETL、ニュース収集・NLPスコアリング、ファクター計算、監査（トレーサビリティ）、および外部APIクライアント（J-Quants / OpenAI / kabuステーション）を提供します。

## 概要
KabuSys は以下の目的を想定した Python パッケージです。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュースの収集と前処理、銘柄紐付け
- OpenAI を用いたニュースセンチメント（銘柄別）とマクロセンチメント（市場レジーム判定）の自動スコアリング
- 研究用のファクター計算（モメンタム、バリュー、ボラティリティ等）および統計ユーティリティ
- 監査ログ（signal / order_request / executions）テーブルの初期化と管理
- データ品質チェック（欠損・重複・スパイク・日付整合性）

パッケージはモジュール毎に責務が分離されており、バッチ処理・研究環境・運用環境の両方で使用できるよう設計されています。

## 主な機能一覧
- データ取得・保存
  - J-Quants クライアント（fetch / save: daily_quotes, financials, market_calendar, listed info）
  - 差分ETL 実行（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
- ニュース関連
  - RSS 収集（fetch_rss）＋前処理（URL除去・正規化）
  - ニュース -> 銘柄ごとのテキスト集約
  - OpenAI を使った銘柄別センチメント（score_news）
- AI / レジーム判定
  - マクロニュースと 1321（ETF）MA200乖離を合成した市場レジーム判定（score_regime）
- 研究ツール
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターンの計算（calc_forward_returns）、IC 計算、統計サマリ、Z-score 正規化
- データ品質とカレンダー
  - market_calendar の管理（is_trading_day / next_trading_day / get_trading_days）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
- 監査ログ
  - 監査（signal_events / order_requests / executions）スキーマ初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env ファイルと環境変数の自動読み込み（kabusys.config）

## 必要条件 (推奨)
- Python 3.10+（型注釈で union 表記等使用）
- 必要 Python パッケージ（主なもの）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
（プロジェクト配布時に requirements.txt / pyproject.toml を参照してください）

## セットアップ手順 (ローカル開発・実行)
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   - 配布されている pyproject.toml / requirements.txt があればそちらを使用してください:
     ```
     pip install -e .
     # または
     pip install -r requirements.txt
     ```

4. 環境変数設定
   - プロジェクトルートに `.env` ファイルを作成すると自動で読み込まれます（kabusys.config）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主な環境変数（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabuステーションのベースURL（省略可、デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot Token（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: Monitoring 用 SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（省略時 development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

## 基本的な使い方

以下はインポートして各機能を呼び出す例です。すべて DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を渡して利用します。

- DuckDB 接続の生成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 監査スキーマを初期化（新規 DB の場合）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  # または既存接続にスキーマだけ追加:
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn, transactional=True)
  ```

- 日次 ETL を実行（J-Quants からデータ取得して保存・品質チェック）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を算出して ai_scores に保存:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数に設定されている場合は api_key を省略可
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"written: {written}")
  ```

- 市場レジームスコアを計算して market_regime に保存:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- ファクター計算（研究用）:
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- データ品質チェック:
  ```python
  from kabusys.data.quality import run_all_checks
  from datetime import date
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意:
- score_news / score_regime は OpenAI API を呼びます。API 料金とレートに注意してください。
- 各関数は「ルックアヘッドバイアス」を避ける設計になっており、内部で date.today() 等を勝手に参照しません。必ず対象日（target_date）を指定する等で再現可能な処理を行ってください。

## .env と挙動の補足
- pakage 起動時に kabusys.config モジュールがプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` と `.env.local` を自動読み込みします。  
  読込順: OS 環境変数（既定） > .env.local（上書き） > .env（補完）。  
- テスト等で自動ロードを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## ディレクトリ構成（要約）
- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン情報）
  - config.py — 環境変数 / .env 自動読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄別）: score_news
    - regime_detector.py — マクロセンチメント + ETF ma200 を合成した市場レジーム判定: score_regime
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save ヘルパー）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）・ETLResult
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py — RSS 取得と前処理
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（モメンタム、バリュー、ボラティリティ）
    - feature_exploration.py — 将来リターン、IC、統計サマリー、ランク関数
  - ai/regime_detector.py, ai/news_nlp.py — OpenAI 呼び出しは retry や JSON モードで堅牢化
- その他: 各モジュールは DuckDB 接続を明示的に受け取り DB 操作を行うため、ユニットテストでのモックや差し替えが容易です。

## 運用上の注意
- OpenAI / J-Quants の API キーとレート制限に注意してください。score_news / regime_detector ではリトライとバックオフが実装されていますが、料金とレートは考慮して運用してください。
- DuckDB の executemany に対する制限（空リスト渡せない等）に留意して実装されていますが、バージョン差異により挙動が変わる可能性があります。duckdb のバージョンを固定して運用することを推奨します。
- 監査ログ（audit）テーブルは削除しない前提で設計されています。バックアップやアーカイブ戦略を考慮してください。
- news_collector は SSRF 対策、XML の安全パース、レスポンスサイズ制限等を備えていますが、外部ソースに依存する点は運用での監視が必要です。

---

追加の利用例、デプロイ手順、CI/CD、あるいは特定モジュールの詳細な API ドキュメントが必要でしたら、用途（バッチ ETL 実行 / 監視 / 戦略評価 等）を教えてください。必要に応じて README を拡張します。