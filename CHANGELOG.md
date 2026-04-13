# Changelog

すべての注目すべき変更履歴はここに記録します。本書式は「Keep a Changelog」準拠です。

なお、ここに記載した項目は提供されたソースコードからの推測に基づいています（実装上のコメントや関数・モジュール名・ログ出力などを元に要点を抽出しています）。

## [Unreleased]

- （現時点の作業中の変更点・追加予定はここに記載してください）

---

## [0.1.0] - 2026-04-13

初回リリース。以下の主要コンポーネントと機能を実装しました。

### Added
- 全体
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - Settings クラスによる環境変数・.env ファイルからの設定管理を実装。
    - プロジェクトルートから .env / .env.local を自動読込（OS 環境変数優先、.env.local は上書き）および読み込み無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - 必須環境変数の取得関数 _require による未設定時の明示的エラー。
    - 各種設定プロパティ（DBパス、PIDファイルパス、しきい値、環境モード判定等）を提供。
    - PAPER_FILL_MODE 等の値検証を実装（許容値チェックと不正値時の例外）。

- 実行・監視起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを実装。
    - プロセス優先度を開始時に設定（set_process_priority）。
    - 環境に応じて paper_trading 用の専用 SQLite DB を使用（settings.is_paper）。
    - DuckDB 接続の利用（settings.duckdb_path）。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - init_monitoring_db を呼んで監視テーブルの存在を保証（冪等操作）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。
    - チェックループで例外をハンドリングして次のポーリングへ継続するフェイルセーフ動作。
    - KeyboardInterrupt による安全終了。

- DB / 分析関連
  - DuckDB を利用したリサーチ用モジュールを実装。
    - research.factor_research:
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の算出（prices_daily テーブル参照）。
      - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率の算出。
      - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE 計算（最新報告値の取得ロジック含む）。
    - research.feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。
      - rank / factor_summary: ランク付け・統計サマリ計算ユーティリティ。
    - research パッケージのエクスポートに zscore_normalize を含めた公開 API。

- ポートフォリオ構築
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選定（同点時は signal_rank で tiebreak）。
    - calc_equal_weights / calc_score_weights: 等分配とスコア加重の重み計算（スコア全て 0 の場合は等分配へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック。既存ポジションのセクター別エクスポージャー計算と新規候補フィルタリング。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数実装（未知レジームはフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出。
    - 単元株（lot_size）丸め、max_position_pct や max_utilization、cost_buffer を考慮した aggregate cap ロジック、スケーリングと端数配分の実装。

- ユーティリティ
  - utils.process_priority:
    - プロセス優先度設定ユーティリティを実装（Windows・POSIX の差分吸収）。
    - set_process_priority(level)（high / normal / low）: psutil を用いた nice / priority 設定、例外・権限不足は警告でスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能（権限不足時は警告でスキップ）。

- AI / ニューススコアリング
  - ai.news_nlp:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores に書き込む処理を実装。
    - タイムウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）。
    - 記事集約（1銘柄あたり最大記事数・最大文字数でトリム）。
    - バッチ送信（最大 20 銘柄/コール）、JSON Mode 出力期待、スコアを ±1.0 にクリップ。
    - 429 / ネットワーク断 / 5xx に対する指数バックオフリトライを実装（最大リトライ数 _MAX_RETRIES）。
    - レスポンス検証・部分成功時の DB 書き換え戦略（該当コード群のみ DELETE→INSERT）を設計。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI スクリプトを実装。
    - システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計して判定（PASS/FAIL）するロジック。
    - コマンドライン引数 --from / --to / --db をサポート。
    - P95 計算、SQL の日付フィルタ適用、データ欠損時の N/A の扱いを実装。
    - デフォルトの合格基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）を定義。

### Changed
- DB 初期化
  - init_monitoring_db を実行して監視用テーブルが存在することを各起動スクリプト（実行・監視）で保証するように変更（冪等）。
- run_monitoring
  - MONITOR_POLL_INTERVAL の値検証を強化。1 未満や不正な値は警告してデフォルトにフォールバックする（time.sleep への不正渡し回避）。

### Fixed
- 設定検証
  - Settings.env / LOG_LEVEL / PAPER_FILL_MODE の不正値に対して明示的な ValueError を投げるようにし、誤設定を早期検出できるようにした。
- レジーム乗数
  - 未知のレジーム値が来た場合は警告を出して 1.0 でフォールバックする安全策を実装。

### Security / Robustness
- AI スコアリング
  - OpenAI API キーが未設定の場合は ValueError を出して早期終了させるチェックを実装。
  - API 呼び出し失敗時にリトライとフェイルセーフ（失敗してもシステム継続）を明示。
- 汎用ログ出力
  - 各主要処理で logger を適切に使用し、エラー発生時に例外情報をログに残すようにした（特に監視ループ・API 呼び出し周り）。

### Documentation / Comments
- 多数のモジュールで設計意図・アルゴリズム・制約（例: 営業日とカレンダー日差・欠損データ時の振る舞い）をコメントに記載し、将来の拡張点（lot_size の銘柄別化・価格フォールバック等）を注記。

---

未記載の細かな実装やマイナーな内部リファクタはソースコメント・関数実装を参照してください。必要であれば、リリースノートの粒度をより細かく分けてバージョン履歴（マイナー・パッチ単位）を作成しますので、希望の粒度を教えてください。