# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

なお、本履歴は提供されたコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-04-16

### 追加 (Added)
- 基本パッケージ初期リリース: kabusys（バージョン 0.1.0）。
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時に MockBrokerClient を使用して本番 DB と分離（paper_trading 用 SQLite を使用）。
    - エンジンはスレッドで実行され、data/stop_requested.flag による安全停止、data/execution.pid の PID 管理をサポート。
    - RiskManager、OrderManager、Reconciler 等の組み立てロジックを含む。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
    - 停止フラグ検知で終了し、例外はログ出力して次ポーリングへフォールバック。
- 設定・環境読み込み
  - config.py: Settings クラスを導入し、環境変数／.env／.env.local から設定を自動読み込みする機能を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）。
    - .env ファイルのパースは export 形式やクォート・エスケープ、インラインコメントの扱いに対応。
    - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - デフォルト値・検証付き設定: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL、PAPER_FILL_MODE（instant/partial/never/reject）など。
    - DB パス、PID/kill フラグ、監視閾値などのプロパティを提供。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選択（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分を提供。スコア合計が 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の配分方式に対応。単元株（lot_size）で丸め、最大ポジション比率・利用率・コストバッファ考慮の aggregate scale-down を実装。価格欠損や上限に対する安全弁を用意。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（売却予定銘柄除外対応、"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームはフォールバック 1.0、警告あり）。
- 研究（Research）機能（DuckDB を使用）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: ATR20、相対 ATR、20 日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE などを使って PER/ROE を計算。
    - DuckDB 接続を受け取り SQL ベースで処理。データ不足時の None ハンドリング。
  - research.feature_exploration
    - calc_forward_returns: 複数ホライズン（例: 1/5/21 営業日）での将来リターンを一括取得。
    - calc_ic / rank / factor_summary: IC（Spearman 相関）計算、ランク化ユーティリティ、基本統計量計算を実装。外部ライブラリに依存しない純粋 Python 実装。
  - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポート。
- ニュース NLP（AI）モジュール
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores に書き込む処理を実装。
    - ターゲットウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティを提供。
    - 銘柄ごとに記事を集約し、1 銘柄あたりの最大記事数／文字数でトリム。
    - 最大バッチ 20 銘柄で API に送信、JSON Mode を期待する仕様。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ再試行を実装（上限あり）。
    - レスポンス検証、スコア ±1.0 のクリップ、部分成功時のテーブル置換戦略（DELETE → INSERT）を考慮。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（Fill/Send）、リスク却下数、API レイテンシ（平均/最大/P95）などを算出して標準出力に表示。
    - 閾値（稼働率・成功率・送信率・P95 レイテンシ）を定義し PASS/FAIL 判定を行う。
    - コマンドライン引数 --from/--to/--db に対応。PAPER_TRADING_SQLITE_PATH 環境変数で DB 指定可能。
- ユーティリティ
  - utils.process_priority: プロセス優先度設定ユーティリティを実装。
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応。nice 値と Windows 優先度クラスの抽象化。
    - set_cpu_affinity により CPU affinity 固定機能を追加（アクセス権限による失敗は警告でスキップ）。
    - 呼び出し元はプラットフォームを意識せず使用可能。
- DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を各ランチャーで呼び、監視用テーブルの存在を保証（冪等）。

### 変更 (Changed)
- なし（初回リリースのため変更点は特になし）。

### 修正 (Fixed)
- なし（初回リリースのため修正点は特になし）。

### 注意事項 / 既知の制約 (Notes / Known issues)
- ai.news_nlp は OpenAI API キー（OPENAI_API_KEY または引数 api_key）を必須とする。未設定時は ValueError を送出。
- calc_score_weights は全銘柄スコアが 0 の場合に等金額配分へフォールバックする（警告ログあり）。
- apply_sector_cap の価格欠損（price=0.0）時はエクスポージャーが過小評価される可能性があり、将来的にフォールバック価格の導入を検討する旨の TODO がある。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォームで失敗する可能性があるが、例外は捕捉して警告を出す挙動になっている。
- paper_verification_report は対象 DB のテーブルが存在しない場合に OperationalError を捕捉して安全に N/A を返すようになっている。
- 一部モジュールは DuckDB / SQLite / psutil / openai 等外部依存があるため、実行環境に応じて依存パッケージの導入が必要。

### セキュリティ (Security)
- なし（現状で明示的なセキュリティ修正は含まれていません）。

---

（以降のバージョンでは各モジュールの拡張、バグ修正、テスト追加、外部 API のフォールバックやレート制御の改善等を記録してください。）