# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成したリリースノートです。

※ 現在のパッケージバージョン: 0.1.0（src/kabusys/__init__.py に基づく）

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

Added
- 基本アーキテクチャとコアコンポーネントを初期実装
  - 実行エンジン起動スクリプト
    - src/kabusys/run_execution.py
    - ExecutionEngine をスレッドで起動し監視するエントリポイントを提供。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient により本番と完全分離して動作。
    - 起動時にプロセス優先度を "high" に設定するフックを追加（utils.process_priority）。
    - 停止フラグ (data/stop_requested.flag) と pid ファイル (data/execution.pid) をサポートし、安全停止を実装。
  - 監視ループ起動スクリプト
    - src/kabusys/run_monitoring.py
    - SystemMonitor を周期的にポーリングするデーモン的スクリプトを実装。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する仕様（Settings 経由）。
  - 設定管理
    - src/kabusys/config.py
    - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。.env と .env.local の読み込み順を実装。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
    - .env の行パーサは export プレフィックス、クォート文字列、インラインコメント (クォートなしの場合に限定) を考慮した堅牢な実装。
    - 各種設定プロパティ（DB パス、API トークン、KABUSYS_ENV/LOG_LEVEL 判定、Paper Trading 関連設定など）を提供。設定取得時のバリデーションを実装（例: PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV の有効値チェック）。
    - Settings クラスとグローバル settings を提供。
  - 環境設定ウィザード CLI
    - src/kabusys/config_setup.py
    - 対話式に .env を生成・更新するウィザードを実装。既存 .env の読み込み、シークレットマスク表示、保存確認をサポート。
  - 設定検証 CLI
    - src/kabusys/validate_config.py
    - 起動前に .env や config/*.yaml の欠落や不備を検出する検証ツールを実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML が存在する場合）を実行。`--strict` オプションで警告も失敗扱いにできる。
  - ロギング設定ユーティリティ
    - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通関数 `setup_logging()` を提供。ログディレクトリの自動作成、失敗時のフォールバック、ログレベル解決順をサポート。
  - プロセス優先度 / CPU affinity ユーティリティ
    - src/kabusys/utils/process_priority.py
    - Windows/Linux/macOS を抽象化してプロセス優先度（high/normal/low）を設定する `set_process_priority()` を実装。`set_cpu_affinity()` も提供。権限不足や未対応 OS の場合は警告ログを出して安全にスキップ。
  - ポートフォリオ構築関連モジュール（純粋関数群）
    - src/kabusys/portfolio/
      - portfolio_builder.py: 候補選定（score/ rank によるソート）と等金額・スコア加重の重み計算（スコア全0 の場合は等金額にフォールバック）。
      - position_sizing.py: 複数の配分方式（risk_based / equal / score）に対応した株数決定ロジック。単元株（lot_size）丸め、per-stock 上限・aggregate cap によるスケールダウン、コストバッファ考慮などを実装。
      - risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）。未知レジームでは警告してフォールバック。
    - モジュールのエクスポートを整理（src/kabusys/portfolio/__init__.py）。
  - Paper Trading 検証レポートツール
    - src/kabusys/tools/paper_verification_report.py
    - パペートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポート出力。基準値（稼働率 99% 等）に基づく PASS/FAIL 判定を実装。
  - 研究用ファクタ計算モジュール（開始）
    - src/kabusys/research/factor_research.py
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクター計算を行う方針と開始実装（モメンタム等の定数と calc_momentum の枠組み）。
  - パッケージ情報
    - src/kabusys/__init__.py にバージョン 0.1.0 を設定。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Implementation details（重要な動作と既知制約）
- .env 自動ロードはプロジェクトルートが見つからない場合スキップされるため、パッケージ配布後も安全に動作する設計。
- run_execution は Paper Trading モード時に専用 DB を使い、本番 DB と完全分離する設計。PAPER_TRADING_SQLITE_PATH を環境変数で上書き可能。
- run_monitoring は環境にかかわらず監視用の sqlite_path（Settings.sqlite_path）を使用するよう明確化。
- .env のパースロジックはシンプルな実装であるため、極端なエッジケース（複雑なエスケープや多行値）は想定していない。
- process_priority / set_cpu_affinity は権限や OS の違いで失敗または無効化される可能性がある。その場合は警告ログを出してスキップする。
- position_sizing の価格欠損（price が 0.0 または未設定）の場合は当該銘柄をスキップする（ログ出力あり）。将来的にフォールバック価格（前日終値等）を導入する余地あり。
- calc_regime_multiplier は未知レジームで 1.0 にフォールバックし、警告を出す。

関連ファイル（主要）
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/utils/logging_setup.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py

今後の改善案（参考）
- .env パーサの追加テストと複雑ケース対応（多行値・より厳密なエスケープ処理）。
- position_sizing に銘柄別 lot_size サポート（stocks マスタ参照）。
- factor_research の完全実装（Value, Volatility, Liquidity の計算ロジック）とユニットテスト。
- ExecutionEngine / SystemMonitor の外部 API 呼び出し部分に対する詳細な統合テストおよびモックテストの強化。