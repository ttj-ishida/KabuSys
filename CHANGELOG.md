CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog のガイドラインに従います。
バージョン番号は semantic versioning に従います。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリースを追加（パッケージバージョン: 0.1.0）。
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に分離して記録する。
    - 停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）をサポート。
    - ExecutionEngine の依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）を組み立てる起動フローを実装。
- 監視用エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path（data/monitoring.db デフォルト）を使用。
    - 停止フラグ検出および例外処理を実装。
- 設定管理
  - config.py: 環境変数/.env 読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml 基準）。
    - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - 複雑な .env パースを実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - 各種環境変数プロパティを提供（DBパス、PIDパス、閾値、PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など）。値検証とデフォルトを実装。
- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder: シグナル選定と重み計算（等金額・スコア加重）を追加。スコアが全て0のとき等金額にフォールバック。
  - portfolio.position_sizing: 発注株数計算を実装（risk_based / equal / score）。単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を考慮した安全な分配ロジックを実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。未知レジーム/未知セクターのフォールバック動作を定義。
- リサーチ・ファクター計算
  - research.factor_research: Momentum / Volatility / Value を DuckDB を使って計算する関数群を追加（prices_daily, raw_financials を参照）。MA200, ATR20, 各種モメンタム等を算出。
  - research.feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクターの統計サマリーを追加。ties の平均ランク処理や丸めによる安定性対策を実装。
  - research モジュールは kabusys.data.stats の zscore_normalize を re-export。
- AI ニュース NLP
  - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書き込む仕組みを追加。
    - ニュース集約ウィンドウの計算（JST 前日15:00～当日08:30 相当の UTC 範囲）。
    - バッチ送信（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフリトライ、JSON レスポンスバリデーション、スコアの ±1.0 クリップ、部分更新（対象コードのみ DELETE→INSERT）等を設計。
- ユーティリティ
  - utils.process_priority: プロセス優先度設定ユーティリティを追加（Windows / POSIX を抽象化）。set_process_priority と set_cpu_affinity を提供。アクセス権限不足時は警告を出してスキップ。
- コマンドラインツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加（期間指定可能）。稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などの指標を算出し PASS/FAIL を判定。
    - デフォルト閾値: 稼働率 99.0%、成立率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms。
    - DB が存在しない/テーブル欠損の場合は安全にハンドリングして "N/A" を表示。
- DB 初期化
  - monitoring_db.init_monitoring_db を呼ぶことで監視テーブルの存在を冪等的に保証（run_monitoring / run_execution 起動時に実行）。

Changed
- パッケージ構成とエクスポート（kabusys/__init__.py）で主要モジュールを公開。
- run_monitoring/run_execution 起動時に最初にプロセス優先度を High に設定するように変更（set_process_priority 呼び出しを最初に移動）。
- Settings の env 判定で許容値を限定し、不正値は例外を送出するよう強化（development / paper_trading / live）。
- position_sizing のスケーリングロジックを改善し、残余キャッシュを用いて lot_size 単位で追加配分する仕組みを導入（再現性のためソートと安定キーを採用）。

Fixed
- .env パーサを改善:
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを修正。
  - override フラグと protected set による OS 環境変数保護を実装（.env.local が OS の環境変数を上書きしないように）。
- run_monitoring の MONITOR_POLL_INTERVAL に対するバリデーションを追加。0 以下や不正値のときはログ警告後にデフォルト値を使用し、time.sleep による ValueError を予防。
- research.feature_exploration.rank と calc_ic の実装で ties と丸め誤差に対する安定性を向上。
- ai.news_nlp のニュースウィンドウ計算を明確化（JST→UTC 変換）し、時間境界の扱い（含む/含まない）を定義。
- portfolio.risk_adjustment.apply_sector_cap で unknown セクターの扱いを明確化（unknown は上限適用対象外）。

Internal
- DuckDB を活用する設計に統一（research, ai, run* スクリプトで duckdb 接続を受け渡し）。
- 多くの関数を「DB 参照なしの純粋関数」として設計し、単体テスト容易性を高める（portfolio モジュール等）。
- ログ出力を充実化（debug/info/warning の適切な利用）。

Environment / Migration notes
- 主要な環境変数（デフォルト値）:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - SQLITE_PATH: data/monitoring.db
  - DUCKDB_PATH: data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
  - OPENAI_API_KEY: ai.news_nlp 用（未設定時は例外）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化
- paper_trading モードでは DB が本番 DB と分離されるため、既存の本番 DB を上書きしないよう PAPER_TRADING_SQLITE_PATH を確認してください。
- .env/.env.local 自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布環境では .env ロードを明示的に制御することを推奨します。

Acknowledgements
- 本リリースはシステム監視・注文実行・ポートフォリオ構築・リサーチ・AI スコアリングを横断する初期基盤を提供します。
- 各モジュールは単体でのテストが可能なように設計されており、今後の改良や性能チューニング、外部 API/DB スキーマの拡張に対応しやすい構成を目指しています。