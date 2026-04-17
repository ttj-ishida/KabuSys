CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

(現時点のコード提供が v0.1.0 のスナップショットであるため、未リリースの項目はありません)

v0.1.0 - 2026-04-17
-------------------

Added
- 全体
  - 初期リリース。自動売買プラットフォーム「KabuSys」のコアモジュール群を追加。
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。

- 実行・監視
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用に分離された SQLite DB (デフォルト: data/paper_trading.db) に記録する仕組みを導入。
    - ExecutionEngine の依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててデーモンスレッドで実行する。
    - 停止制御用の stop フラグファイル (data/stop_requested.flag) を検知して安全に停止する処理を実装。
    - 実行中 PID を data/execution.pid に保存するための pid_file 機能をサポート。

  - run_monitoring.py: システム監視用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。無効値 (0/負数/非整数) は警告を出してデフォルトにフォールバックする。
    - 監視処理は環境にかかわらず本番用の sqlite_path を参照する設計（意図的な挙動として明記）。
    - プロセス優先度を最初に "high" に設定する処理を追加（utils.process_priority.set_process_priority を利用）。
    - 監視 DB の初期化（init_monitoring_db）と duckdb 接続の確立。

- 設定管理
  - src/kabusys/config.py:
    - .env 自動読み込み機構を実装（プロジェクトルートを .git / pyproject.toml で探索し、.env/.env.local をロード）。
    - export KEY=val 形式やクォート付き値、インラインコメントなどに対応する堅牢な .env パーサを実装。
    - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
    - 必須環境変数をチェックする _require() と Settings クラスを追加し、各種設定（DBパス、API トークン、監視閾値、環境ラベルなど）をプロパティとして提供。値検証（例: KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL の妥当性チェック）を行う。

- ポートフォリオ関連（純粋関数群）
  - portfolio.portfolio_builder:
    - シグナル選定関数 select_candidates、等配分・スコア加重の calc_equal_weights / calc_score_weights を追加。スコア合計が0の場合は等金額配分にフォールバック。
  - portfolio.risk_adjustment:
    - セクター集中制限を行う apply_sector_cap と、市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加。未知レジームは 1.0 でフォールバック（警告ログ）。
  - portfolio.position_sizing:
    - calc_position_sizes を実装。allocation_method ("risk_based", "equal", "score") に対応。
    - 単元株（lot_size）丸め、銘柄単位および総額の上限（max_position_pct / max_utilization）、コストバッファ (cost_buffer) を考慮したスケーリングロジックを含む。
    - price 欠損や 0 値を検出してスキップするなど、多数の安全弁を実装。

- 研究・リサーチ
  - research.factor_research:
    - momentum, volatility, value 各ファクター計算関数（calc_momentum, calc_volatility, calc_value）を追加。DuckDB を用いて prices_daily / raw_financials を参照して計算する。
    - 各関数はデータ不足時に None を返す等の堅牢な設計。
  - research.feature_exploration:
    - 将来リターン計算 calc_forward_returns、IC（スピアマン順位相関）計算 calc_ic、ファクター統計 summary を追加。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージ __all__ を整備して必要 API を公開。

- AI / NLP
  - ai.news_nlp:
    - raw_news を OpenAI（gpt-4o-mini）に投げて銘柄ごとのセンチメントスコアを ai_scores に書き込むためのモジュールを追加（バッチ送信、トークン肥大化対策、バックオフ、レスポンス検証、スコアクリップ等の設計を記載）。
    - ニュース収集ウィンドウ計算（calc_news_window）と score_news の骨格を実装（APIキー検証など）。（score_news はコード途中まで実装の状態）

- ツール
  - tools.paper_verification_report:
    - Paper Trading 向けの検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を抽出し、閾値（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 <=200ms）に基づく PASS/FAIL 判定を行う。
    - --from/--to/--db コマンドライン引数をサポートし、データがない場合のフォールバックを実装。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority, set_cpu_affinity を実装。Windows と POSIX（Linux/Mac/FreeBSD）を吸収し、アクセス権限不足や未対応 OS の場合は警告を出して安全にスキップする。

Changed
- 監視挙動
  - run_monitoring.py は監視目的で常に Settings.sqlite_path（本番用）を使用する設計になっている点を明記。これにより paper_trading 環境でも監視データは本番 DB に記録される（意図的な設計上の挙動）。
  - run_execution.py は paper_trading の場合に paper_sqlite_path を使用して本番データと分離する設計（実行側の分離を強化）。

Fixed
- 設定パーサ
  - .env ファイルのパースを強化。export プレフィックス、クォート付き値のエスケープ、インラインコメントの扱いを正しく処理するよう修正。
  - MONITOR_POLL_INTERVAL の不正値 (非整数, 0, 負数) を検出し、警告ログを出してデフォルト 60 秒へフォールバックする安全策を導入。
  - calc_score_weights: 全スコアが 0.0 の場合に等配分へフォールバックする処理を追加（警告ログあり）。

Security
- 設定の取り扱いに関して、必須変数未設定時に ValueError を投げる _require() を追加し、運用ミスによる秘密情報未設定を早期に検出できるようにした。

Notes / Migration
- 監視用スクリプト（run_monitoring.py）は「環境にかかわらず本番 sqlite_path を使用する」点が他のコンポーネントと異なります。テスト環境や paper_trading 環境で監視データを分離したい場合は、実行前に環境変数 SQLITE_PATH を適切に設定してください。
- .env 自動ロードはデフォルトで有効ですが、テストや CI で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ai.news_nlp の score_news は API キー依存であり、未設定の場合は例外を送出します。OpenAI への問い合わせは課金やレート制限の対象となるため注意してください。

Acknowledgements
- 各モジュールのドキュメント文字列とログメッセージによる詳細な設計意図を参照して記載しました。将来的なリファクタやリリースでは、各モジュール毎の細かいリリースノート分割を推奨します。