# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」準拠で記述しています。  

リリースポリシー: 0.x 系はまだ安定化段階の初期リリースを想定しています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-17
初回公開リリース。

### Added
- 全体
  - パッケージ初期実装を追加。モジュール群は自動売買システム「KabuSys」のコア機能（監視・実行・ポートフォリオ構築・リサーチ・ユーティリティ・AIニュース解析・ツール）を含む。
  - バージョン情報: `kabusys.__version__ = "0.1.0"` を設定。

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（OS 環境変数の上書き回避ロジックあり）。
  - .env 行のパーサを強化（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - Settings クラスを提供し、各種設定（DB パス、API トークン、監視閾値、環境種別、PAPER_FILL_MODE 等）の取得とバリデーションを行う。
  - 環境変数が未設定の場合に明確な例外を投げるユーティリティを実装。

- 実行（run_execution.py / execution パッケージ）
  - ExecutionEngine 起動スクリプト `run_execution.py` を追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行と停止フラグ監視を実装。
  - paper_trading 環境に対する分離: KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）を用いることにより本番 DB と完全分離。
  - BrokerClientFactory を介したブローカークライアント生成。RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期利用可能現金を broker.get_available_cash() から初期化。

- 監視（run_monitoring.py / monitoring パッケージ）
  - システム監視ループ起動スクリプト `run_monitoring.py` を追加。プロセス優先度設定、SQLite（monitoring DB）と DuckDB 接続、SystemMonitor の check_once を定期実行。
  - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトへフォールバック。
  - 停止フラグ（data/stop_requested.flag）を監視し、存在したら安全にループを終了。
  - 監視処理は常に production の sqlite_path を使用（環境に依存しない監視データ蓄積）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同スコアは signal_rank 昇順）でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコア合計が 0 の場合は等金額へフォールバックし WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター別の既存保有比率が閾値を超える場合に同セクターの新規候補を除外。`unknown` セクターは上限適用対象外として除外しない。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知のレジームは警告のうえ 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: 各銘柄の発注株数計算（allocation_method: "risk_based" / "equal" / "score"）を実装。損切り・リスク許容率・単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash 超過時のスケールダウン）や残差処理（lot_size 単位での再配分）を考慮。`cost_buffer` により手数料/スリッページを保守的に見積もる。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を DuckDB 接続（prices_daily / raw_financials）を用いて実装。各種期間定数（1M/3M/6M/MA200/ATR20 等）を定義し、データ不足時の None 返却を明確化。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）計算（LEAD を用いたクエリ）と入力検証（horizons の範囲制約）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。データ不足（有効レコード < 3）の場合は None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を実装。
  - 実装方針として DuckDB + 標準ライブラリのみ（pandas など非依存）を採用。

- AI ニュース解析（kabusys.ai.news_nlp）
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメントスコア化する初期実装を追加。
  - calc_news_window: target_date に対するニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
  - score_news の設計・部分実装: 記事集約、バッチ送信（最大 20 銘柄/リクエスト）、JSON Mode 期待レスポンス、スコアクリップ（±1.0）、リトライ戦略（429/ネットワーク/5xx に対する指数バックオフ）等を仕様化。OpenAI API キー未設定時は明示的なエラーを返す。
  - 実装上のフェイルセーフ: API 失敗時はスキップして継続し、部分成功時に既存スコアを保護するようテーブル書き込みを行う（DELETE→INSERT の限定的置換）。

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 検証レポート生成スクリプトを追加。以下の指標を計算・表示:
    - システム稼働率（system_status）
    - 注文成功率 / 送信率（trade_logs）
    - リスク却下数（risk_logs）
    - レイテンシ（avg/max/P95）
  - P95 計算、期間フィルタ機能、閾値による PASS/FAIL 判定（デフォルト閾値をコード内定義）。
  - DB ファイル存在チェックとエラーメッセージを実装。

- ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定。権限不足や未サポート OS の場合は警告を出してスキップ。
  - set_cpu_affinity: カレントプロセスを最初 N コアへピン留めする機能を提供。引数検証と例外ハンドリングあり。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- 外部 API キーは引数または環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）から取得。未設定時は明示エラーや例外を出すようにしており、秘密情報の自動ログ出力は行わない設計を意識。

---

開発メモ / 既知の注意点
- news_nlp モジュールは設計方針・主な処理フローが実装済みだが、ファイル末尾が途中で切れている箇所があり（API 呼び出し後のレスポンス処理・DB 書き込みの完全な実装が残る可能性あり）、本番運用前に追加のテストとレビューが必要です。
- position_sizing では price の欠損時にエクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値や原価でのフォールバック実装が将来的に望まれます。
- .env 自動読み込みはデフォルトで有効。テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 依存: duckdb, psutil, openai（news_nlp を使用する場合）。実行環境にこれらをインストールする必要があります。

（以上）