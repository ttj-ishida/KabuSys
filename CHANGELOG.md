# Changelog

すべての変更は Keep a Changelog の形式に従って記録します。  
このファイルは人間に読みやすく、かつリリースノート作成時に参照できることを目的としています。

なお、このリポジトリの現行バージョンは `0.1.0`（src/kabusys/__init__.py）です。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-17

### Added
- 基本機能の初回実装を追加。
  - 高水準の起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境変数にかかわらず本番の sqlite_path を使用する実装になっている（src/kabusys/run_monitoring.py）。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を用いる（src/kabusys/run_execution.py）。
  - 設定関連
    - Settings クラスを追加し、環境変数からアプリケーション設定を取得する API を提供（src/kabusys/config.py）。J-Quants / kabu API / データベースパス /監視しきい値等をプロパティで取得可能。
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数は保護され上書きされない（src/kabusys/config.py）。
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加（src/kabusys/config_setup.py）。
    - validate_config.py: .env と config/*.yaml の事前検証ツールを追加。`--strict` オプションで警告を FAIL 扱いにできる（src/kabusys/validate_config.py）。
  - ポートフォリオ構築ライブラリ（純粋関数）
    - portfolio_builder.py: 銘柄候補選定（select_candidates）・等配分 / スコア加重（calc_equal_weights, calc_score_weights）を追加（src/kabusys/portfolio/portfolio_builder.py）。
    - risk_adjustment.py: セクターキャップ適用（apply_sector_cap）・レジーム乗数（calc_regime_multiplier）を追加（src/kabusys/portfolio/risk_adjustment.py）。
    - position_sizing.py: 各銘柄の株数計算（calc_position_sizes）を追加。単元株丸め、aggregate cap スケーリング、cost_buffer 取り扱いなどを実装（src/kabusys/portfolio/position_sizing.py）。
    - portfolio パッケージのエクスポート整備（src/kabusys/portfolio/__init__.py）。
  - ユーティリティ
    - process_priority.py: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加（src/kabusys/utils/process_priority.py）。Windows / POSIX を吸収し、可能な場合のみ適用する。
  - 解析・調査用モジュール
    - research/factor_research.py: モメンタム・ボラティリティ等のファクター計算を実装。DuckDB の prices_daily テーブルを前提とする計算関数群を追加（src/kabusys/research/factor_research.py）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し PASS/FAIL 判定を行う（src/kabusys/tools/paper_verification_report.py）。
  - 監視 DB 初期化フック
    - monitoring_db.init_monitoring_db を呼んで監視用テーブルの存在を保証する処理を追加（run_monitoring, run_execution）。

### Changed
- .env パース仕様の強化（src/kabusys/config.py）
  - export プレフィックス対応、クォート文字列のエスケープ対応、インラインコメントの取り扱い、空行・コメント行の無視などを実装。
  - OS 環境変数が優先されるよう保護セットを用いたロード順（OS env > .env.local > .env）。
- 設定検証ロジック（src/kabusys/validate_config.py）
  - 必須環境変数のチェック・プレースホルダ値検出、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検査（PyYAML がある場合）を追加。
  - 本番環境向けのガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を追加。
- run_execution の動作
  - paper_trading 環境向けに paper_sqlite_path を使用して本番 DB と分離。ExecutionEngine 起動時に停止フラグ確認を行い、スレッドでエンジンを稼働させる実装（src/kabusys/run_execution.py）。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 設定など）をコード内で初期値として定義。
- run_monitoring の動作
  - プロセス優先度を最初に "high" に設定してから監視を開始するようになっている（src/kabusys/run_monitoring.py）。
  - 停止フラグ（data/stop_requested.flag）を検知してループを終了する仕組みを実装。
- paper_verification_report の基準値
  - デフォルトの閾値（稼働率 99.0%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定し、その基準に基づく PASS/FAIL 判定を行う（src/kabusys/tools/paper_verification_report.py）。

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Security
- なし

---

注記（開発者向け）
- 監視プロセス（run_monitoring）は説明コメントの通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」する設計になっています。本番 DB を監視する意図がない場合は設定を見直してください。
- Settings のプロパティは未設定時に ValueError を発生させるものがあります（必須値）。CI / デプロイ前に `python -m kabusys.validate_config` を実行して設定を検証することを推奨します。
- process_priority.set_process_priority はプラットフォーム依存の制約により権限不足や未サポート環境で失敗する可能性がありますが、失敗時はログで警告を出して処理は継続します。

（この CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴とは厳密に一致しない可能性があります。）