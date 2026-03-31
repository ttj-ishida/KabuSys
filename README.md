KabuSys — 日本株自動売買プラットフォーム
====================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・AI 支援・監査ログ・ETL を含む自動売買システムのライブラリ群です。本リポジトリは主に以下を提供します。

- J-Quants API 経由のデータ取得（株価・財務・市場カレンダー）と DuckDB への保存
- ニュース収集・NLP による銘柄センチメント算出（OpenAI を利用）
- 市場レジーム判定（ETF + マクロニュースの LLM 評価を合成）
- ファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）用スキーマと初期化
- ETL パイプライン（差分取得 + 保存 + 品質チェック）の統合実行

主な機能一覧
-------------
- データ取得・ETL
  - fetch_daily_quotes / save_daily_quotes（J-Quants 経由の OHLCV 取得と保存）
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一括実行
- ニュース処理・AI
  - fetch_rss（RSS 収集、安全対策付き）
  - score_news（銘柄ごとのニュースセンチメント算出、OpenAI を利用）
  - score_regime（ETF MA とマクロニュースを合成した市場レジーム判定）
- リサーチ・ファクター
  - calc_momentum, calc_value, calc_volatility（ファクター算出）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索）
  - zscore_normalize（クロスセクション正規化ユーティリティ）
- データ品質
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks（品質チェック一括実行）
- 監査ログ（オーダー追跡）
  - init_audit_schema / init_audit_db（監査テーブルのスキーマ作成・DB 初期化）
- 設定管理
  - kabusys.config.Settings（環境変数または .env から設定をロード。自動 .env ロード有り）

動作環境・依存
---------------
- Python >= 3.10（型注釈に | 型を使用）
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- 実行前に上記パッケージをインストールしてください（requirements.txt がある場合はそちらを利用）。

セットアップ手順
----------------

1. リポジトリをクローンして仮想環境を作成
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 例（最低限）:
     - pip install duckdb openai defusedxml
   - もしパッケージ管理ファイル（pyproject.toml / requirements.txt）があれば:
     - pip install -e .    # 開発インストール（プロジェクトがパッケージ化されている場合）
     - または pip install -r requirements.txt

3. 環境変数の設定（.env または .env.local）
   - プロジェクトルートに .env を作成すると自動的にロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=your_slack_token
     - SLACK_CHANNEL_ID=your_slack_channel
   - オプション:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

   - サンプル .env（.env.example を参考に作成してください）:
     JQUANTS_REFRESH_TOKEN=REPLACE_ME
     OPENAI_API_KEY=REPLACE_ME
     KABU_API_PASSWORD=REPLACE_ME
     SLACK_BOT_TOKEN=REPLACE_ME
     SLACK_CHANNEL_ID=REPLACE_ME
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

使い方（代表的な例）
-------------------

- DuckDB 接続の取得（例）
  - import duckdb
  - conn = duckdb.connect(str(Path(os.environ.get("DUCKDB_PATH", "data/kabusys.duckdb"))))

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニューススコアリング（score_news）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n_written = score_news(conn, target_date=date(2026, 3, 20))
  - print(f"scored {n_written} codes")

  - 注意: OPENAI_API_KEY が環境変数に設定されているか、api_key 引数で渡してください。

- 市場レジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # これで signal_events, order_requests, executions テーブルが作成される

- スキーマ初期化（監査テーブルのみ）
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

- ファクター計算・リサーチ操作
  - from kabusys.research import calc_momentum, calc_value, zscore_normalize
  - momentum = calc_momentum(conn, target_date=date(2026,3,20))
  - normalized = zscore_normalize(momentum, columns=["mom_1m", "mom_3m", "mom_6m"])

実運用上の注意
--------------
- OpenAI 利用
  - LLM 呼び出しはコスト・レイテンシがかかります。API キー（OPENAI_API_KEY）とモデル（デフォルト gpt-4o-mini）に注意してください。
  - API エラーやレートリミットはライブラリ内でリトライ処理を備えていますが、失敗時はフォールバック（0.0）で継続する設計の箇所があります。
- 自動 .env ロード
  - kabusys.config はプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Look-ahead バイアス対策
  - 多くの処理は datetime.today() を直接参照せず、target_date を引数で受け取る設計です。バックテストや再現性のため、明示的な日付指定を推奨します。
- DuckDB の互換性
  - 一部の executemany/リストバインドは DuckDB のバージョン差異に配慮した実装になっています。DuckDB は十分新しいバージョンを推奨します。

ディレクトリ構成（主要ファイル）
------------------------------
（src 以下を示しています）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（score_news 等）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + 保存関数
    - pipeline.py                    — ETL パイプライン実装（run_daily_etl 等）
    - etl.py                         — ETLResult 再エクスポート
    - calendar_management.py         — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py              — RSS 収集（fetch_rss 等）
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum/value/volatility）
    - feature_exploration.py         — forward returns, IC, summary 等
  - research/*（補助ファイル）
  - その他（strategy / execution / monitoring 等のパッケージ名が __all__ に含まれるが、必要に応じて展開）

貢献・拡張
-----------
- テスト: 各外部 API 呼び出しはモック化を想定して実装されています（例: OpenAI 呼び出しの差し替え）。
- 新たなデータソースや戦略モジュールは data/ または research/ 配下に追加してください。
- 実稼働（live）では KABUSYS_ENV を適切に設定し、発注・ログ周りの安全対策を厳格に行ってください。

ライセンス・免責
----------------
- 本 README はコードベースの使い方と設計方針を要約したものです。実運用での損失・API 使用料・法令遵守等についてはユーザーの責任で対応してください。

---

不明点や追加してほしい利用例（例: 発注ワークフロー、Slack 通知連携、kabu API の利用例など）があれば教えてください。必要に応じて README に追記します。