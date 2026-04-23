# Changelog

すべての重要な変更をここに記載します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初期リリース。自動売買システム KabuSys の基盤機能を実装しました。主な追加点は以下のとおりです。

### Added
- エントリポイント / 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポート。
    - 起動時にプロセス優先度を「high」に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番用 sqlite_path を使用。
    - 停止フラグによる終了処理、例外発生時のログ保護を実装。

- 設定・環境管理
  - config.py
    - .env の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env/.env.local の読み込み順序と OS 環境変数保護（既存環境変数を上書きしない / protected 指定）。
    - 環境変数パーサの実装（export 形式、クォート、エスケープ、インラインコメント対応）。
    - Settings クラスで主要設定をプロパティとして提供（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 関連など）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - paper_sqlite_path、pid_file_path、閾値（CPU/MEM/DISK）等のデフォルト設定。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI。
    - 複数の設定項目を対話的に入力可能（シークレット入力、選択肢、デフォルトの提示、既存値の利用）。
  - validate_config.py
    - .env および config/*.yaml の起動前検証ツール。
    - 必須環境変数の存在チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML パース（PyYAML がある場合）。
    - --strict モード（警告を FAIL 扱い）をサポート。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で BUY 候補選定（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア全て0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限をチェックして新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームはフォールバック（1.0）し警告を出力。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算を実装。
    - リスクベースの基本計算、単元（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer による保守的評価、残差配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの一括設定ユーティリティ。
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、バックアップ30日）を設定。
    - ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみで継続。
    - ログレベル・ログディレクトリ解決の優先順位を明確化。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティ。
    - Windows / POSIX (Linux/Mac/FreeBSD) に対応、権限不足や未対応 OS の場合は警告を出力して安全にフォールバック。

- モニタリング / DB 初期化
  - monitoring.monitoring_db の初期化呼び出しを起動スクリプトで実行（監視テーブルの存在を保証）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite を参照して稼働率、注文成功率、送信率、API レイテンシ（平均・最大・P95）などを集計・判定するレポートを生成。
    - 日付フィルタ (--from / --to)、--db オプション、しきい値（稼働率 99% 等）に基づく PASS/FAIL 判定を実装。

- 研究（リサーチ）基盤（着手）
  - research/factor_research.py（設計と一部実装）
    - モメンタム等のファクター計算設計を実装開始（DuckDB を使った価格テーブル参照、各種窓長の定義）。（未完／続きあり）

- パッケージ情報
  - __init__.py にてパッケージバージョンを "0.1.0" として定義。

### Changed
- N/A（初期リリースのため変更履歴はありません）

### Fixed
- N/A（初期リリースのため修正履歴はありません）

### Notes / Implementation details
- 環境変数パースは export 形式、引用符やエスケープ、コメント処理に対応しており、実運用での柔軟性を考慮しています。
- run_execution/run_monitoring は起動直後にプロセス優先度を高に設定し、ログ統一化のため setup_logging を最初に呼び出します。
- Paper Trading モードは本番 DB と完全に分離される実装（paper_sqlite_path）で、誤発注リスクを低減します。
- position_sizing の aggregate スケールダウン処理は、整数単元（lot）単位での細かい残差処理を行い、資金不足時に再現性のある切り捨て・追加配分を行うよう設計されています。

---

作成者: KabuSys 開発チーム（コードベースからの変更点を推測して記載）