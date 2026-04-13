# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

全てのリリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 全体
  - 初期パブリックリリース。パッケージのバージョンは `0.1.0` に設定。
- 実行／監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite DB を使用（本番 DB と分離）。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立て、ExecutionEngine のセッション実行を含む。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（psutil によるクロスプラットフォーム対応）。
  - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - SQLite / DuckDB 接続の初期化、SystemMonitor の一回チェックとループ、例外ハンドリングを実装。
- 設定／環境変数
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env / .env.local の自動読み込み機能を実装。
    - 自動ロードを無効化するための環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
    - .env パーサーは export 形式・クォート・エスケープ・コメントを考慮した堅牢な実装。
    - 各種設定プロパティを提供（DBパス、PID/kill flag パス、閾値、ログレベル、環境種別判定、paper_trading 関連設定など）。
    - 設定のバリデーション（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。
- ポートフォリオ構築
  - portfolio モジュール（純粋関数群）を追加:
    - portfolio_builder: 候補選定 (select_candidates)、等配分／スコア配分 (calc_equal_weights, calc_score_weights)。
    - risk_adjustment: セクター上限適用 (apply_sector_cap)、市場レジームに応じた乗数計算 (calc_regime_multiplier)。
    - position_sizing: 各銘柄の発注株数算出 (calc_position_sizes)、risk_based / equal / score の配分方式対応、単元株丸め、aggregate cap のスケーリングロジック（lot 単位の残差配分を含む）。
- リサーチ／ファクター計算
  - research モジュールを追加:
    - factor_research: モメンタム (calc_momentum)、ボラティリティ (calc_volatility)、バリュー (calc_value) の DuckDB ベースのファクター計算関数。
    - feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（Spearmanランク相関）計算 (calc_ic)、統計サマリー (factor_summary)、ランク関数 (rank)。
    - DuckDB を用いた SQL ベースの集計処理とメモリ内処理の組合せを採用。
- AI ニュース NLP
  - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルへ書き込むロジックを追加。
    - 日時ウィンドウ計算（JST基準の前日 15:00 ～ 当日 08:30 を UTC に変換）を提供。
    - 記事集約、銘柄ごとのトリム（記事数・文字数上限）、最大バッチサイズ (_BATCH_SIZE=20) によるバッチ送信。
    - 429 / タイムアウト / 5xx 等のエラーに対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ。
    - 部分成功時に既存スコアを保護する（対象コード絞り込みで DELETE→INSERT を実行）。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均／最大／P95）を算出してコンソール出力。
    - P95 の独自実装、日付フィルタの WHERE 句組立、閾値に基づく PASS/FAIL 判定。
    - コマンドライン引数 (--from / --to / --db) と環境変数 PAPER_TRADING_SQLITE_PATH による DB 指定対応。
- ユーティリティ
  - utils.process_priority: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/macOS/FreeBSD）を吸収し、優先度レベル ("high"/"normal"/"low") の設定を提供。
    - CPU affinity を最初の N コアに固定する関数 set_cpu_affinity を追加（権限不足時は警告してスキップ）。
  - その他のパッケージ初期化ファイル等を追加。

### 変更 (Changed)
- 監視周りの挙動
  - run_monitoring: 監視プロセスは KABUSYS_ENV に依存せず設定された本番 sqlite_path を使用するように明示。（監視データは本番 DB として運用する想定）
- DB 接続
  - run_execution/run_monitoring: 起動時に DuckDB と SQLite の接続を確立して明示的にクローズする実装に統一。
- 設定自動ロード
  - config.py: .env 自動ロードの優先順位を OS 環境変数 > .env.local > .env に明確化。OS側の既存環境変数は保護（上書き不可）される。

### 修正 (Fixed)
- .env パーサーの堅牢化
  - export 形式、クォート内のバックスラッシュエスケープ、インラインコメント、空行・コメント行の扱い等に対応し、誤読を低減。
- 各モジュールの入力バリデーション強化
  - Settings の enum 風設定（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）に対する値チェックを追加し、不正値時に明確なエラーを投げるようにした。
  - feature_exploration.calc_forward_returns: horizons の入力検証（正の整数かつ <= 252）を追加。
- ポジションサイジングの安全弁
  - calc_position_sizes: price が無効な場合のスキップ、lot_size 単位丸め、aggregate cap 超過時のスケールダウンと残差配分ロジックを実装（過剰投下の防止）。
- モニタリングのポーリング間隔取得
  - MONITOR_POLL_INTERVAL の値が不正（非数や <= 0）の場合に警告を出してデフォルトにフォールバック。

### 注意事項 / 破壊的変更 (Breaking changes / Notes)
- 環境変数の必須チェック
  - Settings の一部プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定の場合 ValueError を投げる。運用前に .env の整備または OS 環境変数の設定が必要。
- .env 自動読み込みの挙動
  - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト環境等での安定化に有用）。
- run_monitoring は監視データを本番 sqlite_path に書き込む設計のため、テストや paper_trading で別 DB を使いたい場合は sqlite_path を切り替えるか、run_monitoring を直接修正してください。

### 既知の制限 / 将来の改善予定 (Known issues / TODO)
- position_sizing の price 欠損時フォールバック
  - current implementation notes: price が欠損 (0.0) の場合にエクスポージャーが過小見積もられる可能性がある。将来的に前日終値や取得原価をフォールバックとして利用する検討を予定。
- ai.news_nlp
  - OpenAI とのやり取りに関しては堅牢な設計（バッチ化・リトライ・検証）を導入しているが、API 利用周り（レート管理・エラー時の部分的保存など）の運用テストを推奨。
- DuckDB の executemany の制約に注意
  - ai.news_nlp の書き込み・その他で DuckDB executemany を使用する場合、params が空でないことを確認する実装が必要（既に注意書きを含む）。

---

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして使用する場合は、CI/テスト結果や運用上の注意点を反映して適宜修正してください。）