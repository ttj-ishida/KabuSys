# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
フォーマットは CHANGELOG.md 互換です。

## [Unreleased]

### Added
- なし（現時点で未リリースの作業はありません）。

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-23

初回リリース。プロジェクトのコア機能とユーティリティ群を追加。

### Added
- 全体
  - パッケージ初期化（kabusys.__version__ = 0.1.0）。
  - DuckDB と SQLite を組み合わせた分析・監視基盤の採用（設定でパス指定可能）。
  - 起動スクリプト:
    - run_execution.py: 実行エンジン起動ロジック（ExecutionEngine の起動・スレッド管理、停止フラグ対応、paper_trading 用 DB 分離）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL 環境変数対応、停止フラグ対応）。
  - Paper Trading に関する分離:
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用（データ分離）。
    - Paper Trading 用検証ツール（tools/paper_verification_report.py）を追加。期間指定や閾値判定により PASS/FAIL レポートを生成。
  - 設定関連 CLI:
    - config_setup.py: .env を対話式に生成・更新するウィザード（シークレットマスク、デフォルト値・選択肢対応、.env 出力）。
    - validate_config.py: .env および config/*.yaml の事前検証ツール（必須環境変数チェック、パス存在確認、PyYAML があれば YAML のパース検証、--strict モード）。
  - 環境設定ローダー（config.py）:
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パースは export 構文、クォート値、インラインコメントなどに対応。
    - Settings クラスで各種設定値（パス、閾値、ペーパートレード用設定、ログレベル、KABUSYS_ENV）をラップし、妥当性チェックを実施。
  - ログ・プロセスユーティリティ:
    - utils/logging_setup.py: 統一ログ設定関数 setup_logging。標準出力（stdout）と日次ローテーションファイルハンドラを設定。ログディレクトリ作成失敗時はファイル出力を無効化して継続。
    - utils/process_priority.py: Windows/Linux/macOS を吸収したプロセス優先度設定と CPU affinity 設定ユーティリティ（権限不足時は警告ログでスキップ）。
  - ポートフォリオ構築関連（pure functions、DB参照無し）:
    - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - portfolio/risk_adjustment.py: セクター集中抑止（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes） — risk_based / equal / score 各方式、単元（lot_size）丸め、aggregate cap によるスケーリングと残差処理を実装。
  - Research
    - research/factor_research.py（ファクター計算基盤を追加。Momentum 等の計算を行う設計を含む。DuckDB 接続を受け取り prices_daily / raw_financials を参照する実装方針）。
  - 監視関連
    - monitoring 側の DB 初期化を行う init_monitoring_db の呼び出しを run_scripts に組み込み（監視テーブルの存在を保証、冪等）。
    - 停止制御ファイル（data/stop_requested.flag）および PID 管理（data/execution.pid）により安全停止を実現。
  - ツール
    - tools/paper_verification_report.py: Paper Trading データベースから稼働率、注文成功率、送信率、レイテンシ等を集計し基準値に基づく検証レポートを出力。コマンドライン引数 --from / --to / --db をサポート。

### Changed
- なし（初回リリースのため変更履歴はありません）。

### Fixed
- なし（初回リリースのため修正履歴はありません）。

### Notes / Implementation details
- 環境変数周り:
  - .env 自動読み込みの保護: OS 環境変数は上書き禁止（.env.local は override=True で読み込めるが OS 環境変数は保護）。
  - Settings クラスは各値で不正値検出時に ValueError を送出する（例: LOG_LEVEL、KABUSYS_ENV、PAPER_FILL_MODE）。
- ログ:
  - StreamHandler は stdout を使用（cron 等で stdout/stderr を一括リダイレクトする運用を想定）。
  - 日次ログのローテートを実装し 30 日分保持。
- 実行安全策:
  - run_execution / run_monitoring は起動時にプロセス優先度を "high" に設定しようと試みる（権限無い場合は警告でスキップ）。
  - 停止フラグ（data/stop_requested.flag）を検知して graceful にループ/エンジンを停止する。
- Paper Trading 分離:
  - paper_trading 環境向けに専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離する設計。
- Position sizing の細部:
  - 単元（lot_size）で切り捨て、aggregate cap 超過時は比例スケーリング後に残余キャッシュを fractional remainder に基づき lot 単位で配分するロジックを採用。
  - 価格欠損時の扱い（price が 0/None）はログ出力のうえスキップ。将来的にフォールバック価格の導入を想定する注記あり。

---

作成した CHANGELOG.md は、コード中の実装・設計注記（コメントや TODO、関数名・引数・動作）を基に推測してまとめています。必要であれば以下の点を追加で反映します:
- リリース日を実際のリリース日に調整
- 各ファイル/関数に対する細かい修正点や既知の問題（TODO）を詳細に列挙
- 今後の予定（Backlog）やマイグレーション手順の追記

どの程度の粒度で履歴を記載するか指示いただければ、より詳細な CHANGELOG を作成します。