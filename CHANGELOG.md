CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。  

[Unreleased]
------------

- （現在未リリースの変更はここに記載します）

[0.1.0] - 2026-04-20
--------------------

初回リリース（推測: コードベースからまとめた主要機能・実装の一覧）

Added
- 基本アプリケーション情報
  - パッケージメタ情報（kabusys/__init__.py: __version__ = "0.1.0"）。
- 設定管理
  - Settings クラスによる環境変数ラッパー（kabusys.config）。
  - .env 自動読み込み（プロジェクトルート検出、.env / .env.local の順で読み込み）。
  - .env ファイルの堅牢なパース機能（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ等に対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグ。
- 対話的設定ウィザード
  - config_setup CLI による .env の初期作成・更新支援（値のマスク表示、選択肢、保存プレビュー）。
- 設定検証ツール
  - validate_config CLI: 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスと config/*.yaml の存在・パース検証、本番（live）向けガードチェック、--strict モード。
- 実行系 / 監視系起動スクリプト
  - run_execution: ExecutionEngine を起動するメインスクリプト（プロセス優先度設定、paper_trading 用 DB 分離、Broker クライアント工場、OrderManager / RiskManager / Reconciler の組み立て、デーモンスレッドでの実行、停止フラグ処理）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔上書き、停止フラグ検知、DB 初期化）。
- Paper Trading の分離
  - paper_trading 環境では専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
  - PAPER_FILL_MODE による MockBroker の振る舞い（instant/partial/never/reject）の設定をサポート。
- ロギング・プロセス制御ユーティリティ
  - setup_logging: ルートロガー設定ユーティリティ（コンソール stdout と TimedRotatingFileHandler、ログディレクトリ自動作成、LOG_LEVEL/LOG_DIR 解決順）。
  - process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定、および CPU affinity 設定ユーティリティ（psutil ベース）。
  - ログ作成失敗や権限不足時のフォールバック（ファイル出力不可時はコンソールのみ）を実装。
- ポートフォリオ構築ライブラリ
  - portfolio_builder: 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights)。
  - risk_adjustment: セクター集中制限の適用 (apply_sector_cap)、市場レジームに基づく投下資金乗数 calc_regime_multiplier。
  - position_sizing: 各種配分方式（risk_based / equal / score）に基づく株数計算、単元株丸め、aggregate cap によるスケーリング処理。
  - すべて純粋関数としてメモリ内完結（DB 参照なし）。
- 実行系アーキテクチャ上の準備
  - OrderRepository, OrderManager, Reconciler, RiskManager といったコンポーネントの組み立てを想定するコード構成（実装の存在を示唆する import）。
  - ExecutionEngine の起動・停止制御、PID / stop flag ファイルの処理。
- 解析・検証ツール
  - tools/paper_verification_report: Paper Trading 用の検証レポート生成スクリプト（稼働率、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定）。
  - レポートは日付フィルタ対応、DB 存在チェック、メトリクスの閾値判定を実装。
- DuckDB / SQLite 統合
  - duckdb と sqlite3 を使った接続処理を複数箇所で採用（分析用 DuckDB、監視/発注用 SQLite）。
  - 監視テーブル初期化関数 init_monitoring_db の呼び出し（冪等に DB スキーマを保証する用途）。
- リサーチ基盤（未完のファイルからの判断）
  - research/factor_research.py にファクター計算（Momentum/Value/Volatility/Liquidity）用の骨組みを実装（DuckDB から prices_daily / raw_financials を参照する設計）。
  - 日数定数（1M/3M/6M, MA200, ATR 等）や P95 計算ユーティリティを含む。

Changed
- （初回リリースのため過去変更はなし）

Fixed / Robustness improvements
- 環境変数の検査・フォールバック
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバック処理（負値や非数はデフォルト 60 秒に戻す）。
  - PAPER_FILL_MODE の検証（有効値以外は ValueError を発生させる）。
  - 設定値チェック時にプレースホルダ（"_here"/"your_value"）を警告。
- ログ/プロセス制御の例外ハンドリング
  - ログディレクトリ作成失敗やファイルハンドラ生成失敗時にコンソール出力にフォールバックして継続。
  - set_process_priority / set_cpu_affinity で権限不足や未実装例外を警告ログで扱いスキップする実装（運用環境の互換性向上）。
- DB 初期化の冪等性
  - init_monitoring_db を起動時に呼ぶことで監視テーブルの存在を保証（既存 DB に対して安全に呼べることを想定）。

Security / Secrets
- config_setup の対話表示で機密項目（J-Quants トークン、Kabu API パスワード、LINE トークン）をマスクして表示。

Notes / Implementation details（推測を含む）
- 実運用を意識した設計（プロセス優先度設定、ログローテーション、PID/stop フラグ、kill flag の運用設定等）になっており、development / paper_trading / live の切替を想定した挙動が多数組み込まれている。
- paper_trading 環境向けに発注のモック化（MockBrokerClient）と本番 DB の完全分離が行われている（run_execution の処理より推測）。
- 一部モジュール（ExecutionEngine、BrokerClientFactory、OrderManager 等）はこの範囲のコードからは import されているが実装の詳細は省略されているため、本 CHANGELOG では存在と責務を記載に留める。

Security
- （既知のセキュリティ脆弱性はコードからは検出されないが、.env を絶対にリポジトリへコミットしないことを README 等で明記する設計が示唆されている）

Acknowledgements / TODO（コードから想定される今後の改善点）
- research/factor_research の未完部分や PortfolioConstruction.md / StrategyModel.md に基づく追加実装（シグナル生成や正規化ユーティリティの統合）など、今後の実装継続が想定される。
- position_sizing の lot_size を銘柄別対応に拡張する TODO 等の改善メモが残されている。
- price 欠損時のフォールバック（前日終値や取得原価利用）や、より詳細なコスト推定（スリッページ・手数料）に関する改善が示唆されている。

------------------------------------------------------------
注: 本 CHANGELOG は提供されたソースコードの内容から機能や意図を推測して作成した要約です。実際のリリースノート作成時はコミット履歴や開発者の意図を元に調整してください。