# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。主要な初期リリースとして、機能追加とユーティリティ類を含むバージョン 0.1.0 を公開します。

全体方針:
- CLI、設定、ログ、プロセス制御、ポートフォリオ構築、検証ツール等の基盤機能を整備
- 本番/ペーパートレードのデータ分離や安全上のガードを意識した設計
- DuckDB / SQLite を用いた分析・監視基盤を提供

## [Unreleased]
（次回リリースに向けた変更はここに記載します）

## [0.1.0] - 2026-04-18

### Added
- 基本モジュール一式を追加
  - kabusys パッケージ（__version__ = 0.1.0）
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して paper_trading 専用 SQLite（data/paper_trading.db）に記録し、本番 DB と完全に分離。
    - 起動時にプロセス優先度を高く設定（set_process_priority("high")）。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視 DB の一貫性確保）。
    - stop flag と KeyboardInterrupt を監視して安全に終了。
- 設定管理
  - config.py
    - .env 自動ロード（.env と .env.local、OS 環境変数を保護）機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントなどに対応する堅牢な実装。
    - Settings クラスでアプリケーション設定をプロパティ経由で取得（DB パス、API トークン、監視閾値、環境判定など）。
    - PAPER_FILL_MODE（paper trading のフィルモード）を検証して有効値を保証。
- 設定補助 / 検証 CLI
  - config_setup.py
    - インタラクティブな .env 作成 / 更新ウィザードを提供。既存 .env の読み込み、シークレット項目のマスク、保存プレビューを実装。
    - 生成される .env のテンプレートを定義（マニュアルに沿ったセクション分け）。
  - validate_config.py
    - 起動前検証ツール。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在および（PyYAML があれば）パース検証、本番時のガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
    - --strict モードで警告も失敗扱いにできる。
- ロギング / プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを提供。
    - LOG_DIR 指定や作成失敗時はファイル出力をスキップして stdout のみで継続するフォールバックを実装。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows の priority class / POSIX の nice 値）と、CPU affinity 固定機能を提供。
    - 権限やプラットフォーム非対応時は警告を出して安全にスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選出。
    - calc_equal_weights / calc_score_weights: 配分重みの計算。スコア合計が 0 の場合は等金額配分にフォールバック（WARNING）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑えるフィルタ（既存ポジションからのセクター比率を計算して新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下倍率を返す（未知レジームは警告して 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株丸め、per-position / aggregate 上限、cost_buffer を考慮したスケーリングロジックを実装。
- 分析 / 研究ユーティリティ
  - research/factor_research.py（モジュール追加・モメンタム等の計算方針を実装）
    - DuckDB 接続を受け取り prices_daily / raw_financials を基にファクター計算を行う設計（モメンタム / MA200 / ATR / 流動性等）。
    - モジュールは純関数的に設計（DB 参照は DuckDB 接続経由のみ）。
    - （注）ファイル末尾で切れている実装箇所あり。今後のリリースで完全実装予定。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果の検証レポート生成 CLI を提供。P95 レイテンシ、稼働率、注文成功率、送信率、リスク却下数などを集計して PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db。--db オプション / 環境変数 PAPER_TRADING_SQLITE_PATH をサポート。
    - 判定閾値はファイル内定数で管理（稼働率 99%、注文成功率 90% など）。

### Changed
- 初期リリースのため、既存コードベースの整理・モジュール分割を実施
  - ログ設定やプロセス優先度設定を各種スクリプトから共通ユーティリティへ集約
  - 監視関連（monitoring_db 初期化呼び出し）を起動時に冪等に行うことでテーブル存在を保証

### Fixed
- .env パースの堅牢化
  - export プレフィックスやクォート内でのバックスラッシュエスケープ、行内コメントの扱い等の改善により、実運用での .env 誤解析を低減

### Security
- シークレット（J-Quants リフレッシュトークン、kabu API パスワード等）は Settings 経由で環境変数からのみ取得する方針を明記
- config_setup が生成する .env について「絶対に Git にコミットしないこと」を注釈として出力

### Notes / Usage highlights
- 重要な環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
  - KABUSYS_ENV: development / paper_trading / live（不正値は例外）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、1 以上）
  - PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 時に使用）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロード無効化（テスト用）
  - KILL_FLAG_CLEAR_ON_START: 本番での自動クリアは危険（validate_config で警告）
- ログ
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力。ディレクトリ作成に失敗した場合はコンソール出力のみで継続。
- 起動方法（例）
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - ペーパートレード検証: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

既知の TODO / 今後の改善点:
- research/factor_research.py の一部未完了箇所を完成させる（完全なファクター計算ロジックの実装）
- 銘柄毎の lot_size を考慮した拡張（stocks マスタからの単元情報取り込み）
- position_sizing の price 欠損時のフォールバック価格（前日終値 / 取得原価）処理の追加検討
- ExecutionEngine や SystemMonitor の詳細なユニットテストと E2E テスト整備

以上が今回の初期リリース（0.1.0）の主な変更点です。必要があれば、各ファイルごとの詳細な変更差分（関数単位の説明やサンプル使用例）も作成します。どの情報がさらに必要か教えてください。