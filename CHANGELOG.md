CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に従います。セマンティック バージョニングを採用しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-16
------------------

初回リリース。以下の主要機能・モジュールを実装しています。

Added
- コア
  - パッケージ初期化とバージョン設定を追加（kabusys.__version__ = "0.1.0"）。
  - Settings クラスを実装し、環境変数と .env / .env.local からの自動読み込み機能を提供。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行う。
    - OS 環境変数を保護する仕組み（protected）や自動ロード無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
    - 各種設定プロパティを提供（DB パス、API トークン、Paper Trading 用設定、監視閾値、環境判定等）。
    - 入力検証を実施（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の有効値チェック）。

- 実行・監視起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動用のエントリポイントを実装。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用 SQLite を使用して本番とデータを分離する挙動を採用。
    - BrokerClientFactory からブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて実行スレッドで稼働。
    - 停止フラグ（data/stop_requested.flag）と実行 PID ファイル管理をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する（監視は本番 DB を参照する設計）。
    - 停止フラグ検出で安全にループを終了。

- データベース / 統合
  - sqlite3 と DuckDB の接続処理を追加（init_monitoring_db で監視テーブル初期化）。
  - DuckDB を用いたリサーチ用 SQL 処理を想定した設計（prices_daily / raw_financials 等の参照）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選定（score 同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。全銘柄のスコアが 0 の場合は等配分にフォールバック（警告ログ）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック。既存保有をセクター別に集計して上限超過セクターの候補銘柄を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームはログ警告のうえ 1.0 でフォールバック）。
  - position_sizing.py
    - calc_position_sizes: 重みあるいはリスクベースに基づく発注株数計算を実装。
      - risk_based と equal/score の両方式をサポート。
      - 単元株（lot_size）で丸め、1 銘柄上限・投下資金上限（aggregate cap）を考慮。
      - cost_buffer により手数料/スリッページを保守的に見積もり、投下資金超過時はスケールダウンと残差分の追加配分ロジックを備える。

- リサーチ（kabusys.research）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（MA200）の計算を DuckDB SQL で実装。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を実装。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から直近財務を取得して PER・ROE を計算。
  - feature_exploration.py
    - calc_forward_returns: target_date 基準の将来リターン（horizons）を計算。複数ホライズンをまとめて 1 クエリで取得。
    - calc_ic: Spearman ランク相関（IC）を実装。データ不足時は None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量の集計を実装。
  - research.__init__ に zscore_normalize を再エクスポート（kabusys.data.stats から）。

- AI / ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI API（gpt-4o-mini）を使ったニュースセンチメントスコアリング機能を実装。
    - 指定時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 変換）で記事を集約。
    - 1 回あたり複数銘柄をバッチ（最大 20 銘柄）で送信、JSON Mode を期待して結果を検証。
    - 429・ネットワーク・5xx 等に対するエクスポネンシャルバックオフリトライ、スコアの ±1.0 クリップ、部分失敗時の既存データ保護（対象コードの限定 DELETE / INSERT）など、堅牢性を確保する設計。
    - トークン肥大化対策として銘柄ごとの記事数・文字数上限を導入。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を出力。
    - CLI オプションで期間・DB パス指定 (--from/--to/--db) をサポート。
    - P95（パーセンタイル）計算、日付フィルタの組立て、DB テーブル欠損への耐性を実装。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定（Windows と POSIX に対応）と CPU affinity 固定ユーティリティを実装。
    - 権限不足や未対応環境では警告ログを出してスキップする安全設計。

Security
- （なし）

Deprecated
- （なし）

Removed
- （なし）

Notes / Known limitations
- news_nlp モジュールの処理は OpenAI API キー（OPENAI_API_KEY）を必要とします。未設定時は明示的なエラーになります。
- position_sizing の価格欠損時の挙動について TODO コメントあり（価格欠損によるエクスポージャー過少見積りの可能性）。将来的には前日終値や取得原価でのフォールバックを検討。
- DuckDB を利用する SQL は prices_daily / raw_financials / raw_news など特定のスキーマを想定しています。利用前にデータスキーマの準備が必要です。
- run_monitoring は監視に本番 sqlite_path を使用するため、テスト目的で別 DB を使いたい場合は設計に注意してください。

もし追加で各モジュールごとのリリースノート（詳細な設計意図、API 使用例、制約、既知のバグ）を希望される場合は、対象モジュールを指定して依頼してください。