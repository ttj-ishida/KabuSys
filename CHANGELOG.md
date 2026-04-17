# Changelog

すべての notable な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

注: 以下はリポジトリ内のソースコードから機能追加・挙動を推測して作成した初期の変更履歴です。

## [Unreleased]

（現在の開発中の変更はここに記載）

---

## [0.1.0] - 2026-04-17

初回リリース。以下の主要コンポーネントを実装・追加しました。

### Added
- 全体
  - パッケージ初期版を公開。モジュール群を通して自動売買システムの基本機能（監視、実行、ポートフォリオ構築、リサーチ、AI ニューススコアリング、ユーティリティ）を提供。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可。
    - 監視は環境にかかわらず本番用の SQLite パス（Settings.sqlite_path）を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知処理を実装。
    - 起動時にプロセス優先度を設定する仕組み（utils.process_priority）を呼び出す。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite DB（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てを実装。
    - Engine をスレッドで起動し、停止フラグ（data/stop_requested.flag）により安全停止する仕組みを実装。
    - 実行用 PID ファイル（data/execution.pid）を扱う設定を含む。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート判定は .git または pyproject.toml を探索）。
    - `.env` / `.env.local` の読み込み順序と上書きルール（OS 環境変数を保護）を定義。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
    - export 形式、クォート付き値、インラインコメント等を考慮した .env 行パーサを実装。
    - Settings クラスで各種設定アクセス（DB パス、API トークン、paper_trading モード、監視閾値、PID/kill flag パス、ログレベル判定等）を提供。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - BUY シグナルの候補選定 `select_candidates`、等分配 `calc_equal_weights`、スコア加重 `calc_score_weights` を実装。
    - 全銘柄のスコアが 0 の場合は等金額配分にフォールバックし警告を出す。

  - portfolio.risk_adjustment
    - セクター集中制限を適用する `apply_sector_cap` を実装（売却予定銘柄や unknown セクターの扱いを考慮）。
    - 市場レジームに応じた乗数 `calc_regime_multiplier` を実装（bull/neutral/bear とフォールバック挙動）。

  - portfolio.position_sizing
    - position size（発注株数）を計算する `calc_position_sizes` を実装。
    - `risk_based` / `equal` / `score` の割付方式をサポート。
    - 単元（lot_size）丸め、1銘柄上限・アグリゲート上限、cost_buffer（手数料/スリッページ見積り）に基づくスケールダウンロジックと端数の再配分アルゴリズムを実装。

- 監視／ユーティリティ
  - utils.process_priority
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収するプロセス優先度設定 `set_process_priority` を実装（psutil 使用）。
    - CPU アフィニティ設定 `set_cpu_affinity` を実装。
    - アクセス権限・未対応 OS に対する安全なフォールバックとログ出力を実装。

- リサーチ
  - research.factor_research
    - DuckDB を用いたファクター計算関数を実装: `calc_momentum`, `calc_volatility`, `calc_value`（各関数は prices_daily / raw_financials を参照）。
    - window／lag を用いた SQL 実装で欠損・ウィンドウ不足時の None ハンドリングを行う。
  - research.feature_exploration
    - 将来リターン計算 `calc_forward_returns`（ホライズン検証あり）。
    - IC（スピアマン）計算 `calc_ic`、ランク化ユーティリティ `rank`、統計サマリー `factor_summary` を実装。
    - 外部ライブラリに依存せず、標準ライブラリのみで実装。

- AI / ニュース NLP
  - ai.news_nlp
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルに書き込む処理の骨子を実装。
    - タイムウィンドウ計算（JST ベース→UTC 変換）`calc_news_window`、バッチ処理、API リトライ（指数バックオフ）、レスポンス検証、スコアクリップ処理を設計。
    - API キー解決（引数 or OPENAI_API_KEY 環境変数）、失敗時は明示的に例外を出す。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成ツールを追加。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を集計し、しきい値と比較して PASS/FAIL レポートを標準出力へ出力する CLI を実装。
    - P95 計算、日付フィルタ、DB 存在チェック、SQL の頑健な例外処理を含む。

- パッケージ公開 API
  - research と portfolio パッケージの __init__ で外部利用インターフェースを整理。

### Changed
- DB/起動挙動
  - 監視（run_monitoring）は環境設定にかかわらず production の sqlite_path を使用する旨を明記（環境切り替えの混乱を避ける設計判断）。
  - run_execution は paper_trading 時に専用 DB を使うことで本番データと完全分離する挙動を明確化。

- .env 読み込み
  - 自動 .env 読み込みはプロジェクトルート自動検出に基づくように変更。CWD に依存せずパッケージ配布後も安定動作する設計。

### Fixed
- 安全性・堅牢性向上
  - MONITOR_POLL_INTERVAL の解析で 0 以下や非整数値が与えられた場合にデフォルトへフォールバックし警告を出すように修正（time.sleep に渡す不正値対策）。
  - .env 行解析で export 形式やクォート、エスケープ、インラインコメント処理を正しく扱うよう実装（誤パース対策）。
  - DuckDB / SQLite の接続を finally ブロックで確実にクローズするようにし、リソースリークを防止。
  - calc_score_weights: 全スコアが 0 の場合に等分配にフォールバックして警告を出力するようにし、ゼロ除算を回避。
  - apply_sector_cap: unknown セクターは上限チェックの対象外とし、安全に扱う実装。
  - calc_forward_returns: horizons 引数の検証を追加（正の整数かつ <= 252）。

- ロギング・フェイルセーフ
  - psutil によるプロセス優先度設定や CPU affinity 設定でアクセス拒否や未実装 API が発生した場合に警告ログを出して処理をスキップするようにして、起動失敗を回避。

### Known issues / Notes
- ai.news_nlp の実装は主要な設計（ウィンドウ計算、バッチ送信、リトライ、レスポンス検証）を備えていますが、実際の API 呼び出し周り（チャンク作成、結果の DB 書き込み処理）が未完またはファイル末尾で切れている箇所が見られます。実運用には追加の検証とエラーハンドリング実装が必要です。
- position_sizing の price が欠損（0.0）の場合にエクスポージャー推定が過少見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨コメントが残されています。

---

メジャー / マイナーリリースの運用方針に従い、次回以降の変更は [Unreleased] セクションに追加して公開時に日付付きのバージョンエントリを切り出してください。