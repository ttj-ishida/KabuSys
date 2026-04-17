# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

なお、本ログはソースコードからの推測に基づいて作成しています。実際の変更履歴やリリースノートと差異がある場合があります。

## [Unreleased]

- 次回リリースに向けた未公開の変更はここに記載します。

## [0.1.0] - 2026-04-17

初回公開リリース。以下の主要機能・モジュールを追加しました。

### Added

- パッケージ基盤
  - kabusys パッケージ（__version__ = 0.1.0）を追加。
  - settings オブジェクト経由で環境変数を扱う `kabusys.config.Settings` を追加。
    - OS 環境変数 > .env.local > .env の順で自動読み込み（プロジェクトルート検出あり）。
    - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須変数未設定時に例外を投げる `_require` ユーティリティを提供。

- 実行系 / エンジン
  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時には paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を統合。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動・監視。
    - 実行停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）に対応。
    - プロセス優先度を最初に "high" に設定。

- 監視（Monitoring）
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。不正値はログ出力のうえデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。

- 設定 / 環境読み込み
  - `.env` ファイルのパース機能を実装（`_parse_env_line`）。
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント扱いの改善などを実装。
    - `_load_env_file` により protected keys を尊重した上書き処理が可能。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定（select_candidates）、等重・スコア重み算出（calc_equal_weights / calc_score_weights）を追加。
    - スコアが全て 0 の場合は等金額配分にフォールバックする警告を出力。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限の適用（apply_sector_cap）を追加。既存保有のセクター別エクスポージャーを計算して候補を除外する。
    - 市場レジームに基づく投下資金乗数（calc_regime_multiplier）を追加（bull/neutral/bear 対応、未知レジームはフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 株数決定ロジック（calc_position_sizes）を追加。
    - risk_based / equal / score の割当方式に対応。
    - 単元株（lot_size）丸め、per-position 上限や aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer を用いた保守的見積りを実装。
    - aggregate スケーリング後の残差処理で lot_size 単位で追加配分するロジックを実装。
    - TODO コメントで将来的な lot_size 銘柄別対応を明示。

- 研究（Research）
  - `kabusys.research.factor_research`
    - Momentum/Volatility/Value ファクター計算を実装（DuckDB 経由で prices_daily / raw_financials を参照）。
    - calc_momentum, calc_volatility, calc_value を提供。欠測やデータ不足時の取り扱いに配慮。
  - `kabusys.research.feature_exploration`
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計要約（factor_summary）、ランク関数（rank）を実装。
    - pandas 等の外部依存を用いず標準ライブラリ + DuckDB で処理。
  - `kabusys.research.__init__` で主要 API を再エクスポート。

- AI / ニュース NLP（下位機能を追加）
  - `kabusys.ai.news_nlp`
    - ニュースのタイムウィンドウ計算（calc_news_window）を実装（JST ベース／UTC 変換）。
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価のための設計と score_news の骨格を追加。
    - バッチ処理（最大銘柄数 20）、トークン肥大化対策（記事数・文字数上限）、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフの方針などを実装方針に含める。
    - 注意: ファイル末尾が途中で切れている箇所があるため、記事フェッチ以降の処理は未完または継続作業が必要。

- ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計して標準出力に出力。
    - 基準値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を実装。
    - コマンドラインオプション --from / --to / --db をサポート。

- ユーティリティ
  - `kabusys.utils.process_priority`
    - プラットフォーム依存差分を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応し、優先度レベル "high"/"normal"/"low" を提供。
    - CPU affinity を固定する set_cpu_affinity を追加（アクセス権限エラー等はログにフォールバック）。

### Changed

- N/A（初回リリースのため過去変更なし）

### Fixed

- N/A（初回リリースのため過去修正なし）

### Notes / Migration

- 環境変数の必須項目
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings で必須とされています。リリース前に .env を準備してください（.env.example を参照）。
- paper_trading モード
  - KABUSYS_ENV=paper_trading を設定すると実行系は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に切り替わります。本番 DB と完全に分離されます。
  - PAPER_FILL_MODE の有効値は instant / partial / never / reject。無効値は ValueError を投げます。
- 監視
  - run_monitoring は MONITOR_POLL_INTERVAL でポーリング間隔を調整できます。1 秒未満や不正な値は無視されデフォルト（60 秒）に戻ります。
  - 監視は監視用 DB（Settings.sqlite_path）を使用します（環境にかかわらず本番の sqlite_path を参照する点に注意）。
- OpenAI
  - news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY を使用します。未設定時は ValueError を投げます。
  - news_nlp モジュールの一部処理が未完（ソース途中切断）なため、AI スコアリング機能の本番利用前に完成/検証が必要です。

### Known limitations / TODOs

- position_sizing: 銘柄ごとの単元株数（lot_size）を stocks マスタから取得する拡張は未実装（TODO コメントあり）。
- news_nlp: ファイル末尾で処理が途切れており、記事フェッチ→API呼び出し→DB書き換えの統合処理の完成が必要。
- .env 自動読み込みはプロジェクトルート検出に依存（.git / pyproject.toml）。配布後の環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して読み込みを制御可能。

---

（補足）この CHANGELOG は現在のソースから機能を推測して作成しています。実際のリリースノートに合わせて適宜調整してください。