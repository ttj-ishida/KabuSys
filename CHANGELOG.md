# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。重要度は主観に基づき分類しています。

なお、本CHANGELOGは提供されたコードベースの実装内容から推測して作成しています。実際のコミット履歴やリリース日とは異なる場合があります。

## [Unreleased]

- なし（次回リリース用のプレースホルダ）

## [0.1.0] - 2026-04-16

### Added
- 全体
  - 初回公開リリース。日本株自動売買システム「KabuSys」の基本機能群を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定 / 環境変数
  - 環境変数および .env ファイルの自動読み込みを提供する `kabusys.config.Settings` を追加。
  - .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行う。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env パーサーは `export KEY=val`、クォート、エスケープ、インラインコメントに対応。
  - 各種設定プロパティを実装（API トークン・DB パス・PID/フラグパス・閾値・環境モード等）。
  - 設定のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。

- 実行 / 監視
  - 実行エントリ:
    - run_execution: 実行エンジン起動スクリプトを追加。`paper_trading` 環境では paper 専用 SQLite DB を使用して本番 DB と完全分離する。
    - run_monitoring: システム監視用ポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト `data/stop_requested.flag` ファイルで行う。
  - 実行エンジン周り:
    - ブローカークライアントの抽象化 `BrokerClientFactory` を使用。
    - `ExecutionEngine`, `OrderManager`, `OrderRepository`, `Reconciler`, `RiskManager` を組み合わせて取引セッションを実行。
    - リスク設定（`RiskConfig`）の初期値を設定。`broker.get_available_cash()` を用いて初期ポートフォリオ値を取得。
    - 実行は別スレッドで行い、停止フラグ検出で安全に停止する仕組みを実装（PID ファイル管理含む）。
  - 監視:
    - 監視用 DB 初期化ユーティリティ `init_monitoring_db` の呼び出しにより監視テーブル整備を保証。
    - 監視ループは例外を捕捉してログ出力し、次回ポーリングに続行するフェイルセーフを実装。

- ユーティリティ
  - `kabusys.utils.process_priority` を追加し、Windows/Linux/Mac の違いを吸収してプロセス優先度（high/normal/low）および CPU affinity を設定可能。
  - 設定失敗時は警告ログを出してスキップするフォールトトレラントな実装。

- ポートフォリオ構築
  - `kabusys.portfolio` モジュールを追加。
    - portfolio_builder: シグナル選定 (`select_candidates`)・等金額配分(`calc_equal_weights`)・スコア加重配分(`calc_score_weights`) を実装。スコア全体が 0 の場合は等配分にフォールバック。
    - risk_adjustment: セクター集中除外 (`apply_sector_cap`) と市場レジームに応じた乗数 (`calc_regime_multiplier`) を実装（レジームマップ: bull/neutral/bear）。
    - position_sizing: 各銘柄の発注株数計算 (`calc_position_sizes`) を実装。risk_based / equal / score の配分ロジック、単元株（lot_size）丸め、aggregate cap によるスケールダウン（残差処理の再分配）を含む。コストバッファ（手数料・スリッページ）考慮あり。

- リサーチ / ファクター計算
  - `kabusys.research` モジュールを追加。
    - factor_research:
      - `calc_momentum`: 1M/3M/6M リターン、200 日移動平均乖離率を DuckDB 上で計算。
      - `calc_volatility`: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算。true_range の NULL 伝播を制御。
      - `calc_value`: EPS・ROE を元に PER/ROE を計算（raw_financials と prices_daily を結合して最新財務を取得）。
    - feature_exploration:
      - `calc_forward_returns`: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。入力検証あり。
      - `calc_ic`: スピアマンのランク相関（IC）を実装（ties の平均ランク対応）。
      - `factor_summary`: 基本統計（count/mean/std/min/max/median）を標準ライブラリのみで計算。
      - `rank`: 同順位を平均ランクで扱うランク関数。
  - DuckDB を利用し SQL ウィンドウ関数で効率的に計算する設計。

- AI / ニュース
  - `kabusys.ai.news_nlp` を追加（ニュースセンチメントスコアリング）。
    - OpenAI（gpt-4o-mini）を用いて raw_news を銘柄ごとに集約・スコアリングし、ai_scores テーブルへ書き込みを行う設計。
    - バッチ処理、トークン肥大対策（記事数・文字数トリム）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアクリップ（±1.0）等の方針を実装。
    - ニュース収集ウィンドウ算出ロジック `calc_news_window`（JST 指定の UTC 変換）を提供。
    - API キー未設定時は ValueError を送出。
    - （注意）提供コードは途中で切れているため、score_news の最終実装部分は継続実装が必要。

- ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading の SQLite DB（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等。
    - P95 計算、日付フィルタ、閾値定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）を組み込み、PASS/FAIL 判定を出力。
    - CLI オプション: --from/--to/--db。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし（公開 API キー等は環境変数で取り扱い。OpenAI キー未設定時はエラー）

---

開発メモ（実装上の注意点、今後の改善候補）
- news_nlp の score_news 本体が未完（提供コードが途中で切れている）ため、バッチ送信と DB 書き込みの最終処理を完成させる必要あり。
- position_sizing 内の価格欠損時の扱い（price が 0.0 の場合にエクスポージャー未評価となる）については TODO コメントあり。前日終値や取得原価を用いるフォールバックを検討する。
- .env パーサーは多くのケースをカバーしているが、特殊ケース（複雑なエスケープや多行クォート等）の追加テストを推奨。
- process_priority / set_cpu_affinity は権限や OS に依存して失敗する可能性があるため、本番運用環境での動作確認を推奨。
- paper_verification_report の P95 や統計はサンプルサイズに依存するため、十分なログがあることを前提とする。

もしリリース日やコミット単位でのより詳細な CHANGELOG（モジュール単位の小さな変更履歴やIssue番号など）を希望される場合は、コミットログや差分を提示してください。こちらでより正確な CHANGELOG を作成します。