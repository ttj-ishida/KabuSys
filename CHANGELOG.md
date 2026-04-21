CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

フォーマットの規約: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-04-21
------------------

Added
- 初回リリースを追加。
- 実行用エントリポイント
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - Engine を別スレッドで実行し、data/stop_requested.flag による安全な停止、data/execution.pid への PID 管理（設定により）をサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は環境に関わらず本番 sqlite_path を使用する挙動を明示。
    - 停止フラグ検知と例外ハンドリングにより監視ループの安定稼働を担保。
- 設定管理
  - config.py: 環境変数 / .env 自動読み込みを実装（プロジェクトルートの .git または pyproject.toml を基準に探索）。
    - .env/.env.local の読み込み順と保護（OS 環境変数を上書きしない）を実装。
    - .env 行パーサを強化（export 指定、クォート文字列、バックスラッシュエスケープ、インラインコメント対応）。
    - Settings クラスに各種プロパティを実装（パス、閾値、env 判定、paper_fill_mode の値検証等）。
- 設定ユーティリティ / CLI
  - config_setup: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - シークレット項目は表示をマスク、選択肢・デフォルト提示、保存前の確認を実装。
  - validate_config: .env および config/*.yaml の基本検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス親ディレクトリ確認、PyYAML があれば YAML パース検証、live 環境時の追加ガード（LINE 設定や Kill Switch の注意喚起）を実装。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等額・スコア比率の重み計算（スコア全ゼロ時はフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮して新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear を想定。未知値はフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 発注株数計算を実装（allocation_method: risk_based / equal / score）。
    - 単元株丸め、銘柄ごとの上限・Aggregate cap スケーリング、cost_buffer を用いた保守見積り、残差に基づく追加配分の安定ソートを実装。
- 監視・検査ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）などを集計し PASS/FAIL 判定を出力。
    - 日付フィルタ、P95 計算、テーブル欠如時の耐障害性（OperationalError を捕捉して N/A 扱い）を実装。
- ユーティリティ
  - utils.logging_setup: ルートロガー設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定。
    - 既存ハンドラのクリア処理、ログディレクトリ作成失敗時のフォールバック、環境変数/引数による設定をサポート。
  - utils.process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX(Linux/Mac/FreeBSD) の差分を吸収し安全に設定。psutil の例外を捕捉して失敗時は警告でスキップ。
- research
  - research.factor_research: ファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity 設計方針、DuckDB を用いた実装予定）。一部関数（モメンタム計算）実装開始。

Changed
- なし（初版のため該当なし）。

Fixed
- なし（初版のため該当なし）。

Notes / 実運用上の注意
- run_monitoring は Monitoring 用 DB として Settings.sqlite_path（デフォルト: data/monitoring.db）を環境に関わらず使用します。意図的な隔離が必要な場合は設定を調整してください。
- run_execution は paper_trading モード時に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離します。
- 自動 .env 読み込みはプロジェクトルートが検出できない場合はスキップされます。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority や CPU affinity の設定は OS と権限に依存します。設定に失敗した場合はログに警告が出力され、処理は継続されます。
- ログは既定で logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

開発者向けリファレンス（短記）
- 実行: python -m kabusys.run_execution, python -m kabusys.run_monitoring
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report

(注) 本 CHANGELOG はコードベースの内容から推測して作成しています。詳細な変更履歴はコミットログやリリースノートを併せて参照してください。