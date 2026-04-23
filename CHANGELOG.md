# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

フォーマット: https://keepachangelog.com/（日本語訳に準拠）

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-23
初回リリース — KabuSys 日本株自動売買システムの基本コンポーネントを実装。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全に分離。
    - エンジンの PID ファイル管理、停止フラグ (data/stop_requested.flag) の検知による安全停止対応。
    - 起動時にプロセス優先度を設定するフックを追加（高優先度）。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番 sqlite_path を使用する仕様。
    - 停止フラグの検知、例外時のログ出力、KeyboardInterrupt の処理を実装。

- 設定関連
  - config.py: 環境変数読み込み・管理クラス Settings を実装。
    - .env / .env.local の自動読み込み（OS 環境変数を保護して上書き制御）。
    - .env のパースで export やクォート、インラインコメントをサポート。
    - 各種設定プロパティを提供（DB パス、PID/kill flag パス、閾値、paper_trading 用設定等）およびバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - settings インスタンスをエクスポート。

  - config_setup.py: 対話式 .env ウィザードを追加。
    - 初期 .env 作成 / 既存 .env の更新を支援、秘密項目はマスクして扱う。
    - 保存前の確認および書き出しロジックを実装。

  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在とパース検証（PyYAML が利用可能な場合）。
    - --strict モード（警告を失敗扱い）を実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート・上位選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分の実装（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を回避するための候補除外ロジック。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装（未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数算出ロジックを実装（allocation_method: "risk_based"/"equal"/"score"）。
    - 単元（lot_size）での丸め、ポジション上限・利用率上限、コストバッファを考慮した aggregate 制御、スケーリング時の端数配分アルゴリズムを実装。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout ストリームハンドラと日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の環境変数や引数による上書き、既存ハンドラのクリア処理、ログディレクトリ作成失敗時のフォールバック対応を実装。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac）差分を吸収して set_process_priority, set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- モニタリング・DB 初期化
  - monitoring.monitoring_db の初期化呼び出しを run_* スクリプト側で確実に実行（監視テーブルが存在することを保証）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs を集計して稼働率、注文成功率（fill/send）、P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL 判定を出力。
    - CLI オプションで日付範囲指定（--from, --to）と DB パス指定（--db）。

- 研究用モジュール（開始）
  - research/factor_research.py: ファクター計算のための骨組みを追加（モメンタム・MA・ATR 等を想定）。DuckDB を使った計算方針、定数定義を含む（実装は継続）。

### Changed
- ロギング
  - すべての起動スクリプトから setup_logging を呼び出してログ出力を統一。ログは標準出力に出力し、可能なら日次ローテーションでファイルにも保存する。
- .env 読み込み順序
  - OS 環境変数 > .env.local > .env の順で適用。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- データベース接続ポリシー
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する設計とし、実行（run_execution）は paper_trading 時に専用 DB を使用して分離。

### Fixed
- 環境変数バリデーションとフォールバック
  - MONITOR_POLL_INTERVAL が不正（0 や非整数等）の場合にデフォルト値（60 秒）へフォールバックして警告を出力するように修正。
  - PAPER_FILL_MODE の無効値に対して明示的にエラーを出すバリデーションを追加。
  - Settings.env / log_level の不正値に対する検出を実装し、早期に問題を明示。

### Security
- .env の取り扱いに関する注意書きを config_setup に明記（.env を絶対に Git にコミットしない旨）。

### Internals / Notes
- 各コンポーネントは可能な限り副作用を抑えた純粋関数（portfolio モジュール等）として設計。DB/外部 API へのアクセスは実行コンポーネントに限定。
- Paper Trading（モックブローカー）と Live（実ブローカー）を明確に分離する設計を採用。
- ログディレクトリ作成やプロセス優先度設定は権限不足時に安全にスキップするよう例外処理を行う。

---

今後の予定（例）
- research/factor_research の各ファクター計算実装完了
- ExecutionEngine / Broker クライアントの詳細実装・テスト拡充
- 単体テスト・CI の整備、ドキュメント強化

（本 CHANGELOG はコードベースの内容から推測して作成したものであり、実際の開発履歴とは差異がある場合があります。）