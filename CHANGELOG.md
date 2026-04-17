# CHANGELOG

すべての注目すべき変更点をここに記録します。  
フォーマットは Keep a Changelog に準拠しています。

全般:
- バージョンはパッケージの __version__ に合わせて管理しています（現在: 0.1.0）。

Unreleased
- （次のリリースに向けた未リリース項目はここに記載してください）

[0.1.0] - 2026-04-17
Added
- 基本構成・起動スクリプト
  - run_monitoring.py を追加
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視データ保存には、KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する実装。
    - 停止制御はリポジトリ直下の data/stop_requested.flag による検出で行う。
  - run_execution.py を追加
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite(DB: data/paper_trading.db 相当) を使用して本番 DB と完全分離して動作。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/Reconciler/RiskManager を組み立ててエンジンを起動。停止フラグにより安全に停止可能。

- 設定管理
  - config.py を追加
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - export KEY=val 形式やクォート文字列、エスケープ、インラインコメントを考慮した堅牢な .env パーサを実装。
    - OS 環境変数を保護するための上書き制御（.env.local は override）と KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - Settings クラスを提供し、各種環境変数の取得・バリデーションを行う（例: PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV/LOG_LEVEL の検証、パス系プロパティの Path 化等）。
    - settings インスタンスをデフォルトでエクスポート。

- 監視・ユーティリティ
  - monitoring_db 初期化呼び出し（init_monitoring_db）を start-up ロジックに統合（監視テーブルの冪等な作成を保証）。
  - utils/process_priority.py を追加
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応したプロセス優先度設定（set_process_priority）。
    - CPU affinity を最初の N コアに固定するユーティリティ（set_cpu_affinity）。
    - 権限不足や未対応環境でも安全にフォールバックして警告を出力する堅牢な実装。

- Portfolio（銘柄選定・配分・ポジションサイズ）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み算出（全スコアが 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限により超過セクターの新規候補を除外。unknown セクターは上限を適用しない。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知のレジームは警告の上 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method により株数を算出（risk_based / equal / score をサポート）。
    - 単元株（lot_size）で丸め、per-stock 上限および aggregate cap（available_cash）に応じたスケーリングを実装。cost_buffer を用いた保守的見積りと、端数の割当ロジックを含む。

- 研究・リサーチ機能（DuckDB ベース）
  - research/factor_research.py
    - calc_momentum / calc_volatility / calc_value: prices_daily/raw_financials テーブルを参照してモメンタム、ボラティリティ、バリュー系ファクターを計算。各ウィンドウや必要サンプル数に基づく None フォールバックを実装。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズンに対応した将来リターン計算（入力検証あり）。
    - calc_ic: スピアマンのランク相関（IC）計算。レコード不足や等分散の場合は None。
    - factor_summary / rank: ファクターの基本統計量とランク変換ユーティリティ。
  - research/__init__.py で主要関数をエクスポートし、zscore_normalize を data.stats から公開。

- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py を追加（ニュース記事のセンチメントスコア処理）
    - ターゲット日の前日 15:00 JST 〜 当日 08:30 JST に対応するニュースウィンドウ計算（calc_news_window）。
    - raw_news と news_symbols を銘柄別に集約し、最大記事数/最大文字数でトリムして OpenAI にバッチ送信する想定。
    - バッチ処理（最大銘柄数 / リトライ（429/タイムアウト/5xx）・指数バックオフ、レスポンス検証、スコア ±1.0 クリップ、ai_scores テーブルへの部分置換ロジック）を設計。
    - OPENAI_API_KEY の解決と未設定時の ValueError を実装。
    - （注）API 呼び出し部分は堅牢性を考慮した設計で実装されている（バッチサイズ・最大トークン制限等の定数化）。

- ツール
  - tools/paper_verification_report.py を追加
    - Paper Trading 用の検証レポート生成ツール。CLI で期間指定（--from/--to）可能。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出して PASS/FAIL 判定を行う。
    - DB のテーブルが存在しない場合でも sqlite3.OperationalError をハンドリングして安全にレポートを出力。
    - P95 の計算、フォーマットユーティリティを含む。

- パッケージ初期化
  - kabusys/__init__.py にパッケージ名・バージョンと主要サブパッケージの __all__ を定義。

Changed
- 新規リリースのため、初回実装として上記機能を集約（設計段階での堅牢性・入力検証を重視）。
- .env 読み込み順序・優先度を明確化（OS 環境 > .env.local > .env）し、OS 環境変数を保護する仕組みを導入。

Fixed
- （この初回リリースでは既知のバグ修正履歴はありません。今後のリリースで追記します）

Known issues / Notes
- position_sizing.calc_position_sizes 内に価格欠損時の保険（fallback 価格使用）の TODO コメントが残っています。価格が欠損するとエクスポージャーが過少評価される可能性があるため、将来的に前日終値等のフォールバックを検討しています。
- ai/news_nlp.py の実装は API 呼び出し・レスポンス処理部分の完全な実装を想定した設計となっており、実際の API キー運用・レート制限環境では追加の運用制御が必要になる可能性があります。
- run_monitoring/run_execution はプロセス優先度設定やファイルベースの停止フラグに依存します。コンテナや一部環境では優先度変更やファイルパス権限で制約が発生する場合があります（set_process_priority は失敗時に警告を出してフォールバックします）。

署名
- この CHANGELOG は、リポジトリ内のソースコード（src/kabusys 以下）から読み取れる実装・設計方針に基づいて作成しました。実際の挙動・運用は環境設定や外部コンポーネント（OpenAI API、各種 DB ファイル等）に依存します。