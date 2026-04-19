# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  

フォーマット: バージョン見出し → Added / Changed / Fixed / Removed / Deprecated / Security の分類で記載しています。

Unreleased
---------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------
Added
- 初回リリースを追加。KabuSys の基本機能群を実装。
  - 実行エントリ
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB から分離。
      - BrokerClientFactory によるブローカークライアント生成を利用。
      - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler を組み合わせて実行スレッドでセッションを起動／監視。
      - 停止フラグ（data/stop_requested.flag）検知による安全停止、実行 PID ファイル出力（data/execution.pid）に対応。
  - 監視エントリ
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告を出力。
      - 監視プロセスは監視用テーブル初期化（init_monitoring_db）と DuckDB 接続を行う。
      - 監視は環境設定にかかわらず本番 sqlite_path を使用する旨を明記。
      - 停止フラグファイル検知で安全にループを終了。
  - 設定管理
    - config.py: Settings クラスを実装し、環境変数経由で各種設定を提供。
      - .env 自動ロード機能（.env → .env.local の順、OS 環境変数を保護）を実装。無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
      - .env の柔軟なパース（export プレフィックス対応、クォート内エスケープ、インラインコメントの扱い）を実装。
      - 各種プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode の妥当性チェック、PID/KILL フラグパス、閾値設定、環境種別チェック等）を提供。
    - config_setup.py: .env を対話式に作成・更新するウィザード CLI を追加。
      - J-Quants や kabu API、DB パス、LOG_LEVEL、Kill Switch 設定など主要項目を対話で入力可能。秘密項目はマスク表示。
      - 保存前の確認、キャンセル動作に対応。
    - validate_config.py: 起動前に .env および config/*.yaml の不備を検出する検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML があれば）パース検証、live 環境向けガードチェックを実装。
      - --strict モードで警告を FAIL 扱いにするオプションを提供。
  - ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
      - stdout（StreamHandler）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler、30日分保持）をルートロガーへ設定。
      - LOG_DIR/LOG_LEVEL および関数引数でのオーバーライドに対応。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
      - Windows（psutil の PRIORITY_CLASS を使用）と POSIX（nice 値）を吸収する実装。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。
      - 権限不足や未対応 OS の場合は警告を出力してスキップ。
  - ポートフォリオ構築（純関数群）
    - portfolio/portfolio_builder.py: 候補選定・重み算出関数を実装。
      - select_candidates（スコア降順・タイブレークルール）、calc_equal_weights、calc_score_weights（全スコア0のとき等金額にフォールバック）。
    - portfolio/risk_adjustment.py: セクター上限適用とレジーム乗数を実装。
      - apply_sector_cap（既存ポジションを考慮したセクター集中制限、"unknown" セクターは除外対象外）と calc_regime_multiplier（"bull"/"neutral"/"bear" のマップ、未知は警告して 1.0 フォールバック）。
    - portfolio/position_sizing.py: 株数決定ロジックを実装。
      - allocation_method に "risk_based"/"equal"/"score" をサポート。
      - lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer に基づく conservative なコスト推定、aggregate cap によるスケールダウンと端数の再配分ロジックを実装。
  - リサーチ
    - research/factor_research.py: ファクター計算モジュール（モメンタム／MA200乖離／ATR／流動性等）の骨格を追加。DuckDB 接続を受け取って prices_daily 等を参照する設計を採用（部分実装あり）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。
      - PAPER_TRADING_SQLITE_PATH / --db で DB を指定可能。期間フィルタ（--from / --to）対応。
      - 稼働率（system_status）、注文成功率（trade_logs）、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定（閾値をファイル先頭で定義）を出力。
      - P95 計算、データ欠損時の N/A ハンドリング、SQL の OperationalError 保護を実装。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes
- 本リリースでは設計文書（PortfolioConstruction.md、StrategyModel.md 等）に準拠した実装が行われていますが、一部は将来的な拡張（例: 銘柄ごとの lot_size マスタ、価格フォールバック処理など）を想定して TODO コメントを残しています。
- 実行時に必要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）が未設定の場合は起動前検証ツール（validate_config）で検出できます。