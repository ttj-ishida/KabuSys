# Changelog

すべての変更は Keep a Changelog 準拠で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-17

初回リリース。本リポジトリに含まれる主要機能・モジュールを実装しています。

### 追加
- 全体
  - パッケージ `kabusys` を追加。__version__ = 0.1.0。
  - プロジェクトの設定・環境変数管理を行う `kabusys.config.Settings` を実装。
    - .env/.env.local の自動読み込み機構（プロジェクトルート検出、オーバーライド制御、保護キー扱い）を実装。
    - .env 行パーサーはコメント、クォート、エスケープ、`export KEY=...` 形式に対応。
    - 多数のプロパティ（J-Quants、kabuAPI、LINE、DB パス、監視閾値、環境判定等）を提供し、入力検証を実施（例: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE）。
- 実行・監視
  - `run_execution.py`:
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、paper_trading 環境での専用 DB 分離、バックグラウンドスレッドでの実行、停止フラグ監視、PID ファイル取り扱いを実装。
    - BrokerClientFactory を利用し、本番/ペーパートレードで適切なブローカークライアントを選択。
    - OrderRepository、OrderManager、RiskManager（RiskConfig により各種リスク制御を行う）、Reconciler を組み合わせて ExecutionEngine を構成。
  - `run_monitoring.py`:
    - SystemMonitor ポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔オーバーライド（デフォルト 60 秒）、停止フラグ検知、例外耐性を実装。
    - 監視用 DB（monitoring）は環境に関わらず本番 sqlite_path を使用する仕様。
- ポートフォリオ構築
  - `kabusys.portfolio` パッケージ:
    - `portfolio_builder`:
      - シグナル選別（スコア降順、タイブレーク: signal_rank）を実装。
      - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を提供。全スコアが 0 の場合は等配分へフォールバック。
    - `risk_adjustment`:
      - セクター集中制限（apply_sector_cap）を実装。既存ポジションを踏まえたセクター別エクスポージャー算出と候補除外ロジックを提供（"unknown" セクターは除外対象外）。
      - 市場レジームに基づく乗数（calc_regime_multiplier）を提供（bull/neutral/bear に対応、未知レジームはフォールバック）。
    - `position_sizing`:
      - 各銘柄の発注株数計算（risk_based / equal / score）を実装。
      - lot_size（単元株）丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer を用いた保守的見積り、残差に対する再配分ロジックを実装。
- 研究・ファクター計算
  - `kabusys.research`:
    - `factor_research`:
      - DuckDB を用いたファクター計算関数を実装: calc_momentum（1/3/6M リターン、MA200 乖離）、calc_volatility（ATR20、ATR%・売買代金指標）、calc_value（PER、ROE）。
      - SQL ウィンドウ関数や行数チェックによる欠損制御を行う実装。
    - `feature_exploration`:
      - 将来リターン計算（calc_forward_returns）を実装。複数ホライズン対応、入力検証（horizons 範囲）。
      - スピアマンランク相関（IC）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
    - research パッケージの __init__ で主要関数をエクスポート。
- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用の検証レポート生成スクリプトを実装。コマンドライン引数（--from/--to/--db）対応。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計・判定（閾値はソース内定義）。
    - P95 計算、日付フィルタ生成、DB 存在チェック、SQL の例外耐性を実装。
- AI / NLP
  - `kabusys.ai.news_nlp`:
    - raw_news から銘柄別に記事を集約し OpenAI API（gpt-4o-mini）でセンチメントを取得して ai_scores に書き込む設計を実装。
    - バッチ処理、トークン肥大化対策（記事数・文字数制限）、API のリトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）等の方針を組み込んでいる。
    - calc_news_window（ニュース時間ウィンドウ計算）や score_news の初期処理を実装。
- ユーティリティ
  - `kabusys.utils.process_priority`:
    - process priority（Windows の優先クラス / POSIX nice 値）を抽象化して設定するユーティリティを実装（set_process_priority, set_cpu_affinity）。
    - 未対応 OS や権限不足時は警告を出して安全にスキップするよう実装。

### 変更（設計上のフォールバック・検証強化）
- MONITOR_POLL_INTERVAL の不正な値（0 や負数、非整数）は警告を出してデフォルト（60 秒）にフォールバックするよう実装。
- PAPER_FILL_MODE の入力検証を厳格化（有効値以外は ValueError）。
- calc_score_weights: 全銘柄のスコアが 0.0 の場合は等金額配分にフォールバック（WARNING ログ）。
- calc_regime_multiplier: 未知のレジームは WARNING を出して 1.0 でフォールバック。
- process priority / cpu affinity 設定は AccessDenied 等の例外を捕捉して警告ログを出し処理を継続するように変更（フェイルセーフ）。

### 修正（安全性・堅牢性）
- run_monitoring / run_execution: 停止フラグ（data/stop_requested.flag）の検知と安全な終了処理を実装。
- DB 初期化: 監視テーブルの存在保証（init_monitoring_db）を起動時に呼び出し、冪等的にテーブルを確保。
- position_sizing: aggregate cap のスケーリング時に単元株（lot_size）で丸めた後、残余キャッシュで内訳を追加配分するアルゴリズムで過度に余るケースを低減。

### 既知の注意点 / TODO
- apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性あり。将来的に前日終値や取得原価でのフォールバックを検討中（ソース内 TODO に明記）。
- position_sizing: 将来的に銘柄ごとの lot_size をサポートする設計への拡張を想定（コメントで言及）。
- research モジュールは DuckDB の prices_daily / raw_financials テーブル構造に依存。実データ投入と DB スキーマの整合性確認が必要。
- ai.news_nlp: スニペットは主要ロジックを含むが、提供コードの末尾が切れているため（スニペット終端で中断）完全実装の有無は確認が必要。実運用前にスコアの書き込みトランザクション周りやエラー時の部分更新ロジックを確認してください。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる。CI/配布後の挙動に注意。

---

今後のリリースでは、テストカバレッジ、例外ハンドリングの追加強化、AI モジュールの完成、銘柄別 lot_size サポート、より詳細なドキュメントや運用ガイドの追加を予定しています。