CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」準拠で記載しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在のブランチに未リリースの変更はありません）

0.1.0 - 2026-04-24
-----------------

Added
- 初回リリース。KabuSys のコア機能群を実装。
  - 実行コンポーネント
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" に設定して起動し、スレッドで engine.run_session を実行。停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を扱う。
    - BrokerClientFactory により環境（KABUSYS_ENV）に応じて実ブローカー／MockBrokerClient を選択可能。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
  - 監視コンポーネント
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視起動時はプロセス優先度を "high" に設定。
  - 設定管理
    - config.py: Settings クラスを実装。環境変数読み込み（.env, .env.local の自動読み込み）や各種設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 関連設定等）を提供。
    - .env 自動ロードは OS 環境変数を保護（保護キーは上書きしない）し、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - 設定ツール
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - validate_config.py: .env と config/*.yaml の事前検証 CLI。--strict モードで警告を FAIL 扱いにできる。PyYAML がない場合は YAML の内容検証をスキップして警告を出す。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
    - portfolio/risk_adjustment.py: セクター集中上限チェック（既存ポジションを考慮）とレジームに応じた投下資金乗数（bull/neutral/bear）を実装。
    - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）。単元株（lot_size）丸め、単銘柄上限・全体投資上限（aggregate cap）とスケーリング、残差に基づく追加配分ロジックを実装。
  - レポート・調査ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツール。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し PASS/FAIL 判定を出力。コマンドラインで期間指定可能（--from / --to）およびデータベース指定（--db）。
    - research/factor_research.py: ファクター計算モジュールの骨組み（モメンタム等）を実装（DuckDB 経由で prices_daily/raw_financials を参照する設計）。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。コンソール出力は stdout、日次ローテートのファイル出力をサポート（TimedRotatingFileHandler、30 日分保持）。LOG_LEVEL / LOG_DIR の解決順に対応し、ファイル出力失敗時はコンソールのみで継続。
    - utils/process_priority.py: psutil を用いたクロスプラットフォームのプロセス優先度設定および CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足等は警告でスキップする。

Changed
- （初回リリースにつき、過去リリースからの変更は無し）

Fixed
- .env 解析の堅牢化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理（クォートあり/なしの違いを考慮）などを正しく処理。
- calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分にフォールバックするようにし、ゼロ除算や不正な比率計算を防止。
- position_sizing:
  - 単元株（lot_size）での丸め処理を確実に行うよう改善。
  - aggregate cap を超えた際のスケーリングで、小数端数に基づく追加配分（fractions に基づく優先配分）を実装し、利用可能現金をより有効に活用するロジックを導入。
- logging_setup: ログディレクトリ作成に失敗した場合にファイルハンドラをスキップし、コンソール出力のみで継続するよう堅牢化。コンソールは stdout を使用（stderr ではない）。
- process_priority: 未対応 OS や権限不足の場合に警告を出してスキップするようにし、モジュール読み込み時の例外を抑制。

Security
- （現バージョンで特記すべきセキュリティ修正は無し）

Deprecated
- なし

Removed
- なし

注記 / Breaking changes
- run_monitoring の設計上、Monitoring は KABUSYS_ENV の値にかかわらず常に settings.sqlite_path（本番想定の SQLite パス）を使用して DB に接続します。監視データを環境ごとに分離したい場合は運用上の注意が必要です。
- デフォルトの Kill Switch 動作:
  - Settings.kill_flag_clear_on_start により起動時に kill flag を自動クリアする動作を制御します（デフォルト 0）。本番環境では 0 を推奨します。validate_config にも本番時の注意喚起チェックを実装済み。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。プロジェクトルートが特定できない場合は自動ロードをスキップします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

今後の予定（短期）
- research/factor_research の各ファクター実装完了（現在はモメンタム等の骨組み）。
- Engine / Broker 周りの追加テスト、MockBroker の挙動検証・文書化。
- 単元株サイズを銘柄毎に持てるように position_sizing の拡張（stocks マスタの導入予定）。
- YAML 設定ファイルのスキーマ検証を追加（PyYAML 利用時に stricter な検証を実行）。

-----