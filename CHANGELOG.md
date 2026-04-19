# Changelog

すべての注目すべき変更を記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 初回リリース: KabuSys の基本的な起動スクリプト、設定管理、ユーティリティ、ポートフォリオ構築、検証ツールなどの主要機能を追加。
- 起動/運用スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。  
    - 停止フラグファイル data/stop_requested.flag を検知して安全にループを終了。  
    - 監視は環境にかかわらず本番用の sqlite_path を使用して DB に接続し、DuckDB も利用。
  - run_execution: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の別 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / Reconciler / RiskManager を組み合わせて ExecutionEngine を起動。  
    - data/execution.pid に PID を記録する仕組み（pid_file 経由）。停止フラグを検知するとエンジン停止を試行。
- 設定・検証・セットアップ
  - config.py: 環境変数読み込みと Settings クラスを実装。  
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロード機構。  
    - .env の読み込み規則: export プレフィックス、クォート文字とエスケープ、インラインコメントの扱いなどに対応。  
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能。  
    - Settings に各種プロパティ（J-Quants / kabu API / DB パス / paper_trading 設定 / 監視閾値 / env/log_level 判定など）を追加。入力値の検証（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）。
  - config_setup.py: 対話式 .env ウィザードを実装。  
    - 既存 .env の読み込み・既定値の提示・シークレットのマスク表示・保存機能を提供。  
  - validate_config.py: 起動前検証 CLI を実装。  
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML がインストールされている場合）、本番時のガード（LINE 設定や KILL_FLAG_CLEAR_ON_START）を実施。  
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でログファイルを出力（デフォルト logs/<app_name>.log）。30日分保持。  
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。LOG_LEVEL / LOG_DIR の解釈順を実装。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。  
    - Windows と POSIX（Linux/Mac/FreeBSD）で差分を吸収して nice/priority を設定。AccessDenied 等をハンドリングして安全にフォールバック。  
    - set_cpu_affinity により最初の N コアにプロセスを固定する機能を提供。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py: 候補抽出と重み計算（等分配・スコア加重）を追加。  
    - select_candidates: score 降順、同点は signal_rank でタイブレーク。  
    - calc_equal_weights / calc_score_weights: スコア合計が 0 の場合に等分配へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限とレジーム乗数を追加。  
    - apply_sector_cap: 既存ポジションのセクター比率に基づき新規候補を除外（unknown セクターは除外対象にしない）。  
    - calc_regime_multiplier: "bull","neutral","bear" に応じた multiplier を返す（未知値は 1.0 にフォールバック）。
  - portfolio/position_sizing.py: 発注株数計算ロジックを追加。  
    - allocation_method: "risk_based" / "equal" / "score" をサポート。  
    - 単元（lot_size）丸め、per-position の上限、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積り）考慮、残余キャッシュに基づく再配分ロジックを実装。
  - portfolio/__init__.py: 主要関数をエクスポート。
- 研究・分析
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム / MA / ATR / ボラティリティ / 流動性等の設計方針と定数）。  
    - calc_momentum の実装開始（ファイルは途中まで実装済み）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。  
    - SQLite（paper_trading DB）からシステム安定性、注文成功率、リスク却下数、レイテンシ（avg/max/P95）を算出し、閾値に基づき PASS/FAIL 判定を行う。  
    - CLI で期間指定 (--from / --to) と DB パス (--db) を受け取る。
- パッケージメタ
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details / 運用上の注意
- .env 自動ロードは OS 環境変数を保護する仕組み（protected set）を導入しており、.env.local は .env を上書き可能。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動読み込みは行われません（テスト等で便利）。
- run_monitoring は監視テーブルの初期化（init_monitoring_db）を実行して冪等にテーブル作成を保証します。監視は常に sqlite_path（本番向け）を参照します。
- run_execution は paper_trading 環境時に DB を分離するため paper_sqlite_path を使用します。これによりペーパートレードのログが本番 DB と混在しないようにしています。
- ログは stdout と日次ローテーションファイルの両方へ出力する設計です。cron 等で stdout/stderr をまとめてリダイレクトする運用を想定して stdout に出力します。
- process_priority の適用は可能な範囲で行い、権限不足や未サポート OS の場合は警告を出してスキップします。
- portfolio.PositionSizing の集計スケールダウンや残余配分ロジックは整数単元（lot_size）を前提とした安全な配分を行うよう設計されています。
- research/factor_research.py は実装途中の箇所（calc_momentum の続きが未完）があります。今後のリリースで完成予定。

---

今後の予定（例）
- factor_research の完成（全ファクター実装・DuckDB SQL 最適化）
- ExecutionEngine / Broker クライアント周りのテスト強化とモックの整備
- monitoring / alerting の拡張（LINE 通知実装など）
- config の型チェック・ドキュメントの整備

 SPDX-License-Identifier: MIT (コードベースのライセンスはリポジトリで確認してください)