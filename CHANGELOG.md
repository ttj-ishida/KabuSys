CHANGELOG
=========

すべての notable な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。
※日付はリポジトリ内のコード（バージョン表記等）から推測して記載しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-20
--------------------

Added
- 初期リリース。日本株自動売買システムのコア機能を追加。
- ポートフォリオ構築（pure 関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソートと上位 N 選出
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコア 0 の場合は等金額へフォールバック）
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を防ぐフィルタ
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: 等配分／スコア配分／リスクベースに基づく発注株数計算、単元株丸め、aggregate cap（スケーリング）
- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
    - BrokerClientFactory によるブローカークライアント生成
    - ExecutionEngine、OrderManager、RiskManager、Reconciler を組み立ててデーモンスレッドで起動
    - KABUSYS_ENV=paper_trading の場合は paper 専用 DB（デフォルト data/paper_trading.db）を使用し本番 DB と分離
    - 停止フラグ（data/stop_requested.flag）検知でグレースフル停止、pid ファイル管理
    - 起動時にプロセス優先度を "high" に設定
- 監視プロセス起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計
    - 停止フラグ検知でループ終了、例外時にログを残して次ポーリングへフォールバック
- 設定管理 / CLI
  - src/kabusys/config.py
    - Settings クラスによる環境変数ラッパー（多くの設定プロパティを提供）
    - .env 自動読み込み（プロジェクトルート検出、.env / .env.local）、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化
    - robust な .env パーサ（export 形式、クォートやエスケープ、インラインコメントの扱い）
    - PAPER_FILL_MODE 等の妥当性チェック
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援
  - src/kabusys/validate_config.py
    - .env および config/*.yaml の起動前検証 CLI（--strict オプションで警告を FAIL 扱いに）
- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging
    - stdout への StreamHandler（stdout を使用）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を追加
    - ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR に対応
  - src/kabusys/utils/process_priority.py
    - psutil を利用したクロスプラットフォームのプロセス優先度設定（Windows/Posix 対応）
    - CPU affinity 設定ヘルパ（set_cpu_affinity）
- 分析/検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト（稼働率、注文成功率、送信率、P95 レイテンシ等を算出）
    - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定
- データベース / 分析
  - DuckDB 接続を受け取って分析処理を行う設計（duckdb を利用）
  - 監視用 SQLite DB 初期化ヘルパ（monitoring_db の初期化呼び出し箇所あり）
- 研究用モジュール（未完/計画）
  - src/kabusys/research/factor_research.py
    - モメンタム等のファクター計算を行う設計。DuckDB の prices_daily / raw_financials を参照する想定（ファイル末尾で未完了箇所あり）
- パッケージ情報
  - __version__ = "0.1.0"

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- 環境変数取り扱いに関する注意書き（.env を絶対にコミットしない等）を config_setup に明記。

Notes / Design decisions
- Portfolio 系関数群は純粋関数（副作用なし）として実装され、テスト容易性と再利用性を確保。
- Paper Trading は本番 DB と完全分離される設計（PAPER_TRADING_SQLITE_PATH により上書き可能）。
- ログは標準出力（stdout）を基本とし、ファイルは日次ローテーションで保存。ログディレクトリ作成失敗時はコンソール出力のみで継続する。
- プロセス優先度や CPU affinity の設定は可能な範囲で行い、設定失敗時は警告を出してスキップする（権限問題等に寛容）。
- 停止制御はファイルベースのフラグ（data/stop_requested.flag）で行い、CLI や外部オーケストレーターから容易に制御できる。

参考
- 各 CLI スクリプトはモジュールとしても実行可能（python -m kabusys.<module>）。
- 既知の未完事項: research/factor_research.py の一部（ファイル末尾）が未完で、追加ファクター実装やテストが必要。