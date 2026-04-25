CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式で記載しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

- （現時点の作業ブランチに未リリースの変更はありません）

0.1.0 - 2026-04-25
-----------------

Added
- 基本アプリケーション構成を実装し初期リリースを追加。
  - パッケージ情報: kabusys.__version__ = 0.1.0
- 実行系 / 監視系の起動スクリプトを追加。
  - run_execution.py: ExecutionEngine の起動ロジック、ブローカーファクトリ経由の BrokerClient 作成、スレッド実行と停止フラグ（data/stop_requested.flag）による安全停止、pid ファイル管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）、停止フラグ検出処理。
- 環境設定関連 CLI を追加。
  - config_setup.py: 対話式ウィザードで .env の初期作成/更新を支援。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI（--strict オプションで警告を失敗扱いにできる）。
- Paper Trading 向けユーティリティを追加。
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、レイテンシ等を集計してレポート出力。閾値による PASS/FAIL 判定を実装（稼働率・成功率・P95 レイテンシ等）。
- ポートフォリオ構築ロジック（純粋関数群）を追加。
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap に応じたスケーリング、cost_buffer を考慮した保守的計算。
  - portfolio/risk_adjustment.py: セクター集中制限適用 (apply_sector_cap)、市場レジーム乗数 (calc_regime_multiplier)。
  - portfolio/__init__.py でこれらを公開。
- ロギング / プロセス制御ユーティリティを追加。
  - utils/logging_setup.py: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する汎用関数。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続する堅牢性を実装。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを提供。アクセス権限や未対応環境では警告を出してフォールバック。
- 設定読み込み・検証ロジックを整備。
  - config.py:
    - .env 自動読み込み機構（プロジェクトルートの検出: .git または pyproject.toml を基準）を実装。OS 環境変数を保護する仕組みを導入（.env.local を override 可能だが OS 環境変数は保護）。
    - .env パーサーは export KEY=val 形式、クォートやエスケープ、インラインコメントを考慮して堅牢に解析。
    - 各種環境変数用のプロパティ（パス、閾値、env 判定、paper_trading 用 DB パス、PAPER_FILL_MODE の妥当性チェック等）を実装。
    - settings インスタンスを提供。
- DuckDB / SQLite を用いたデータ層の初期接続処理を追加。
  - run_* スクリプトで duckdb 接続と sqlite3 接続を行い、監視用テーブルの初期化 init_monitoring_db を実行する設計（monitoring は環境に関わらず本番 sqlite_path を使用する点に注意）。
- research モジュールの雛形を追加。
  - research/factor_research.py: モメンタム / ボラティリティ / ライクイディティ / バリュー等の計算方針と定数を定義。DuckDB を使ったファクター計算を想定（calc_momentum 等を実装開始）。

Changed
- ロギングの設計方針: StreamHandler を stdout に向けることで cron/Task Scheduler 等からの標準出力運用に配慮。
- run_execution/run_monitoring の挙動:
  - 起動直後にプロセス優先度を high に設定する処理を追加（set_process_priority("high") を最初に呼ぶ）。
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と完全分離する挙動を明示。
  - run_monitoring は MONITOR_POLL_INTERVAL 環境変数を受け付けるようにし、不正値時はデフォルトにフォールバックして警告を出力。

Fixed
- 環境変数パースの堅牢化:
  - クォート文字内のバックスラッシュエスケープ、クォートなしでのインラインコメント認識（直前が空白の場合のみコメントと扱う）などをサポートし、.env の幅広い書式に耐えるよう改善。
- ログディレクトリ作成に失敗した場合でも起動続行できるようにし、ファイルハンドラ作成エラーはログに警告してコンソールのみで継続するフォールバックを実装。
- process_priority/set_cpu_affinity: 対応しない OS や権限不足のケースで例外を握り潰して警告し、プロセスを停止させない堅牢化を行った。

Security
- .env ファイルの生成ウィザードで作成された .env に対して「決して Git にコミットしない」旨のヘッダを追加。

Notes / Usage highlights
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途を想定）。
- デフォルトの DB/ログパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - デフォルトログディレクトリ: logs/
- run_monitoring は監視 DB に対して本番 sqlite_path を常に使用する設計（監視データは環境に依存させない）。
- run_execution は paper_trading 環境時に MockBrokerClient を使用し、ペーパートレードデータを paper_sqlite_path に記録して本番 DB と完全分離する想定。
- Paper Verification レポートの閾値（デフォルト）:
  - 稼働率 (uptime) >= 99.0%
  - 注文成立率 (fill rate) >= 90.0%
  - 送信率 (send rate) >= 95.0%
  - P95 レイテンシ <= 200 ms

Known issues / TODO
- research/factor_research.calc_momentum などの関数実装が途中（ファイル最後で cut-off 気味）。DuckDB ベースの計算ルーチンは引き続き実装が必要。
- position_sizing の価格欠損時のフォールバック（現状 price が 0.0 の場合にエクスポージャーが過小評価される可能性あり）は TODO コメントで記載。過去終値や取得原価を使ったフォールバックを検討する必要がある。
- 将来的な拡張: 銘柄毎の lot_size をサポートするため、stocks マスタに単元情報を持たせる設計への移行を想定。

Acknowledgements
- 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット単位・差分情報を基にしたものではありません。必要であれば Git の履歴（コミットメッセージ）からより正確な CHANGELOG を生成します。