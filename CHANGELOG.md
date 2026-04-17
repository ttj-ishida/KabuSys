# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

- 次の変更履歴は、リポジトリ内のソースコード（src/kabusys 以下）から推測して作成しています。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 全体
  - プロジェクト初期リリース相当の機能群を追加。
  - パッケージメタ情報を `kabusys.__init__` にて v0.1.0 として定義。

- 実行／監視
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - 環境変数 KABUSYS_ENV に応じて paper_trading モード用の専用 SQLite を使用（data/paper_trading.db をデフォルト）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フローを実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の扱いを含む。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は実行環境に無関係に本番 sqlite_path を利用する設計。
    - 停止フラグ検知でループを終了する処理を実装。

- 設定管理
  - config.py：環境変数／.env の管理を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）。
    - .env/.env.local の読み込み順序および既存 OS 環境変数の保護（protected）を考慮した安全な読み込みロジックを導入。
    - export プレフィックスやクォート／エスケープ、インラインコメント処理等に対応した .env パーサを実装。
    - Settings クラスを導入し、各種設定値（DB パス、API キー、しきい値、環境判定プロパティなど）をプロパティとして提供。値検証（有効値チェック）を行う。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py：候補選定と重み計算機能を追加。
    - select_candidates：スコア降順・タイブレークに signal_rank を利用した候補選定。
    - calc_equal_weights、calc_score_weights：等分配およびスコア加重（全スコア0で等分配にフォールバック）。
  - portfolio/risk_adjustment.py：セクター上限とレジーム乗数を実装。
    - apply_sector_cap：既存ポジションのセクター曝露を計算し、セクター上限超過時に新規候補を除外（"unknown" セクターは除外しないポリシー）。
    - calc_regime_multiplier：レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告後 1.0 でフォールバック）。
  - portfolio/position_sizing.py：株数決定ロジックを実装。
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差に基づく追加配分ロジックを実装。

- ユーティリティ
  - utils/process_priority.py：クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows（HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）を吸収して set_process_priority を提供。
    - set_cpu_affinity によるプロセス固定（最初の N コア）を実装。
    - 権限不足や未対応 OS に対するフォールバックとログ出力を実装。

- リサーチ／ファクター計算
  - research/factor_research.py：モメンタム、ボラティリティ、バリュー系ファクター計算を追加（DuckDB を用いた SQL ベース実装）。
    - calc_momentum、calc_volatility、calc_value：prices_daily / raw_financials テーブルを参照して各種ファクター（mom_1m/3m/6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe など）を計算。
    - ウィンドウバッファや欠損データに対する扱い（一定行数未満は None）を明記。
  - research/feature_exploration.py：将来リターン、IC（スピアマン ρ）、ファクター統計サマリ等のユーティリティを追加。
    - calc_forward_returns：複数ホライズンをまとめて取得する効率的クエリを実装（horizons のバリデーションあり）。
    - calc_ic：ランク相関（Spearman）をランク計算→共分散方式で実装（同順位は平均ランク処理）。
    - factor_summary、rank：基本統計量とランク変換を実装。
  - research パッケージの __init__ で zscore_normalize（kabusys.data.stats 由来）などを公開。

- ツール
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）などを集計して標準出力へフォーマット付き出力。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。
    - P95 計算、閾値（稼働率/成功率/送信率/P95）に基づく PASS/FAIL 判定を搭載。
    - DB が存在しない場合のエラーメッセージを実装。

- AI ニュース NLP
  - ai/news_nlp.py：raw_news を OpenAI API（gpt-4o-mini）でスコアリングするロジックを実装（設計・定数・窓計算・バッチング・リトライ方針を含む）。
    - ニュース収集ウィンドウ（JST→UTC 変換）を calc_news_window で実装。
    - API キー解決ロジック、スコアクリップ、バッチサイズ、リトライポリシー等を定義。
    - （ファイル末尾で記事集約フェーズ呼び出しへ進む実装の痕跡あり）

### 変更 (Changed)
- .env 読み込みの優先順位を明確化（OS 環境 > .env.local > .env）、自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- Settings のプロパティに値検証を追加（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の許容値チェック）。
- run_monitoring.py / run_execution.py 起動時に set_process_priority("high") を最初に呼ぶようにし、プロセス優先度設定を初期化処理に組み込み。

### 修正 (Fixed)
- calc_score_weights：全銘柄のスコア合計が 0 の場合に等金額配分へフォールバック（分母 0 回避）。
- run_monitoring.py の MONITOR_POLL_INTERVAL 取得で 0 以下や不正値を検出した場合にデフォルトへフォールバックし、警告ログを出すように修正（time.sleep に無効値を渡す問題を回避）。
- utils/process_priority.py：権限不足や未実装メソッド発生時に例外を捕捉して警告ログを出し、プロセスの異常終了を回避する堅牢化を実施。
- portfolio/position_sizing.py：aggregate cap によるスケーリング時の丸め・残差分配ロジックを実装し、利用可能現金を超える発注を防止するアルゴリズムを改善。

### 注意点 / 既知の問題 (Known Issues)
- ai/news_nlp.py：ファイル末尾付近で処理が途中（_fetch_articles の結果利用以降の処理が表示されていない）であるため、完全な書き込み処理（DuckDB への置換/INSERT 等）の実装が未確認。実行前に該当関数の完全実装を確認してください。
- position_sizing の価格欠損時（price が 0.0）の扱いに関して、TODO コメントで前日終値等のフォールバック戦略が言及されており、欠損データがある場合の挙動に注意が必要。
- .env パーサは多くのケースに対応するが、極端なクォート／エスケープ構成や非 UTF-8 ファイルでの挙動は限定的（読み込み失敗時は警告）となる。

### セキュリティ (Security)
- OpenAI API キーなどの機密情報は Settings / .env により管理される設計。自動読み込みを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）も提供し、テスト環境などでの意図せぬリーク防止を考慮。

---

将来のリリースでは、未実装箇所の完成、テストカバレッジの追加、ログの構造化（例えば JSON ログ出力対応）、およびポートフォリオ構築ロジックのパラメータ化・外部化を予定してください。必要であれば、この CHANGELOG をベースに改訂（Unreleased セクションの追加やリリース日付の更新）します。