# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

全般: この CHANGELOG は与えられたコードベース（バージョン __version__ = 0.1.0）から推測できる機能・実装・既知の挙動を基に作成しています。

## [Unreleased]

- （現時点で未リリースの変更はありません。次回リリース時にここに差分を記載してください）

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - サブパッケージ: data, strategy, execution, monitoring を公開。

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止判定にプロジェクト直下の `data/stop_requested.flag` を利用。
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority.set_process_priority を利用）。
    - SQLite（monitoring 用）と DuckDB へ接続し、monitoring DB テーブルを初期化。
    - check_once() 実行時の例外は捕捉してログ出力し、次のポーリングへフォールスルーする堅牢化。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）へ接続し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンはスレッドで実行され、停止フラグ検知で安全に停止処理を実行（pid ファイル：data/execution.pid を利用）。
    - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors 等）を設定し初期ポートフォリオ値に broker.get_available_cash() を使用。

- 設定管理
  - config.Settings クラスを実装。
    - .env 自動読み込み機能（プロジェクトルートに基づき .env → .env.local の順で読み込み、OS 環境変数は保護）。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 必須環境変数未設定時は ValueError を送出する _require() を提供。
    - 各種プロパティを提供（J-Quants / kabu API / LINE / DuckDB/SQLite パス / paper_trading 用パス / 監視設定 / CPU/MEM/DISK 閾値 / 環境種別判定等）。
    - `PAPER_FILL_MODE` の検証（instant, partial, never, reject のみ有効）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の検証。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する set_process_priority(level) を実装。許容値: "high" / "normal" / "low"。
    - 指定コア数にプロセスをピン留めする set_cpu_affinity(cpu_count) を実装。
    - 権限不足や未対応プラットフォームでは警告を出して安全にスキップ。

- 監視関連
  - monitoring.monitoring_db の初期化関数を利用する実行フロー（run_monitoring/run_execution 両方で呼び出し、監視テーブルの存在を保証）。

- Paper Trading ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを実装。
    - コマンドライン引数 `--from`, `--to`, `--db` をサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` と組み合わせて DB パスを解決。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計して出力。
    - PASS/FAIL 判定を行う閾値を定義（稼働率 99.0% など）し、要件を満たさない場合は FAIL として理由を列挙。
    - P95 計算や日付フィルタ、DB 存在チェック、SQLite の例外（テーブルが存在しない等）に対するフォールバック実装。

- ポートフォリオ構築・ポジションサイズ
  - portfolio.portfolio_builder
    - select_candidates（スコア降順＋タイブレークで signal_rank）を実装。
    - calc_equal_weights（等金額配分）を実装。
    - calc_score_weights（スコア加重、全スコアが 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment
    - apply_sector_cap：セクター集中の上限チェック。既存保有のセクター別時価で上限超過セクターをブロック（"unknown" セクターは除外しない）。
    - calc_regime_multiplier：レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルトマップと未知レジームでの 1.0 フォールバック）。
  - portfolio/position_sizing
    - calc_position_sizes：allocation_method（risk_based / equal / score）に基づく発注株数算出。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap のスケーリング（コストバッファを考慮）を実装。
    - 利用可能現金を基にスケールダウンし、残余キャッシュで端数の lot_size 単位を残差に基づいて追加配分するアルゴリズムを実装。

- リサーチ（DuckDB ベース）
  - research.factor_research
    - calc_momentum：1M/3M/6M リターン、200日移動平均乖離率を計算。
    - calc_volatility：20日 ATR、ATR%（ATR / close）、20日平均売買代金、出来高比率を計算。
    - calc_value：raw_financials と prices_daily を用い PER（EPS が 0/欠損の場合は None）と ROE を計算。
    - 各関数は DuckDB 接続と target_date を受け取り、(date, code) をキーとする dict のリストを返す。
  - research.feature_exploration
    - calc_forward_returns：指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得するクエリを実装。入力チェック（horizons は 1〜252 の正整数）を実装。
    - calc_ic：factor と forward returns を code で結合して Spearman ランク相関（IC）を計算。有効レコードが 3 未満の場合は None。
    - rank / factor_summary：ランク付け（同順位は平均ランク）と各列の基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージ __init__ で zscore_normalize をエクスポート（kabusys.data.stats から）。

- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメントスコア（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を記述。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1 銘柄当たり記事数と文字数の制限（最大 10 記事、最大 3000 文字）を実装してトークン肥大化を対策。
    - 再試行ロジック（429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ、最大リトライ回数 3）を備える。
    - レスポンス検証、スコアの ±1.0 クリップ、部分成功時に既存スコアを保護するため対象コードのみ削除→挿入する戦略を採用。
    - API キー未設定時は ValueError を送出。

### Changed
- run_monitoring と run_execution のプロセス優先度設定を共通ユーティリティへ集約（utils/process_priority）。
- .env 読み込みロジックを細かく実装し、.env.local を .env より優先して上書きする仕様を採用（ただし OS 環境変数は保護）。

### Fixed
- ポーリングループでの例外安全性を向上（monitor.check_once() の例外を捕捉してループを継続）。
- paper_verification_report: 日付フィルタ・テーブル未存在時の例外を捕捉してデフォルト値でレポート生成可能に。

### Known issues / Notes
- run_monitoring は「監視処理は環境にかかわらず本番 sqlite_path を使用する」という実装注記があるため、監視データが paper_trading 用 DB と分離されない点に注意が必要（意図的な設計の可能性あり）。
- portfolio/risk_adjustment.apply_sector_cap 内で price が欠損（0.0）の場合のエクスポージャー過少見積りに関する TODO コメントあり。将来的に前日終値等のフォールバックを検討する必要あり。
- news_nlp は外部 API（OpenAI）に依存するため、API 利用制限やコストに関する運用設計が必要。
- process_priority の優先度設定や CPU affinity 設定は権限に依存するため、実行環境により設定に失敗してスキップされる可能性がある（ログで警告が出る）。
- calc_forward_returns の horizons パラメータは 1〜252 の範囲チェックを行う（不正入力で ValueError）。
- 多くの箇所で ValueError を投げる入力検証があるため、実運用では環境変数や引数の妥当性を事前に検査することを推奨。

### Removed
- なし（初回リリース相当のため）。

### Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で渡す設計。キーが未設定の場合は処理が停止して ValueError を送出する。キーの取り扱いは環境変数保護（.env ファイルの読み込みは OS 環境変数を上書きしないデフォルトの動作）によって配慮。

---

備考:
- 本 CHANGELOG はソースコードから推測して作成しています。実際の開発履歴（コミット単位の差分や過去のバージョンとの比較）が利用可能であれば、より正確な CHANGELOG を作成できます。必要であればコミットログやリリース日付の具体情報を与えてください。