# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。重要な変更点を日本語でまとめています。

なお、本ファイルはコードベースから推測して作成しています。実際のコミット履歴・リリースノートと差異がある可能性があります。

## [Unreleased]

### Added
- run_monitoring 起動スクリプトを追加
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止制御に data/stop_requested.flag を使用。停止フラグ検知でループを終了。
  - 監視プロセスは KABUSYS_ENV に依存せず本番用 sqlite_path を使用して監視テーブルを初期化。
  - 起動時にプロセス優先度を "high" に設定。

- run_execution 起動スクリプトを追加
  - KABUSYS_ENV=paper_trading のときは paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
  - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
  - ExecutionEngine をバックグラウンドスレッドで実行。停止フラグ検知でエンジン停止・正常終了処理。
  - PID ファイルの記録・取り扱いをサポート。

- 環境設定（kabusys.config）を強化
  - プロジェクトルート探索による .env 自動読み込み（.git または pyproject.toml を起点）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサを拡張（export プレフィックス対応、クォート文字とバックスラッシュエスケープ、インラインコメント処理、保護された OS 環境変数の上書き防止）。
  - Settings に以下を追加/検証:
    - PAPER_FILL_MODE（instant/partial/never/reject）検証。
    - PAPER_TRADING_SQLITE_PATH。
    - kill_flag_clear_on_start、kill_flag_path、pid_file_path。
    - CPU/MEMORY/DISK のしきい値プロパティ（浮動小数）。
    - env と log_level の値検証（有効値チェック）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- process_priority ユーティリティを追加（kabusys.utils.process_priority）
  - set_process_priority(level) による Windows / POSIX（Linux, macOS, FreeBSD）での優先度設定。
  - set_cpu_affinity(cpu_count) による CPU アフィニティ固定機能。
  - 権限不足・未サポート環境では警告を出して安全にスキップ。

- Portfolio 構成モジュールを追加（kabusys.portfolio）
  - portfolio_builder: select_candidates（スコア降順、signal_rank によるタイブレーク）、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等配分へフォールバック）。
  - risk_adjustment: apply_sector_cap（セクター集中上限チェック、売却予定銘柄の除外対応）、calc_regime_multiplier（レジームに応じた投下資金乗数）。
  - position_sizing: calc_position_sizes（risk_based / equal / score の割付方式、lot_size による丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積もり、各種安全弁）。
  - すべて純粋関数（DB参照なし、メモリ内計算）。

- Paper Trading 検証レポートツールを追加（kabusys.tools.paper_verification_report）
  - CLI で期間指定（--from / --to）、または DB パス指定（--db）可能。
  - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを集計。
  - 事前定義された閾値に基づき PASS / FAIL を判定し、判定理由を出力。

- Research モジュールを追加（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value（DuckDB を用いた SQL ベース実装、各ファクター計算）。
  - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（スピアマン IC）、rank（同順位は平均ランク）、factor_summary（基本統計量）。
  - research パッケージ __init__ で zscore_normalize 等を再エクスポート。

- AI ニュース NLP モジュールを追加（kabusys.ai.news_nlp、実装途中含む）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントの銘柄別スコア付け機能を実装。
  - タイムウィンドウ計算（JST 基準、UTC 変換）を行う calc_news_window を提供。
  - score_news 関数（バッチ処理、チャンクサイズ、トークン肥大化対策、リトライ/バックオフ、レスポンス検証、スコアクリップ、テーブル更新方針）を実装（コード末尾で途中切れあり、処理フローの説明あり）。

- パッケージメタ情報: パッケージ __version__ = "0.1.0" を設定。

### Changed
- 監視関連初期化を明示化
  - run_execution/run_monitoring 共に init_monitoring_db を呼んで監視テーブルの存在を保証（冪等）。
- プロセス優先度設定を起動直後に実行するよう統一（run_execution / run_monitoring）。
- .env 読み込みロジックを堅牢化（引用符やエスケープ、コメント処理を改善）。

### Fixed
- .env パーサの不正行・コメント処理を強化。export 付き行やクォート内のエスケープを正しく解釈するよう修正。
- environment 取得・検証周りの入力検証を追加（無効な値は早期にエラー化またはフォールバック）。

---

## [0.1.0] - 2026-04-17

注: パッケージの __version__ に基づく初期バージョン推定日を入れています（コードから推測）。

### Added
- 初回公開相当の機能群を実装:
  - 実行コンポーネント: ExecutionEngine 起動スクリプト、注文管理（OrderRepository / OrderManager）、リスク管理（RiskManager）、Reconciler。
  - 監視コンポーネント: SystemMonitor ポーリング起動スクリプト run_monitoring。
  - ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター上限・レジーム調整。
  - リサーチ機能: ファクター計算（モメンタム/ボラティリティ/バリュー）、将来リターン計算、IC 計算、統計サマリー。
  - ユーティリティ: .env 自動読み込み、環境設定ラッパー（Settings）、プロセス優先度設定ユーティリティ。
  - ツール: Paper Trading 検証レポート生成スクリプト。
  - AI 連携の下地: ニュース NLP スコアリングのためのモジュール骨格（OpenAI 経由のスコアリングロジックの実装開始）。

### Changed
- （初期リリースのため特記事項なし）

### Fixed
- （初期リリースのため特記事項なし）

---

備考:
- AI ニュースモジュールは API キー取得・エラーハンドリング・DB 書き込みロジック等、細部でフェイルセーフや部分的実装が見受けられます（コード末尾が切れているため、実運用前に完全実装とテストを推奨します）。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後は動作環境での検証を推奨します（パッケージ化/インストール後のパス振る舞いに注意）。
- 実際のリリース日やタグ名はリポジトリのコミット履歴に基づいて決定してください。