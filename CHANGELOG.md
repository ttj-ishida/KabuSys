# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリース日付はコミットより推測して記載しています。

## [Unreleased]

（次回リリースに向けた変更をここに記載してください）

## [0.1.0] - 2026-04-16

### Added
- 基本パッケージ初期実装を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 実行系 / 監視起動スクリプト
  - run_execution.py を追加。ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し、paper_trading 用に分離された SQLite DB（data/paper_trading.db、環境変数で上書き可）を使用。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager のデフォルト設定（max_position_pct=0.20 等）と、initial_portfolio_value を broker.get_available_cash() で初期化する実装。
    - ExecutionEngine をデーモンスレッドで実行し、data/stop_requested.flag による外部停止を監視。PID ファイル管理をサポート。
  - run_monitoring.py を追加。SystemMonitor のポーリングループを実行するエントリポイントを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計（監視データは本番 DB へ記録）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。

- 設定・環境管理
  - config.py を追加。
    - .env / .env.local の自動読み込み（プロジェクトルートの検出は .git または pyproject.toml ベース）。
    - 読み込みの優先度: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パーサーは export プレフィックスやシングル/ダブルクォート、エスケープ、インラインコメントを考慮して堅牢に実装。
    - Settings クラスを提供し、J-Quants / kabu / LINE / DB / 監視閾値 / システム設定などを環境変数から取得。必須キー未設定時は ValueError を送出。
    - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）と PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）の設定。

- ポートフォリオ構築モジュール（pure functions）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選抜（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づく候補除外。既存保有のセクター別時価（売却予定銘柄を除外）を考慮。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト map 実装、未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）対応、cost_buffer による保守的見積り、スケールダウンと端数配分のロジックを実装。
  - いずれも DB 参照なしの純粋関数として設計（メモリ内計算のみ）。

- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（DuckDB の prices_daily テーブル参照）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率の算出。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（target_date 以前の最新財務情報を取得）。
    - 全関数は DuckDB 接続を受け取り SQL ベースで高速に計算する設計。
  - research.feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）の計算（結合・None 除外、3 レコード未満で None を返す）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計（count, mean, std, min, max, median）。
    - pandas 等外部依存を避け、標準ライブラリのみで実装。

- research パッケージのエクスポート
  - zscore_normalize（kabusys.data.stats から）、上記ファクタ関数群を research パッケージの __all__ として公開。

- AI ニュース NLP（OpenAI 統合）
  - ai.news_nlp を追加（ニュースセンチメントスコアリング機能）。
    - raw_news / news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別スコアを ai_scores テーブルへ書き込むワークフローを実装。
    - バッチサイズ、記事・文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）をサポート。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンス検証、スコアの ±1.0 クリッピング、部分失敗時に既存スコアを保護するためのコード絞り込み更新ロジックを採用。
    - target_date に対応したニュースウィンドウ計算（JST→UTC 変換）を実装。
    - API キー未設定時は明示的な ValueError を送出。
    - フェイルセーフ設計（API 失敗時は処理をスキップして継続）。

- ツール
  - tools.paper_verification_report を追加。Paper Trading の検証レポート生成 CLI。
    - コマンドライン引数: --from / --to / --db（PAPER_TRADING_SQLITE_PATH も利用可）。
    - システム安定性（稼働率・エラー数）、注文成功率（fill/send rate）、リスク却下数、API レイテンシ（avg/max/P95）を集計し、PASS/FAIL 判定を出力。P95 は独自実装で算出。
    - DB が存在しない場合のエラーメッセージを実装。
    - しきい値（稼働率 99%、fill 90%、send 95%、P95 latency 200ms）を定義して判定。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX の差を吸収してプロセスの優先度（high/normal/low）を設定。権限不足や未サポート環境では警告ログでスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定するユーティリティ（無効時は全コア）。
  - 監視および実行系の起動時にプロセス優先度を High に設定する呼び出しを run_monitoring/run_execution に追加。

- DB 関連
  - DuckDB 接続の利用（duckdb.connect）を導入し、research・ai などで利用可能に。
  - monitoring の初期化関数 init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数または環境変数（OPENAI_API_KEY）として供給するようにし、未設定時は ValueError を発生させることで誤動作を防止。

---

注記:
- 多くのモジュールは「DB 参照なしの純粋関数」または「DuckDB 経由での読み取り専用集計」を採用しており、本番の発注 API への副作用を起こさない設計を目指しています。
- 一部モジュール内に将来改善の TODO コメント（例: price フォールバック、銘柄別 lot_size の拡張）が残されています。今後のリリースで対応予定です。