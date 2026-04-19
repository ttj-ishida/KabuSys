# Changelog

すべての変更は Keep a Changelog の形式に従い、SemVer を採用します。
https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- research/factor_research.py の骨組みを追加。Momentum / Value / Volatility / Liquidity などのファクター計算を行う設計になっており、DuckDB 接続を受け取って prices_daily や raw_financials を参照して計算する方針を明記。
- config/.env ウィザード（kabusys.config_setup）を追加。対話式で .env を生成・更新でき、既存値の再利用やシークレットのマスク表示に対応。
- 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML があれば）をチェック。--strict オプションで警告をエラー扱いにできる。
- 実行系起動スクリプトを追加：
  - run_execution.py: ExecutionEngine 起動用。プロセス優先度を設定し、paper_trading 環境時は専用 SQLite（data/paper_trading.db）を使用する分離設計、BrokerClientFactory によるブローカー切替、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててスレッドで実行。停止フラグ（data/stop_requested.flag）や実行 PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用（監視 DB を本番 DB に集約）。

### Changed
- 設定読み込みロジック（kabusys.config）:
  - .env 自動ロード機能を導入（プロジェクトルートの検出に .git / pyproject.toml を利用）。OS 環境変数を保護する仕組み（protected set）を考慮した上で .env/.env.local を読み込む。
  - .env パース処理を堅牢化（export 形式対応、クォート内のエスケープ処理、インラインコメント処理など）。
  - Settings クラスに各種プロパティを追加・検証（J-Quants / kabu API / LINE / DB パス / paper_trading 用設定 / 監視・スロット関連閾値 / env/log_level の検証など）。
  - PAPER_FILL_MODE の妥当性チェックを実装（instant/partial/never/reject のみ許容）。
- ロギング設定ユーティリティ（kabusys.utils.logging_setup）を追加。StreamHandler（stdout）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしコンソール出力のみ継続する耐障害性を確保。
- プロセス優先度関連ユーティリティ（kabusys.utils.process_priority）を追加。Windows/Linux/macOS を吸収して nice 値や Windows の優先度クラスへ変換。CPU affinity 設定関数も提供。権限不足時は警告を出してスキップする安全設計。
- Paper Trading 向け検証レポートツール（kabusys.tools.paper_verification_report）を追加。稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し PASS/FAIL 判定する。--from/--to/--db オプション対応。P95 は内製関数で算出。
- ポートフォリオ構築モジュール（kabusys.portfolio）を追加:
  - portfolio_builder: 候補選定（スコア降順、signal_rank でタイブレーク）、等金額/スコア加重ウエイト計算（スコア全0 の場合は等分フォールバック）。
  - risk_adjustment: セクター集中制限の適用（既存ポジションを考慮して同一セクターの上限超過時に候補除外）、レジームに基づく乗数（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - position_sizing: 発注株数決定ロジック（risk_based / equal / score）。単元株（lot_size）丸め、ポートフォリオ上限・銘柄上限・手数料スリッページを考慮した aggregate cap スケーリング、残差処理による追加配分ロジックを実装。

### Fixed
- SQLite / DuckDB 接続と監視・実行のクリーンアップ処理を確実に実行するように try/finally ブロックを適切に配置（run_monitoring/run_execution）。

### Notes / Known issues
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨を TODO コメントで明記。将来的に前日終値や取得原価をフォールバックする予定。
- position_sizing の lot_size は現在グローバル固定（デフォルト 100）で、将来的に銘柄別単元を stocks マスタから取得する拡張を想定している。
- research/factor_research.py はファイル末端で未完（calc_momentum の実装途中の痕跡あり）。今後の実装で DuckDB を用いた完全なファクター計算を追加予定。

---

## [0.1.0] - 2026-04-19

初期リリース。主要な機能を実装。
- 基本構成
  - パッケージ初期化（__version__ = "0.1.0"）
  - Settings クラスによる環境変数管理と検証
  - .env 自動ロード（.env / .env.local をプロジェクトルートから読み込む）
- 実行・監視
  - run_execution.py: ExecutionEngine 起動フロー、paper_trading 用 DB 分離、停止フラグおよび PID 管理
  - run_monitoring.py: SystemMonitor ポーリングループ、MONITOR_POLL_INTERVAL による設定、停止フラグ検知
- 監視・データ
  - DuckDB / SQLite を用いた永続化接続を標準化（設定でパス指定可能）
- ユーティリティ
  - logging_setup: 統一的なログ設定（stdout + 日次ローテーション）
  - process_priority: OS 間差分を吸収した優先度 / CPU affinity 設定
- Portfolio（資金配分ロジック）
  - 候補選定、ウエイト計算、ポジションサイズ算出、セクター上限・レジーム乗数の適用
- CLI / ツール
  - config_setup: 対話式 .env ウィザード
  - validate_config: 環境設定検証 CLI
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプト
- ドキュメント
  - 各モジュールに設計ノート・注釈・使用方法を記載（モジュールトップの docstring）

---

（以降のリリースでは、各ファイルの未完了部分（例: factor_research の続き、Strategy/Execution の詳細な実装やテスト追加など）を実装していく予定です。）