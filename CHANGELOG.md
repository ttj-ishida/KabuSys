# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
主なリリースと実装内容を、ソースコードから推測して日本語でまとめています。

## [Unreleased]

### Added
- news_nlp モジュールの継続実装予定
  - OpenAI API を用いたニュースのセンチメント集約/スコアリング機能の残り処理（記事フェッチの続き・API バッチ送信・DB 書き込みの完全実装）
- テストと CI の整備（モジュール単位のユニットテスト、DuckDB を使ったリサーチ関数の統合テスト等）
- 銘柄ごとの lot_size を stocks マスタから取得する対応（現状は全銘柄共通 lot_size=100）
- 価格欠損時のフォールバックロジック（risk_adjustment の TODO：前日終値や取得原価での補完）

### Fixed / Changed
- 既知の制約や TODO の解消予定（詳細は Issue を参照）

---

## [0.1.0] - 2026-04-17

初期リリース。自動売買システム KabuSys のコア機能群を実装。

### Added

- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 設定読み込み・管理（kabusys.config）
  - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）
  - .env / .env.local の読み込み優先度（OS 環境変数 > .env.local > .env）
  - .env パーサーで以下に対応:
    - export KEY=val 形式
    - シングル／ダブルクォート、バックスラッシュエスケープ
    - コメント（クォートなしの場合の '#' の扱い）
  - Settings クラスで環境変数をプロパティ化:
    - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - KABUSYS_ENV 検証（development / paper_trading / live）
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
    - 各種監視閾値（CPU/MEMORY/DISK）や PID/KILL フラグのパス
    - ログレベル検証

- 実行・監視プロセス起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプト（プロセス優先度を最初に High に設定）
    - paper_trading 環境では paper_trading 用 SQLite を使用（環境分離）
    - BrokerClientFactory を介してブローカークライアントを生成（paper 環境では MockBrokerClient を想定）
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session をバックグラウンドスレッドで実行
    - 停止フラグ（data/stop_requested.flag）を監視し安全に停止
    - Execution 用 PID ファイル管理（data/execution.pid）
    - RiskConfig のデフォルトパラメータ（max_position_pct 等）を設定、初期ポートフォリオ値を broker.get_available_cash() で取得
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（意図的な設計）
    - 停止フラグ検知でループ終了、例外ハンドリングで耐障害性を確保

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db(sqlite_conn) を呼び出して監視テーブルの存在を保証（冪等）

- ユーティリティ
  - process_priority モジュール（kabusys.utils.process_priority）
    - set_process_priority(level) で Windows / POSIX を吸収してプロセス優先度を設定
    - set_cpu_affinity(cpu_count) でプロセスの CPU affinity 固定（権限／未対応 OS は警告でスキップ）
    - 権限不足や未実装 API を安全に扱うための例外処理とログ出力

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で上位 N 件抽出（タイブレークは signal_rank）
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）
  - risk_adjustment
    - apply_sector_cap: セクター集中上限 (max_sector_pct) に基づき新規候補をフィルタ（"unknown" セクターは免除）
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）
  - position_sizing
    - calc_position_sizes: allocations を元に銘柄ごとの発注株数を計算
      - allocation_method: "risk_based" / "equal" / "score"
      - 単元株（lot_size）丸め、1 銘柄上限および aggregate cap（available_cash）によるスケールダウン
      - cost_buffer を考慮した保守的なコスト見積りと残差分の lot 単位配分ロジック
      - TODO: 将来的な銘柄別 lot_size 対応を想定する記述あり

- 研究（research）モジュール
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily から計算
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比を計算（欠損扱いの扱いに注意）
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（EPS が 0 の場合は None）
  - feature_exploration
    - calc_forward_returns: 将来リターン（例: 翌日・翌週・翌月）を LEAD を用いて計算
    - calc_ic: スピアマンのランク相関（IC）計算（有効レコード < 3 は None）
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー
    - rank: 同順位は平均ランクで処理するランク関数
  - research パッケージから zscore_normalize をエクスポート（kabusys.data.stats を参照）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の集計と Pass/Fail 判定基準を実装
    - P95 計算、日付フィルタ、DB 存在チェック、OperationalError に対する耐性を実装

- AI ニュース NLP（部分実装）
  - ai/news_nlp.py（実装の多くを含むが、ソースは途中で切れている）
    - ニュース収集ウィンドウ計算（JST→UTC 変換）を実装（calc_news_window）
    - OpenAI（gpt-4o-mini）を使ったバッチスコアリングを想定した設計（バッチサイズ、モデル、リトライ方針、スコアクリップ等）
    - 設計方針: JSON 出力厳格化、トークン肥大化対策（最大記事数・文字数トリム）、429/5xx の指数バックオフ、部分成功時の DB 保護（スコア対象コードのみ置換）など
    - 注意: score_news の記事収集フェーズが未完（ソースが途中で切れているため本番運用前に完成が必要）

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Known limitations / Notes
- run_monitoring は実装上「監視は環境にかかわらず本番 sqlite_path を使用する」仕様になっているため、開発環境で監視を分離したい場合は注意が必要。
- ai/news_nlp モジュールはファイル末尾が未完であり、実運用前に記事取得・API 呼び出し・レスポンス検証・DB書換ロジックの完成が必要。
- position_sizing と apply_sector_cap は価格データ欠損時のフォールバックが簡易（現状では price が 0.0 の場合にスキップ）であり、将来的に前日終値等のフォールバック実装が検討される。
- set_process_priority / set_cpu_affinity は権限不足や未対応 OS の場合は警告ログを出して安全にスキップする仕様。

### Security
- 外部 API キー（OpenAI など）は Settings を通じて環境変数で管理する設計。API キー未設定時は明示的に例外を投げたり、エラー表示を行う実装箇所あり。

---

（注）本 CHANGELOG は現行ソースコードの実装・コメント・ドキュメント文字列から推測して作成しています。実際のコミット履歴や運用履歴とは差異がある可能性があります。必要であれば Git のコミットログに基づく厳密な CHANGELOG を生成できます。