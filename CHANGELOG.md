CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に準拠しています。
比較対象のバージョン: __version__ = 0.1.0

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-24
-----------------

Added
- 初回リリースとして主要コンポーネントを追加。
  - 起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止はリポジトリ直下 data/stop_requested.flag の検出で行う。
      - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する仕様。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の別 SQLite DB を使用（data/paper_trading.db、環境変数で上書き可）。
      - BrokerClientFactory を経由してブローカークライアントを生成。Engine をスレッドで起動し、stop flag により安全に停止可能。
      - 実行中の PID を data/execution.pid に記録する仕組みの受け皿を用意。
  - 設定管理・検証・ウィザード
    - config.py: 環境変数と Settings クラスを提供。
      - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - .env の読み込みで export 形式・クォート文字列・インラインコメントに対応。
      - 各種設定プロパティ（DB パス、PID パス、しきい値、PAPER_FILL_MODE 等）とバリデーションを実装。
    - config_setup.py: 対話的 .env 作成ウィザードを追加（.env の読み書き機能を含む）。
    - validate_config.py: 起動前の設定検証 CLI を追加（--strict オプションで警告を失敗扱いにできる）。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の検査、live 環境用の追加ガード等を実装。
  - ロギング・プロセス制御ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
      - コンソールは stdout に出力、日次ローテーション（TimedRotatingFileHandler）でログをファイルに保存（デフォルト logs/、30日分保持）。
      - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py: OS に依存しないプロセス優先度設定 / CPU affinity 設定ユーティリティを追加。
      - Windows / POSIX(Linux, macOS 等) に対応し、許可エラー時はワーニングを出してスキップ。
  - ポートフォリオ構築モジュール（純粋関数群、DB 参照なし）
    - portfolio/portfolio_builder.py
      - select_candidates: スコア降順で候補選定（タイブレーク: signal_rank）。
      - calc_equal_weights / calc_score_weights: 等金額・スコア加重のウェイト計算（スコアが全て 0 の場合は等金額にフォールバック）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター比率を計算して新規候補を除外）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。単元株丸め、max_position_pct、max_utilization、aggregate cap、cost_buffer を考慮。
    - portfolio/__init__.py で上記関数をエクスポート。
  - Paper Trading サポート・検証
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
      - system_status, trade_logs, risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（P95）等を集計し PASS/FAIL を判定。
      - デフォルト DB は data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで上書き可能。
  - 研究 / ファクター計算
    - research/factor_research.py を追加（DuckDB 接続を受け prices_daily/raw_financials を参照して各種ファクターを計算する設計）。
      - Momentum, Value, Volatility, Liquidity の計算ロジックを意図。calc_momentum 等の関数基盤を実装（コードの一部は継続実装の余地あり）。
  - パッケージ初期化
    - __init__.py にバージョン情報 __version__ = "0.1.0" を設定。

Changed
- n/a（初回リリースのため過去からの変更はなし）。

Fixed
- n/a（初回リリースのためバグ修正履歴はなし）。

Deprecated
- n/a。

Removed
- n/a。

Security
- 環境変数読み込み時に OS 環境変数を保護する仕組み（.env の上書き制御）を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを抑止可能。

Notes / 実装上の注意
- Monitoring の DB 書き込み先は Settings.sqlite_path（本番用パス）を使用する仕様です。運用で環境分離が必要な場合は config／環境変数で適切に設定してください。
- run_execution は paper_trading モード時に paper 用の SQLite を使用し、本番 DB とデータを完全に分離するよう配慮しています。
- .env パーサは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント（スペース直前の #）など多くの実用ケースに対応していますが、特殊ケースでは期待通り動作しない可能性があります。
- research/factor_research.py はファクター計算の設計に沿った実装が含まれますが、一部関数の実装が継続作業となっている箇所（コメントや TODO あり）が存在します。
- process_priority や CPU affinity の設定は権限や OS に依存するため、権限不足や未サポート環境では警告を出して安全にスキップします。

開発 / 運用に関する推奨
- .env は絶対にリポジトリへコミットしないこと。config_setup により生成された .env ファイル作成後に validate_config で設定チェックを行ってください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に設定することを強く推奨します（validate_config のガードあり）。
- ログ出力先（LOG_DIR）に書き込み権限があることを事前に確認してください。書き込みに失敗するとファイルハンドラは無効化され、コンソール出力のみになります。

---- 

（この CHANGELOG はソースコードの内容から推測して作成しました。実際のリリースノートとして利用する場合は運用情報や変更履歴をプロジェクトの実際のコミット履歴に基づいて補正してください。）