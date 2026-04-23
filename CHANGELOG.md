Keep a Changelog
=================

すべての変更は慣例に従って記載します。  
フォーマット: https://keepachangelog.com/（日本語）

[未リリース]
------------

（現在のコードベースでは明示的な未リリース差分はありません。初回リリースとして以下を記載しています。）

0.1.0 - 2026-04-23
-----------------

Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を High に設定し、停止フラグ（data/stop_requested.flag）検知で安全に終了する。
    - SQLite / DuckDB 接続の初期化（init_monitoring_db 呼び出し含む）とログ設定を実装。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド起動を実装。
    - 起動時にプロセス優先度を High に設定。PID ファイル管理、停止フラグ検知による安全停止をサポート。
    - RiskConfig のデフォルト値（max_position_pct や max_utilization 等）を設定し、初期ポートフォリオ値に broker.get_available_cash() を使用。

- 設定・環境管理
  - config.py
    - Settings クラスを追加。環境変数をプロパティ経由で取得・検証する API を提供（JQUANTS_REFRESH_TOKEN 等の必須値、KABUSYS_ENV / LOG_LEVEL 検証など）。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。OS 環境変数は保護して上書きされない。
    - .env の行パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、行末コメントなどに対応。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグパス、CPU/Memory/Disk 閾値などのプロパティを追加。
    - settings = Settings() をモジュールレベルで公開。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 入力プロンプト、既存 .env 読込、シークレット値のマスク表示、最終確認とファイル書き込みを実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性・存在チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス（親ディレクトリ存在チェック）、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加警告などを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・タイブレークで signal_rank による整列。上位 N を返す。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率による重み計算。全スコアが 0 の場合は等配分にフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用。既存ポジションのセクター別エクスポージャー計算（売却予定銘柄除外）、上限超過セクターの新規候補除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数の算出。未知のレジームは警告して 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいて発注株数を決定。lot_size（単元）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を用いた保守的見積り、残差処理に基づく追加配分ロジックを実装。

  - portfolio/__init__.py で主要関数を公開。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）をルートロガーに設定。
    - 重複ハンドラ防止のため既存ハンドラをクリア。LOG_LEVEL / LOG_DIR の優先解決ルールを実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - set_process_priority(level) を追加（"high"/"normal"/"low"）。Windows/Linux/macOS を吸収して psutil で優先度設定を試行、権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count) を追加。最初の N コアにプロセスをピン留め（サポートされない環境では警告でスキップ）。

- モニタリング / 実行データベース初期化
  - monitoring.monitoring_db.init_monitoring_db を run スクリプトから呼び出して監視テーブルの存在を保証（冪等）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）。
    - 指標: システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数などを集計。
    - 閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を用いた PASS/FAIL 判定を実装。
    - 日付フィルタ (--from / --to) をサポート。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - DuckDB 接続を受けて prices_daily / raw_financials を参照し、Momentum / Value / Volatility / Liquidity の計算を行うモジュールを追加。モメンタム指標（1M/3M/6M、MA200乖離）等の設計を記載（実装の一部がファイル末尾で未完）。

- パッケージ
  - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため既存コードからの差分変更は無し。設計方針やデフォルト値は各モジュール内ドキュメントに記載。）

Fixed
- （該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- 環境変数の取り扱いにおいて .env を絶対にリポジトリにコミットしない旨を config_setup.py に明記。シークレット項目は対話ウィザードでマスク表示。

補足メモ
- プロジェクトルートの自動検出は __file__ を基点に親ディレクトリを探索するため、CWD に依存しない動作を意図しています。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用途など）。
- 一部モジュール（例: research/factor_research.py）の実装は設計に沿っているものの、ファイル末尾で未完の箇所があります。将来的な拡充・ユニットテスト追加を推奨します。

（必要であれば、リリース日や各変更の担当者、コミット参照などの詳細を追記できます。）