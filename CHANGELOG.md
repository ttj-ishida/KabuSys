CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------

Added
- パッケージ初期リリースを導入（__version__ = "0.1.0"）。
- 実行エントリスクリプトを追加:
  - run_execution.py — ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は本番 DB と分離して専用の PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用。
    - ブローカークライアント生成を BrokerClientFactory 経由で行い、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定（psutil 経由のプラットフォーム対応）。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒、0 以下や不正値は警告してデフォルトにフォールバック）。
    - 監視処理は環境変数 KABUSYS_ENV に関わらず本番の sqlite_path（デフォルト: data/monitoring.db）を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。

- 設定 / 環境変数管理:
  - config.Settings を実装:
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml で探索）。OS 環境変数を保護する挙動（.env.local は上書き可能だが OS 環境変数は上書きされない）。
    - .env パーサを実装（export 形式、クォート・エスケープ、インラインコメント処理に対応）。
    - 多数のプロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH、閾値パラメータ、LOG_LEVEL、KABUSYS_ENV 等）を提供。無効値に対するバリデーションを実施。
    - 環境読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。

- 監視（monitoring）関連:
  - init_monitoring_db 関数呼び出しで監視用テーブルを冪等に初期化する扱いを各起動スクリプトに組み込み。

- ポートフォリオ構築（pure functions, DB 参照なし）:
  - portfolio.portfolio_builder:
    - select_candidates: シグナルのスコア降順ソート・上位 N 選出（同スコア時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等額配分 および スコア加重配分（全スコア 0 の場合は等分配にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用する関数（売却予定コードを除外可能、"unknown" セクターは適用除外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく資金乗数（未知のレジームは警告して 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した株数決定ロジックを実装。
      - 単元丸め（lot_size, デフォルト 100）、max_position_pct による上限、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer を用いた保守的見積り。
      - risk_based 方式では risk_pct / stop_loss_pct に基づくポジション計算、等分配方式では weight に基づく割当。
      - スケールダウン後は残余キャッシュで fractional 残差 の大きい順に lot 単位を追加配分する実装。
      - 設計上の TODO として price 欠損時のフォールバック（前日終値等）に関する注記を残す。

- 研究 / リサーチ機能（DuckDB 前提）:
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials テーブルを参照して、モメンタム、ATR、流動性、PER/ROE 等を計算。
    - 各計算はウィンドウサイズやデータ不足時の NULL ハンドリング、必要行数チェック（例: MA200 の行数チェック）をサポート。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン (1/5/21 日など) を計算（ホライズンの検証・範囲設定あり）。
    - calc_ic: スピアマンランク相関（IC）を計算。3 銘柄未満なら None。
    - factor_summary / rank: 基本統計量と順位付けユーティリティを提供。
  - research.__init__: zscore_normalize を含む主要 API をエクスポート。

- AI ニュース NLP:
  - ai.news_nlp:
    - raw_news / news_symbols から銘柄別に記事を集約して OpenAI API (gpt-4o-mini + JSON Mode) へ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルに書き込む処理を実装（バッチ処理、1バッチあたり最大 20 銘柄）。
    - 入力トリミング (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)、スコアクリップ（±1.0）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、部分失敗に対する部分的 DB 更新戦略（DELETE → INSERT の限定的置換）などを設計。
    - calc_news_window ユーティリティで JST ベースのニュース収集ウィンドウを正しく算出（UTC に変換して DB 比較に使用）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

- ユーティリティ:
  - utils.process_priority:
    - set_process_priority(level) を実装（Windows / POSIX(Linux/Mac/FreeBSD) を吸収）。psutil による優先度設定を試み、失敗時は警告してスキップ。
    - set_cpu_affinity(cpu_count) を実装（None なら変更しない、少数のコアに固定可能）。失敗時は警告してスキップ。

- ツール:
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成スクリプトを追加（コマンドラインから実行可能）。
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ 等の集計と閾値判定（定義済みの合格基準: 稼働率>=99%、注文成功率>=90% など）。
    - 日付フィルタリング、DB 存在チェック、各種テーブルの欠如に対するフォールバックを実装。

Changed
- （初期リリースのため、過去バージョンからの変更履歴は無し）

Fixed
- （初期リリースのため、過去バージョンからの修正履歴は無し）

Notes / Known limitations / TODO
- ai.news_nlp モジュールは堅牢性を考慮した設計が施されていますが、API レスポンスの具体的パース処理や部分的な例外ハンドリングの詳細は今後の改善対象（コード末尾に処理継続のための guard が含まれているが、実装の継続が必要）。
- position_sizing.calc_position_sizes と apply_sector_cap は price が欠損（0.0）だった場合に過少見積もりとなる点がコメントとして残っており、将来的に前日終値や取得原価を用いたフォールバックを検討する旨の TODO が記載されています。
- .env 自動ロードはプロジェクトルート特定に依存するため、パッケージ配布後や特殊な配置環境では自動ロードがスキップされる可能性があります。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- psutil を用いた優先度 / affinity の設定は権限や OS 実装に依存し、失敗時は警告してスキップする挙動です。

開発者向け補足
- DuckDB 接続を受け取る研究系 API（research.*）は副作用を持たない純粋関数的インターフェースを心掛けており、テストしやすい構造になっています。
- 多くのコンポーネントで環境変数による動作変更（ファイルパス、閾値、モード切替）が可能です。CI / 本番環境では .env の取り扱いに注意してください。

--- 
（この CHANGELOG は、提供されたソースコードのコメントと実装から推測して作成しています。実際のリリースノートとして公開する前に、変更点・日付・バージョン番号をプロジェクトの実情に合わせて調整してください。）