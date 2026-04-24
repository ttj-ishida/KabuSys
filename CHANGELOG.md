CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-24
-------------------

Added
- 基本アプリケーションの初期実装を追加しました（バージョン 0.1.0）。
- 起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプトを追加。プロセス優先度を "high" に設定し、スレッドでエンジンを起動・監視します。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離する設計を導入。
    - 停止フラグ（data/stop_requested.flag）を監視し、検知時にエンジンを安全に停止します。PID ファイル（data/execution.pid）を管理。
  - src/kabusys/run_monitoring.py
    - システム監視ループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path（data/monitoring.db デフォルト）を使用する仕様。

- 設定管理・ユーティリティ
  - src/kabusys/config.py
    - 環境変数・設定読み込み機能を実装。プロジェクトルートを自動検出して .env/.env.local を読み込み（上書きルールあり）。
    - .env の自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを実装し、J-Quants や kabu API、各種パス、監視閾値、環境判定ユーティリティなどをプロパティ経由で提供。
    - PAPER_FILL_MODE（paper_trading の MockBroker の fill モード）に対する検証（instant/partial/never/reject）。
  - src/kabusys/config_setup.py
    - 対話式 .env 作成ウィザードを追加。既存 .env 読み込み、項目ごとの説明／デフォルト、シークレットマスク表示、保存確認を実装。
    - .env に書き込むテンプレートを整備（J-Quants / kabu / DB / LINE / ログ / Kill Switch 等）。
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml を検査する CLI を追加。必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、PyYAML があれば YAML のパース検証、live 環境向けの追加警告等を実装。
    - --strict モードで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なログ設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順や、ファイルハンドラ作成失敗時のフォールバック処理を実装。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定と CPU affinity ユーティリティを実装。set_process_priority("high"|"normal"|"low")、set_cpu_affinity() を提供。
    - 権限不足等の例外は警告として扱い処理を継続。

- ポートフォリオ構築モジュール
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap を追加。既存ポジションと価格情報を基にブロック対象セクターを除外。
    - レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。未知レジームは 1.0 でフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元（lot_size）、stop_loss、max_position_pct、max_utilization、cost_buffer を考慮した株数計算、aggregate cap によるスケーリングと残差配分アルゴリズムを備える。

- 研究・分析ツール
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールの骨組みを追加。モメンタム、MA200、ATR、出来高等の計算を想定した定数や関数（calc_momentum など）を配置（DuckDB 経由で prices_daily, raw_financials を参照する設計）。
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート出力スクリプトを追加。期間指定可能（--from/--to）、P95 や成功率・送信率・稼働率の算出と PASS/FAIL 判定を実装。デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 latency 200ms）。
    - PAPER_TRADING_SQLITE_PATH 環境変数／--db オプションで DB パス指定可能。

- パッケージ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Notes / 補足
- 環境変数関連
  - .env のパースはシングル／ダブルクォートや export プレフィックス、インラインコメントの扱いに対応。override 時には OS の既存環境変数を保護します。
  - 自動ロード順序: OS 環境 > .env.local > .env。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - 監視ループのポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（正の整数で、無効値はデフォルト 60 秒にフォールバック）。
  - Paper Trading 関連: PAPER_FILL_MODE（instant/partial/never/reject）、PAPER_TRADING_SQLITE_PATH により本番データと分離。

- ログ
  - デフォルトログディレクトリは logs/。LOG_DIR を使って変更可能。ログは標準出力 (stdout) と日次ローテートファイル出力の両方に出力されます。

- 実行制御
  - 停止フラグ（data/stop_requested.flag）や PID ファイルを用いた安全な起動・停止に対応。

開発者向けメモ
- validate_config は PyYAML が未インストールの場合でも動作し、YAML 検証はスキップされます（警告発行）。
- position_sizing の将来的な拡張点として、銘柄別の lot_size を stocks マスタに持たせる案がコメントで残されています。
- factor_research モジュールは DuckDB を利用する設計のため、prices_daily/raw_financials テーブル準備が前提です。

---