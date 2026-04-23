# Changelog

すべての重要な変更を Keep a Changelog の形式で記録します。
このファイルでは主にコードベースの初期リリース内容を推測して記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 今のところ特に未リリースの変更はありません。

## [0.1.0] - 2026-04-23
初回公開リリース。以下の主要コンポーネントと機能を含みます。

### 追加
- 実行・監視用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用に分離した SQLite（data/paper_trading.db をデフォルト）を使用。
    - 起動前にプロセス優先度を "high" に設定し、停止フラグ（data/execution.pid / data/stop_requested.flag）を監視して安全に停止可能。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバック。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する（ローカル開発でも本番 monitoring DB を参照する挙動）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 環境設定関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツール。
    - J-Quants / kabu API / DB パス / LOG_LEVEL / Kill Switch 等の設定を対話的に行える。
  - validate_config.py
    - .env および config/*.yaml の基本整合性を起動前にチェックする CLI。
    - --strict モードで警告も失敗扱いにできる。
- ログ・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - stdout に StreamHandler、日次ローテーション（30日保持）のファイルハンドラをルートロガーに設定。
    - LOG_DIR（引数 or 環境変数）を解決・作成できない場合はファイルハンドラをスキップし、コンソール出力のみで継続。
    - デフォルトログディレクトリ: logs/、デフォルトレベル: INFO。
  - utils/process_priority.py
    - Windows / POSIX (Linux/Mac/FreeBSD) を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を指定コア数に固定する set_cpu_affinity を提供（失敗時は警告を出してスキップ）。
    - psutil の権限エラーを安全にハンドリング。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア重み配分を計算。全スコアが 0 の場合は等分にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限に基づき候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation method（risk_based / equal / score）に基づいて発注株数を計算。単元株丸め、1銘柄上限、aggregate cap のスケーリング、cost_buffer による保守見積りなどを実装。
- Research（分析）基礎
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity といったファクターの計算を想定したモジュールを追加（DuckDB 接続を受け取り prices_daily 等のテーブルを参照する設計）。
    - モメンタム (1M/3M/6M)、MA200 乖離、ATR、出来高指標等の計算方針を記載。実装の一部が開始されている（部分実装の可能性あり）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計し、稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出してレポート出力。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL 判定を行う。
- 設定管理
  - config.py
    - .env の自動読み込み（プロジェクトルートから .env/.env.local を読み込む）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パース機能強化（export プレフィックス、引用符あり/なしの処理、インラインコメント処理）。
    - Settings クラスを追加し、J-Quants トークンや KABU API 設定、DB パス、各種閾値、KABUSYS_ENV のバリデーション等のプロパティを提供。
    - PAPER_FILL_MODE の受け付け値検証 (instant|partial|never|reject)。
    - paper_sqlite_path, pid_file_path, kill_flag_path, kill_flag_clear_on_start 等の設定プロパティを提供。

### 変更
- ロギングの既定動作
  - ログ出力は stdout に統一（cron 等からの起動時のリダイレクト運用を考慮）。
  - ログディレクトリ作成に失敗した場合でもプロセスを停止させずに stdout のみで継続するよう堅牢化。
- 実行/監視プロセスの優先度
  - 起動時に set_process_priority("high") を呼び出してプロセス優先度を上げるように統一。

### 修正（注意点 / フォールバック）
- 環境変数の堅牢性
  - MONITOR_POLL_INTERVAL の不正値（ゼロや文字列など）を検出し、警告出力のうえデフォルト（60秒）にフォールバックするようにした。
  - PAPER_FILL_MODE の不正値は ValueError を投げるようにして早期検出。
- DB 周りの安全性
  - run_execution/run_monitoring で init_monitoring_db を呼び出し、監視テーブルが存在することを冪等的に保証。
  - run_execution は停止フラグが既に立っている場合は起動せず終了するガードを追加。
- 例外ハンドリング
  - run_monitoring の主ループで monitor.check_once() が例外を投げてもループを継続し、例外スタックトレースをログに残して次ポーリングまで待機するようにした。
  - process_priority / set_cpu_affinity は権限エラーや未対応 OS を安全にハンドリングして警告ログを出力する。

### 既知の制約・TODO（ドキュメント的補足）
- research/factor_research.py は設計方針と一部関数の開始実装を含むが、完全実装（全ファクターの SQL 実装や境界ケースのハンドリング）は継続作業が必要。
- position_sizing の lot_size 将来的拡張: 銘柄別単元対応の拡張を予定（現状は全銘柄共通の単元を想定）。
- apply_sector_cap は price_map に欠損（0.0）があるとエクスポージャーが過少見積りされる注記があり、今後フォールバック価格導入を検討。

---

著者注: 本 CHANGELOG はコード内容から推測して作成しています。実際の変更履歴やリリース日、影響範囲はリポジトリのコミット履歴やリリースノートと照合してください。