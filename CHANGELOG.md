# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して自動的に作成した要約です。

## [Unreleased]

（該当なし）

## [0.1.0] - 2026-04-17

初回リリース。システム全体のコア機能を実装しました。以下は主要な追加・改善点と注意事項のサマリです。

### Added
- 全体
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - Settings クラスによる環境変数ベースの設定管理を追加。.env 自動読み込み機能、.env/.env.local の優先度、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を実装。
  - .env ファイルの堅牢なパース実装（クォート／エスケープ、コメント処理、`export KEY=val` 形式対応）。
  - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL 等）と必須値チェック（_require）。

- 実行・監視
  - run_execution.py: ExecutionEngine 起動スクリプト
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - PID ファイル、停止フラグ（data/stop_requested.flag）による安全な起動/停止制御。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告の上デフォルトへフォールバック。
    - 監視は環境に関係なく本番用 sqlite_path を使用。
    - 停止フラグ検知、例外捕捉でループを継続する堅牢化。init_monitoring_db 呼び出しで監視テーブルを保証。

- データ・リサーチ
  - research パッケージを追加
    - factor_research: calc_momentum / calc_volatility / calc_value — DuckDB を利用したファクター計算（ウィンドウ関数、欠損ハンドリング）。
    - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank — 将来リターン・IC（Spearman）・統計サマリ等のユーティリティ（外部依存なし、標準ライブラリのみ）。
    - research.__init__ で zscore_normalize を含むエクスポートを集約。
  - DuckDB 接続を前提とした、prices_daily / raw_financials テーブル参照の定義。

- ポートフォリオ構築
  - portfolio モジュールを追加
    - portfolio_builder: select_candidates / calc_equal_weights / calc_score_weights（全スコアが 0 の場合に等金額配分へフォールバック）。
    - risk_adjustment: apply_sector_cap（セクター集中制限、unknown セクターの扱いを明示）、calc_regime_multiplier（bull/neutral/bear マップ、未知レジームはフォールバック）。
    - position_sizing: calc_position_sizes（risk_based / equal / score の割当方式、単元株（lot_size）で丸め、アグリゲートキャップのスケーリングと端数配分ロジックを実装）。
  - portfolio.__init__ で主要関数群を公開。

- AI / NLP
  - ai.news_nlp モジュールを追加
    - raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores テーブルへ書き込む処理を設計。
    - タイムウィンドウ計算（JST→UTC 変換）、記事トリム（最大記事数・最大文字数）、銘柄バッチ処理（最大 20 銘柄／コール）、リトライ（指数バックオフ）とレスポンス検証、スコアクリッピング（±1.0）、部分置換（DELETE→INSERT）による安全な書き込み。
    - API キーの未設定時に ValueError を送出。

- ツール
  - tools.paper_verification_report スクリプトを追加
    - Paper Trading DB（デフォルト data/paper_trading.db）から各種指標を集計し検証レポートを標準出力へ出力。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数等。合格基準の閾値設定および Pass/Fail 判定を実装。
    - P95 計算、日付フィルタ、DB 存在チェック、sqlite の OperationalError を考慮したフォールバックを実装。

- ユーティリティ
  - utils.process_priority: set_process_priority / set_cpu_affinity を追加（Windows と POSIX の差分吸収、権限エラーは警告ログでスキップ）。
  - utils パッケージを追加（将来ユーティリティ群を追加予定）。

### Changed
- 設計方針の明確化
  - 研究・リサーチ系機能は外部 API を呼ばず DuckDB / ローカルデータのみ参照する方針を明示。
  - 時刻処理で datetime.today()/date.today() を参照しない（ルックアヘッドバイアス対策）旨を各所に記載。
- DB 接続
  - run_execution と run_monitoring で DuckDB + SQLite を併用。監視テーブル保障のため init_monitoring_db を起動時に呼び出す（冪等処理）。

### Fixed
- .env パースの堅牢化
  - クォートあり／なしのパース、バックスラッシュによるエスケープ、インラインコメント処理、`export ` プレフィックス対応などを実装し .env の柔軟な記述に対応。
- ポジションサイズ計算
  - weight 正規化が期待通りでないケース（全スコア 0）に備えて calc_score_weights で警告を出し等金額配分へフォールバック。
  - aggregate cap のスケーリングで lot_size 単位丸めや端数の配分ロジックを追加し、available_cash を超えないように安定化。
- プロセス優先度設定の安全化
  - 未対応 OS や権限不足時に例外を投げず警告ログでスキップするよう修正。
- run_monitoring のポーリング間隔
  - MONITOR_POLL_INTERVAL が 0 以下や非整数の場合に ValueError を避け、警告の上でデフォルトへフォールバックするように修正。
- ai.news_nlp
  - OpenAI の失敗（429 / ネットワーク / タイムアウト / 5xx）に対してエクスポネンシャルバックオフでリトライするロジックを導入。部分失敗時に既存データを保護するために書き換え対象の code を限定して DELETE/INSERT を行う仕様。

### Security
- API キー / 秘密値
  - J-Quants / kabu ステーション等の必須トークンは Settings のプロパティで未設定時に ValueError を送出し、明示的な設定を要求。
  - OpenAI API キーが未設定の場合は ai.news_nlp.score_news がエラーを吐くため、鍵の漏洩や未設定に注意。

### Notes / Known limitations
- run_monitoring は監視用 DB に常に settings.sqlite_path を使用する（環境に依らない仕様）。paper_trading と完全に分離したい場合は運用上の注意が必要。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_map の導入を想定する旨が TODO コメントとして残っています。
- apply_sector_cap は price_map に価格が欠損（0.0）だとエクスポージャーを過少見積もる可能性があり、前日終値等のフォールバックは将来の改善項目です。
- ai.news_nlp の実装は OpenAI との入出力形式に依存するため、API 仕様変更に備えたテストとエラーハンドリングが必要です。

---

この CHANGELOG はコードの実装内容から推測して作成したものであり、実運用の変更履歴やコミットログと完全に一致するものではありません。必要に応じて補足・修正してください。