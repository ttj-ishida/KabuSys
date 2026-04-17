# CHANGELOG

すべての注目すべき変更を記録します。このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の方針に沿って管理されています。

## [0.1.0] - 2026-04-17 (Initial release)

### Added
- 基本パッケージ初版を追加。
  - パッケージ情報: kabusys/__init__.py にて __version__ = "0.1.0" を定義。

- 実行系・監視用エントリポイントを追加。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/ RiskManager/Reconciler の組み立て、別スレッドでの engine.run_session 実行と停止フラグ監視を実装。
    - 起動前に data/execution.pid 等の PID / stop フラグを参照する挙動を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視は常に本番 DB を参照する設計）。

- 設定・環境読み込みユーティリティを追加。
  - config.py
    - プロジェクトルート自動検出（.git or pyproject.toml を基準）による .env 自動読み込み（優先度: OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理等をサポート。
    - Settings クラスで各種設定値をラップ（DB パス、PID/kill フラグパス、閾値、env/log_level 判定、paper_trading 用設定など）。
    - PAPER_FILL_MODE の入力検証、KABUSYS_ENV/LOG_LEVEL の検証を実装。

- ポートフォリオ構築ロジック（純関数群）を追加。
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。unknown セクターは上限判定対象外、未知レジームはフォールバックで 1.0 を返し警告ログを出力。
  - portfolio/position_sizing.py
    - 各種配分方式 ("risk_based" / "equal" / "score") に基づく株数算出を実装。
    - 単元株(lot_size) 丸め、per-stock 上限、aggregate cap によるスケールダウン、余りのロット配分ロジック、cost_buffer による保守的見積りを実装。

- 研究（Research）モジュールを追加（DuckDB ベース）。
  - research/factor_research.py
    - Momentum / Volatility / Value の各ファクター計算を実装（prices_daily / raw_financials を参照）。
    - 長期移動平均や ATR 等のウィンドウ処理を DuckDB SQL で効率的に実行。
  - research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC（calc_ic）および基本統計量要約 (factor_summary) を実装。pandas 等の外部依存を使わずに純 Python 実装。
  - research/__init__.py により公開 API を整理。

- ユーティリティを追加。
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定 set_process_priority(level)（Windows / POSIX を吸収）と set_cpu_affinity(cpu_count) を実装。権限不足や未対応 OS はログ警告でスキップ。

- 運用ツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプト。コマンドライン実行可能 (python -m kabusys.tools.paper_verification_report)。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどを集計し PASS/FAIL 判定を行うデフォルト閾値を定義。
    - --from/--to/--db オプションに対応。DB 存在チェックや SQL エラーに対するフォールトトレランスを実装。

- AI ニュース NLP モジュール（初期実装）を追加。
  - ai/news_nlp.py
    - raw_news / news_symbols を前提に、OpenAI (gpt-4o-mini) を用いた銘柄別センチメントスコアリング処理の設計と多くの実装を追加。
    - タイムウィンドウ計算 calc_news_window、API キー解決、トークン肥大化対策、リトライ/バックオフ方針、スコアのクリップ等を実装。
    - （注）ファイル末尾が切れており score_news の一部が未完・実装継続予定。部分実装として追加。

- DB 初期化ユーティリティ利用。
  - 監視テーブル初期化のため monitoring_db.init_monitoring_db を run_monitoring と run_execution で呼び出す（冪等に実行）。

### Changed
- 監視と実行のプロセス起動時にプロセス優先度を最初に High に設定するように変更（set_process_priority("high") を追加）。
- run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を参照する明示的な設計とした（監視は本番データ前提）。
- run_execution は paper_trading 環境時に paper_sqlite_path を使って DB を完全分離する仕様を追加。

### Fixed
- .env パーサの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、行内コメント処理など様々な .env 形式に対応し、誤読を減らす実装改善を行った。

- position_sizing のスケーリング周りの詳細ロジックを実装（aggregate cap のスケールダウンと余り配分ロジックなど）し、available_cash 超過時の挙動を整備。

### Deprecated
- なし

### Removed
- なし

### Security
- なし（公開鍵・認証まわりの変更は含まれていない。ただし OpenAI API キーは環境変数または明示引数で受け取り、未設定時はエラーを投げる設計）

---

注意事項 / 既知の制約
- ai/news_nlp.py の score_news 実装がファイル末尾で切れており、完全実装には追補が必要です（API 呼び出し周り・結果書き込み処理の完了を要する）。
- run_monitoring の監視対象 DB が常に本番 sqlite_path を参照する点は意図的な設計です。開発環境で監視データを分離したい場合は別途設定や実行ラッパーが必要です。
- process_priority/set_cpu_affinity は権限や OS に依存するため、環境によってはスキップされることがあります（警告ログで通知）。
- Portfolio の lot_size は現状グローバル共通の想定（将来的に銘柄別拡張を想定した TODO を含む）。

今後の予定（短期）
- ai/news_nlp.score_news の残り実装（OpenAI 呼び出し、レスポンス検証、ai_scores 書き込み処理）。
- テスト追加（ユニット/統合）および CLI/ドキュメントの拡充。
- ポートフォリオ/ポジションサイズの銘柄別 lot_size 対応などの改善。

--- 

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴・バージョン運用方針に合わせて適宜修正してください。）