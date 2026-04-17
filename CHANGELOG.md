# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。日付はソースコードの現状から推測して付与しています。

## [0.1.0] - 2026-04-17
初回リリース。以下の主要機能・モジュールを実装しています。

### 追加
- 全体
  - パッケージ k abusys の初期実装を追加。バージョンは src/kabusys/__init__.py にて "0.1.0" として定義。
  - DuckDB と SQLite の併用設計を導入（分析用に DuckDB、監視/実行ログに SQLite を利用）。

- 設定・環境読み込み (src/kabusys/config.py)
  - .env と .env.local の自動ロード機構を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの抑止をサポート。
  - .env パーサを強化:
    - export KEY=val 形式に対応
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理
    - インラインコメント扱いルールの実装
    - override / protected（OS 環境変数保護）をサポートする読み込み関数を追加
  - Settings クラスを提供し、環境変数経由でアプリ設定にアクセス可能に:
    - DB パス (DUCKDB_PATH/SQLITE_PATH/PAPER_TRADING_SQLITE_PATH)
    - PID / キルフラグ等の監視関連パス
    - CPU/MEM/DISK 閾値
    - KABUSYS_ENV 検証（development / paper_trading / live）
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）
    - LOG_LEVEL 検証

- 実行・デーモン化ユーティリティ
  - プロセス優先度設定ユーティリティを追加 (src/kabusys/utils/process_priority.py)
    - Windows と POSIX（Linux/Mac/FreeBSD）を透過的に扱い、nice / priority class を設定
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供
    - アクセス権限不足など発生時は警告を出して処理をスキップする安全設計

- 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
  - ExecutionEngine の起動スクリプトを実装。処理の要点:
    - process priority を high に設定して起動
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と完全分離
    - 監視テーブルの初期化（init_monitoring_db）
    - BrokerClientFactory によるブローカークライアント生成（paper/live 切替を想定）
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動
    - 停止フラグ (data/stop_requested.flag) による安全な停止処理
    - 実行 PID ファイルのパス管理

- 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
  - SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）。不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視 DB は本番参照を意図）。
    - 停止フラグ検出でループを終了、例外はログ出力して次のポーリングまで待機。

- 監視 DB 初期化
  - monitoring 用 DB の初期化を担う init_monitoring_db の呼び出しを実装（各起動スクリプトで冪等に実行）。

- Portfolio（銘柄選定・配分・ポジション調整）
  - portfolio_builder (src/kabusys/portfolio/portfolio_builder.py)
    - select_candidates: スコア降順で上位 N を選抜（同点時は signal_rank でタイブレーク）
    - calc_equal_weights / calc_score_weights: 等分配およびスコア正規化重み計算（スコア合計が 0 の場合は等分配へフォールバックして警告）
  - risk_adjustment (src/kabusys/portfolio/risk_adjustment.py)
    - apply_sector_cap: 既存保有のセクター露出が閾値を超える銘柄を当該セクターから除外（"unknown" セクターは上限を適用しない）
    - calc_regime_multiplier: market regime に応じた資金投下乗数（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバックして警告）
  - position_sizing (src/kabusys/portfolio/position_sizing.py)
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した発注株数計算
      - リスクベース: risk_pct / (price * stop_loss_pct) に基づく計算、単元株（lot_size）丸め、1銘柄上限の適用
      - equal/score: weight に基づく配分、max_utilization（投下上限）や aggregate cap（利用可能現金を超えた場合のスケールダウン）を実装
      - cost_buffer を使った保守的見積り、スケールダウン後の残差ロジックで単元単位の追加配分を行う再現性のある実装
    - 未取得価格の扱い（価格が無効な場合はスキップ）や将来拡張の TODO コメントを含む

