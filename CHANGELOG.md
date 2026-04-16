# CHANGELOG

すべての変更は Keep a Changelog に準拠しています。重要な変更・追加点を日本語で記載しています（コードベースから推測してまとめた内容です）。

## [Unreleased]
特になし。

## [0.1.0] - 2026-04-16
初回リリース相当の機能群を追加しました。自動売買システムのコア機能（設定管理、実行・監視起動スクリプト、ポートフォリオ構築、リサーチ、ユーティリティ、Paper Trading 検証ツール、AI ニューススコアリング連携など）を含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョン定義を追加（kabusys.__version__ = "0.1.0"）。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - paper_trading 環境向けに専用 SQLite DB を使用（data/paper_trading.db をデフォルト）し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行、停止フラグ監視（data/stop_requested.flag）を実装。
    - プロセス優先度を起動時に設定する仕組みを導入（高優先度："high"）。

  - run_monitoring.py: SystemMonitor のポーリングループ起動エントリポイントを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検出で安全にループ終了、KeyboardInterrupt にも対応。

- 設定管理
  - config.py:
    - .env / .env.local の自動ロード機能（プロジェクトルート自動検出）を追加。OS 環境変数を保護する仕組みあり。
    - .env パーサを強化（export プレフィックス対応、クォート文字列のエスケープ処理、インラインコメントの扱いなど）。
    - Settings クラスを導入し、環境変数に基づくプロパティ（DBパス、API トークン、監視閾値、paper_trading 用設定など）を提供。値検証（有効値チェック）を実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - BUY シグナル選定（select_candidates）。
    - 等分配・スコア基準配分（calc_equal_weights、calc_score_weights）。スコアが全て 0 の場合は警告して等分配にフォールバック。

  - portfolio/risk_adjustment.py:
    - セクター集中制限の適用（apply_sector_cap）。既存保有のセクター比率を計算して上限超過セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。既定のマッピング（bull/neutral/bear）とフォールバックの挙動を実装。

  - portfolio/position_sizing.py:
    - ポジションサイズ算出ロジック（calc_position_sizes）。risk_based / equal / score の割当方式に対応。
    - 単元株（lot）丸め、per-position 上限、aggregate cap（利用可能現金でスケーリング）や cost_buffer を考慮した安全な配分を実装。
    - 価格欠損時のスキップやログ出力を実装。

- 研究（Research）・ファクター計算
  - research/factor_research.py:
    - momentum, volatility, value ファクター計算（calc_momentum、calc_volatility、calc_value）を DuckDB を使った SQL ウィンドウ関数で実装。
    - 計算に用いるウィンドウサイズやスキャン範囲の定数化（200日 MA、ATR 20 日等）、データ不足時の None ハンドリングを実装。

  - research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ファクターの統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を追加。
    - 外部ライブラリ非依存（標準ライブラリのみ）で実装。

  - research/__init__.py: 上記 API をパッケージレベルで公開（zscore_normalize もエクスポート）。

- AI ニュース NLP（OpenAI 連携）
  - ai/news_nlp.py:
    - raw_news テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0～1.0）を算出して ai_scores テーブルに書き込むワークフローを実装。
    - バッチ（最大 20 銘柄）処理、記事文字数・件数のトリム、429 / ネットワーク / 5xx に対する指数バックオフリトライ、レスポンスの厳密な JSON 検証、スコアのクリップを実装。
    - calc_news_window によるニュース収集ウィンドウ計算を提供（JST に基づく UTC 変換）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成ツールを追加。DB（paper_trading.db）からシステム稼働率・注文成功率・送信率・レイテンシなどを集計し、閾値（稼働率 99% 等）に基づいて PASS/FAIL 判定を出力。
    - P95 計算、NULL / テーブル未存在時のフォールバック処理、コマンドライン引数（--from/--to/--db）を実装。

- ユーティリティ
  - utils/process_priority.py:
    - プラットフォーム非依存でプロセス優先度（Windows の priority class / POSIX の nice）を設定する set_process_priority を実装。失敗時は警告してスキップ。
    - set_cpu_affinity によりカレントプロセスの CPU affinity を設定するユーティリティを追加（アクセス権限不足等は警告してスキップ）。

- DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を起動時に呼び出して監視テーブルの存在を保証（冪等に初期化）。

### Changed / Improved
- .env 読み込みの優先度と保護
  - OS 環境変数を保護しつつ .env/.env.local をロードする順序を明確化（OS > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサの堅牢化（export サポート、クォート内バックスラッシュエスケープ、インラインコメントの扱い）により複雑な .env 設定を安全に読み込み可能に。

- DB / 環境分離
  - Paper Trading 実行時は paper_sqlite_path を使って本番 DB と完全分離するように変更（run_execution.py）。
  - 監視処理は環境に関係なく本番 sqlite_path を参照して監視用テーブルを初期化・利用（run_monitoring.py）。

- ロバストネス強化
  - MONITOR_POLL_INTERVAL の不正値検出とデフォルトフォールバックを実装。
  - PAPER_FILL_MODE の値検証を追加（有効値を限定）。
  - 各所での例外捕捉とログ出力（monitor.check_once の例外捕捉、DB アクセス失敗時のフォールバック）により長時間稼働の堅牢性を向上。

- パフォーマンス設計
  - research モジュールの DuckDB クエリはウィンドウ関数を多用し、スキャン範囲を限定してパフォーマンスを考慮した設計。

### Fixed
- 環境値の安全処理
  - 環境変数未設定時に明示的なエラーを返す _require を追加し、必須トークン未設定時の早期検出を容易に。
  - paper_verification_report の DB 存在チェックにより、誤った DB パスでのクラッシュを防止してユーザ向けエラーメッセージを改善。

### Notes / Known limitations
- ai/news_nlp.py は OpenAI API を前提とするため、API キー（OPENAI_API_KEY）が必須。API キー未設定時は明確なエラーを返します。
- 一部の処理（例: 価格欠損時のフォールバック価格使用など）は将来的な拡張（前日終値や取得原価のフォールバック）を想定した TODO コメントがあります。
- position_sizing の lot_size は現状 global 値（全銘柄共通）を前提。将来的に銘柄別 lot_map を受け取る拡張を想定。
- Docker / 実運用での権限関連（nice や cpu_affinity の設定）は実行環境の権限によって制約されるため、権限不足時は警告を出してスキップします。

---

この CHANGELOG はコードベースの内容から推測して作成したため、実際のリリースノートと差異がある可能性があります。必要であれば、より細かい変更点（ファイル単位の差分や作者・コミット情報）に基づいて追記・修正します。