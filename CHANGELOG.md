CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します（https://keepachangelog.com/ja/1.0.0/）。

Unreleased
----------

（現時点では未リリースの変更はありません。コードベースの状態は下の 0.1.0 にまとめています。）

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーション構成
  - パッケージのバージョンを __version__ = "0.1.0" として定義。
- 実行スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全に終了。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を設定。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時には専用の paper_trading DB を使用し MockBroker を利用（本番 DB と分離）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による制御を実装。
    - スレッドでエンジンを実行し、停止要求を検知して安全停止。
- 設定関連
  - config.Settings: 環境変数ベースの設定クラスを導入。
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、API トークン、ログレベル、KABUSYS_ENV 等をプロパティで取得。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - is_live / is_paper / is_dev ヘルパーを追加。
  - 自動 .env 読み込み機能:
    - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env, .env.local を自動読み込み（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - config_setup: 対話式 .env 作成ウィザードを追加（python -m kabusys.config_setup）。
    - デフォルト値・選択肢・機密項目マスク・保存機能を実装。
  - validate_config: 起動前の設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML があれば厳密に検証）。
    - --strict モードで警告をエラー扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコアで上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を提供（スコア全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を検出して候補を除外するロジックを実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に対する乗数を実装（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 各種配分方法（risk_based / equal / score）に基づく株数算出、単元（lot_size）丸め、aggregate cap によるスケール調整を実装。
    - 手数料・スリッページ反映用の cost_buffer、max_position_pct、max_utilization、stop_loss_pct、risk_pct 等のパラメータをサポート。
    - キャパシティ超過時のスケールダウンと残余配分処理を実装（端数処理に再現性あり）。
- 実行時ユーティリティ
  - utils.logging_setup:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（daily、30日保持）を設定する統一ロギング設定を提供。
    - LOG_DIR/LOG_LEVEL の環境変数や引数指定に対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみ実行。
  - utils.process_priority:
    - set_process_priority(set_cpu_affinity): Windows / POSIX の差異を吸収してプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティを提供。
    - 権限不足などの際は警告を出して安全にスキップ。
- 実行コンポーネントの組み立て（Execution）
  - run_execution にて BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み合わせて起動するフローを実装。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）をソース中に定義。
- 監視関連
  - run_monitoring が sqlite3 と duckdb 接続を確立し、init_monitoring_db により監視用テーブルを初期化。
  - SystemMonitor の check_once を定期実行して system_status 等を記録（例外発生はログに出力して次回まで待機）。
- Paper Trading 用検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計し、PASS/FAIL 判定付きレポートを標準出力。
    - 日付範囲指定 (--from / --to) と DB パス指定 (--db / 環境変数) に対応。
- research.factor_research（骨格）
  - DuckDB を用いたファクター計算モジュールの設計を導入（モメンタム、バリュー、ボラティリティ、流動性）。
  - 関数インターフェース（calc_momentum 等）と計算方針を記載（prices_daily/raw_financials を参照する想定）。

Changed
- 環境変数パースの改善
  - .env パーサーが export KEY=val 形式、クォート内のエスケープ、インラインコメントの取り扱い、クォートなしの # コメント判定（直前が空白の場合のみ）等に対応し堅牢化。
- ログ出力方針
  - StreamHandler を stdout に固定（cron/Task Scheduler 等でのリダイレクト運用を考慮）。

Fixed
- 起動時の DB 監視テーブル初期化を冪等に（init_monitoring_db を起動フローに組み込み）。
- run_execution が paper_trading 環境で本番 DB を誤って使用しないように分離（paper_sqlite_path 使用）。

Known issues / Notes
- research.factor_research の calc_momentum 関数はファイル末尾で途中（"start_da..." に断片あり）。完全実装が未完了の可能性あり。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的に価格フォールバック実装が推奨されている。
- position_sizing は単元株（lot_size）を全銘柄共通としている。将来的に銘柄別 lot_map への拡張予定（TODO コメント）。
- run_monitoring は監視用 DB に本番 sqlite_path を常に使用する設計のため、テスト環境での運用時は注意が必要。
- process_priority / set_cpu_affinity は権限不足や未対応 OS での例外を安全にハンドリングするが、期待通りに動作しない可能性のあるプラットフォームが存在する。

Security
- 機密情報（J-Quants リフレッシュトークン、KABU API パスワード等）は .env として管理することを推奨。.env は絶対にリポジトリにコミットしない旨を config_setup に明記。

Acknowledgements
- 仕様コメント（PortfolioConstruction.md / StrategyModel.md 等）に沿った設計方針で実装されていることを反映。

(注) 本 CHANGELOG は、提示されたソースコードの構造・コメントから機能・変更点を推測して作成したものです。実際のコミット履歴や差分情報に基づくものではありません。必要であれば、実際の Git 履歴やリリースノートに合わせて調整します。