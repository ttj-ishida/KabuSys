CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

Unreleased
----------

- （現在の差分は 0.1.0 リリースとして記録されています）

0.1.0 — 2026-04-18
------------------

Added
- 初版リリース。KabuSys 自動売買フレームワークの基盤機能を追加。
- 実行エントリ / 管理スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine をスレッドで起動。
    - 停止フラグ (data/stop_requested.flag) 検知による安全停止処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する挙動。
    - stop フラグ (data/stop_requested.flag) と KeyboardInterrupt のハンドリングを実装。
- 設定・環境管理
  - config.py: Settings クラスを追加。
    - .env/.env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パースロジックを実装（export 形式、クォート、エスケープ、インラインコメント対応）。
    - 各種設定プロパティを提供（J-Quants / kabu / LINE / DB / 監視閾値 / システム設定など）。
    - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ関連設定を実装。
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 主要環境変数のテンプレート、シークレット扱いでのマスク表示、保存機能を提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - --strict オプションで警告を失敗扱いにできるモードを提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選出（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア比率配分（スコア全0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（売却予定銘柄を除外、"unknown" セクターは上限対象外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based, equal, score）に基づく株数算出。
    - 単元株（lot_size）丸め、max_position_pct/max_utilization の制約、aggregate cap スケーリング（残差処理による追加配分）を実装。
- 研究用ファクター計算
  - research/factor_research.py: DuckDB を使った各種ファクター計算を追加（Momentum / Volatility 等）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（データ不足時は None）。
    - calc_volatility: ATR/相対ATR/平均売買代金/出来高比率 等（ウィンドウ不足時は None）。
    - 設計は DuckDB の prices_daily / raw_financials を参照する純粋関数。
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などを集計。
    - しきい値（稼働率 99%、注文成立率 90%、送信率 95%、P95 <= 200 ms）による PASS/FAIL 判定。
    - --from / --to / --db オプションをサポート。
- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows と POSIX を吸収）。
    - CPU affinity 設定ユーティリティを追加。
    - 許可されない環境での安全なフォールバックと警告出力。

Changed
- 初版なので「変更」はなし（リリース時点での初期実装を記録）。

Fixed
- 初版なので既知のバグ修正はなし。

Notes / Implementation Details（重要な挙動・デフォルト）
- データベース
  - DuckDB データファイルのデフォルト: data/kabusys.duckdb
  - SQLite 監視 DB のデフォルト: data/monitoring.db
  - ペーパートレード用 SQLite のデフォルト: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に分離）
- 起動時挙動
  - run_execution / run_monitoring 起動時にプロセス優先度を "high" に設定しようとします（失敗しても起動は継続）。
  - run_monitoring は監視 DB に対して init_monitoring_db を呼び出し、監視テーブルの存在を保証します。
  - run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。無効値はデフォルト 60 秒にフォールバック。
- 環境ファイルの自動読み込み
  - プロジェクトルートが検出できる場合、.env（既存の OS 環境は上書きしない）→ .env.local（上書き可）を順にロードします。
  - OS 側の既存環境変数は保護され、.env.local の override でも上書きされません。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます（テスト等で利用）。
- セキュリティ/運用上の注意
  - .env は絶対にリポジトリにコミットしない旨を config_setup.py の出力で明記。
  - validate_config の live 系チェックでは LINE 通知設定や KILL_FLAG_CLEAR_ON_START の安全性を警告します。

今後の予定（候補）
- per-stock lot_size の銘柄別対応（stocks マスタからの読み込み）
- monitoring の SystemMonitor / monitoring_db の詳細な拡張（現在は init と check_once の呼び出しを提供）
- factor_research の追加ファクター・テストカバレッジの強化
- 実行系のエラーハンドリングや再試行ロジックの強化

参考
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 日付はソースツリー中の現行日付（このリリースの記録日）を使用しています。