# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-24

### Added
- 初期リリースとして以下の主要機能・モジュールを追加しました。
  - 環境設定関連
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - よくあるフォーマット（export 付き、シングル/ダブルクォート、インラインコメント等）に対応した .env パーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
    - Settings クラスを実装し、環境変数を型付きプロパティ経由で取得（J-Quants / kabu API / DB パス /監視閾値 等）。
    - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH など paper_trading 向け設定を追加。
  - 設定支援ツール
    - 対話式ウィザード `kabusys.config_setup` を追加。`.env` の初期作成・更新を支援。
    - 設定検証 CLI `kabusys.validate_config` を追加。必須環境変数や config/*.yaml、KABUSYS_ENV 等を事前チェック。`--strict` オプションで警告を FAIL 扱いにできる。
  - 実行・監視スクリプト
    - `run_execution.py` を追加。ExecutionEngine 起動スクリプト（プロセス優先度設定、paper_trading 用 DB 分離、BrokerClientFactory によるブローカ抽象化、スレッドでの実行制御、停止フラグ対応）。
    - `run_monitoring.py` を追加。SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL でポーリング間隔上書き可能、停止フラグ対応、監視 DB は環境に依らず本番 sqlite_path を使用）。
  - ログ・プロセス管理ユーティリティ
    - `kabusys.utils.logging_setup.setup_logging` を追加。ルートロガーに stdout ストリームと日次ローテートファイルハンドラ（TimedRotatingFileHandler）を設定。既存ハンドラをクリアして二重出力を防止。ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみで継続。
    - `kabusys.utils.process_priority` を追加。Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）と CPU affinity 設定をサポート。失敗時に安全にフォールバックする設計。
  - ポートフォリオ構築（純粋関数群）
    - `kabusys.portfolio` モジュールを追加。
      - `portfolio_builder`：候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。
      - `risk_adjustment`：セクター上限適用（apply_sector_cap）、レジーム乗数計算（calc_regime_multiplier）。
      - `position_sizing`：株数計算（calc_position_sizes） — risk_based / equal / score の各配分方式、lot_size・cost_buffer・aggregate cap によるスケール調整。
  - ペーパートレード検証ツール
    - `kabusys.tools.paper_verification_report` を追加。paper_trading 用 SQLite データから稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計し PASS/FAIL 判定を出力するコマンドラインツール。
  - リサーチ（骨格）
    - `kabusys.research.factor_research` を追加（モメンタム等のファクター計算ロジックの下地。DuckDB 接続を受けて価格・財務テーブルから計算する設計）。

### Changed
- ログ出力の既定を統一
  - すべての起動スクリプトから `setup_logging(app_name=...)` を呼ぶことで、ログ設定（stdout + 日次ローテーション）を統一。
  - StreamHandler は stdout を使用するように設計（cron 等で stdout/stderr の扱いを一本化しやすくするため）。
- .env 読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順で読み込まれるように変更（.env.local は OS 環境を上書き可能だが OS 環境と衝突するキーは保護）。
- DB の取り扱い
  - 監視機能（run_monitoring）は環境にかかわらず Settings.sqlite_path（監視用本番 DB 想定）を使用するように明確化。
  - 実行エンジン（run_execution）は paper_trading 環境時に専用の paper_sqlite_path を使用し、本番 DB と分離する振る舞いを導入。

### Fixed
- 耐障害性の向上
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもループを継続し、例外情報をログ出力するように変更（監視の単発障害でプロセスが落ちないように）。
  - logging_setup でログディレクトリ作成失敗時に明示的に警告を出し、ファイルハンドラ生成失敗時はコンソール出力のみで継続するように（起動失敗を避ける）。
  - process_priority/set_cpu_affinity で権限不足や未対応プラットフォームに遭遇した場合に警告ログを出して安全にスキップする処理を追加。
- validate_config の堅牢化
  - PyYAML 未インストール時に YAML ファイル検証をスキップし、警告を表示するように変更（外部ライブラリ非必須）。
  - config/*.yaml の存在確認とパース結果を詳細に報告するように改善。
- .env パーサの堅牢化
  - export プレフィックスやクォート内部のバックスラッシュエスケープ、インラインコメントの取り扱いなど、現実的な .env 書式の多様性に対応。

### Security
- .env の取り扱いに関する注意喚起を config_setup の出力に明記（.env を絶対にリポジトリにコミットしないことを推奨）。

### Internal / Non-user-facing
- パッケージ初期化で __version__ を 0.1.0 に設定。
- モジュールのエクスポートを整理（kabusys.portfolio の __all__ など）。

---

今後の予定（例）
- factor_research の実装完了（ファクター計算関数群の実装継続）。
- ExecutionEngine / BrokerClient の詳細実装・テスト拡充。
- 単体テスト・CI の追加とドキュメント整備。

もし特定ファイルについてより詳しい変更点（行単位や設計意図）を記載希望でしたら、対象ファイルを指定してください。