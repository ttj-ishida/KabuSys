# Changelog

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。  
このファイルはコードベースの現在の状態から推測して作成した変更履歴です（実際のコミット履歴とは異なる場合があります）。

## [Unreleased]

### Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて MockBrokerClient を使用する（KABUSYS_ENV=paper_trading 時）ことで本番 DB と完全分離されたペーパートレードが可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 設定管理・ウィザード・検証ツールを追加
  - config.py: 環境変数と .env ファイルの自動読み込み、設定取得用 Settings クラスを提供。プロジェクトルート自動検出、PAPER_FILL_MODE 等の検証を実装。
  - config_setup.py: 対話式 .env 作成 / 更新ウィザードを追加（.env のテンプレート生成、シークレット扱い、保存確認など）。
  - validate_config.py: 起動前設定検証 CLI を追加（必須環境変数チェック、config/*.yaml の存在・パース検査、--strict オプション）。
- ペーパートレード関連ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、レイテンシなどを集計して PASS/FAIL 判定を行う。
- ポートフォリオ構築モジュールを追加
  - portfolio/portfolio_builder.py: 候補選定と等重・スコア重み計算を実装（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装（risk_based / equal / score、単元株丸め、aggregate cap スケーリング等）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用とレジーム別乗数（calc_regime_multiplier, apply_sector_cap）。
  - portfolio/__init__.py でエクスポートを整理。
- 研究・ファクター計算
  - research/factor_research.py: DuckDB 接続を用いたモメンタム・ボラティリティ等のファクター計算実装（calc_momentum, calc_volatility 等、DuckDB SQL ベース）。Analytics 用に DuckDB を利用する設計。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定と CPU affinity のユーティリティを追加。Windows / POSIX の差分を吸収し、アクセス権限不足時は警告でスキップ。
- 監視 DB 初期化ユーティリティ参照（init_monitoring_db を使用するコードを追加）および PID / stop フラグの取り扱いを全体で統一。

### Changed
- DB 分離のルールを明確化
  - run_execution は paper_trading 環境時に専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番の monitoring DB と分離するように設計。
  - run_monitoring は環境にかかわらず本番用 sqlite_path を利用して監視データを記録する設計（監視は常に本番 DB を想定）。
- .env 読み込みの優先度と保護
  - config.py で自動ロード順を OS 環境変数 > .env.local > .env に統一。既存 OS 環境変数を保護するため protected セットを導入。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
- 設定検証の厳格化
  - validate_config.py にて必須 / 推奨項目のチェックや本番環境（KABUSYS_ENV=live）向けの追加警告を実装。--strict で警告を FAIL 扱いにできる。
- ログ・プロセス周り
  - 起動スクリプトでプロセス優先度を起動直後に High に設定する処理を追加（set_process_priority("high")）。
  - 起動時の PID ファイル / stop flag の取り扱いを統一し、安全に起動・停止できるようにした。

### Fixed
- .env パーサの堅牢化
  - config._parse_env_line でシングル/ダブルクォートのエスケープやインラインコメントの扱いを改善。export プレフィックスにも対応。
  - _load_env_file でファイル読み込みエラーを警告に落として処理継続するように修正。
- ポートフォリオ関連ロジックの安全策追加
  - calc_score_weights: 全スコアが 0 の場合に等重配分へフォールバックし、警告を出すようにした。
  - apply_sector_cap: "unknown" セクターの銘柄はセクター上限の適用対象外とする挙動を明確化。
  - calc_position_sizes: 価格欠損（None/0）の銘柄をスキップするようにし、不整合で例外が発生しないようにした。aggregate cap 適用時の端数配分アルゴリズムを実装し、lot_size 単位で安定して配分するよう改良。
- run_monitoring のポーリング間隔設定
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非数値）に対しては警告しデフォルト 60 秒へフォールバックするように修正（time.sleep の ValueError を回避）。

### Security
- .env の取り扱いに関する注意を config_setup.py のヘッダに明記（.env を絶対に Git にコミットしない旨）。

---

## [0.1.0] - 2026-04-17

初回リリース相当（コードベースから推測）。

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__init__.__version__ = "0.1.0"）。
- 実行インフラ
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。BrokerClientFactory を用いたブローカー接続、OrderManager / Reconciler / RiskManager を組み立ててバックグラウンドスレッドで実行可能にした。
  - run_monitoring.py: SystemMonitor のポーリングループを実装。監視停止フラグ検知、例外時のログ出力、sqlite / duckdb の接続管理を含む。
- 設定周り
  - config.py: Settings クラスを実装（各種環境変数ラッパ、型変換、バリデーション）。
  - config_setup.py: 対話式ウィザードで .env を生成・更新するツールを提供。テンプレート化した .env 出力を実装。
  - validate_config.py: 起動前設定チェック用 CLI を実装（必須環境変数、YAML 構成ファイルチェック、パス存在チェックなど）。
- ポートフォリオおよび資金配分
  - portfolio モジュール群を実装（候補選定、重み付け、ポジションサイズ計算、セクター上限、レジーム乗数）。
- 研究（リサーチ）
  - research/factor_research.py: DuckDB を利用したファクター計算基盤（モメンタム・ボラティリティ等）。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定ユーティリティ（Windows / POSIX 対応）および CPU affinity 設定。
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成。

### Changed
- なし（初回リリース想定）。

### Fixed
- なし（初回リリース想定）。

---

注記:
- 本 CHANGELOG はリポジトリ内のソースコードから推測して作成しています。実際のコミットメッセージやバージョニング運用と差異がある場合があります。
- 今後のリリースでは、機能追加・バグ修正・設計変更を上記の形式で逐次記載してください。