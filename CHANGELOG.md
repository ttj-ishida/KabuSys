CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog"（https://keepachangelog.com/ja/1.0.0/）に準拠します。

Unreleased
----------

（現時点では未リリースの差分はありません。）

0.1.0 - 2026-04-18
------------------

Added
- 実行スクリプトを追加/整備
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。KABUSYS_ENV が paper_trading の場合は paper 用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全分離する設計。エンジンはデーモンスレッドで実行され、 data/stop_requested.flag を検知して安全にシャットダウンする。実行時にプロセス優先度を "high" に設定し、PID ファイルを管理する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視モジュールは環境にかかわらず本番 sqlite_path を使用する（監視 DB 初期化処理あり）。stop フラグ検出や check_once() の例外ハンドリングを行う。

- 設定関連
  - config.py: 環境変数・設定管理モジュールを実装。プロジェクトルートを .git / pyproject.toml で探索して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。.env パースは export プレフィックス、クォート（エスケープ含む）、インラインコメントの取り扱いに対応。Settings クラスで各種設定値（DB パス、API トークン、Paper Trading の挙動など）をプロパティとして提供。
    - PAPER_FILL_MODE の有効値制約（instant / partial / never / reject）
    - KABUSYS_ENV の有効値検査（development / paper_trading / live）
  - settings オブジェクトを提供。

- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を実装。シークレット値はマスク表示、選択肢やデフォルトをサポートし、最終的にテンプレートコメント付きの .env を書き込む。
  - validate_config.py: 起動前の設定検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ検査、config/*.yaml の存在と（PyYAML がある場合は）パース検査、KABUSYS_ENV=live 時の追加ガードを実施。--strict オプションで警告も失敗扱いにできる。

- ロギング/プロセス制御ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを実装。stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR 作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定ユーティリティを実装。Windows と POSIX（Linux/macOS/FreeBSD）を吸収し、nice 値／Windows 優先度クラスを切り替え。CPU affinity 設定もサポート（set_cpu_affinity）。

- ポートフォリオ構築ライブラリ (純関数群)
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルを score 降順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア重み配分を実装。スコアが全て 0 の場合は等分配にフォールバックして警告出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェックに基づき新規候補をフィルタリング（売却予定銘柄は露出計算から除外、"unknown" セクターは適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（既知以外は 1.0 でフォールバック、警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に従い、lot_size（単元）に丸めた発注株数を算出。per-position 上限・aggregate cap（available_cash）・cost_buffer（手数料/スリッページ見積）を考慮したスケールダウン処理を実装。risk_based ではリスク量・ストップロスに基づく算出。

- 解析/リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨組みを実装（モメンタム、MA、ATR、流動性等の計算を想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを生成する設計。

- ユーティリティ/ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを実装。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計し、閾値に基づいて PASS/FAIL を判定・出力する。P95 計算や期間フィルタ（ISO8601 形式）に対応。DB パスは引数 --db、環境変数 PAPER_TRADING_SQLITE_PATH、デフォルトの順で解決。

Changed
- パッケージ公開情報
  - __init__.py に __version__ = "0.1.0" を追加（初回バージョン）。

Fixed
- 再現性・堅牢性向上
  - logging_setup: 既存ハンドラを flush/close のうえ安全にクリアしてから再設定する処理を実装し、二重ハンドラ設定を防止。
  - config の .env ロード: OS 環境変数を保護するため protected セットを導入し、.env.local の override を安全に実行する仕様に。

Security
- .env 取り扱い上の注意
  - config_setup の .env ヘッダに "絶対に Git にコミットしないこと" を明示。シークレット項目はウィザードでマスク表示。

Notes / 内部メモ
- Monitoring と Execution の DB 関連
  - 監視（run_monitoring）は "本番の" sqlite_path を使用して監視テーブルを初期化する（環境に依らず監視対象は一元管理する想定）。
  - Execution は paper_trading 環境であれば paper_sqlite_path を使用して注文ログ等を完全分離する。
- 将来的な改善点（TODO）
  - portfolio.risk_adjustment.apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価）を用いたエクスポージャー推定の追加検討。
  - position_sizing: 銘柄ごとの lot_size を stocks マスタに持たせる設計への拡張。
  - research/factor_research: ファクタ計算関数群の完全実装と単体テスト追加。

Acknowledgments
- このリリースはプロジェクトの初期実装をまとめたもので、監視、実行、設定管理、ポートフォリオ構築、レポーティング、ユーティリティなど自動化取引システムに必要な主要コンポーネントを含みます。

---