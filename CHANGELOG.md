# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]

### Added
- run_monitoring スクリプトを追加
  - SystemMonitor ポーリングループを起動するスクリプトを実装。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止はプロジェクト直下の data/stop_requested.flag ファイルで制御。
  - 監視は環境にかかわらず本番用の sqlite_path を使用する仕様を採用。
  - 例外時にも監視ループを継続するように例外ハンドリングを強化。

- run_execution スクリプトを追加
  - ExecutionEngine を起動するサードプロセス用スクリプトを実装。
  - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
  - 停止フラグ（data/stop_requested.flag）を検出してエンジンを安全に停止する機能を実装。
  - 実行時 PID ファイルを扱う設定を追加。

- 設定管理・自動ロード機能を追加（kabusys.config）
  - .env 自動読み込みをプロジェクトルート（.git または pyproject.toml を起点）から行う実装を追加。
  - .env のパース機能を強化（export プレフィックス対応、シングル／ダブルクォートのエスケープ処理、インラインコメント処理など）。
  - 必須環境変数チェック用のヘルパー _require を提供。
  - 各種設定プロパティを Settings クラスで提供（DB パス、API トークン、paper_trading 用設定、監視閾値、ログレベル、環境種別など）。

- 設定ウィザード（kabusys.config_setup）を追加
  - 対話式で .env を生成・更新する CLI を追加。
  - 保存前の確認表示や既存 .env の読み込み・再利用をサポート。
  - デフォルト値、選択肢、シークレット入力（表示マスク）等をサポート。
  - 出力テンプレートは .env に直接書き込む形式。

- 設定検証 CLI（kabusys.validate_config）を追加
  - .env と config/*.yaml の設定チェックを行う CLI を実装。
  - 必須環境変数未設定チェック、KABUSYS_ENV の妥当性チェック、ログレベルチェック、DB パスの親ディレクトリ存在確認、YAML ファイルの存在およびパース検証（PyYAML が利用可能な場合）を行う。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Switch 設定の警告）を実装。
  - --strict オプションで警告を FAIL 扱いにできる。

- ロギング設定ユーティリティを追加（kabusys.utils.logging_setup）
  - setup_logging() を通じて全アプリケーションで統一的なログ設定を提供。
  - stdout への StreamHandler（標準出力）と、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を組み合わせて設定。
  - 既存ハンドラの二重登録を避けるため、再設定時に既存ハンドラを flush/close してクリアする。
  - 環境変数 LOG_DIR / LOG_LEVEL の優先解決を実装。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。

- プロセス優先度・CPU affinity ユーティリティを追加（kabusys.utils.process_priority）
  - set_process_priority(level) で Windows / POSIX を吸収してプロセス優先度を設定。
  - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアへピンニングする機能を追加（アクセス権限不足時は警告を出してスキップ）。
  - 標準的な優先度レベル ("high", "normal", "low") をサポート。

- Paper Trading 検証レポートツールを追加（kabusys.tools.paper_verification_report）
  - ペーパートレード用 SQLite DB（PAPER_TRADING_SQLITE_PATH で指定可）を集計してレポートを生成。
  - 稼働率 (uptime)、注文成功率(fill rate)、送信率(send rate)、レイテンシ（avg/max/P95）等を算出。
  - PASS/FAIL 判定（閾値: uptime >= 99%、fill >= 90%、send >= 95%、P95 latency <= 200ms）を実装。
  - 日付フィルタ（--from, --to）による集計が可能。

- ポートフォリオ構築ライブラリを追加（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等分配へフォールバック。
  - risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。未知レジームはフォールバックで警告を出す。
  - position_sizing: allocation_method("risk_based"/"equal"/"score") に応じた発注株数計算を実装。単元株（lot_size）丸め、最大ポジション上限、aggregate cap（利用可能現金に基づくスケーリング）や cost_buffer を考慮したスケーリングロジックを実装。価格欠損時のスキップ等の耐性を持たせる。

- 研究用ファクターモジュールの骨子を追加（kabusys.research.factor_research）
  - モメンタム、移動平均乖離、ATR、出来高等を DuckDB の prices_daily 等から計算するための設計と一部定数を実装（関数の実装途中あり）。

### Changed
- 設定ロードの挙動を明確化
  - OS 環境変数を保護して .env/.env.local の上書き順序を制御（.env.local は override=True で上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。

- ログ設定の挙動
  - stdout を標準出力に固定（stderr ではない） — cron/スケジューラでのリダイレクト運用を想定。
  - 既存ハンドラが存在する場合は安全にクローズしてから再設定。

### Fixed
- MONITOR_POLL_INTERVAL とポーリングループの堅牢性向上
  - 環境変数 MONITOR_POLL_INTERVAL の不正値（負数・0・非数）に対してデフォルトにフォールバックし、警告を出力するように修正。time.sleep に渡す不正値によるクラッシュを防止。

- .env パースの改善
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応し、不正な .env 行による誤読を減らすよう改善。

- ExecutionEngine 起動時の DB 分離
  - paper_trading モード時に paper_trading 用 SQLite を明示的に使用するように修正し、本番データとの混在リスクを回避。

### Security
- .env の取り扱いに関する注意
  - config_setup により生成される .env は Git にコミットしない旨を明記（テンプレートヘッダに警告を追加）。

---

## [0.1.0] - 2026-04-19

### Added
- 初回公開: KabuSys 基本コンポーネントを実装
  - 実行スクリプト: run_execution, run_monitoring
  - 設定関連: kabusys.config, config_setup ウィザード、validate_config 検証ツール
  - ロギング/プロセス制御ユーティリティ: logging_setup, process_priority
  - ポートフォリオ構築: portfolio_builder, position_sizing, risk_adjustment
  - Paper Trading 検証ツール: tools.paper_verification_report
  - 研究用ファクター計算基盤（factor_research の骨子）
  - パッケージメタ情報: __version__ = "0.1.0"

### Changed
- N/A（初回リリース）

### Fixed
- N/A（初回リリース）

---

注: 上記 CHANGELOG は提供されたソースコードから機能・意図を推測して作成した要約です。実際の変更履歴（コミット単位やリリースノート）とは差異がある可能性があります。必要であれば、各モジュールの詳細（例: EngineConfig / RiskConfig のデフォルト値、各関数の例外挙動、未実装箇所の TODO）を反映した改訂版を作成します。