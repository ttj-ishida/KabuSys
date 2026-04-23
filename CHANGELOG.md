CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（日本語）

[0.1.0] - 2026-04-23
--------------------

Added
- 初回公開リリース。主要コンポーネントと CLI/ユーティリティを追加。
- 起動スクリプト / デーモン
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、MockBrokerClient を選択して本番 DB と分離する挙動を実装。
  - run_monitoring.py: システム監視ループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）検知による安全停止、起動時にプロセス優先度を高に設定。
- 設定 / 環境管理
  - config.py: .env 自動ロード機能と堅牢な .env パーサーを追加。Settings クラスを提供し、DuckDB / SQLite パス、paper_trading 用 DB パス、各種しきい値・フラグ等を環境変数から容易に取得可能に。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数チェック、パスの存在確認、config/*.yaml の基本的な存在・パースチェック、--strict モードをサポート。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額重み (calc_equal_weights)、スコア重み (calc_score_weights) を追加。
  - portfolio/risk_adjustment.py: セクター集中制限適用 (apply_sector_cap)、市場レジームに基づく乗数 (calc_regime_multiplier) を追加。
  - portfolio/position_sizing.py: 発注株数算出ロジック (calc_position_sizes) を追加。risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケーリング、cost_buffer 等をサポート。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。stdout 出力の StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせ、ログディレクトリ作成失敗時はファイル出力をスキップするフォールバックを実装。ログレベル/ログディレクトリは引数・環境変数で制御可能。
  - utils/process_priority.py: プロセス優先度（Windows/Linux/macOS対応）と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS の場合は警告を出してスキップ。
- 監視・モニタリング
  - monitoring_db の初期化呼び出しを実装場所から呼ぶことで監視テーブルが常に保証されるように（init_monitoring_db を使用）。
- DuckDB / SQLite 統合
  - 起動スクリプトやツールで DuckDB 接続を使用。分析データと監視データを分離して利用可能。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。期間フィルタ、稼働率・注文成功率・送信率・レイテンシ（P95 等）を算出し、定義済み閾値に基づく PASS/FAIL を出力。デフォルトの DB パスは data/paper_trading.db。閾値 (稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms) を使用。
- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- ログ出力の挙動を明確化: コンソール出力は stdout を使用。起動スクリプトは最初にロギング設定を行い、その後プロセス優先度を設定する順序に統一。
- run_monitoring: 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を参照する仕様（監視は本番 DB を対象に想定）。
- run_execution: paper_trading 環境では paper_sqlite_path を使用して DB を分離。

Fixed / Robustness improvements
- .env パーサー（config._parse_env_line）を堅牢化:
  - export プレフィックス対応、クォート文字とバックスラッシュエスケープ対応、インラインコメントの扱い改善。
- MONITOR_POLL_INTERVAL の値が不正な場合のフォールバック処理を追加（警告ログ出力、デフォルト 60 秒に戻す）。
- utils/logging_setup.py:
  - ログディレクトリ作成失敗時にファイルハンドラの作成をスキップし、コンソール出力のみで継続する安全なフォールバックを追加。
  - 既存ハンドラを安全に flush/close してから置き換える実装で二重設定を防止。
- utils/process_priority.py:
  - Windows / POSIX（Linux, Darwin, FreeBSD）それぞれに対する優先度設定を実装。権限不足や未対応 OS の場合は警告を出してスキップ。
- portfolio/calc_score_weights: 全銘柄スコアが 0 の場合に等金額配分へフォールバックして警告を出す。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクター（sector_map に存在しない銘柄）に対してはセクター上限を適用しない仕様にして誤除外を防止。
- position_sizing.calc_position_sizes:
  - 価格欠損時のスキップ、lot_size による丸め、aggregate cap によるスケールダウン、スケーリング後の端数配分を実装し、合計投下額が available_cash を超えないように調整。
  - cost_buffer を用いた保守的なコスト見積り対応。
- run_execution / run_monitoring:
  - 停止フラグ（data/stop_requested.flag）を監視し、安全に停止するフローを実装。
  - PID ファイル管理（起動時の pid_file を ExecutionEngine / SystemMonitor に渡す設計）を整備。
- validate_config.py:
  - 必須環境変数の簡易チェック、プレースホルダ検出、config/*.yaml の存在チェックと PyYAML がない場合のスキップ警告を実装。
- tools/paper_verification_report.py:
  - P95 算出ユーティリティと、欠損データ（テーブル未存在など）を考慮したフォールバックでレポート生成が途中で失敗しないように。

Notes / Known issues
- research/factor_research.py にてファクター計算（calc_momentum 等）の実装が含まれているが、ファイル末尾が途中で切れている（実装の続きが必要）。現状は基本的な定数や関数スケルトンを含む段階。
- 一部の外部依存（psutil, duckdb, PyYAML など）が必要。validate_config では PyYAML 未インストール時に YAML 検証をスキップするが、本番では必要に応じて依存関係をインストールすること。
- ログファイルのパーミッションやディレクトリ権限によってファイル出力が無効化されることがある。意図的にその場合は stdout での確認を行ってください。

その他
- ドキュメント内（コードコメント）に設計ノート（PortfolioConstruction.md, StrategyModel.md 等）への参照があるため、運用・戦略設計時は併せて参照してください。