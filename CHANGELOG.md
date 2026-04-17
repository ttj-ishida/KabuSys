# Changelog

すべての重要な変更点をこのファイルに記録します。書式は「Keep a Changelog」に準拠します。  
日付はリリース推定日（コード内コメント・参照日から推定）です。

※ 本 CHANGELOG は提供されたコードベースの内容から機能・振る舞いを推測して作成しています。

## [Unreleased]

### Added
- News NLP スコアリング機能（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルに書き込む処理を追加。  
  - バッチサイズ、トークン肥大化対策、エクスポネンシャルバックオフのリトライ、レスポンス検証、スコアクリップなどの実装設計あり。  
  - （注）ファイル末尾が途中で切れており処理が未完／未検証の箇所が存在するため、実運用前に完了確認が必要。

### Changed
- なし（新規追加機能の補完・未リリース修正想定）

### Fixed
- なし

---

## [0.1.0] - 2026-04-17

### Added
- パッケージ基盤
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。

- 設定管理（kabusys.config）
  - .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml）。  
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。  
  - .env パーサーの強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のエスケープ処理をサポート
    - 行内コメント処理（クォートなしの場合、# の直前が空白/タブならコメントとみなす）
  - Settings クラスを提供し、各種設定（API トークン、DB パス、監視閾値、環境種別など）をプロパティ経由で取得可能に。
  - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）を追加。
  - KABUSYS_ENV / LOG_LEVEL の許容値チェックを実装。

- 実行・監視スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと実行（ExecutionEngine.run_session を別スレッドで起動）。  
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）を扱う管理ロジックを実装。  
    - RiskManager のデフォルト設定（max_position_pct / max_utilization / rate_limit_per_sec / circuit_breaker_* / max_drawdown 等）を付与。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログを出してデフォルトにフォールバック。
    - 監視は環境に関わらず production 用 sqlite_path を使用（monitoring 用 DB 初期化呼び出しあり）。
    - 停止フラグ検知でループを終了、例外時はログを残して次ポーリングへ継続。KeyboardInterrupt 対応。
    - プロセス優先度を起動時に "high" に設定する処理を導入。

- 監視 DB 初期化呼び出し
  - run_execution / run_monitoring の両スクリプトで init_monitoring_db を呼び、監視用テーブルの存在を保証（冪等）。

- DuckDB サポート
  - DuckDB 接続を Settings.duckdb_path で受け取り、リサーチ／AI／エンジン等で共通利用できるように追加。

- ユーティリティ（kabusys.utils.process_priority）
  - プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows: psutil の PRIORITY_CLASS を使用。
    - POSIX (Linux / Darwin / FreeBSD): nice 値を設定。
    - set_cpu_affinity 関数で CPU affinity を最初の N コアに固定するロジックを追加（権限不足等は警告でスキップ）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順に選択（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights を実装（スコア総和が 0 の場合は等配分へフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限による候補除外ロジック（sell_codes で当日売却予定を除外可能）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知値は警告の上フォールバック1.0）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数決定ロジックを実装。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）等を考慮したスケーリング・端数処理を実装。
    - aggregate cap によるスケールダウン、余剰キャッシュを使った端数調整アルゴリズムを導入。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を参照し、各種ファクター（モメンタム、ATR、avg_turnover、PER、ROE 等）を計算。
    - ウィンドウ長や不足データ時の None 処理を明示的に扱う。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を LEAD を使った単一クエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を標準ライブラリのみで実装（tie は平均ランクで処理）。有効レコードが少ない場合は None を返す。
    - factor_summary / rank: 基本統計量・ランク変換ユーティリティを実装。
  - research/__init__.py で必要関数をエクスポート。

- データツール（kabusys.tools.paper_verification_report）
  - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率・注文成功率・送信率・リスク却下数・レイテンシ（avg/max/P95）を集計し、PASS/FAIL 判定（閾値はソース内定義）で出力。
    - --from/--to/--db CLI 引数に対応。DB 存在チェックと sqlite3.OperationalError の耐性を持つ。

### Changed
- なし（初期リリースとして各機能を追加）

### Fixed
- なし（初期リリースとして特定のバグ修正履歴はありません）

### Security
- API キー/機密情報の取り扱い注意点:
  - Settings は必須環境変数未設定時に ValueError を送出する（運用時の明示的エラーを確保）。
  - OpenAI API キーは環境変数 OPENAI_API_KEY または明示引数で提供する必要がある（news_nlp で未設定時は例外）。

---

注意および今後の検討事項
- ai/news_nlp モジュールは設計がほぼ記述されているものの、ファイルが途中で切れているため未完成の箇所があります。実運用前に処理完了・例外処理・トランザクション整合性（DuckDB 側）を確認してください。
- position_sizing の price 欠損時の扱いや apply_sector_cap の price フォールバック（前日終値や取得原価）については TODO コメントがあり、将来拡張が必要です。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム非対応時に警告でスキップするため、期待通りに優先度が設定されないケースを運用にて確認してください。
- run_execution/run_monitoring はファイルベースの停止フラグ・PID 管理に依存しているため、コンテナ化やクラスタ環境では別途制御方法の適用を検討してください。

以上。必要であれば、各リリースノートの英語版や、未完了箇所を洗い出した issue リストの作成も支援します。