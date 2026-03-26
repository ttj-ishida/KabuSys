# KabuSys — 日本株自動売買プラットフォーム（README）

概要
----
KabuSys は日本株のデータプラットフォーム、リサーチ、ニュースNLP、レジーム判定、および監査付きの発注監視を想定したライブラリ群です。  
主に以下の用途を想定しています。

- J-Quants API からの市場データ ETL（株価、財務、取引カレンダー）
- RSS ベースのニュース収集と LLM（OpenAI）による銘柄・マクロセンチメント評価
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの融合）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック、カレンダー管理、監査ログ（シグナル→発注→約定のトレーサビリティ）
- DuckDB を用いたローカルデータベース管理

主要な設計方針は「ルックアヘッドバイアス回避」「冪等性」「フォールバック（安全）」です。外部 API 呼び出しはリトライ/レート制限・フェイルセーフを備えています。

主な機能一覧
--------------
- 環境設定読み込み（.env / .env.local をプロジェクトルートから自動読み込み）
- J-Quants クライアント（fetch / save / 認証・リトライ・レート管理）
- ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
- ニュース収集（RSS パーサー、SSRF 対策、前処理、raw_news 保存）
- ニュース NLP（gpt-4o-mini を使った銘柄別センチメント集約 → ai_scores テーブル）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロセンチメントの合成）
- 研究用ユーティリティ（モメンタム、ボラティリティ、バリュー、forward returns、IC、統計要約）
- 監査ログ（signal_events, order_requests, executions テーブルの初期化とユーティリティ）
- DuckDB を前提とした永続化ユーティリティ

セットアップ手順
----------------
前提
- Python 3.10+ を推奨（型アノテーションで PEP604 等を使用）
- DuckDB、OpenAI SDK、defusedxml 等の依存パッケージ

推奨手順（ローカル開発）
1. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. パッケージインストール（プロジェクトルートで）:
   - pip install -e .        （パッケージ化されている場合）
   - 必要に応じて個別にインストール:
     - pip install duckdb openai defusedxml

3. 環境変数設定
   - プロジェクトルートに .env を作成するか、環境変数をエクスポートしてください。
   - 自動読み込みはデフォルトで有効（.env と .env.local をプロジェクトルートから読み込み）。
   - 自動ロードを無効にしたい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（または一般的に使用する）環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に利用）
- OPENAI_API_KEY: OpenAI 呼び出し（score_news / score_regime で使用可能。関数引数で上書き可）
- KABU_API_PASSWORD: kabuステーション API 認証パスワード（発注連携等を行う場合）
- SLACK_BOT_TOKEN: Slack 通知用（監視機能等を組み込む場合）
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID
- LOG_LEVEL: ログレベル（DEBUG/INFO/...。デフォルト INFO）
- KABUSYS_ENV: 環境区分（development / paper_trading / live）
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

使い方（主要な API と実行例）
----------------------------

基本的な準備（DuckDB 接続）
- Python から DuckDB 接続を作成して各関数を呼び出します。

例: ETL を一日分実行する
- from datetime import date
- import duckdb
- from kabusys.config import settings
- from kabusys.data.pipeline import run_daily_etl
- conn = duckdb.connect(str(settings.duckdb_path))
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

例: ニュースセンチメントを算出して DB に書き込む
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- conn = duckdb.connect(str(settings.duckdb_path))
- n_written = score_news(conn, target_date=date(2026, 3, 20))
- print(f"scored {n_written} symbols")

例: 市場レジーム判定を実行
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- conn = duckdb.connect(str(settings.duckdb_path))
- score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API key は env または api_key 引数で指定

例: 監査DB を初期化
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit_duckdb.duckdb")

重要な点
- OpenAI API 呼び出しは api_key 引数で明示的に渡すことも可能。渡さない場合は環境変数 OPENAI_API_KEY を参照します。
- API 呼び出し失敗時は多くの処理がフェイルセーフ（0 でフォールバック）やスキップして継続する設計です。ログで原因を確認してください。
- ETL の差分更新は最終取得日を基に自動で date_from を決定し、backfill により直近数日の再取得で後出し修正に対応します。

