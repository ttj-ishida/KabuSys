CHANGELOG
=========

すべての変更は Keep a Changelog の方針に従って記載しています。
https://keepachangelog.com/ja/

Unreleased
----------

（現時点のコードベースに対する未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 初回公開リリース。
- 実行系 / 監視系の起動スクリプトを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用し、MockBrokerClient を利用する設計（本番 DB と完全分離）。
    - プロセス優先度を高く設定（起動時）。停止フラグ（data/stop_requested.flag）検出により安全停止。
    - PID ファイル管理（data/execution.pid）およびスレッドでのエンジン実行管理。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を利用する仕様。
    - 停止フラグ検出でループを終了。KeyboardInterrupt に対応。
- 設定関連ユーティリティを追加。
  - src/kabusys/config.py
    - プロジェクトルート自動検出（.git または pyproject.toml）。
    - .env 自動読み込み（.env, .env.local）と保護付き上書きロジック。
    - .env パース機能の強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理）。
    - Settings クラスに多数のプロパティを実装（DB パス、紙トレード設定、閾値、環境判定等）と値検証。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - 各種項目の説明、デフォルト、シークレット入力対応、保存前確認を実装。
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML パース（PyYAML が存在する場合）など。
    - --strict モードで警告も失敗扱いにできるオプションを実装。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし、メモリ計算）。
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレーク）、等配分・スコア加重配分の実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数算出、単元株丸め、aggregate cap（現金上限に応じたスケーリング）を実装。
- ユーティリティを追加。
  - src/kabusys/utils/logging_setup.py
    - ルートロガーの統一的設定ユーティリティ。
    - stdout 出力用 StreamHandler と 日次ローテート（TimedRotatingFileHandler）を併用、ログディレクトリ自動作成（失敗時はファイル出力をスキップ）。
  - src/kabusys/utils/process_priority.py
    - Windows/Linux/macOS に対応したプロセス優先度設定（psutil ベース）。
    - CPU affinity を設定するヘルパーも実装。
- ツール・レポートスクリプトを追加。
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツール。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - デフォルト DB パス: data/paper_trading.db。PAPER_TRADING_SQLITE_PATH 環境変数または --db で上書き可能。
- 研究用モジュール（骨組み）を追加。
  - src/kabusys/research/factor_research.py
    - ファクター計算（Momentum、Value、Volatility、Liquidity）のための設計と一部初期実装（calc_momentum などの計算方針・定数を含む）。
- パッケージ初期設定
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- ロギング挙動とデフォルトの出力先を統一。
  - stdout をメインストリームに使用することを明示（cron 等からの起動を考慮）。
  - ログはデフォルトで logs/<app_name>.log に日次ローテートで保存（最大30世代保持）。
- 実行系・監視系で起動直後にプロセス優先度を "high" に設定するように統一。
- run_execution と run_monitoring は起動時に監視テーブルの存在を保証するため init_monitoring_db を呼び出す（冪等）。

Fixed
- .env パースの不具合を修正（export 前置、引用符内のエスケープ、行末コメントの扱いなどに対応）。
- 設定ロードの安全性を向上（OS 環境変数を保護しつつ .env.local を上書き可能にするロジック実装）。

Notes / Documentation
- .env 自動ロードはデフォルトで有効。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要なデフォルトファイルパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH (監視用): data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID ファイル: data/execution.pid
- run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、1 以上）。
- Paper verification レポートの基準値:
  - 稼働率 >= 99.0%
  - 注文成立率 (fill_rate) >= 90.0%
  - 送信率 (send_rate) >= 95.0%
  - P95 レイテンシ <= 200 ms

Acknowledgements
- このリリースのコードは内部ユーティリティ（psutil, duckdb, sqlite3, logging 等）を利用しています。YAML のパースは PyYAML がインストールされている場合のみ config 検証に用いられます。

[0.1.0]: https://example.com/your-repo/releases/tag/v0.1.0