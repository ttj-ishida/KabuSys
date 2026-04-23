# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルでは主にコードベースから推測できる新機能、挙動、注意点を記載しています。

## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーションと CLI:
  - kabusys パッケージ本体を追加（__version__ = 0.1.0）。
  - 環境設定ウィザード CLI: `kabusys.config_setup` を追加。対話式で `.env` ファイルを生成・更新可能。
  - 設定検証 CLI: `kabusys.validate_config` を追加。必須環境変数や config/*.yaml、パス等の事前チェックを実施。
  - Paper Trading 検証レポート生成スクリプト: `kabusys.tools.paper_verification_report` を追加。ペーパートレード用 SQLite DB から稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL レポートを表示する。
- 実行 / 監視ランチャー:
  - 実行エンジンスクリプト: `run_execution.py` を追加。ExecutionEngine を起動し、ブローカークライアントの抽象化経由で発注を行う。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を分離して使用（`data/paper_trading.db` がデフォルト）。
  - 監視ループスクリプト: `run_monitoring.py` を追加。SystemMonitor をポーリング実行し監視データを SQLite に記録。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。
- 設定・環境処理:
  - `kabusys.config.Settings` を実装。環境変数から各種設定を取得するユーティリティ（DB パス、API トークン、環境種別、閾値等）。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` / `.env.local` を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。既存の OS 環境変数は保護される。
  - `.env` パーサを強化: export 形式のサポート、クォート／エスケープ、インラインコメントの取り扱いを実装。
  - PAPER_FILL_MODE のバリデーションを追加（有効値: "instant", "partial", "never", "reject"）。
- ポートフォリオ構築関連（純粋関数群）:
  - 候補選定・重み計算: `portfolio.portfolio_builder`（select_candidates, calc_equal_weights, calc_score_weights）を追加。
  - セクター集中制限・レジーム乗数: `portfolio.risk_adjustment`（apply_sector_cap, calc_regime_multiplier）を追加。
  - 株数決定・リスク制限・単元丸め: `portfolio.position_sizing`（calc_position_sizes）を追加。risk_based / equal / score の各配分法に対応し、aggregate cap と lot_size に基づくスケーリング処理を実装。
  - モジュールエクスポートをまとめた `kabusys.portfolio` を追加。
- ユーティリティ:
  - ログ設定ユーティリティ: `kabusys.utils.logging_setup.setup_logging` を追加。コンソール(stdout) と 日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティ: `kabusys.utils.process_priority` を追加。Windows / POSIX の差分を吸収して優先度（high/normal/low）や CPU affinity を設定（権限不足や未対応 OS では警告を出してスキップ）。
- データベース関連:
  - SQLite（監視用）と DuckDB（分析用）の利用をコード内で明確化。多くの起動スクリプトが両方の接続を開くようになっている。
- リサーチ（ファクター計算）:
  - `kabusys.research.factor_research` を追加。Momentum / Value / Volatility / Liquidity 等のファクター計算方針を実装する設計で、DuckDB 経由で prices_daily / raw_financials を参照する実装が始まっている（モメンタム関連の関数骨格を含む）。

### Changed
- 監視と実行の DB 分離ポリシーの明確化:
  - 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する実装になっている（監視データは環境に依存せず本番 DB を参照する意図）。
  - 実行（run_execution）は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離する（ペーパートレードを完全に本番 DB から切り離す）。
- デフォルト・パスとファイル名:
  - データ/ログのデフォルトパスを統一（例: data/kabusys.duckdb, data/monitoring.db, logs/<app>.log）。
- ログ出力:
  - 実行時に stdout を使う設計に統一（cron などで stdout/stderr を一本化する運用想定）。
- 環境ロードの優先順:
  - OS 環境変数 > .env.local > .env の順でロードされる仕様を明確化。

### Fixed / Robustness
- 環境変数パースの堅牢化:
  - 不正な MONITOR_POLL_INTERVAL 値や PAPER_FILL_MODE の誤設定時に適切に警告・例外を発生させるようにした（MONITOR_POLL_INTERVAL が不正な場合はデフォルト 60 秒にフォールバック）。
  - .env 読み込みでファイルアクセス失敗時に警告を出して処理を継続するようにした。
- 起動中の安全対策:
  - 起動時にプロセス優先度を "high" に設定するフローを追加（アクセス拒否や未対応 OS の場合はログで警告して継続）。
  - 起動・停止制御用のフラグファイル（data/stop_requested.flag、data/kill.flag など）および PID ファイルの取り扱いを実装。停止フラグの検知で安全にシャットダウンするループを用意。
- Paper trading 用のレポートと統計:
  - 空データやテーブル未存在時にもエラーにならずフォールバック（N/A や 0 扱い）してレポート出力するように堅牢化。

### Notes / Known issues / TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされ得る旨の注記あり。将来的に前日終値や取得原価等でのフォールバックを検討する想定。
- research.factor_research:
  - ファイル内にモメンタム算出関数の骨格があるが一部（ファイル末尾）が未完の様子。今後の実装で Value / Volatility / Liquidity の算出処理および Zスコア正規化の統合が必要。
- ログディレクトリ作成失敗時:
  - ファイルハンドラの作成に失敗した場合はコンソールのみで継続する実装。運用時には logs/ ディレクトリのパーミッションやマウント状態を確認してください。
- 実行/監視の DB 接続:
  - run_monitoring が本番 sqlite_path を参照することは意図的な設計だが、環境により運用上の注意が必要（テスト環境で監視データを分離したい場合は設計を見直すか設定で別パスを指定してください）。

### Security
- シークレット扱いの環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env に直接保存する想定だが、.env は Git にコミットしないことを強く推奨する注釈を追加済み（config_setup がヘッダに警告を出力）。

---

今後のリリースでは以下を予定しています（優先度順、推測）:
- research/factor_research の完全実装（各ファクター計算と正規化パイプライン）。
- ExecutionEngine / BrokerClient 周りの詳細実装・テストカバレッジ強化。
- 単体テスト・CI 設定、ドキュメント整備（API doc、運用手順）。
- モニタリングのアラート送信（LINE 連携）の追加・強化。