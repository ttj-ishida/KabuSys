# Changelog

すべての変更は Keep a Changelog の規約に従って記載します。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

なお、本リリース内容はソースコードから推測してまとめたもので、実際のコミット履歴ではありません。

## [0.1.0] - 2026-04-17

### Added
- 全体
  - プロジェクト初期リリース。日本株自動売買システム「KabuSys」のコアモジュール群を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` に設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 停止制御: プロジェクトルートの `data/stop_requested.flag` を検知してループを終了。
    - 監視用 DB は環境にかかわらず本番用の `sqlite_path` を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient（BrokerClientFactory 経由）を使用し、paper_trading 用の専用 SQLite（`data/paper_trading.db` デフォルト）を使用して本番 DB と分離。
    - エンジンの PID 管理（`data/execution.pid`）と停止フラグ検知（`data/stop_requested.flag`）による安全停止機構を実装。
    - 実行中スレッドをデーモンで起動し、フラグ検知でエンジン停止を行うループを実装。

- 設定管理
  - config.Settings クラスを追加。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env と .env.local の読み込み順序と上書きルール（OS 環境変数は保護）。
    - 多数の設定プロパティを提供（J-Quants / kabuAPI トークン、LINE API、DuckDB/SQLite パス、Paper Trading 関連、監視しきい値等）。
    - `PAPER_FILL_MODE` の検証（有効値: instant|partial|never|reject）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能（テスト用）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI を追加。
    - 指定期間（--from / --to）または DB 全体を集計して、稼働率、注文成功率、送信率、P95 レイテンシ等の指標を出力。
    - 判定基準（稼働率、成立率、送信率、P95 レイテンシ）を定義し PASS/FAIL 判定を行う。
    - `PAPER_TRADING_SQLITE_PATH` 環境変数または `--db` オプションでターゲット DB を指定可能。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を追加。
    - calc_score_weights は全スコアが 0 の場合に等金額配分にフォールバックし警告を出す。
  - portfolio.risk_adjustment
    - セクター集中制限を行う apply_sector_cap を追加。既存保有からセクター別エクスポージャを計算し上限超過セクターの新規候補を除外。`unknown` セクターは上限適用除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull:1.0, neutral:0.7, bear:0.3。未知は 1.0 にフォールバックして警告）。
  - portfolio.position_sizing
    - 株数算出ロジック calc_position_sizes を追加。
    - risk_based / equal / score の配分方式に対応。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash に収めるスケーリング）、cost_buffer を用いた保守的コスト見積り、残余キャッシュを用いた再配分ロジックを実装。
    - 価格欠損や非正の価格はスキップする挙動。

- 研究（research）
  - research.factor_research
    - モメンタム、ボラティリティ、バリュー系ファクター計算（calc_momentum, calc_volatility, calc_value）を追加。DuckDB の prices_daily / raw_financials を参照。
    - パフォーマンスと欠損制御（ウィンドウサイズ・行数検査）を考慮。
  - research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク関数（rank）を追加。
    - 外部ライブラリ非依存（標準ライブラリのみ）での実装。
  - research.__init__ で公開 API を整理（zscore_normalize を data.stats から再公開）。

- AI（ニュース NLP）
  - ai.news_nlp
    - raw_news を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを計算して ai_scores に書き込む処理を実装（score_news）。
    - ニュース対象ウィンドウの計算（JST ベース → UTC 変換: 前日 15:00 JST ～ 当日 08:30 JST）を実装（calc_news_window）。
    - バッチ処理（最大 20 銘柄）・トークン肥大化対策（1銘柄あたり記事数・文字数上限）・JSON Mode を利用する想定。
    - エラー（429/ネットワーク/5xx 等）に対して指数バックオフでリトライする仕組みを想定（定数で上限とバックオフ基数を定義）。
    - API キー未設定時のエラー処理。

- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度を設定する set_process_priority(level) を追加（Windows と POSIX(Linux/Mac/FreeBSD)を吸収）。
    - CPU affinity を設定する set_cpu_affinity(cpu_count) を追加（指定が None の場合は無処理）。
    - 権限不足や未対応プラットフォームでの失敗は警告に留める安全設計。

### Changed
- .env 読み込み挙動
  - .env/.env.local の自動読み込みはプロジェクトルートが検出できた場合のみ行う（CWD に依存しない）。OS 環境変数を保護するため protected set を使用して優先度を制御。

- 起動時の優先度設定
  - run_monitoring と run_execution の両方で起動直後にプロセス優先度を "high" に試みるよう統一。

### Fixed
- 環境ファイルパーサーの堅牢化
  - _parse_env_line にて以下をサポート/修正:
    - `export KEY=val` 形式への対応。
    - 引用符あり値のバックスラッシュエスケープ処理と対応する閉じクォート検出。
    - 引用なし値のインラインコメント判定（`#` の前がスペース/タブの場合のみコメントとみなす）。
    - 空行・コメント行を無視。

- calc_score_weights のフォールバック
  - 全スコアが 0.0 の場合、等金額配分にフォールバックして警告を出す不具合回避。

### Known issues / Notes
- ai.news_nlp の実装はファイル末尾で途中切れが見られ、細部（記事取得関数やAPIレスポンス処理から DB 書き込みまでの完全な実装）が未完の可能性があります。実行時は該当関数の完全実装とテストが必要です。
- position_sizing 内で価格が欠損（0.0）の場合、エクスポージャーや総投資額が過少見積りされる旨の TODO が残っています。将来的に前日終値や取得原価でのフォールバックを検討する想定。
- run_monitoring は「監視は常に本番 sqlite_path を使う」設計になっており、テスト環境や paper_trading と監視 DB を明確に分離したい場合は運用上の注意が必要です。
- process_priority / set_cpu_affinity は権限やプラットフォームの差異により発行されないことがあるため、重要な環境での動作確認を推奨します。

### Security
- API キーや機密情報は環境変数で管理する設計。`.env` 自動読み込み機能は存在するが、OS 環境変数は上書きされないよう保護している。

---

将来的なリリースでは、AI モジュールの完全実装、追加のテストケース、エラー処理改善、パフォーマンス最適化やドキュメントの拡充を計画してください。