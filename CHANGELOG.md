# Changelog

すべての重要な変更は Keep a Changelog の形式で記載しています。  
追跡方針: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在の配布バージョンは 0.1.0 です。今後の変更はここに記載されます）

---

## [0.1.0] - 2026-04-19

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能と運用ユーティリティを実装しました。主な追加点は以下の通りです。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` としてリリース。
  - パッケージ公開用のモジュール構成（execution、monitoring、portfolio、utils、tools、research 等）を実装。

- 設定・環境管理 (`src/kabusys/config.py`, `src/kabusys/config_setup.py`)
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理）。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local（上書き） > .env（未設定のみ）。
  - 設定取得用の Settings クラスを実装（J-Quants / kabuAPI / DB パス / ログレベル / 各種閾値など）。
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を実装。シークレット値のマスク表示、既存値読み込み、保存処理を提供。

- 起動前検証 CLI (`src/kabusys/validate_config.py`)
  - .env と config/*.yaml の基本的な妥当性チェックを行う CLI を実装。
  - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML の存在/パースチェック（PyYAML 未インストール時は通知）、本番環境向けのガードチェックを実装。
  - `--strict` オプションで警告をエラー扱いにできる。

- 実行エンジン起動スクリプト (`src/kabusys/run_execution.py`)
  - ExecutionEngine 起動スクリプトを実装。
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用 SQLite（既定: data/paper_trading.db）に記録することで本番 DB と分離。
  - 起動時にプロセス優先度を "high" に設定する仕組みを呼び出し。
  - duckdb を分析用コネクションとして接続、監視テーブルの初期化を保証。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立て、ExecutionEngine のデーモンスレッド起動、stop フラグ（data/execution.pid / data/stop_requested.flag）による安全停止を実装。
  - RiskManager のデフォルト設定（最大ポジション比率、利用率、レートリミット、サーキットブレーカー等）を実装し、初期ポートフォリオ値を broker.get_available_cash() で取得して初期化。

- 監視起動スクリプト (`src/kabusys/run_monitoring.py`)
  - SystemMonitor ポーリングループ起動スクリプトを実装。
  - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（運用上の意図を明記）。
  - 停止フラグ（data/stop_requested.flag）検出によるループ終了、安全な例外ハンドリング、DB 接続のクローズ。

- ポートフォリオ構築 (`src/kabusys/portfolio/*.py`)
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。スコア全てが 0 の場合のフォールバック警告あり。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のレジームはフォールバックして 1.0 を返す。
  - position_sizing: 発注株数計算（calc_position_sizes）を実装。allocation_method として "risk_based" / "equal" / "score" をサポート、単元株（lot_size）丸め、1 銘柄上限、aggregate cap（総投資額が利用可能現金を超過した場合のスケーリング）や cost_buffer を考慮した安全な割当ロジックを実装。スケーリング時の切り捨て残差を lot 単位で再配分するロジックあり。

- ロギング・プロセスユーティリティ (`src/kabusys/utils/*.py`)
  - logging_setup: すべての起動スクリプトから共通利用できるロギング設定ユーティリティを実装。stdout への StreamHandler（標準出力）、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。既存ハンドラはクリアして二重出力を防止。
  - process_priority: psutil を使ったクロスプラットフォームのプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 設定（set_cpu_affinity）を実装。権限不足や未対応 OS は警告してスキップ。

- Paper Trading 検証ツール (`src/kabusys/tools/paper_verification_report.py`)
  - Paper Trading 用 SQLite から集計して検証レポートを生成する CLI を実装。
  - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（平均/最大/P95）を算出し、基準値（稼働率>=99%、成立率>=90%、送信率>=95%、P95<=200ms）との照合で PASS/FAIL 判定を出力。
  - コマンドラインで期間指定（--from/--to）および DB パス指定（--db）に対応。

- 研究用ファクター計算（骨子） (`src/kabusys/research/factor_research.py`)
  - DuckDB を利用したファクター計算モジュールの骨子（モメンタム/MA200/ATR/流動性などの計画）を追加。calc_momentum など計算インタフェースと定数群を導入（実装途中の部分あり）。

### Changed
- ログ出力の振る舞い改善
  - logging_setup が既存ハンドラを安全に flush/close してから削除するようにし、複数回起動時のハンドラ二重登録問題を回避。

### Fixed
- 環境変数・入力の堅牢化
  - .env のパースでクォート内のエスケープや export プレフィックス、インラインコメント処理を正しく扱うように修正（複雑な値を安全に扱えるように）。
  - MONITOR_POLL_INTERVAL の不正値に対して警告を出しデフォルトへフォールバックする安全策を追加（time.sleep に渡す不正値回避）。

### Notes / Operational remarks
- 監視（run_monitoring）は設計上 KABUSYS_ENV にかかわらず本番用の sqlite_path を使用します（運用・監査目的で監視データを一元化する意図）。運用時の DB パス設定に注意してください。
- Paper Trading と本番 DB は容易に分離できるよう設計されています（settings.paper_sqlite_path を使用）。
- 一部モジュール（research の詳細実装など）は骨子または計算インタフェースのみで、今後の拡張を予定しています。
- ファイル/ディレクトリの作成に失敗した場合（例: ログディレクトリ作成失敗）は、ファイル出力をスキップしてコンソール出力のみで継続するフェイルセーフ動作を採用しています。

---

開発に関する問い合わせや不具合報告はプロジェクト管理者までお願いします。