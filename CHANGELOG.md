Keep a Changelog
=================

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
主要な変更点はバージョンごとに記載しています。

注: 以下の変更履歴は提供されたコードベースの内容から推測して作成しています。

Unreleased
----------

（現在のスナップショット・初回リリースに続く将来の変更をここに記載します）

0.1.0 - 2026-04-13
------------------

Added
- 基本アプリケーション構成
  - kabusys.config.Settings クラスを導入。環境変数 / .env ファイルから設定を読み込み、各種設定値（DB パス、API トークン、閾値、実行環境フラグ等）を提供。
  - 自動 .env ロード機能を実装（プロジェクトルート判定: .git / pyproject.toml を探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルパーサを実装し、クォート、export プレフィックス、行内コメント等に対応。

- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine を起動する CLI エントリポイントを追加。
    - KABUSYS_ENV により paper_trading モードをサポート。paper_trading の場合は専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - プロセス優先度を高（"high"）に設定して起動する処理を追加。
    - ブローカークライアント生成（BrokerClientFactory）や OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の run_session 呼び出しを行う。
    - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors, circuit_breaker_window_sec, max_drawdown, initial_portfolio_value）を設定。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する旨の挙動を明示。
    - プロセス優先度を高に設定してからモニタリングを開始。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db が監視用テーブルの存在を保証（冪等な初期化）。

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順に選択。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分を提供。スコア合計が 0 の場合は等配分へフォールバック（警告出力）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用。既存保有のセクター比率が閾値を超える場合、新規候補を除外。unknown セクターは適用除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: 各銘柄の発注株数を計算。allocation_method ("risk_based" / "equal" / "score") をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超えた場合のスケールダウン）、cost_buffer を用いた保守的コスト見積り、残差に基づく追加配分（lot 単位）等を実装。

- 研究・因子計算
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB 上の prices_daily / raw_financials を参照してモメンタム、ATR 等のファクターを算出。ウィンドウやデータ不足時の振る舞いを明示。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（デフォルト horizons=[1,5,21]）。入力バリデーションあり。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）計算、ランク関数、基本統計サマリーを標準ライブラリのみで実装。
  - research パッケージは zscore_normalize を kabusys.data.stats からエクスポートするよう結合。

- AI ニュース NLP
  - ai.news_nlp:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとに ai_scores テーブルへ書き込む処理を実装。
    - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウを計算するユーティリティ（calc_news_window）。
    - バッチ処理（1 コール最大 20 銘柄）、記事数/文字数トリム、429・ネットワーク断・5xx に対する指数バックオフリトライ、レスポンス検証、スコア ±1.0 クリップ、部分書き換えでの安全な DB 操作方針を実装。
    - OpenAI API キー未設定時は例外を送出（明示的に api_key を渡すか OPENAI_API_KEY を設定する必要あり）。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows の priority class / POSIX の nice 値を吸収してプラットフォーム非依存に優先度を設定。対応 OS の一覧とフォールバック挙動を明示。
    - set_cpu_affinity(cpu_count): 最初の N コアにピン留め。アクセス拒否などの失敗時は警告してスキップ。
  - その他、パッケージ __init__ にバージョン情報 __version__ = "0.1.0" を追加。

- CLI ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成ツールを追加。コマンドライン引数 --from/--to/--db をサポート。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算・表示。閾値による PASS/FAIL 判定、DB 存在チェック、テーブル未存在時の耐障害性（OperationalError を捕捉）を実装。

Changed
- （初回リリースのため無し）

Fixed
- （初回リリースのため無し）

Deprecated
- （初回リリースのため無し）

Removed
- （初回リリースのため無し）

Security
- OpenAI API キー等の機密値は環境変数に依存する設計。Settings._require で必須トークン未設定時に明示エラーを出すため、デプロイ時に環境変数管理が必要。

Notes / Known behaviors
- run_monitoring.py は「監視は環境にかかわらず本番 sqlite_path を使用する」とコメントで明示しているため、開発・paper_trading 環境で監視を実行しても本番 DB を参照します。監視の分離が必要な場合は運用手順で DB パスを切り替えてください。
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後や実行パスが変わる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御するか、明示的に環境変数を設定してください。
- PAPER_FILL_MODE 等の一部環境変数には入力検証を行います。無効な値を与えると ValueError が発生します。
- calc_position_sizes の単元丸めや aggregate スケーリングは lot_size 単位で処理されるため、極端に小さい available_cash や price が欠損していると期待した配分にならない可能性があります（コード内に TODO/注意コメントあり）。
- ai.news_nlp の処理は OpenAI API との通信依存・レート制限・モデルレスポンスの形式に敏感です。運用時は API キー・レート制限・モデル変更時のレスポンス検証に注意してください。

開発者向け補足
- DuckDB 接続を受ける研究モジュールは SQL クエリに直接パラメータをバインドしており、prices_daily / raw_financials テーブルのスキーマに依存します。データ投入・マイグレーション時はこれらスキーマ互換性を保つこと。
- ロギングは各モジュールで logger = logging.getLogger(__name__) を使用しているため、上位（アプリ起動時）で basicConfig やハンドラを設定して運用してください。

---- 

（以降のリリースでは Changed / Fixed / Security 等のカテゴリを適宜更新してください）