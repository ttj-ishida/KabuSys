# CHANGELOG

この変更履歴は Keep a Changelog の書式に準拠しています。  
コードベースからの推測に基づき記載しています（実装済み機能・振る舞いの要約）。

全般:
- 初期バージョンとして v0.1.0 をリリース。
- 環境変数による構成、ローカル .env ウィザード、設定検証 CLI、監視/実行用起動スクリプト、ポートフォリオ構築ロジック、ペーパートレード検証ツール、ユーティリティ群（ロギング・プロセス優先度設定等）を含む。

## [Unreleased]

- （現在の差分はありません）

## [0.1.0] - 2026-04-19

### 追加 (Added)
- プロジェクト基本機能を追加
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを作成。
    - Engine をデーモンスレッドで実行し、data/stop_requested.flag による停止監視、data/execution.pid に PID を書き出す想定。
    - 標準的な RiskManager 設定（max_position_pct, max_utilization 等）のデフォルト値を提供し、broker.get_available_cash() を初期 portfolio value として使用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数で間隔を指定可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）でループ終了。
    - 監視用 DB は環境に関わらず production 用 sqlite_path を使用（監視は本番 DB を参照する設計）。

- 環境設定 / 構成管理
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 高度な .env パース対応（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの処理）。
    - Settings クラスで各種設定プロパティを提供（DB パス・API トークン・環境種別・監視閾値等）。
    - PAPER_FILL_MODE 検証、KABUSYS_ENV / LOG_LEVEL のバリデーション。
  - config_setup.py（対話式ウィザード）
    - .env 初期作成・更新を支援する対話式ウィザードを提供。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch の設定を対話入力で作成できる。
  - validate_config.py（設定検証 CLI）
    - .env および config/*.yaml の妥当性チェックを実行する CLI を提供。
    - --strict モードで警告を FAIL 扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV 検証、パス存在確認、YAML のパース検証（PyYAML がある場合）などを実施。
    - 本番環境（KABUSYS_ENV=live）に対する追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険性）を警告。

- ツール
  - tools.paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、レイテンシ）を集計しレポートを生成する CLI。
    - P95 計算、期間フィルタ、定義済み閾値に基づく PASS/FAIL 判定を実装。
    - 主要閾値: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（同点時は signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分の実装（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックで 1.0）。Bear/Neutral の挙動について注記あり。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を算出。単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer による保守的コスト見積り、端数処理（remainders）を実装。

- 研究用モジュール（研究 / ファクター計算）
  - research.factor_research（部分実装）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照してモメンタム・MA200乖離等の計算を行う設計（モメンタム計算のインターフェースが存在。実装途中の痕跡あり）。

- ユーティリティ
  - utils.logging_setup
    - ルートロガーを統一的に設定するユーティリティを提供。
    - コンソール出力は stdout を使用（cron 等でのリダイレクトを考慮）。
    - 日次ローテートされるファイルハンドラ（TimedRotatingFileHandler, 30日保持）をサポート。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラの flush/close とクリアを行い二重設定を防止。
  - utils.process_priority
    - プロセス優先度設定ユーティリティ（set_process_priority, set_cpu_affinity）。
    - Windows / POSIX（Linux, macOS, FreeBSD）間の差分を吸収する実装。アクセス権限エラーや未対応 API に対しては警告を出してスキップする安全設計。

### 変更 (Changed)
- ロギングの取り扱いを明確化
  - stdout を使用することでログのリダイレクトを想定（stderr ではなく stdout）。
  - 既存ハンドラを削除してから再設定することで多重ハンドラ設定問題を回避。

- .env 読み込みの挙動
  - OS 環境変数を保護するため protected セットを導入し、.env.local は .env より優先的に上書き（ただし OS 環境変数は上書きされない）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- Execution / Monitoring 起動フロー
  - 起動時にプロセス優先度を高（"high"）に設定する呼び出しを追加（set_process_priority）。
  - 監視起動は常に production 用 sqlite_path を使用する（他環境と分離しない監視ポリシー）。

### 修正 (Fixed)
- .env パースの堅牢化
  - export プレフィックス・クォート内のエスケープ処理・インラインコメント扱い等に対応し、現実的な .env パターンに耐えるように改善。

- DB 初期化の冪等化
  - init_monitoring_db(sqlite_conn) を実行して監視テーブルの存在を保証。paper_trading 用 DB と本番 DB の分離を確実化。

### ドキュメント補足 / 注意事項 (Notes)
- config.setup と validate_config により、ローカル開発者は .env の生成・検証を簡単に行えるようになっている。特に本番環境では KILL_FLAG_CLEAR_ON_START や LINE 通知設定の有無などに注意するよう警告を出すガードがある。
- position_sizing の算出ロジックにはいくつかの TODO/注意（価格欠損時の扱い、将来的な銘柄別 lot_size 対応など）がコード内コメントとして残されている。
- research.factor_research は設計に沿ったインターフェースを提供しているが、完全実装には追加の SQL / 集計ロジックが必要な箇所がある（コード末尾に未完の痕跡あり）。

### セキュリティ (Security)
- 本リリースでの機密情報の扱いは .env に集中しており、config_setup 文章内で .env を絶対に Git にコミットしないよう明記している。
- 環境変数の必須項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）は validate_config による検出対象。

---

将来的な改善案（非網羅）
- research モジュールの完全実装（ファクター計算の SQL 最適化、欠損値の扱いの厳密化）。
- 銘柄ごとの lot_size 対応、手数料・スリッページのより現実的なモデル化。
- SystemMonitor / ExecutionEngine の詳細なテスト、モニタリングデータの可視化ツール追加。