主要な関数（抜粋）
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.pipeline.run_prices_etl(...)
- kabusys.data.pipeline.run_financials_etl(...)
- kabusys.data.pipeline.run_calendar_etl(...)
- kabusys.data.calendar_management.calendar_update_job(...)
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.news_collector.fetch_rss(...)
- kabusys.ai.news_nlp.score_news(...)
- kabusys.ai.regime_detector.score_regime(...)
- kabusys.data.audit.init_audit_schema / init_audit_db(...)
- kabusys.research.* のファクター計算関数（calc_momentum 等）
- kabusys.data.stats.zscore_normalize(...)

ディレクトリ構成
----------------
（主要ファイルを抜粋した構成例）

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数/.env 読み込み・Settings 定義
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュースの LLM スコアリング（銘柄別）
    - regime_detector.py           # ETF 1321 MA200 とマクロニュースを合成したレジーム判定
  - data/
    - __init__.py
    - calendar_management.py       # マーケットカレンダー管理（営業日判定等）
    - pipeline.py                  # ETL パイプラインと run_daily_etl
    - etl.py                       # ETLResult の再エクスポート
    - jquants_client.py            # J-Quants API クライアント（fetch/save）
    - news_collector.py            # RSS 収集、記事正規化、SSRF 対策
    - stats.py                     # 統計ユーティリティ（zscore 正規化等）
    - quality.py                   # データ品質チェック
    - audit.py                     # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           # Momentum/Value/Volatility 計算
    - feature_exploration.py       # forward returns / IC / summary / rank
  - ai/…, data/…, research/…        # 各サブパッケージ

設計・運用上の注意
-----------------
- ルックアヘッドバイアスの防止:
  - 日付内部参照で datetime.today() / date.today() を安易に使わない設計。全てのバッチは target_date を明示的に受け取るか、ETL エントリで今日の日付を決定します。
  - prices_daily 等のクエリは target_date 未満（排他）で最新値を計算する等、バックテスト用途を意識しています。
- 冪等性:
  - J-Quants から保存する際は ON CONFLICT DO UPDATE を多用して冪等性を保っています。
  - 監査ログでは order_request_id を冪等キーとして二重発注を防止する設計です。
- セキュリティ:
  - news_collector では SSRF 対策（リダイレクト検査・プライベートIP拒否）、defusedxml による XML パース保護、レスポンスサイズ上限などを実装しています。
- フェイルセーフ:
  - OpenAI API など外部依存はリトライとフォールバック（ゼロスコア）を備え、パイプライン全体を止めないようにしています。ただし、結果の信頼性はログや品質チェックで監視してください。

トラブルシューティング
----------------------
- 環境変数が足りない場合:
  - config.Settings のプロパティ（例: jquants_refresh_token）で _require を使っているため、未設定時は ValueError が発生します。README の「必須環境変数」を確認してください。
- OpenAI 呼び出しで JSON パースエラー:
  - レスポンスを検証して空スコア（0.0）でフォールバックするようになっています。API レスポンスやレート制限を確認してください。
- DuckDB に関するエラー:
  - DuckDB のバージョン差異で executemany の空配列処理などが影響する箇所があります。DuckDB の安定版を使ってください。

ライセンス・貢献
----------------
- 本リポジトリのライセンス表記が同梱されていない場合は、プロジェクト方針に従って追加してください。  
- バグ報告・改善提案は Issue を作成してください。ユニットテストと型チェック（mypy 等）の追加を歓迎します。

補足メモ
--------
- 自動で .env をプロジェクトルートから読み込む仕組みがあります（config._find_project_root）。テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI クライアント呼び出し箇所はテスト容易性を考慮し、内部の _call_openai_api をモック差し替えられるように実装されています。

以上が KabuSys の概要・セットアップ・基本的な使い方です。より詳細な API（関数の引数や戻り値の仕様）は各モジュールの docstring を参照してください。質問や README の補足希望があれば教えてください。