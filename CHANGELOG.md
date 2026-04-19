CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。

Unreleased
----------

注: パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています。本CHANGELOGは今回提供されたコードベース（初回リリース相当）の機能追加・設計方針をまとめたものです。

Added
-----

- 全体
  - プロジェクトの初期実装を追加。モジュール構成は実稼働用の Execution / Monitoring、ポートフォリオ構築、設定関連ユーティリティ、ログ設定、プロセス優先度設定、バックグラウンド用ツール類を含む。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用の専用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を構築して起動（スレッドで実行）。
    - 停止フラグファイル (data/stop_requested.flag) を検知して安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定。
    - PID ファイルのサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは共通 DB に記録）。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定関連
  - config.py
    - .env ファイル自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env のパースは export プレフィックス、クォート付き値、エスケープシーケンス、インラインコメント等に対応する堅牢な実装。
    - Settings クラスでアプリケーション設定をプロパティ経由で取得可能に。J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境（development, paper_trading, live）などをカバー。
    - 環境変数保護（OS環境変数の上書きを防ぐ）や自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

  - config_setup.py
    - .env を対話式に作成・更新するウィザードを追加。
    - 入力補助、選択肢提示、シークレット値のマスク表示、保存前の確認を備える。
    - .env のテンプレートフォーマットを定義して出力。

  - validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML ファイルの存在/パース確認（PyYAML がある場合のみ）、本番環境時の追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いできる。

- ロギング / プロセス管理
  - utils/logging_setup.py
    - 全起動スクリプトから共通利用できるログ設定ユーティリティを追加。
    - コンソール出力は stdout（StreamHandler）、ファイル出力は日次ローテーション（TimedRotatingFileHandler）を使用。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。

  - utils/process_priority.py
    - psutil を用いてクロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - POSIX 系では nice 値、Windows では HIGH_PRIORITY_CLASS 等を利用。失敗時は警告を出してスキップ。
    - CPU affinity 設定ヘルパーも追加（指定コア数にピン留め）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順で上位 N）select_candidates を実装。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別集中制限を適用する関数を実装（既存保有を考慮）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 をフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を決定する主要なアルゴリズムを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-position と aggregate の上限、cost_buffer による保守的見積り、スケールダウンと残差処理による切り捨て後の再分配ロジックを含む。
    - 価格欠損や無効価格はログ出力してスキップ。

- Paper Trading / 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の SQLite DB（デフォルト data/paper_trading.db）から検証レポートを生成するツールを追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）などを算出。
    - Pass/Fail 基準値を定義（稼働率 >= 99%, 成立率 >= 90%, 送信率 >= 95%, P95 レイテンシ <= 200 ms）し、判定を表示。
    - 日付フィルタ、DB パス指定オプションをサポート。

- その他
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（Momentum、Value、Volatility、Liquidity 等を計算する方針・定数を定義）。DuckDB 接続を受け取って prices_daily, raw_financials を参照する設計。
  - パッケージ __init__ を追加しバージョンを 0.1.0 に設定。

Changed
-------

- （初期リリースにつき該当なし）

Fixed
-----

- （初期リリースにつき該当なし）

Notes / Migration / 注意点
------------------------

- 設定読み込み
  - 自動 .env ロードはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後に機能が不要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
  - .env の上書きルール: OS 環境変数は保護され、.env.local は .env を上書き可能（os 環境変数 > .env.local > .env の優先順）。

- DB の分離
  - run_execution は paper_trading モード時に PAPER_TRADING_SQLITE_PATH（設定名: PAPER_TRADING_SQLITE_PATH）で指定された DB を使用し、本番監視 DB（SQLITE_PATH）とは分離されます。一方、監視（run_monitoring）は環境に関わらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（監視データは一元管理）。

- ログ
  - ログは標準出力（stdout）と日次ローテートファイルへ出力。ログディレクトリ作成に失敗した場合はファイル出力を自動的にスキップします。

- プロセス優先度 / CPU affinity
  - 実行時に権限不足で優先度変更が失敗する場合は警告が出ますが処理は継続します。

- Paper Trading レポート
  - データが存在しない場合は "N/A" を表示し、Fail 判定の理由として出力されます。

- 未実装 / TODO
  - research/factor_research.py はファクター計算の設計と定数を含むが、一部関数の実装が未完（スニペット末尾が途中で切れているため、実装の続きが必要）。
  - position_sizing の price フォールバック（前日終値や取得原価を使う）について TODO コメントあり。
  - 将来的には銘柄ごとの lot_size をマスタ（stocks マスタ）で扱う拡張が想定されている。

開発者向けメモ
---------------

- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（validate_config.py でもチェック済み）。
- ログレベル、DB パス、各種閾値は Settings 経由で取得可能。unit-test などで自動 .env ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。
- run_execution/run_monitoring はそれぞれ main() をエントリポイントとしており、直接 python -m kabusys.run_execution などで起動できます。

---

今後のリリースで追加すべき改善案（提案）
- research/factor_research の完全実装とユニットテスト追加。
- 設定の型検証（pydantic 等）の導入による Settings の堅牢化。
- モニタリング・トレースのメトリクス出力（Prometheus 等）やアラート送信（LINE）実装の拡充。
- position_sizing の lot_size を銘柄別にサポートし、価格欠損時のフォールバック戦略を実装。

以上。必要であれば、実際のリリース日やバージョン履歴（過去の変更を分割）を反映した正式な履歴に整形します。どの形式（Unreleased のまま / 日付付きのリリース履歴）を希望しますか？