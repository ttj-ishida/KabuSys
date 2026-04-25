# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

最新の変更は上に記載されています。

## [Unreleased]

### Added
- 監視プロセス起動スクリプトを追加
  - src/kabusys/run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）
  - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了
  - SystemMonitor を初期化して定期的に check_once() を実行
  - 監視用 DB は環境にかかわらず本番 sqlite_path を使用

- 実行エンジン起動スクリプトを追加
  - src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（data/paper_trading.db）を使用し、MockBroker を利用して本番 DB と分離
  - 実行中は PID ファイルを管理し、停止フラグで安全にエンジンを停止
  - スレッドで ExecutionEngine をデーモン実行

- 環境設定・検証用 CLI を実装
  - src/kabusys/config_setup.py: 対話式ウィザードで .env を作成/更新
  - src/kabusys/validate_config.py: .env と config/*.yaml の基本的な前提チェック、--strict モードをサポート

- 設定管理モジュールの強化
  - src/kabusys/config.py
  - プロジェクトルート自動検出（.git / pyproject.toml）
  - .env ファイルの自動読み込み（.env, .env.local、OS 環境変数を保護）
  - export プレフィックス、クォート、エスケープ、インラインコメントなどを考慮した堅牢な .env パーサ実装
  - 各種設定プロパティ（DB パス、paper_trading 関連、監視閾値、ログレベル等）を追加

- ロギングユーティリティを追加
  - src/kabusys/utils/logging_setup.py
  - stdout（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler）を統一的に設定
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック
  - LOG_LEVEL / LOG_DIR の解決ロジックを実装

- プロセス優先度 / CPU affinity ユーティリティを追加
  - src/kabusys/utils/process_priority.py
  - Windows / POSIX の差分を吸収してプロセス優先度を変更
  - CPU affinity の設定機能を提供（利用不可時は警告でスキップ）

- ポートフォリオ構築ライブラリを追加
  - src/kabusys/portfolio/*
  - 銘柄選定（select_candidates）、重み計算（等金額・スコア加重）
  - セクター集中制限（apply_sector_cap）
  - レジームに応じた投下資金乗数（calc_regime_multiplier）
  - 株数決定ロジック（calc_position_sizes）:
    - allocation_method: "risk_based", "equal", "score" をサポート
    - lot_size による丸め、max_position_pct / max_utilization / cost_buffer による合計キャップとスケーリング
    - 手数料・スリッページ見積りのための cost_buffer サポート

- Paper Trading 検証レポートツールを追加
  - src/kabusys/tools/paper_verification_report.py
  - 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定
  - デフォルト DB は data/paper_trading.db、コマンドラインで期間や DB パスを指定可能
  - 判定閾値（稼働率 99%、成功率等）を定義

- 研究用ファクター計算モジュールの骨組みを追加
  - src/kabusys/research/factor_research.py
  - Momentum / Value / Volatility / Liquidity に関する設計と定数を追加
  - DuckDB 接続を受けて prices_daily / raw_financials を使う方針で実装予定（モジュールの一部は実装途中）

### Changed
- パッケージ情報
  - src/kabusys/__init__.py にバージョン 0.1.0 を設定

### Fixed
- .env 読み込みの堅牢性向上
  - ファイル読み込み失敗時に警告を出してスキップするように変更
  - export 形式や引用符内のエスケープ、インラインコメント処理の改善で誤読を低減

### Documentation
- 各モジュールに docstring を追加して利用方法・設計方針を明記
- config_setup による .env テンプレートの生成を実装し、注意事項（.env を Git にコミットしない等）を明記

---

## [0.1.0] - 2026-04-25

初回公開リリース。

### Added
- 初期実装として以下の主要コンポーネントを追加：
  - 実行エンジン起動スクリプト（run_execution）
  - 監視ループ起動スクリプト（run_monitoring）
  - 環境設定ウィザード（config_setup）
  - 設定検証ツール（validate_config）
  - 設定管理（config）
  - ロギング設定ユーティリティ（logging_setup）
  - プロセス優先度 / CPU affinity ユーティリティ（process_priority）
  - ポートフォリオ構築（portfolio.*：選定、重み、セクター制限、レジーム乗数、株数決定）
  - Paper Trading 検証レポート（tools/paper_verification_report）
  - 研究用ファクター計算モジュール（research/factor_research）（設計・一部実装）
  - パッケージのエントリポイントとバージョン管理（__init__.py）

### Changed
- N/A（初回リリースのため差分なし）

### Fixed
- N/A（初回リリースで既知の改修はなし）

---

## Deprecated
- なし

## Removed
- なし

## Security
- なし

注:
- 本 CHANGELOG は、提供されたコードベースの内容から機能・振る舞いを推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、そちらを優先してください。