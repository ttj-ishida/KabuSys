# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
タグ付け前の最初のリリースとして v0.1.0 を記録しています。

全体的な方針・注記
- コードベースは日本株自動売買システム「KabuSys」の初期実装です。
- 設定は主に環境変数（.env）で管理し、DuckDB / SQLite を分析・監視用に利用します。
- 実行系（Execution）と監視系（Monitoring）は分離されており、ペーパートレード用 DB を用意することで本番 DB と分離できる設計です。

## [0.1.0] - 2026-04-18

### Added
- プロジェクト初期リリース（v0.1.0）。
- コアパッケージエントリポイント
  - kabusys.__version__ = "0.1.0"
  - パッケージ API エクスポート: data, strategy, execution, monitoring。

- 設定管理
  - kabusys.config
    - .env 自動ロード機能（プロジェクトルート検出: .git / pyproject.toml）を実装。
    - .env/.env.local の読み込みルール（OS 環境変数の保護、override の扱い）。
    - .env 行パーサーは export 形式、クォート（シングル・ダブル）とエスケープ、インラインコメントの扱いに対応。
    - Settings クラスを導入し、各種設定値（J-Quants、kabuAPI、DB パス、監視閾値、環境種別など）をプロパティとして取得可能に。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV 検証（development/paper_trading/live）などのバリデーションを実装。

- 環境設定・検証 CLI
  - kabusys.config_setup
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - J-Quants/Kabu API トークン等のシークレット項目をマスク表示しつつ入力を支援。
    - .env の読み書きロジックを含む（既存値の再利用、オプション項目の扱い）。
  - kabusys.validate_config
    - 起動前チェック CLI。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース（PyYAML がある場合）を検証。
    - --strict オプションで警告を失敗として扱うモードを追加。
    - 本番（live）時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）をチェック。

- 実行・監視ランナー
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（paper_trading 時はモックを利用する想定）。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による外部停止検知とエンジン停止処理を実装。
    - PID ファイル作成場所を data/execution.pid に指定可能（Settings 経由）。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。0 以下の値は警告してデフォルトにフォールバック。
    - 監視は「環境にかかわらず」production 用 sqlite_path を使用する設計（監視データは本番 DB を参照）。
    - data/stop_requested.flag による停止機構を実装。

- モニタリング DB 初期化
  - monitoring_db 初期化ユーティリティ（起動時に監視テーブルが存在することを保証、冪等）。

- ユーティリティ
  - kabusys.utils.logging_setup
    - 共通ログ設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - ログレベル / ログディレクトリの解決順（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続するフォールバック実装。
  - kabusys.utils.process_priority
    - プラットフォーム差分を吸収したプロセス優先度（high/normal/low）設定を実装（psutil 経由）。
    - Windows 用の priority class、POSIX 用の nice 値を考慮。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。アクセス権限や未サポート環境時は警告してスキップ。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。スコア合計がゼロの場合は等分配にフォールバックし警告を出す。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用して候補を除外。売却予定銘柄を露出計算から除外する機能あり。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数計算を実装。
    - 単元（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap によるスケーリング（cost_buffer を考慮）、残差の取り扱い（fractional remainder に基づく追加配分）を実装。
    - risk_based モードではリスク許容量（risk_pct）とストップロス率（stop_loss_pct）からベース株数を算出。
    - 価格欠損や単元未満の処理に関するログ出力を含む。

- 研究・因子計算（基礎）
  - kabusys.research.factor_research
    - Momentum / Value / Volatility / Liquidity ファクターの計算方針と定数を定義。DuckDB 接続を用いた prices_daily / raw_financials 参照を想定しており、モメンタム計算関数（calc_momentum）の骨格を追加（ファイルは途中までの実装）。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）からデータを取得し、システム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを計算して PASS/FAIL 判定（閾値はソース内に定義: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ（--from/--to）と --db オプションをサポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Operational details
- 実行時の挙動
  - run_execution/run_monitoring は起動直後にプロセス優先度を "high" に設定しようと試みます（権限不足や未サポート OS では警告してスキップ）。
  - 両ランナーは data/stop_requested.flag による外部停止をサポート。ExecutionEngine は PID ファイルを管理し、監視は一定間隔で check_once を呼び出します。
  - run_execution は paper_trading モード時に paper 用 DB を使い、ブローカーをモック化して発注を隔離する設計です（実ブローカーとは分離）。
- 依存関係と挙動のフォールバック
  - psutil が必要な機能（プロセス優先度・CPU affinity）については、AccessDenied や未実装例外を捕捉して警告し、処理を続行します。
  - logging_setup はログディレクトリ作成に失敗した場合にファイル出力を無効化して stdout のみで動作します。
  - validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出します。

今後の改善候補（コード中の TODO や注意点）
- position_sizing: 銘柄ごとの単元サイズ（lot_size）を stocks マスタから取得できるよう拡張する案がある。
- risk_adjustment.apply_sector_cap: 価格が欠損（0.0）な場合のフォールバック価格（前日終値等）を導入することでエクスポージャー見積りを改善できる。
- research.factor_research: ファクター計算の実装を完了し、Z スコア正規化ユーティリティとの統合を行う。

----- 
この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリース日付は運用に合わせて調整してください。