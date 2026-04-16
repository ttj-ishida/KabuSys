Keep a Changelog 準拠の形式で、本リポジトリの初回リリース向け CHANGELOG を作成しました。
コード内容から推測して記載しています（実装上の挙動・既定値・注意点を含む）。

CHANGELOG.md
=============
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

Unreleased
----------
（現在のリポジトリ状態は次のリリースに含める予定です）

[0.1.0] - 2026-04-16
--------------------
初回リリース。

Added
-----
- 基本アプリケーションパッケージを追加
  - kabusys パッケージの初期バージョンを導入（__version__ = 0.1.0）。

- 環境・設定管理 (src/kabusys/config.py)
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - 読み込み順: OS 環境変数 > .env.local > .env。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などをサポート。
  - Settings クラスを提供し、各種環境変数（DB パス・API トークン・監視閾値・実行モードなど）をプロパティで取得。
  - PAPER_FILL_MODE の検証、KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL のバリデーションを実装。

- 実行・監視起動スクリプト
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成（モックと本番の選択想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組立て・起動を行う。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）を利用した制御を実装。
    - デフォルトでプロセス優先度を "high" に設定。

  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用（監視データは常に本番側 DB に記録する設計）。
    - 停止フラグの検知、例外のハンドリング、接続の確実なクローズ処理を実装。
    - デフォルトプロセス優先度を "high" に設定。

- 監視 DB 初期化ユーティリティ（init_monitoring_db を各所から呼び出すことでテーブル存在を保証）

- Execution 周りのコンポーネント（概要、設定）
  - RiskManager（デフォルトコンフィグの導入、initial_portfolio_value を broker.get_available_cash() で初期化）
  - ExecutionEngine（スレッド実行/停止制御、duckdb 接続を使用）
  - OrderManager / OrderRepository / Reconciler の使用・組立て

- Portfolio 関連（src/kabusys/portfolio/**）
  - portfolio_builder
    - select_candidates: スコア降順 + signal_rank のタイブレークで候補選定
    - calc_equal_weights / calc_score_weights: 重み計算（スコアが全て 0 の場合は等配分へフォールバック）
  - risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーから新規候補を除外（unknown セクターは除外しない）
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear のマップ、未知レジームは警告して 1.0 にフォールバック）
  - position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算
    - 単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer による保守的見積り、aggregate cap によるスケーリング（端数処理ロジック含む）

- Research / ファクター計算（src/kabusys/research/**）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（不足データは None）
    - calc_volatility: ATR20、相対 ATR、平均売買代金、出来高比率を計算（データ不足判定あり）
    - calc_value: raw_financials と株価を組み合わせて PER / ROE を計算（target_date 以前の最新財務データを取得）
    - DuckDB を用いた SQL ベース実装（prices_daily / raw_financials を参照）
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターン一括取得（ホライズンの検証あり）
    - calc_ic: スピアマンのランク相関（IC）を計算（レコード不足時は None）
    - rank / factor_summary: ランク変換、基本統計量計算（count/mean/std/min/max/median）

- Research パッケージ公開 API に必要なエクスポートを追加（zscore_normalize を含む）

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書き込むための実装。
  - デザイン上の特徴:
    - タイムウィンドウ計算（JST 基準 → UTC へ変換）を提供（calc_news_window）。
    - 銘柄ごとに記事を集約し、1銘柄あたりの最大記事数 / 文字数でトリムしてトークン肥大化を抑制。
    - 最大 BATCH_SIZE（デフォルト 20）でバッチ送信、429/ネットワーク断/5xx に対して指数バックオフでリトライ。
    - レスポンスのバリデーション（JSON 形式、results キー、code の既知性、スコア数値化）とスコアクリッピング（±1.0）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - フェイルセーフ: API 失敗時も部分成功分を保護して継続する設計。DuckDB の executemany に関する注意（params が空でないこと）に留意して置換処理を行う。
  - （注意）news_nlp.py はファイル末尾で断片的に終わっているように見えます（コードベースの取得時点）。実運用前に関数の完全実装・テストを推奨。

- CLI ツール: Paper Trading 検証レポート
  - src/kabusys/tools/paper_verification_report.py
    - paper_trading DB を解析し、稼働率・注文成功率・送信率・P95 レイテンシ等の指標を計算して標準出力にレポートを表示する。
    - CLI 引数: --from / --to / --db（PAPER_TRADING_SQLITE_PATH 環境変数やデフォルトパスを優先）
    - 既定の合格基準を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 <= 200 ms）。該当しない場合は FAIL として指摘。
    - P95 計算や各種クエリで DB テーブルが存在しない場合のフォールバックを実装。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度を設定。権限不足や未サポート環境では警告してスキップ。
  - set_cpu_affinity(cpu_count): 最初の N コアにプロセスを固定する機能（引数検証、権限エラー・未実装時は警告してスキップ）。

Changed
-------
- n/a（初回リリースのため「変更」はありません）

Fixed
-----
- n/a（初回リリースのため「修正」はありません）

Security
--------
- n/a（現時点で特記すべきセキュリティ修正はありません）
  - ただし OpenAI API キー等の秘匿情報は環境変数経由で取り扱う設計を採用しています。運用環境では適切に管理してください。

Notes / Upgrade / Known issues
------------------------------
- run_monitoring は監視データ記録に常に本番 sqlite_path を使用します。監視データを分離したい場合は設定やコードの見直しが必要です。
- news_nlp.py が途中で切れている/未完の可能性があります。OpenAI に関するロジックは重要な箇所のため、実運用前に完全な実装・単体テスト・エンドツーエンドテストを行ってください。
- position_sizing のスケールダウン処理や price の欠損時の挙動（price が 0.0 の場合、エクスポージャーが過少見積りされる可能性）についてはコメントに注意事項を残しています。将来的に価格フォールバック（前日終値等）を導入することを推奨します。
- .env の自動読み込みはプロジェクトルート探索に依存するため、配布後やパッケージ化後の動作に影響する可能性があります。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で制御してください。
- DuckDB / SQLite のパスは Settings でデフォルトを持っています（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。本番運用時は適切な配置を行ってください。

Acknowledgements
----------------
- この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノート作成時は、リリースに含めるコミットや PR の差分を参照の上、必要に応じて調整してください。