# CHANGELOG

すべての注目すべき変更を記載します。本ドキュメントは Keep a Changelog の形式に準拠しています。

注意: 以下の項目は、提供されたコードベースの内容から推測してまとめたものであり、実際のコミット履歴ではありません。

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 基本機能の初期実装を追加（KabuSys v0.1.0 相当）。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を設定（`set_process_priority("high")`）。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite を使用して本番 DB と分離。
    - ブローカークライアント生成（BrokerClientFactory）、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。
    - 起動時にプロセス優先度を設定。

- 設定管理
  - config.py
    - プロジェクトルート（.git または pyproject.toml）を基準に .env 自動読み込みを実装（オプトアウト可能）。
    - .env / .env.local の読み込み順と上書きルール（OS 環境変数は保護）を実装。
    - 複雑な .env 行パース（export 形式・クォート・エスケープ・インラインコメント処理）に対応。
    - Settings クラスに多数のプロパティを実装（DB パス、Paper Trading 設定、監視しきい値、PID/KILL フラグパス、環境検証など）。
    - `PAPER_FILL_MODE`／`KABUSYS_ENV`／`LOG_LEVEL` などの値検証（不正値時は ValueError）。

- ツール
  - tools.paper_verification_report.py
    - Paper Trading の検証レポート生成コマンドを追加。
    - 稼働率・注文成功率・送信率・レイテンシ (P95) 等を算出し PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB 存在チェック、エラー時のフォールバックを実装。

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder
    - 候補選定 select_candidates、等金額/スコア加重 weight 計算を追加。
  - portfolio.risk_adjustment
    - セクター上限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を追加。
  - portfolio.position_sizing
    - position sizing の核となる calc_position_sizes を実装。
    - risk_based / equal / score の各配分方式、単元株（lot）丸め、aggregate cap スケーリング、cost_buffer を考慮した算出。

- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームのプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加（psutil 利用）。
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収。権限不足などは警告ログでスキップ。

- リサーチモジュール
  - research.factor_research
    - Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）を追加。DuckDB を使用して prices_daily / raw_financials を参照。
  - research.feature_exploration
    - 将来リターン calc_forward_returns、IC 計算 calc_ic、ファクター要約 factor_summary、ランク化ユーティリティ rank を追加。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news を集約して OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルに反映する score_news を実装。
    - 日付ウィンドウ計算、記事トリム（記事数・文字数上限）、20 銘柄ずつのバッチ送信、リトライ戦略、レスポンス検証、スコアクリッピング（±1.0）、部分更新（DELETE→INSERT）による保護を実装。

### 変更 (Changed)
- DB 利用方針の明確化
  - 監視（monitoring）は環境にかかわらず本番 sqlite_path を参照する旨をドキュメント化。
  - 実行エンジンは paper_trading 環境で専用 DB を用いることでデータ分離を確保。

- ログ・例外ハンドリング
  - 各所で不正入力やデータ欠損時にログ出力してフォールバックする設計を採用（例: MONITOR_POLL_INTERVAL の不正値、psutil の権限不足、DuckDB / SQLite のテーブル未存在時のフォールバック）。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL の扱いを堅牢化
  - 0 以下や非数入力は警告を出してデフォルト値にフォールバック（time.sleep に渡す不正値回避）。

- position sizing の堅牢化
  - 価格が欠損・0 の場合にスキップするようにしてゼロ除算や不正な株数計算を回避。
  - aggregate cap スケーリングの端数処理で単元株単位の分配を行い、残余キャッシュで再分配する処理を実装。

- ファクター計算の欠損管理
  - 移動平均や ATR 等のウィンドウ不足時に None を返すことで不完全データへの耐性を確保。

- .env パーサの改善
  - export 形式・クォート・エスケープ・インラインコメント処理を強化し、多様な .env 表記に対応。

### セキュリティ (Security)
- 自動 .env 読み込みの保護
  - OS 環境変数を上書きしない保護機構と、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動読み込みの無効化をサポート。

### 注意事項 / 既知の制限 (Notes / Known issues)
- price のフォールバック
  - apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある点は TODO コメントとして残されている（前日終値や取得原価等のフォールバックを検討）。
- ai.news_nlp の API キー
  - OpenAI API キーは明示的に渡すか環境変数 OPENAI_API_KEY を設定する必要がある。未設定時は ValueError を送出。
- set_cpu_affinity / set_process_priority の動作はプラットフォームと権限に依存し、失敗時は警告ログでスキップされる。
- DuckDB の executemany に関する既知制約（空パラメータの扱い）へ配慮した実装がある。

---

フルリリースノートや個別のコミット単位の差分が必要であれば、追加の情報（コミットログや時系列スナップショット）を提供してください。今回の CHANGELOG はコード内容からの推測に基づく要約です。