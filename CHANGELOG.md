CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、Semantic Versioning を想定しています。

Unreleased
----------
- 進行中 / TODO
  - research/factor_research.py が途中で切れており（start_da より続きが未実装）、ファクター計算モジュールの完全実装が残っています。
  - position_sizing や risk_adjustment にいくつかの注記（TODO: lot_size の銘柄別対応、価格フォールバック処理等）があり、今後の改善候補として残されています。

0.1.0 - 2026-04-18
------------------

Added
- 初回公開（ベース機能群を実装）
  - 実行用スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアントの生成、OrderManager/RiskManager/Reconciler の組み立て、スレッドでのエンジン実行、停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル出力（data/execution.pid）などを実装。
      - KABUSYS_ENV=paper_trading 時に paper_trading 用 DB を使用する（settings.paper_sqlite_path により本番 DB と完全分離）。
  - 監視用スクリプト
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知でループを終了。Monitoring は環境にかかわらず本番 sqlite_path を使用し、監視用 DB 初期化を行う。
  - 設定関連 CLI
    - config_setup.py
      - .env 初期作成・更新の対話型ウィザードを追加。秘密値マスク表示、デフォルト値や選択肢の提示、確定後に .env を生成。
    - validate_config.py
      - .env と config/*.yaml の簡易検証ツールを追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリチェック、PyYAML があれば YAML のパース検証も行う。--strict フラグで警告を失敗扱いにできる。
  - 設定・環境管理
    - config.py
      - .env 自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml を基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - 複雑な .env 行パーサを実装（export プレフィックス対応、クォート中のエスケープ、インラインコメント処理、上書き保護など）。
      - Settings クラスを提供し、各種環境設定（DB パス、API トークン、PAPER_FILL_MODE のバリデーション、閾値、PID/kill flag パス 等）をプロパティとして安全に取得可能。
  - ポートフォリオ構築ライブラリ
    - portfolio/portfolio_builder.py
      - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全 0 の場合は警告を出して等金額にフォールバック。
    - portfolio/risk_adjustment.py
      - セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のセクター/レジームに対するフォールバックやデバッグログを提供。
    - portfolio/position_sizing.py
      - 株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮した配分アルゴリズム、残差処理による追加配分を含む。
  - ユーティリティ
    - utils/logging_setup.py
      - ルートロガー初期化ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力（logs/<app_name>.log）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続。
    - utils/process_priority.py
      - クロスプラットフォームなプロセス優先度設定（Windows の priority class / POSIX の nice 値）、および set_cpu_affinity を実装。権限不足や未対応 OS では警告を出して安全にスキップ。
  - モニタリング DB 初期化
    - monitoring/monitoring_db.init_monitoring_db を利用して監視テーブルが存在することを保証（冪等に実行）。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ指標（平均・最大・P95）等を集計してレポートを生成。基準値を定義し PASS/FAIL 判定を出力する。日付フィルタ/DB パス指定オプションあり。

Changed
- 実装/設計に関する注釈と安全装置を追加
  - run_monitoring / run_execution で起動直後にプロセス優先度を "high" に設定する挙動を明確化。
  - run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で調整可能、0 以下や不正値はログで警告しデフォルトにフォールバック。
  - logging_setup: 標準エラーではなく標準出力を StreamHandler に使用する方針に変更（cron 等でのリダイレクトを想定）。
  - config.py の env 自動ロードは OS 環境変数を保護する仕組み（protected set）を導入。

Fixed
- 堅牢性・安全性向上
  - ディレクトリ作成やファイルハンドラ作成に失敗した場合は明示的にログを出してフォールバック（ログ出力は継続）するように修正。
  - process_priority の未対応環境や権限不足での例外を捕捉して、アプリケーションの起動失敗を防ぐ。
  - ExecutionEngine 起動時に監視テーブルの存在を保証するため init_monitoring_db を呼び出し、初回起動時のテーブル不足での障害を回避。

Known Issues / Notes
- research/factor_research.py のモジュールは途中で実装が終わっており、完全なファクター計算パイプラインは未完成です（Unreleased に記載）。
- position_sizing の価格フォールバック（価格未取得時の扱い）や、将来的な銘柄別 lot_size 管理は TODO コメントとして残されています。
- PAPER_FILL_MODE の値は厳密に検証され、無効値は ValueError を送出します。運用環境では .env の設定に注意してください。
- .env パーサは複雑なケース（エスケープ、クォート、コメント）に対応していますが、極端に特殊なフォーマットは想定外の動作となる可能性があります。

ライセンス、貢献方法などはリポジトリルートの他ファイルを参照してください。