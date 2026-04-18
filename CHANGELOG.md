CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
このファイルは「Keep a Changelog」形式に準拠しています。セマンティックバージョニングを使用します。

Unreleased
----------

- （今後のリリース向けの予定・メモをここに記載してください）

0.1.0 - 2026-04-18
------------------

Added
- 実行／監視用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db を既定）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を使って実行環境に応じたブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動。停止フラグ（data/stop_requested.flag）検知で Graceful shutdown を実施。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は常に本番用の sqlite_path を使用する（環境に依らない監視 DB アクセス）。
    - 停止フラグ検知でループを終了し、DB 接続を確実にクローズ。

- 設定管理・ユーティリティ
  - config.py
    - .env ファイルの自動読み込みを追加（プロジェクトルート自動検出: .git または pyproject.toml を起点）。
    - .env パーサーを実装（コメント、export プレフィクス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
    - Settings クラスを実装し、環境変数のラッパーを提供（各種パス、API トークン、しきい値、KABUSYS_ENV 検証等）。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path、kill_flag_clear_on_start などの設定を追加。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加。既存 .env 読み込み、選択肢・デフォルト提示、シークレットマスク表示、保存確認を実装。
  - validate_config.py
    - 起動前設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ検査、config/*.yaml の存在・パースチェック（PyYAML が無ければ警告）、本番時のガード（LINE 設定、KILL_FLAG_CLEAR_ON_START）等を実行。--strict オプションで警告を FAIL 扱いにできる。
  - utils/logging_setup.py
    - 統一的ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソール出力のみで安全に継続。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows の優先度クラスや POSIX の nice 値を抽象化して set_process_priority() を提供。アクセス権限不足や未対応 OS では警告を出してスキップ。

- ポートフォリオ構築関連（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア順に選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全てが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮）により候補銘柄を除外するロジックを実装。unknown セクターは上限適用外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームはフォールバック（1.0）し警告出力。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいて発注株数を計算。単元株（lot_size）で丸め、1銘柄上限・aggregate 上限（available_cash）を考慮。コストバッファを使った保守的見積りおよびスケーリングと残差分配ロジックを実装。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシを集計して PASS/FAIL 判定（閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - --from / --to / --db オプションを提供し、PAPER_TRADING_SQLITE_PATH 環境変数にも対応。

- データ分析基盤（研究用）
  - research/factor_research.py（基盤実装）
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクター計算方針と基礎定数を定義。モメンタム計算関数（calc_momentum）の追加を開始（prices_daily に基づく計算を想定）。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- 監視・実行スクリプト共通でプロセス優先度を最初に "high" に設定することで重要プロセスの優先度を確保。
- logging_setup: stderr ではなく stdout に StreamHandler を向けることで cron / Task Scheduler などからのログリダイレクト運用を想定。

Fixed
- なし（初回公開。各モジュールでエラー処理やフォールバックを多用し、実運用時の耐障害性を考慮した実装になっていることを注記）

Notes / Implementation details
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされるため、配布環境でも CWD に依存せず動作する設計。
- 多くのモジュールは DB 参照を限定（例: portfolio/*.py は純粋関数）し、ユニットテストしやすい構造にしてある。
- 一部の関数（例: research.calc_momentum）は実装途中の箇所が見られるため、将来追加のファクターや最適化が予定される。

Acknowledgements
- 本 CHANGELOG はコードベースからの推測に基づいて作成しています。実際のリリース履歴とは差異がある場合があります。必要であれば、より詳細なリリース日付／差分情報を提供してください。