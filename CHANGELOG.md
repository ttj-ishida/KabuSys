# Changelog

すべての重要な変更は Keep a Changelog の慣習に従って記載しています。日付はコード snapshot の想定日付（本システムの現状）です。

## [0.1.0] - 2026-04-23

### Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - 実行・監視スクリプト
    - run_execution: 実際の実行エンジン起動スクリプトを追加。settings に応じて paper_trading 用の専用 SQLite を使用する分離実装を含む（src/kabusys/run_execution.py）。
    - run_monitoring: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能。常に本番の sqlite_path を監視 DB に使用（src/kabusys/run_monitoring.py）。
  - 設定管理
    - Settings クラス: 環境変数から各種設定を取得・検証するユーティリティを追加（src/kabusys/config.py）。
    - 自動 .env ロード機構: プロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local をロード。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサ: export 形式、引用符付き値（エスケープ処理対応）、インラインコメントの取り扱いを実装。
  - 設定関連 CLI
    - config_setup: 対話式ウィザードで .env の初期作成/更新を支援（src/kabusys/config_setup.py）。
    - validate_config: .env と config/*.yaml の基本的な検証 CLI を追加。--strict オプションで警告も失敗扱いにできる（src/kabusys/validate_config.py）。
  - ポートフォリオ構築ロジック（純関数）
    - portfolio/portfolio_builder: 候補選定・等配分・スコア加重配分（tie-breaker の仕様含む）を追加。
    - portfolio/risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。
    - portfolio/position_sizing: 発注株数計算（risk_based / equal / score）、単元株（lot）丸め、aggregate cap によるスケーリング、コストバッファ考慮を実装。
  - ユーティリティ
    - logging_setup: stdout ストリームハンドラ + 日次ローテーションファイルハンドラ（TimedRotatingFileHandler）で統一的ログ設定を実装。ログディレクトリ作成失敗時はファイル出力をフォールバック（src/kabusys/utils/logging_setup.py）。
    - process_priority: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定を追加（src/kabusys/utils/process_priority.py）。
  - ツール
    - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の集計・判定を行う（src/kabusys/tools/paper_verification_report.py）。
  - データアクセス
    - DuckDB / SQLite の両方に接続する設計を採用（実行エンジン・監視機能で利用）。
  - モジュール定義
    - パッケージメタ情報（__version__ = "0.1.0"）を追加（src/kabusys/__init__.py）。

### Changed
- 起動時のプロセス優先度を自動で "high" に設定するように統一（run_execution / run_monitoring が起動直後に set_process_priority("high") を呼び出す）。
- ロギング挙動:
  - コンソール出力は stderr ではなく stdout を使用（外部ジョブスケジューラからのリダイレクトを想定）。
  - 既存ハンドラをクリアして二重設定を防止する挙動を追加。

### Fixed
- .env 読み込み時の上書き制御:
  - .env と .env.local のロード順を明確化（OS 環境変数が優先され、.env.local は上書き可、.env は未設定キーのみセット）。
  - 環境変数上書き時に OS 側の既存キーを保護する仕組みを実装。
- run_execution: paper_trading 環境では専用 DB（PAPER_TRADING_SQLITE_PATH の設定）を使用することで本番 DB と完全分離するよう修正。

### Documentation
- 各モジュールに日本語 docstring を追加（使い方、引数、挙動、設計方針を明記）。特に PortfolioConstruction / StrategyModel に基づく仕様注釈を含む。
- config_setup と validate_config に利用手順を CLI ヘルプとして実装。

### Performance
- position_sizing の aggregate cap スケーリング処理は残差分配を考慮し、限られた現金でより再現性のある配分を行うアルゴリズムを実装。

### Internal / Misc
- stop フラグ / pid ファイルの扱い:
  - run_monitoring と run_execution で data/stop_requested.flag による安全停止処理を追加。
  - run_execution は起動時に停止フラグが立っていれば起動せず終了する挙動。
  - 実行エンジンの PID ファイルパスは Settings を経由して一元管理。
- Settings による型変換・検証を強化（env/log level のバリデーション、paper_fill_mode の有効値チェックなど）。
- research/factor_research モジュールにファクター計算の骨格と定数を追加（Momentum/Value/Volatility/Liquidity の計画。注意: 一部関数は実装未完／途中）。

### Removed
- なし（初期リリースのため該当なし）。

### Known issues / Notes
- research/factor_research の実装は途中で切れている箇所があります。実際のファクター計算ロジックは追加実装が必要です。
- apply_sector_cap は price_map に欠損（0.0）価格がある場合にエクスポージャーが過少評価される問題を注記しており、将来的に価格フォールバックの追加が検討されています。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム非対応時に警告を出してスキップする設計です（安全なフォールバック）。

---

今後の予定（参考）
- factor_research の完全実装（DuckDB クエリによるファクター計算）。
- 実運用に向けたテスト・監視強化、各種エラー時の自動アラート（LINE 通知）統合。
- 銘柄別単元株数対応（lot_map）などの position_sizing 拡張。

もし特定ファイルや機能について、より詳細な変更点説明や別バージョン分け（Unreleased / 次期リリース向けの TODO）を希望される場合はお知らせください。