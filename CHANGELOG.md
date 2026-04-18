# Changelog

すべての重要な変更は Keep a Changelog 規約に従って記載します。  
このファイルでは主にコードベースから推測される機能追加・設計仕様・既知の制約点をまとめています。

フォーマット:
- Unreleased: 今後の改善予定・未反映の TODO
- 各バージョン: リリース日に基づく主要な追加・変更・修正

## [Unreleased]

- 今後の改善予定（ソース内コメントや TODO に基づく）
  - position_sizing: 銘柄ごとの単元（lot_size）を銘柄マスタから取得する設計への拡張予定（現在は全銘柄共通の lot_size を想定）。
  - risk_adjustment.apply_sector_cap: 価格データ欠損時のフォールバック（前日終値や取得原価など）を追加し、エクスポージャー算出の過少見積りを改善する予定。
  - research/factor_research: ファクター計算モジュールの実装継続（ファイル終端が途中となっているため追加実装が必要）。
  - ロギング・ファイルハンドラ作成失敗時の挙動改善やより詳細な監視・アラート機能の拡張。
  - テスト・ドキュメント整備（各モジュールの単体テストと使用例の追加）。

---

## [0.1.0] - 2026-04-18

Added
- アプリケーションの初期リリース相当の機能群を追加。
  - 実行スクリプト
    - run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV により paper_trading 時は専用の SQLite（data/paper_trading.db をデフォルト）を使用する分離設計を実装。
      - プロセス優先度を高（"high"）に設定する仕組みを起動時に実行。
      - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）によるプロセス制御に対応。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てを実装。
      - RiskManager の既定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値をブローカーから取得して利用。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値の場合はデフォルトにフォールバックして警告を出力。
      - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用する設計（監視データの一元化）。
      - 停止フラグ（data/stop_requested.flag）検知でループを終了。
      - duckdb と sqlite の接続を確立して SystemMonitor に渡す。

  - 設定管理
    - config.py
      - Settings クラスを導入し、環境変数から設定を一元取得。
      - .env 自動ロード機能（プロジェクトルート検出: .git / pyproject.toml）を実装。`.env.local` は上書き可能。
      - 複数の設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、データベースパス、PAPER_FILL_MODE、paper_sqlite_path、PID/KILL フラグ周り、閾値など）。
      - env パースで引用符・エスケープ・コメント処理に対応するパーサを実装。
      - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを行い不正値では ValueError を送出。

  - 設定支援ツール
    - config_setup.py
      - 対話式ウィザードにより .env ファイルを生成・更新する CLI を追加。
      - 入力支援、既存 .env 読み込み、秘密情報マスク表示、保存前確認などを実装。
      - デフォルト値や選択肢の提示により初期セットアップを容易にする。
    - validate_config.py
      - 起動前に .env と config/*.yaml（存在する場合）の検証を行う CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV 検証、LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML 未インストール時はスキップ）を実装。
      - --strict オプションで警告をエラー扱いにする機能を実装。

  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: スコア降順で候補選定（タイブレークに signal_rank）。
      - calc_equal_weights / calc_score_weights: 等重・スコア加重の重み計算。全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限に基づき候補を除外する関数。売却予定銘柄を除外して既存エクスポージャーを算出。
      - calc_regime_multiplier: market レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す（未知値は 1.0 でフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
      - 単元丸め、1銘柄上限・aggregate cap のスケーリング、cost_buffer を考慮した保守的見積りを実装。
      - aggregate cap 超過時のスケーリングと端数再配分ロジックを実装。

  - ユーティリティ
    - utils/logging_setup.py
      - setup_logging を実装して全起動スクリプトで統一したログ設定を提供。
      - コンソール stdout ハンドラと TimedRotatingFileHandler（daily, 30 日保持）をルートロガーに設定。既存ハンドラをクリアして二重設定を防止。
      - LOG_LEVEL / LOG_DIR 解決、ファイルハンドラ作成失敗時のフォールバックを実装。
    - utils/process_priority.py
      - set_process_priority / set_cpu_affinity を実装して Windows / POSIX の差分を吸収。
      - psutil を利用し、権限不足や未対応 OS の場合は警告を出してスキップ。

  - 監視・テスト・レポート関連
    - monitoring モジュール初期化呼び出し（init_monitoring_db）を run_monitoring / run_execution 起動時に実行（監視テーブルを冪等に保証）。
    - tools/paper_verification_report.py
      - Paper Trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）から期間レポートを生成する CLI を追加。
      - 指標: 稼働率（uptime %）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数。
      - 判定基準（閾値）を定義し、PASS/FAIL 判定を出力。
      - 日付フィルタ (--from/--to)、--db オプションを提供。

  - パッケージ初期情報
    - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- N/A（初回相当の追加のため変更履歴は無し）

Fixed
- N/A（明示的なバグ修正の履歴はコードからは検出できず）

Security
- .env ファイルは絶対に Git にコミットしない旨を config_setup の出力テンプレートに明記。

Notes / 実装上の注意点
- 環境変数の自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。プロジェクトルートが見つからない場合は自動ロードをスキップする。
- PAPER_TRADING は本番 DB と完全に分離される設計（paper_sqlite_path が使用される）。
- run_monitoring は監視用に常に本番 sqlite_path を使用する（環境に依存しない監視データの一元化）。
- position_sizing 等は価格欠損時にスキップする（ログ出力はあるが、価格フォールバックは未実装）。
- process_priority や CPU affinity の設定は権限不足や未対応環境で失敗する可能性があるため安全にフォールバックする実装。
- YAML 検証は PyYAML が未インストールだとスキップされる（警告表示）。

参考: 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒。デフォルト: 60）

---

作成者注:
上記の CHANGELOG はリポジトリ内のソースコードとコメントから推測して作成しています。実際のリリースノートとして利用する場合は、コミット履歴やリリース単位の変更点（実装者の意図）に基づいて補正してください。