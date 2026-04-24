Keep a Changelog 準拠の CHANGELOG.md（日本語）

すべての変更はセマンティックバージョニングに従います。  
詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------

（現在なし）

0.1.0 - 2026-04-24
-----------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading SQLite DB（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用するようサポート。
    - 起動時にプロセス優先度を "high" に設定する仕組みを追加（utils.process_priority）。
    - 停止フラグ（data/stop_requested.flag）を監視し、検出時はエンジンを安全に停止する。
    - 実行中は execution.pid に PID を書く（PID ファイルパスは設定で変更可）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値が与えられた場合はデフォルトにフォールバックし警告を出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明記（意図的な挙動）。
    - 停止フラグ（data/stop_requested.flag）を検出してループを退出する。
- 設定・環境管理
  - config.py: Settings クラスを追加。
    - 環境変数の取得をラッパー化し、各種設定（DBパス、API トークン、監視閾値、環境種別判定など）をプロパティとして提供。
    - .env の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env 読み込みの挙動: OS 環境変数は保護され、.env.local が .env をオーバーライド可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - PAPER_FILL_MODE（paper_trading 用の約定挙動）などの入力検証を追加。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 主要な設定項目の説明、秘密値のマスク表示、デフォルト値サポートを提供。
- 設定検証ツール
  - validate_config.py: 起動前に .env および config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェックを実装。
    - PyYAML が無い場合は YAML の検証をスキップして警告を出す。
    - --strict モードで警告を FAIL として扱うオプションを追加。
- ロギングとプロセス制御ユーティリティ
  - utils/logging_setup.py: 統一されたログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - 既存ハンドラをクリアして重複設定を防止。
    - LOG_DIR / LOG_LEVEL の環境変数を尊重し、ディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続。
  - utils/process_priority.py: psutil を用いたクロスプラットフォームのプロセス優先度設定ユーティリティを追加。
    - Windows, Linux/macOS 等を吸収する実装。設定失敗時は警告を出してスキップ。
    - CPU affinity 設定ヘルパー set_cpu_affinity も提供。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - 候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
    - スコアが全て 0 の場合は等配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py:
    - セクター集中上限を適用する apply_sector_cap を実装（既存保有のセクター別時価を計算して新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピング、未知の値は 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - risk_based / equal / score の各配分方式に対応した株数決定ロジックを実装。
    - lot_size（単元株）丸め、ポジション上限、投下資金合計（aggregate cap）のスケーリングロジックを備える。
    - cost_buffer を用いた保守的なコスト見積りと残余配分ロジックを実装。
- リサーチ（ファクター計算）モジュール
  - research/factor_research.py:
    - モメンタムや移動平均、ATR、流動性等のファクター計算設計（calc_momentum の骨組みと定数）を追加。DuckDB を用いた prices_daily / raw_financials 参照を想定した実装方針。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成立率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。
    - --from / --to / --db オプションをサポート。デフォルト DB は data/paper_trading.db。
    - P95 計算、各種閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
- その他
  - パッケージメタ情報: __version__ = "0.1.0"

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

注意・移行ガイド
- 監視 DB の挙動:
  - run_monitoring は設計上「環境にかかわらず」Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。開発 / 本番で別 DB を使いたい場合は環境変数 SQLITE_PATH を設定してください。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、Execution は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離されます。PAPER_TRADING_SQLITE_PATH で上書き可能。
- .env 自動読み込み:
  - プロジェクトルートの自動検出に失敗した場合は .env の自動読み込みをスキップします。自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で設定できます。不正な値（非数値、0 以下）は無視され、デフォルト 60 秒が使用されます。
- ロギング:
  - デフォルトで logs/<app_name>.log に日次ローテーションでログが保存されます。LOG_DIR 環境変数で変更可能。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

開発者向けメモ
- .env のパースは export プレフィックス、クォート値、インラインコメント（スペース/タブ直前の #）などに対応しています。OS 環境変数は保護され、.env.local は .env を上書きする設計です。
- process_priority は psutil に依存します。psutil が無い、あるいは権限不足の場合は警告を出して処理を継続します。

お問い合わせ
- 仕様や挙動に問題がある場合、issue を作成していただければ対応します。