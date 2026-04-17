# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
文書は日本語です。

現在のバージョン: 0.1.0

## [Unreleased]

（現時点で未リリースの変更はありません。）

## [0.1.0] - 2026-04-17

初回公開リリース。

### 追加 (Added)
- 全体
  - パッケージ初期版を公開（kabusys v0.1.0）。
  - パッケージメタ情報: __version__ = "0.1.0"。

- 環境設定・設定管理
  - Settings クラスを実装。環境変数経由で各種設定（J-Quants / kabu API / LINE / DB パス / 監視閾値 等）を取得可能に。
  - .env 自動読み込み機能を追加（プロジェクトルートの検出: .git または pyproject.toml を基準）。優先順位は OS 環境変数 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサ実装。以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォートとバックスラッシュエスケープ
    - インラインコメントの合理的取り扱い（クォート有無に応じた挙動）
  - 各種設定値に対するバリデーションを実装:
    - KABUSYS_ENV の有効値チェック（development / paper_trading / live）
    - LOG_LEVEL の有効値チェック
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）

- 実行・監視スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等のコンポーネントを組み立て、ExecutionEngine を起動するワークフローを提供。
    - 実行中の停止は data/stop_requested.flag を監視（停止フラグによる安全停止）。
    - エンジンの PID 管理とデーモンスレッド運用をサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はフォールバックしてログ出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（運用上の意図的仕様）。
    - 停止フラグ（data/stop_requested.flag）を監視して安全にループを終了。
  - 起動時にプロセス優先度を "high" に設定する初期処理を run_execution/run_monitoring に追加。

- データベース関連
  - DuckDB 接続の利用をサポート（研究・ファクター計算向けに duckdb 接続を受け渡す設計）。
  - 監視用テーブル初期化関数 init_monitoring_db の利用により、監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を返す。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計が 0 の場合は等分にフォールバックして警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック。既存保有のセクターエクスポージャ計算と候補除外のロジック（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告を出して 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 各銘柄の発注株数計算を実装。
      - allocation_method: "risk_based" / "equal" / "score" に対応。
      - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ見積）を考慮したスケールダウン・残余配分ロジックを実装。

- 研究・ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算（target_date 以前の最新財務データを使用）。
    - すべて DuckDB における SQL ウィンドウ関数を活用した実装。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括で計算。
    - calc_ic: スピアマンのランク相関（IC）を計算。データ不足・定数分散等に対する安全処理を実装。
    - rank / factor_summary: ランク化と統計サマリー（count/mean/std/min/max/median）を提供。
  - research パッケージは外部ライブラリ（pandas 等）に依存せず、標準ライブラリと DuckDB のみで実装。

- ニュース NLP（AI）
  - ai.news_nlp:
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルへ書き込むためのロジックを追加。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの文字数・記事数制限、スコアの ±1.0 クリップ、API リトライ（指数バックオフ）等を実装。
    - 出力の厳密な JSON 検証と部分更新（該当コードのみ DELETE → INSERT）により、部分失敗時に既存データを保護する設計。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算ユーティリティを提供。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポートを生成する CLI を追加。
    - 検証指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - CLI オプション: --from / --to（YYYY-MM-DD）、--db（DB パス）。PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能。
    - デフォルト閾値を定義し、PASS/FAIL の判定ロジックを実装。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX を吸収してカレントプロセスの優先度を設定（high/normal/low）。権限不足や未サポート OS 時は警告を出してスキップ。
    - set_cpu_affinity: カレントプロセスの CPU affinity を最初の N コアに固定するユーティリティを追加（N が None の場合は何もしない）。権限不足時は警告でスキップ。

### 変更 (Changed)
- 環境・DB の扱い
  - 監視（run_monitoring）は設計上、KABUSYS_ENV に関係なく本番 sqlite_path を使用するように明示（監視データは本番 DB を参照する運用を想定）。
  - 実行エンジン（run_execution）は paper_trading 環境では paper_sqlite_path を使用し、本番 DB と分離。これにより Paper 環境と Live 環境のデータ隔離を保証。

- ログ・例外処理
  - MONITOR_POLL_INTERVAL 等の環境値が不正な場合にデフォルトへフォールバックし、警告ログを出す挙動を採用（運用での致命的停止を回避）。
  - 各種 I/O / DB 操作での例外を捕捉してフェイルセーフ動作（例: monitoring.check_once のエラーはループ継続、AI API の失敗は部分スキップ）を基本方針に。

### 修正 (Fixed)
- .env 読み込みでのファイルオープン失敗時に警告を出してスキップするハンドリングを追加（テスト環境での権限等を想定）。
- research.feature_exploration.rank: 同順位の平均ランク算出で丸め誤差による ties 判定漏れを回避するため round(..., 12) を導入。
- position_sizing のスケールダウン処理における残差配分ロジックを安定化（lot_size 単位の追加配分を残差順に行い、再現性を確保）。

### その他 (Other)
- ドキュメント的コメント（docstring）を各主要モジュールに充実させ、設計思想・計算式・引数/戻り値の説明を併記。
- TODO コメントなどで将来的拡張ポイント（銘柄別 lot_size、価格フォールバック等）を明示。

### 既知の制約 / 注意点
- ai/news_nlp モジュールは OpenAI API キーを必要とし、キー未設定時は ValueError を送出するため、運用時は OPENAI_API_KEY の設定が必要。
- calc_momentum / calc_volatility 等は DuckDB の prices_daily / raw_financials を前提としているため、これらのテーブルが存在しない場合は OperationalError となる（呼び出し元でハンドリングが必要）。
- run_monitoring は監視データに対して本番 DB を使うため、テスト環境で監視を実行する際は注意が必要（本番 DB を汚さないように設定の上で実行すること）。

---

リリースに関する問い合わせや不具合報告は issue を作成してください。