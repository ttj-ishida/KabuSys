# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
慣例: 重大リリース / 機能追加 / 修正等を項目ごとに分類しています。

※ 内容はソースコードから推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-21

### Added
- 初期リリース: KabuSys 日本株自動売買システムのコア実装を追加。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト。スレッドでエンジンを起動し、stop フラグ / PID ファイルを扱う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
- 設定・環境管理
  - config.py: .env の自動ロード（.env / .env.local）と設定値取得用 Settings クラスを提供。各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABUSYS_ENV、PAPER_FILL_MODE 等）とデフォルト値・検証を実装。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加（--env-file で保存先指定可）。
  - validate_config.py: 起動前の設定検証 CLI（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスと config/*.yaml の存在・パース確認、live 環境に対するガード等）。
- Execution コンポーネント（設計に基づく組立て）
  - BrokerClientFactory（ブローカークライアント生成：paper_trading 時は MockBrokerClient を使用）
  - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（リスク設定を含む）
  - Paper trading 用に本番 DB と分離された data/paper_trading.db を利用する仕組みを追加。
- 監視（Monitoring）
  - monitoring_db.init_monitoring_db の呼び出しにより監視テーブルの初期化を保証。
  - SystemMonitor の単発チェック（check_once）をポーリングループで定期実行。
  - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を用いる（設計による監視の一元化）。
- ポートフォリオ構築（Portfolio）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank を利用）。
    - calc_equal_weights / calc_score_weights: 重み算出（スコア合計が 0 の場合は等分配へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用して候補をフィルタ。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）を実装。未知レジームは 1.0 でフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: 投下株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した保守的見積りなど。
- ユーティリティ
  - utils.logging_setup: ルートロガーの初期化ユーティリティ。コンソール（stdout）と日次ローテートファイル出力を統一設定。ログディレクトリ作成失敗時はフォールバック。
  - utils.process_priority: プラットフォーム差分を吸収したプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity の簡易設定。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプト。稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等を集計して PASS/FAIL 判定を出力。引数で期間指定（--from / --to / --db）可能。
- research.factor_research: DuckDB を用いたファクター計算基盤（モメンタム / MA200, ATR などの計算予定）を追加（実装の一部まで含む）。

### Changed
- ログ出力の標準化: logging_setup で stdout を使用する設計にして、コンソール出力とログファイル出力を統一。
- .env 自動ロードの振る舞い:
  - OS 環境変数優先、次に .env、.env.local（.env.local は既存キーを上書き）という順序で自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動ロードを無効化可能。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL により上書き可能。無効な値（0 以下や非数）の場合はデフォルト 60 秒にフォールバックし警告を出力。
- run_execution は paper_trading モード時に paper_sqlite_path を使用して本番 DB と完全分離（安全設計）。
- validate_config は PyYAML 未導入時に YAML 検証をスキップして警告を出す（柔軟化）。
- process_priority の実装は例外を捕捉し、権限不足等で失敗した場合はログ警告でスキップするように変更（起動失敗を防ぐ）。

### Fixed
- .env パーサーの堅牢化:
  - export プレフィックス対応、クォート（シングル/ダブル）のバックスラッシュエスケープを正しく処理。
  - クォート無しの値に対するインラインコメント処理を改善（'#' 前がスペース/タブの場合にコメント扱い）。
- run_monitoring / run_execution における DB 接続の finally ブロックで接続を確実にクローズするように修正（リソースリーク防止）。
- logging_setup: ログディレクトリ作成やファイルハンドラ作成に失敗した場合、例外で処理を止めずにコンソール出力のみで継続するように修正。
- position_sizing の aggregate スケーリングで残余キャッシュ分を優先度に従って lot_size 単位で再配分するロジックを実装し、より効率的な配分を実現。

### Security
- 重要なシークレット類（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN）は .env に保管し、config_setup にてシークレット入力をマスク表示する流れを提供。README 等への取り扱い注意の明記を推奨。

### Known issues / Notes
- research.factor_research の一部関数がソース上で途中（ファイル末尾で切れている）になっており、ファクター計算の完全実装が未完。追加実装が必要。
- 一部の TODO（例: position_sizing の将来的な lot_size 拡張や price フォールバック）が残っている。
- monitor / execution の停止はプロジェクトルートの data/stop_requested.flag によるファイルベースの制御を行う設計。運用時は stop/kill フラグの適切な取り扱い（ファイルパーミッション・自動クリア設定等）に注意。

---

この CHANGELOG はソースコードからの推測に基づくため、実際のコミット履歴と差異がある場合があります。必要であれば、特定ファイルや機能ごとにより詳細な変更点（設計意図・既知の制約・将来の改善案）を追加します。どの形式（例: Git のコミット一覧に基づく正確な CHANGELOG）で出力するか指定いただければ、さらに調整できます。