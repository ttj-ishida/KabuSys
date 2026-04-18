CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
バージョン番号は src/kabusys/__init__.py の __version__ を基にしています。

Unreleased
----------

- 注意・既知の制限
  - research/factor_research.py は実装途中でファイル末尾が切れている箇所があります（計算ロジックの一部未完）。リサーチ機能の完全稼働には追加実装が必要です。
  - position_sizing.calc_position_sizes と risk_adjustment.apply_sector_cap に注釈（TODO）が残っています。価格欠損時のフォールバックや銘柄別単元対応などの改善余地があります。
  - ログディレクトリ作成やプロセス優先度設定は権限や環境によって失敗する可能性があり、失敗時は警告ログで継続する設計です。

0.1.0 - 2026-04-18
------------------

Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite を使用して本番データと完全に分離（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - ブローカークライアントを生成する BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、別スレッドで engine.run_session を実行。停止フラグ（data/stop_requested.flag）検出で安全停止。
    - プロセス優先度を "high" に設定する処理を起動直後に実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL により上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視 DB（SQLite）は Monitoring では常に本番 sqlite_path を使用する設計（env に依存しない）。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。
  - CLI / 設定周り
    - config.py
      - .env 自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を探索）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パース実装は export プレフィックス、クォート／エスケープ、インラインコメント等に対応。
      - Settings クラスで環境変数をラップし、各種プロパティ（DB パス、PID パス、しきい値、env 判定、paper_trading 用設定等）を提供。PAPER_FILL_MODE 等の値検証も実施。
    - config_setup.py
      - 対話式ウィザードによる .env 初期作成/更新ツール。既存 .env 読み込み、シークレット項目のマスク表示、確認後保存をサポート。
    - validate_config.py
      - .env と config/*.yaml の事前検証ツール。必須環境変数確認、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML パース検証を実施。
      - --strict オプションで警告を FAIL 扱いにできる。
  - ユーティリティ
    - utils/logging_setup.py
      - 全アプリケーションで共通利用するログ設定ユーティリティ。
      - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。既存ハンドラはクリアして重複出力を防止。
      - LOG_LEVEL / LOG_DIR の解決順とファイルハンドラ失敗時のフォールバック動作を実装。
    - utils/process_priority.py
      - psutil ベースで Windows/Linux/macOS を吸収するプロセス優先度設定。
      - set_process_priority(level) を提供（"high" / "normal" / "low"）。
      - set_cpu_affinity(cpu_count) により最初の N コアにピンニング可能。権限不足や未対応 OS では警告を出してスキップ。
  - ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
    - portfolio/portfolio_builder.py
      - select_candidates: buy シグナルをスコア降順でソートし上位 N を返す（同点時は signal_rank でタイブレーク）。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバックして警告）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、指定上限を超えるセクターの新規候補を除外。unknown セクターは上限を適用しない。
      - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull/neutral/bear をサポート、未知のレジームは警告後 1.0 にフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes: weight / candidates / portfolio_value / available_cash 等をもとに発注株数を計算。
      - 対応 allocation_method: "risk_based"（リスクベース） と "equal"/"score"。
      - lot_size（単元）を考慮した丸め、1銘柄上限・aggregate cap（利用可能現金を超えた場合のスケールダウン）・cost_buffer（手数料・スリッページ想定）対応。
      - スケーリング時の残差取り扱いや残余配分ロジックを実装し再現性を確保。
  - Paper Trading 向け検証ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から集計してレポートを出力。
      - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなど。
      - 閾値を定義して PASS/FAIL を判定（例: uptime >= 99%、fill_rate >= 90%、P95 latency <= 200 ms）。
      - 日付フィルタ（--from / --to）に対応。latency の P95 計算、NULL 耐性を備える。
  - パッケージメタ
    - src/kabusys/__init__.py にバージョン 0.1.0 を設定。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- （該当なし）

開発者向けメモ / TODO
- research/factor_research.py の続きを実装し、DuckDB 経由でのファクター計算パイプラインを完成させる必要があります。
- position_sizing の将来的拡張として、銘柄別 lot_size マッピング導入と価格欠損時のフォールバック（前日終値や取得原価）を検討してください（ファイル内に TODO コメントあり）。
- 本番環境（KABUSYS_ENV=live）での運用時は validate_config の警告を慎重に確認し、KILL_FLAG_CLEAR_ON_START の値に注意してください（デフォルト 0 推奨）。
- ログディレクトリ作成やプロセス優先度設定は実行環境の権限に依存します。コンテナ運用やサービスユーザー権限での動作確認を推奨します。

ライセンスや著作権の記載はリポジトリの他ファイルを参照してください。