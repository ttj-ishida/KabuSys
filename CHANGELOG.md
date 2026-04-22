# Changelog

すべての重要な変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベースから推測して作成した変更履歴です。

## [Unreleased]

### Added
- 起動スクリプトを実装
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動を明示。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時の専用 DB（data/paper_trading.db）と MockBrokerClient の利用に対応。起動/停止のための stop flag / pid ファイル管理を実装。
- 設定・環境変数関連
  - config.py: .env の自動ロード機能を実装（.env, .env.local の優先度処理、OS 環境変数の保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - config_setup.py: .env を対話的に作成・更新するウィザード CLI を追加。
  - validate_config.py: 起動前に .env と config/*.yaml の基本検証を行う CLI を追加（--strict オプションで警告を失敗扱いにできる）。
  - Settings クラスに各種プロパティを追加（DB パス、paper_trading 用パス、閾値設定、ログ・環境設定など）。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。コンソール出力を stdout に、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を組み合わせて設定。ログディレクトリ作成失敗時のフォールバック処理あり。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。アクセス権限や未対応 OS を想定した安全なエラーハンドリングを実装。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）と重み計算（等金額、スコア加重）を実装。スコアが全て 0 の場合は等金額へフォールバックし警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）およびマーケットレジームに応じた投下資金乗数（calc_regime_multiplier）を追加。未知レジームはフォールバックで 1.0 を返す。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-position および aggregate cap、cost_buffer（コスト推定）対応、スケールダウン時の再分配ロジックを搭載。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB を解析し、稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを出力する CLI を追加。閾値（稼働率 99%、成立率 90% など）に基づく PASS/FAIL 判定を実装。

### Changed
- DB 周りの挙動を明確化
  - 監視用途 (run_monitoring) は環境にかかわらず本番 sqlite_path を参照する設計となっていることを明示（安全上の理由）。
  - 実行エンジン (run_execution) は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離。
- ログ出力の挙動
  - ログはコンソールに stdout を使うよう変更（cron 等での出力リダイレクトを考慮）。
  - ログファイルは日次ローテーション（30 日分保持）により管理するように変更。

### Fixed
- .env のパース安定化
  - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどを考慮したパーサを実装。これにより .env の多様な記述を正しく読み込めるよう改善。
  - .env.local を .env より優先して上書きする挙動、既定の OS 環境変数を上書きしない protected 処理を導入。
- 起動時の安全性向上
  - run_execution/run_monitoring で stop flag を監視し、フラグが立っている場合に安全に起動/停止する処理を追加。
  - run_monitoring 内の MONITOR_POLL_INTERVAL の不正値を検出してデフォルトへフォールバックする警告を実装（time.sleep に不正な値を渡さないため）。
- プロセス優先度設定の失敗を非致命化
  - 権限不足や未対応プラットフォーム時に警告を出して処理を継続するように変更。

### Security
- config_setup のヘッダに「.env は絶対に Git にコミットしないこと」を明示して、シークレットの取り扱いに対する注意喚起を追加。

## [0.1.0] - 初期リリース
（パッケージの初期バージョン。実装されている主要機能の概要）

### Added
- 基本的な自動売買フレームワークの骨格を実装:
  - ExecutionEngine および Order 管理周りの起動スクリプト（run_execution.py）。
  - SystemMonitor を用いた監視ループ起動スクリプト（run_monitoring.py）。
  - 設定管理（Settings クラス）、.env 自動ロード、対話式設定ウィザード、設定検証 CLI。
  - ロギング設定ユーティリティとプロセス優先度ユーティリティ。
  - ポートフォリオ構築（候補選別、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数）。
  - Paper Trading 用の検証レポート生成ツール。
  - research/factor_research モジュール（ファクター計算。注: ファイルは長く複雑なため一部省略あり）。

### Changed
- パッケージメタ情報にバージョンを付与（__version__ = "0.1.0"）。

### Notes
- 一部モジュールは外部ライブラリ（psutil, duckdb, PyYAML 等）に依存するため、導入環境でのインストールが必要。
- config/*.yaml の内容検証は PyYAML 未インストール時にスキップされるが、その旨を警告する実装。

----

今後の予定（推測）
- factor_research の完全実装（ファクター計算の SQL/実装完了）。
- ExecutionEngine と Broker クライアント間の統合テスト、ペーパートレードの振る舞い検証。
- 追加の監視メトリクスやアラート送信（LINE 連携）の実装・改善。

（上記変更点は提供されたコード内容から推測して作成しています。実際のコミット履歴と異なる場合があります。）