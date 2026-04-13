Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトではセマンティックバージョニングに従います: MAJOR.MINOR.PATCH

## [0.1.0] - 2026-04-13

初回リリース — 基本的な自動売買・リサーチ・監視ユーティリティ群を実装。

### Added
- 基本パッケージ情報
  - kabusys パッケージ（__version__ = 0.1.0）。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアント生成を BrokerClientFactory で抽象化。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を使用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0/負の値はデフォルトにフォールバックして警告出力。
    - 監視用 DB(initialization) は環境に関係なく本番 sqlite_path を使用する設計。

- 設定 / 環境読み込み
  - config.Settings を実装し、環境変数から各種設定を提供（DB パス、API トークン、環境種別など）。
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export 形式やクォート、インラインコメント、エスケープを考慮した堅牢な実装。
  - 必須値未設定時は _require() が ValueError を投げる。
  - 設定例: PAPER_FILL_MODE（paper trading の fill モード検証）、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH / KILL_FLAG_PATH、しきい値系（CPU/MEMORY/DISK）など。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順に上位 N を選択（タイブレークは signal_rank）。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮、sell_codes を除外可能）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームは警告のうえ 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 等配分・スコア配分・リスクベース配分をサポート。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash に基づいたスケーリング）を実装。
    - cost_buffer を考慮した保守的なコスト見積と余剰配分アルゴリズム（端数処理）を実装。
    - 未実装/拡張 TODO: 銘柄別 lot_size を将来サポートする計画をコメントで明示。

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（target_date 以前の最新財務データを使用）。
    - 全て DuckDB 接続を受け取り SQL ベースで効率的に計算。
  - research.feature_exploration
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで計算（horizons 引数、入力検証あり）。
    - calc_ic: スピアマン（ランク）相関による IC 計算（ランク付け・同順位は平均ランク）。
    - factor_summary: count/mean/std/min/max/median を計算するユーティリティ。
    - rank: ランク付けユーティリティ（丸めによる ties 対応）。
  - research.__init__ にて主要関数と zscore_normalize をエクスポート。

- AI / ニュース NLP
  - ai.news_nlp
    - raw_news + news_symbols を集約して OpenAI （gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込むロジックを実装。
    - バッチ処理（デフォルト 20 銘柄/チャンク）、最大記事数/文字数トリム、429/ネットワーク/5xx に対する指数バックオフでのリトライ制御。
    - レスポンスの厳密な JSON 検証、スコアは ±1.0 にクリップ、部分失敗に備えた書き込み戦略（対象コードで DELETE→INSERT を行い既存スコアを保護）。
    - calc_news_window: ターゲット日付に対するニュース収集ウィンドウ（JST の前日 15:00 〜 当日 08:30 に対応）を提供。
    - API キーは引数または環境変数 OPENAI_API_KEY（未指定なら ValueError）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成ツールを追加。
    - CLI で期間指定可能（--from / --to / --db）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を集計し、PASS/FAIL を判定する閾値を規定（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - P95 の算出ロジック、レポート出力フォーマットを実装。
    - DB ファイルが存在しない場合の明確なエラーメッセージ。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) を実装（Windows / POSIX の差分吸収）。
    - set_cpu_affinity(cpu_count) を実装（最初の N コアにプロセスをピンニング）。
    - アクセス権限不足や未対応 OS では警告を出してスキップするフェールセーフ。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known issues / Notes / TODO
- run_monitoring は Monitoring 用 DB 初期化のために常に本番 sqlite_path を使用する点に注意。環境設定による DB 分離が不要な設計。
- portfolio.position_sizing:
  - price が欠損（0.0）だとエクスポージャーが過少見積もられる問題についてコメントで TODO を記載。将来的にフォールバック価格（前日終値等）を導入予定。
  - lot_size は現状全銘柄共通（将来的に銘柄別の lot_map を受け取る拡張を検討）。
- ai.news_nlp:
  - OpenAI API の利用には API キーが必須（環境変数 OPENAI_API_KEY または引数で指定）。
  - ネットワークや API 側のエラーはリトライするが、最終的にチャンクが失敗した場合はそのチャンク分のスコア取得をスキップし、他の銘柄のデータは保護される設計。
  - レスポンスの厳格な JSON 形式を期待しているため、モデル出力に逸脱があると失敗する可能性がある。
- research モジュールは標準ライブラリと DuckDB のみで実装（pandas 等の外部依存なし）。大規模データでの実行時は DuckDB のリソースに依存。
- config の .env 自動ロードはプロジェクトルート検出に依存するため、配布後や特殊なデプロイでルートが見つからない場合はロードされない（この場合は環境変数で明示的に設定する必要あり）。

### Security
- OpenAI API キーや各種 API トークンは環境変数で管理すること。config._require() は必須トークン未設定時に例外を投げるため、運用環境では適切にシークレットを設定してください。

-- End of changelog --