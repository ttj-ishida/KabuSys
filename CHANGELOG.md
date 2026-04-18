KEEP A CHANGELOG に準拠した形式で、このコードベースから推測される変更履歴を日本語で作成しました。初回リリース相当（v0.1.0）としてまとめています。

CHANGELOG.md
===========

全般
----
- 本ドキュメントは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。
- 日付はソースコードの導入時点を推定して記載しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-18
--------------------

Added
-----
- アプリケーションの初期リリース（KabuSys v0.1.0）。
- 環境 / 設定管理
  - .env 自動ロード機能を実装（プロジェクトルートの .env, .env.local を環境変数に読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応）。
  - Settings クラスを追加し、環境変数経由で設定値を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）。
  - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）や KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
- 設定ユーティリティ / CLI
  - 対話式の環境設定ウィザードを実装（kabusys.config_setup）。.env の初期作成・更新を支援。
  - 設定検証 CLI を実装（kabusys.validate_config）。必須環境変数・ファイルパス・config/*.yaml の存在や簡易パース（PyYAML があれば内容検証）を行う。--strict オプションで警告を FAIL 扱いにできる。
- 実行関連
  - ExecutionEngine 起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は MockBrokerClient 想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。停止フラグ（data/stop_requested.flag）検知で安全停止。
    - ExecutionEngine に PID ファイルの取り扱い（data/execution.pid）を導入。
    - RiskManager のデフォルト設定を追加（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors, circuit_breaker_window_sec, max_drawdown 等）。initial_portfolio_value を broker.get_available_cash() で初期化。
  - 監視ループ起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（monitoring DB は production path を参照する設計）。
    - SystemMonitor の定期実行、停止フラグ検知、例外ハンドリング、DB（SQLite / DuckDB）クローズ処理を実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder: 信号の候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。
  - position_sizing: 発注株数計算（calc_position_sizes）を実装。allocation_method に応じた計算（"risk_based" / "equal" / "score"）、単元株（lot_size）丸め、コストバッファ、aggregate cap によるスケールダウンと残差処理を含む。
- ユーティリティ
  - process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する set_process_priority と、CPU affinity を設定する set_cpu_affinity を実装（psutil ベース、権限不足や未対応環境では警告を出してスキップ）。
- リサーチ / ファクター計算
  - research.factor_research: DuckDB 接続を用いたファクター計算モジュールを実装。モメンタム（1/3/6 か月リターン、MA200乖離）やボラティリティ（ATR20 等）を計算する関数を提供。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを実装。稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）などを集計し PASS/FAIL 判定を行う。--from/--to/--db オプション対応。
- パッケージ情報
  - __version__ を 0.1.0 に設定。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- .env のパース処理を強化（export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなど）し、実運用での .env 設定ミスに耐性を持たせた。
- 設定検証 CLI が PyYAML 未導入環境でも graceful に動作するよう、YAML 検証をオプトアウト可能にした（警告出力）。

Deprecated
----------
- （該当なし）

Removed
-------
- （該当なし）

Security
--------
- .env は絶対に VCS にコミットしない旨をドキュメント（config_setup が生成するヘッダ）に明記。

Notes / Known issues / TODO
--------------------------
- apply_sector_cap 内で price_map に欠損（0.0）値がある場合のエクスポージャー過少見積りについての注意と将来的なフォールバック（前日終値や取得原価の利用）をコメントで残している。現状では欠損価格は 0.0 扱いとなり、正確なエクスポージャー算出ができない可能性がある。
- position_sizing は現状全銘柄共通の lot_size（デフォルト 100）前提。将来的には銘柄別 lot_size をサポートする設計拡張が想定されている。
- set_process_priority / set_cpu_affinity は権限不足や未対応 OS（psutil の定数が無い等）では設定できないため、運用環境の権限（root/管理者）に注意が必要。
- run_monitoring は設計上「監視は本番 DB を参照する」ため、開発環境で動かす際は sqlite_path に注意すること（監視データは production path に記録される）。
- Paper Trading と本番 DB の分離は run_execution 側で考慮済み（settings.paper_sqlite_path を使用）が、他のモジュールが誤って本番 DB を参照しないよう環境変数の設定に注意が必要。
- research.factor_research の SQL は DuckDB 上の prices_daily / raw_financials スキーマに依存するため、データ整備が前提。

CLI / エントリポイント（代表）
-----------------------------
- python -m kabusys.config_setup    （対話式 .env 作成 / 更新ウィザード）
- python -m kabusys.validate_config [--strict]
- python -m kabusys.run_monitoring  （監視ループ起動）
- python -m kabusys.run_execution   （ExecutionEngine 起動）
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ライセンス / コントリビューション
--------------------------------
- 本 CHANGELOG は提供されたソースコードから推測して作成したものであり、実際のリリースノートはバージョン管理履歴やリリース担当の記録に基づいて作成することを推奨します。