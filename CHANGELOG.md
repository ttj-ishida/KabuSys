# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを意識して記載しています。

## [Unreleased]

### Added
- 監視・実行系の起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。停止はプロジェクト内の data/stop_requested.flag による。
  - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の場合は専用の Paper Trading DB を使用し MockBrokerClient を利用することで本番 DB と完全分離する。
- 環境設定／検証ツールを追加
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加（シークレット項目のマスク表示、選択肢・デフォルト対応）。
  - validate_config.py: .env と config/*.yaml の起動前チェック用 CLI を追加。--strict オプションで警告を失敗扱いにできる。PyYAML 未インストール時のフォールバックやファイルパスの親ディレクトリ検査を実装。
- 設定管理の強化
  - config.py: .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。.env/.env.local の取り込み順序・上書き規則（OS 環境変数保護）に対応。キー/値パースで export 前置、クォート内のエスケープ、インラインコメントの扱いなどをサポート。Settings クラスで各種設定値（DB パス、紙トレード用設定、監視閾値、PID/kill フラグパス等）をプロパティとして提供し、値検証を行う（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
- ロギング／プロセス優先度ユーティリティを追加
  - utils/logging_setup.py: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定する共通ユーティリティを実装。既存ハンドラのクリアやログディレクトリ作成のフォールバック処理を含む。
  - utils/process_priority.py: Windows/Linux/macOS の差を吸収するプロセス優先度設定ユーティリティを実装。CPU affinity 設定関数も追加し、権限不足等の際は警告を出して安全にスキップする。
- ポートフォリオ構成・ポジション算出関数群を実装
  - portfolio/portfolio_builder.py: シグナルのソート（score 降順、signal_rank によるタイブレーク）、等金額・スコア加重配分関数を実装。スコア全てが 0 の場合は等金額にフォールバックして警告出力。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を実装（regime によるフォールバック挙動を含む）。
  - portfolio/position_sizing.py: allocation_method に応じた株数計算を実装（"risk_based", "equal", "score"）。単元株（lot_size）での丸め、1銘柄上限・合計投下キャップ、cost_buffer による保守見積り、利用可能現金に合わせたスケールダウンロジック（端数処理で残余キャッシュを有効活用）などをサポート。
- 分析用 DB として DuckDB を導入
  - 実行・監視スクリプトやファクター計算モジュールは duckdb 接続を受け取って分析用テーブル（prices_daily など）を参照できるようにした。
- Paper Trading 検証レポート生成ツールを追加
  - tools/paper_verification_report.py: paper_trading 用の SQLite DB を解析して稼働率、注文成功率、送信率、API レイテンシ（P95 を含む）等を集計・判定するレポートを生成する CLI を実装。閾値と Pass/Fail 判定ロジックを搭載。

### Changed
- .env 読み込みロジックの挙動整理
  - OS 環境変数は保護され、.env.local による上書きは OS 環境変数を侵害しないよう配慮。
- ロギングの既存設定クリアと stdout を使用するデフォルト方針の採用
  - stdout を標準出力先とすることで cron 等でのリダイレクト運用に適合。
- 実行フローの安全性向上
  - 起動直後にプロセス優先度設定を行うように統一（run_monitoring/run_execution）。
  - run_execution は停止フラグを検出した場合、起動せずに安全に終了する挙動を追加。

### Fixed
- 環境変数パースの不正値やポーリング間隔の負値等に対するフォールバック処理を追加（MONITOR_POLL_INTERVAL の検証とデフォルトフォールバック）。
- .env の読み込み失敗やログディレクトリ作成失敗時にプロセスがクラッシュしないよう例外処理を追加。

---

## [0.1.0] - 2026-04-18

初回リリース相当の機能群を収録。

### Added
- パッケージ初期構成
  - 基本メタ情報: src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
- 実行基盤
  - 実行エンジン起動スクリプト（run_execution.py）と監視起動スクリプト（run_monitoring.py）を提供。
  - ExecutionEngine／OrderManager／RiskManager／Reconciler 等の組み立てロジック（起動時の依存注入）を実装（run_execution に記述）。
  - PID ファイル、停止フラグによるプロセス制御を実装。
- 設定・運用ツール
  - Settings クラスで主要設定項目をプロパティ化（DB パス、KABUSYS_ENV、PAPER_FILL_MODE、監視閾値等）。
  - config_setup と validate_config による初期設定と起動前チェックの仕組みを実装。
- ロギング・プロセス制御ユーティリティ
  - logging_setup.py と process_priority.py を実装し、クロスプラットフォームでの運用をサポート。
- ポートフォリオ構築ロジック
  - 候補選定、重み付け、セクター制限、レジーム乗数、ポジションサイズ算出ロジックを実装。
- 解析ツール
  - tools/paper_verification_report.py により、Paper Trading の検証レポート出力を提供。
- 研究用フェーズ
  - research/factor_research.py にファクター計算の骨格（モメンタム／移動平均／ATR 等の定義と計算方針）を追加（未完成の関数の開始）。

### Changed
- プロジェクトルート自動検出を導入（.git / pyproject.toml を基準）、これにより .env の自動読み込みが __file__ に依存して確実に行われるようにした。
- DB 周りの分離: paper_trading モード時は paper_trading.db を使用することで本番データと分離。

### Fixed
- 環境変数の未設定時に早期に分かるように _require() を実装し、起動時の問題を明示するようにした。

---

## Unreleased / 0.1.0 に関する注意事項・既知の制約
- research/factor_research.py は設計方針と一部定数・関数の骨格があるものの、モメンタム計算等の実装が途中のため、完全なファクター出力は未完成の可能性があります。
- process_priority と CPU affinity の設定は実行環境の権限に依存し、権限不足時はログ警告の上でスキップされます。
- .env の自動ロードはプロジェクトルートが特定できない場合にはスキップされます（CI や配布パッケージでの動作に注意）。
- Paper Trading の挙動は設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）に依存します。設定不備は validate_config で検出できます。

---

（補足）より詳細な変更履歴や古いバージョンからの差分が必要な場合は、Git のコミットログやリポジトリ履歴に基づく追記を推奨します。今回の CHANGELOG は提供されたソースコードの内容から推測して作成しています。