- 研究・ファクター計算 (src/kabusys/research)
  - factor_research.py: ファクター計算実装
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（データ不足時は None）
    - calc_volatility: ATR(20)、ATR 比率、20日平均売買代金、出来高比率
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新の財務データを target_date 以前から採取）
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズンの将来リターン計算（複数ホライズンに対応、入力検証あり）
    - calc_ic: スピアマンのランク相関（IC）計算（有効レコードが 3 未満なら None）
    - factor_summary / rank: 基本統計量計算とランク付け（同順位は平均ランク）
  - research パッケージ初期エクスポート追加（zscore_normalize は kabusys.data.stats から参照）

- ツール
  - paper_verification_report (src/kabusys/tools/paper_verification_report.py)
    - Paper Trading 用検証レポート生成 CLI を実装（期間指定オプション --from / --to / --db）
    - 指標: 稼働率（uptime）、注文成功率・送信率、リスク却下数、平均/最大/P95 レイテンシ
    - P95 計算、SQL の日付フィルタ構築、各種クエリの失敗(OperationalError)に対するフォールバック処理
    - 合格基準（閾値）を定義し、PASS/FAIL レポートを標準出力へ出力

- AI / ニュース NLP (src/kabusys/ai/news_nlp.py)
  - ニュースセンチメントスコアリングモジュールを実装（OpenAI API を利用）
    - タイムウィンドウ計算（JST 基準を UTC に変換）を実装（calc_news_window）
    - バッチ処理（1 API コールで最大 _BATCH_SIZE 銘柄）・トークン肥大化対策（記事数・文字数制限）
    - モデル: gpt-4o-mini をデフォルトとした実装方針
    - レスポンス検証、スコア ±1.0 にクリップ、書き込みは ai_scores テーブルへ置換方式（部分失敗時の保護）
    - 429/ネットワーク/5xx に対する指数バックオフのリトライ戦略
    - 注意: ファイルは途中で切れているが、主要な設計・定数・API エラーハンドリング方針を導入済み

### 変更（設計・挙動）
- 監視（run_monitoring.py）
  - 監視ループは MONITOR_POLL_INTERVAL により調整可能。0 以下や不正値はログ警告してデフォルトにフォールバック。
  - 停止フラグ（data/stop_requested.flag）による外部停止をサポート。

- 実行（run_execution.py）
  - paper_trading 環境では専用の SQLite DB（data/paper_trading.db がデフォルト）を使用して本番 DB と分離。

- 環境変数読み込み
  - OS 環境変数を保護する protected セットを導入し、.env.local の上書き動作を制御。

### 修正（堅牢性・エラーハンドリング）
- .env 読み込みでファイルアクセス失敗時に警告を出すように改善。
- process_priority で AccessDenied 等が発生した場合は警告を出し処理をスキップしてフォールバック。
- DB クエリ周り（ツール類）で sqlite3.OperationalError を補足してフォールバック値を利用する実装。
- position_sizing / portfolio 等で価格欠損時に安全にスキップするガードを追加。

### 既知の制約 / TODO
- position_sizing の lot_size は現在全銘柄共通（将来的に銘柄別単元対応を検討）。
- apply_sector_cap は price が 0.0 の場合にエクスポージャーが過少評価される可能性がある旨の TODO コメントあり（フォールバック価格導入の検討）。
- ai/news_nlp.py はファイル末尾が切れている（score_news の記事取得ロジックが途中）ため、完全な流れは未完成の可能性あり。API キーの取り扱いやパラメタ周りのテストが必要。
- DuckDB の書き込み（executemany）の制約を意識した実装があるため、DuckDB バージョン依存に注意。

## 開発方針メモ（参考）
- 本リリースは「本番口座の実行ロジック」「監視」「ポートフォリオ構築」「リサーチ」「Paper Trading 用検証」「ニュース NLP（初期）」を包括的に含む初期実装です。運用・検証を通じて以下を重点的に改善する予定です:
  - ai/news_nlp の完全実装とエンドツーエンド検証
  - lot_size や銘柄別設定の柔軟化
  - エラー観測・アラートフロー（LINE 等）と運用ドキュメントの充実
  - 単体テストと統合テストの追加（特に DB クエリ・数値計算ロジック）

（以上）