Keep a Changelog
=================
すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

履歴
----

### Unreleased
- （現在なし）

### [0.1.0] - 2026-04-18
初回リリース。自動売買システム KabuSys のコアユーティリティ、CLI、ポートフォリオ構築・ポジション計算、監視・実行ランナー、検証ツール等を追加。

Added
- 起動スクリプト / デーモン
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_sqlite_path（data/paper_trading.db がデフォルト）を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動処理を実装。
    - 停止フラグ（data/stop_requested.flag）を監視して安全に停止。実行 PID を data/execution.pid に出力。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用（監視 DB の初期化処理を含む）。
    - 停止フラグ検知でループ終了。KeyboardInterrupt にも対応。
  - 両スクリプトとも起動時に set_process_priority("high") を呼び出してプロセス優先度を上げる（可能な環境で）。

- 設定・環境管理
  - config.py: Settings クラスを導入し、環境変数経由でアプリ設定を取得する API を提供。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 等のプロパティを用意。
    - PAPER_FILL_MODE の妥当性チェックを実装（"instant", "partial", "never", "reject" のみ許容）。
    - KABUSYS_ENV の妥当性チェック（"development","paper_trading","live"）。
  - .env の自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み順序: OS 環境 > .env.local（上書き） > .env（未設定のみ）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。

- .env パーサ
  - export KEY=val 形式、シングル/ダブルクォート値、バックスラッシュエスケープ、インラインコメント処理などをサポートする堅牢なパーサを実装。
  - _load_env_file に protected 引数を設け OS 環境変数の上書き防止を行う。

- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 入力項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。
    - 既存 .env の読み込み・マスク表示、保存機能を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 値チェック、DB パス（親ディレクトリ存在確認）、config/*.yaml の存在・パース検証（PyYAML がある場合）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict モードで警告も失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション／デフォルト logs/、30日分保持）を設定する共通ユーティリティを実装。
    - LOG_LEVEL / LOG_DIR の解決順、ディレクトリ作成失敗時はファイル出力をスキップし stdout のみで継続。
  - utils/process_priority.py:
    - Windows と POSIX（Linux/Mac 等）を吸収するプロセス優先度設定と CPU Affinity 設定ユーティリティを実装（psutil 使用、権限不足時は警告してスキップ）。

- ポートフォリオ構築 / ポジションサイジング
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補を選択、同点時は signal_rank によるタイブレーク。
    - calc_equal_weights, calc_score_weights: 等配分・スコア正規化配分を提供。スコア全0 の場合は等配分へフォールバック（警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 同一セクター集中を抑制するため既存ポジション比率が閾値以上のセクターの新規候補を除外する機能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づく株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、スケールダウン後の残余キャッシュを用いた端数配分ロジックなどを実装。

- リサーチ / ファクター計算（下位モジュール）
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity 系ファクター算出方針とモメンタム計算関数（calc_momentum）を追加（DuckDB 接続を利用、prices_daily / raw_financials を参照する想定）。（一部実装が継続中）

- DuckDB サポート
  - run_monitoring, run_execution 等で分析用 DuckDB を使用するための接続処理を追加（Settings.duckdb_path を利用）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成ツールを追加。P95 計算、稼働率・注文成功率・送信率・レイテンシ指標を算出し PASS/FAIL 判定を表示。
    - CLI 引数で期間指定 (--from, --to) と DB パス指定 (--db)。環境変数 PAPER_TRADING_SQLITE_PATH をサポート。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

補足 / 実運用上の注意
- .env ファイルは機密情報を含むため絶対に VCS にコミットしないこと（config_setup.py のヘッダで注意喚起）。
- LOG_DIR や DB パスの親ディレクトリは存在しない場合があるため、起動環境でのディレクトリ作成権限に注意すること。ログディレクトリ作成失敗時はファイルローテーションは無効化され stdout のみ出力となる。
- process_priority / cpu_affinity は権限やプラットフォームによって制約を受ける（アクセス拒否時は警告してスキップ）。
- Paper Trading 実行時は本番 DB と分離されるよう設計済み（PAPER_TRADING_SQLITE_PATH を利用）。

既知の制約 / TODO
- research/factor_research.py の一部実装が継続中（ファクターの完全実装・最適化）。
- position_sizing の価格フォールバック（価格欠損時の処理）など追加の堅牢化がコメントで示唆されている（将来の拡張予定）。
- 将来的に銘柄毎の lot_size をサポートするための拡張（stocks マスタの導入）が予定されている。

開発者向けメモ
- 自動 .env ロードはプロジェクトルートを .git / pyproject.toml から判定するため、配布形態やテスト時に挙動が異なる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと良い。
- validate_config の --strict モードは CI やデプロイ前チェックに有用。

----- 
（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートは開発者の意図や実態に合わせて調整してください。）