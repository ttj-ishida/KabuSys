README
=====

概要
----
KabuSys は日本株向けのデータプラットフォームとリサーチ／自動売買支援ライブラリです。J-Quants や RSS、OpenAI（LLM）など外部データソースを取り込み、データETL、品質チェック、ニュースセンチメント評価、マーケットレジーム判定、ファクター計算、監査ログ（オーダー/約定トレーサビリティ）などを提供します。

主な用途例:
- J-Quants から株価・財務・市場カレンダーを差分取得して DuckDB に保存
- RSS ニュースを収集して LLM で銘柄ごとのセンチメントを算出
- ETF の移動平均等とマクロニュースを組み合わせて市場レジームを判定
- 研究用にファクター計算・将来リターン・IC 等を算出
- 戦略→シグナル→発注→約定の監査ログを DuckDB に記録

機能一覧
--------
- data/
  - ETL パイプライン（run_daily_etl を中心に prices/financials/calendar を差分取得）
  - J-Quants API クライアント（認証・ページネーション・レートリミッティング・保存関数）
  - ニュース収集（RSS、SSRF 対策、前処理、raw_news への保存）
  - カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - データ品質チェック（欠損・重複・スパイク・日付整合性検査）
  - 監査ログ（signal_events / order_requests / executions）テーブル作成・初期化ユーティリティ
  - 統計ユーティリティ（Zスコア正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）200日MA 乖離とマクロニュース LLM スコアを合成して market_regime に書き込む
- research/
  - ファクター計算（momentum, value, volatility 等）
  - 特徴量探索（forward returns, IC, summary, rank 等）
- 設定管理（kabusys.config）: .env ファイル／環境変数を自動読み込み。settings オブジェクトから各種設定を参照可能

要件（想定）
-------------
- Python 3.10+
- 必要な外部パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <project-root>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. パッケージのインストール
   - pip install -e .            # プロジェクトを editable インストール（pyproject.toml がある場合）
   - もしくは依存を直接インストール:
     - pip install duckdb openai defusedxml

   > 補足: requirements.txt / pyproject.toml がある場合はそちらを参照してください。

4. 環境変数設定 (.env)
   プロジェクトルートの .env（および .env.local）を作成します。自動読み込みは kabusys.config によりプロジェクトルート（.git または pyproject.toml 基準）を探索して行われます。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN         (必須) J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD            (必須) kabuステーション API パスワード
   - KABU_API_BASE_URL            (任意) kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN              (必須) Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID             (必須) Slack チャンネル ID
   - DUCKDB_PATH                  (任意) DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH                  (任意) SQLite（モニタリング用）パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV                  (任意) development | paper_trading | live（デフォルト development）
   - LOG_LEVEL                    (任意) DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
   - OPENAI_API_KEY               (必須 for AI 機能) OpenAI API キー（関数呼び出し時に api_key を明示しても可）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD (任意) 1 に設定すると自動ロードを無効化

5. DuckDB の準備（任意）
   - デフォルトでは data/kabusys.duckdb が使用されます。ファイルが無ければ ETL/save 関数がファイルを作成します。
   - 監査用に別 DB を作る場合は data/audit.duckdb 等を指定してください。

基本的な使い方
-------------

- 設定参照
  ```py
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  ```

- DuckDB 接続
  ```py
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得と品質チェック）
  ```py
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20), id_token=None)
  print(result.to_dict())
  ```

- ニュースセンチメント算出（ai_scores へ書き込む）
  ```py
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は settings または api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定（market_regime へ書き込む）
  ```py
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```py
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # テーブル (signal_events, order_requests, executions) が作成されます
  ```

- 研究用 API 例
  ```py
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  conn = duckdb.connect(str(settings.duckdb_path))
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  forwards = calc_forward_returns(conn, target_date=date(2026, 3, 20), horizons=[1,5,21])
  ic = calc_ic(momentum, forwards, "mom_1m", "fwd_1d")
  ```

注意点 / 動作設計上のポイント
---------------------------
- Look-ahead バイアス防止:
  - 多くの関数は内部で datetime.today() / date.today() を直接参照しない設計です。target_date を明示的に渡すことが推奨されます。
- 冪等性:
  - jquants_client の保存関数や監査ログ初期化などは冪等性を考慮して実装されています（ON CONFLICT / INSERT … DO UPDATE 等）。
- フォールバック:
  - market_calendar が未取得の場合は曜日ベース（単純な土日判定）のフォールバックを行います。
- エラー処理:
  - 外部 API 呼び出し（OpenAI、J-Quants、RSS）はリトライやフェイルセーフを備え、API 不良時にはスキップ・デフォルト値で継続する設計が多く採用されています。

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py
  - config.py                   # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py               # ニュースセンチメント（ai_scores 書き込み）
    - regime_detector.py        # 市場レジーム判定（market_regime 書き込み）
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント + 保存ロジック
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    # マーケットカレンダー管理
    - news_collector.py         # RSS 収集と前処理
    - quality.py                # データ品質チェック
    - stats.py                  # 統計ユーティリティ（zscore_normalize）
    - audit.py                  # 監査ログ・テーブル初期化
    - etl.py                    # ETL 公開インターフェース（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py        # ファクター計算（momentum/value/volatility 等）
    - feature_exploration.py    # 将来リターン・IC 等
  - monitoring/ (実装ファイルはプロジェクトにより存在する想定)

貢献・テスト
------------
- テスト用に環境変数自動ロードを無効化するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ユニットテストでは外部 API 呼び出しや time.sleep, network I/O をモックすることを推奨します（コード中にモック差替えポイントが設計されています）。

ライセンス / その他
------------------
- この README はコードベースのコメントを元に生成されています。実運用に際しては pyproject.toml / requirements.txt を確認し、必要なライブラリ・バージョンを明示したうえで環境構築してください。

お問い合わせ
------------
実装や使い方に関する質問があれば、プロジェクトの issue に記載してください。