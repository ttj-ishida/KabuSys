# Changelog

すべての注目すべき変更はこのファイルに記載します。  
このファイルは「Keep a Changelog」形式に準拠しています。

現在の日付: 2026-04-13

## [Unreleased]

（現在のコードベース上の未リリース変更はありません）

## [0.1.0] - 2026-04-13

初回公開リリース。以下の主要機能を実装しています。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージエクスポートを整理（portfolio / research / execution / monitoring 等を公開）。

- 設定・環境変数管理（kabusys.config）
  - Settings クラスを実装し、環境変数から各種設定（DBパス、APIキー、各種閾値、PID/KILLファイルパス、環境モード等）を取得可能に。
  - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - .env/.env.local の読み込み順序（OS 環境 > .env.local > .env）と .env の上書き制御をサポート。
  - .env パーサは export KEY=val 形式、クォート文字列とバックスラッシュエスケープ、インラインコメントの扱いなどを考慮する堅牢な実装。
  - 各種入力検証を追加（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の有効値チェックなど）。未設定の必須環境変数は ValueError を送出。

- 実行系ランチャー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - start-up 時にプロセス優先度を設定（high）。
    - Paper Trading 環境（KABUSYS_ENV=paper_trading）では専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入し、初期ポートフォリオ値を broker.get_available_cash() から取得。
    - duckdb 接続の初期化を行う。

  - run_monitoring.py: SystemMonitor ポーリングスクリプトを追加。
    - 起動時にプロセス優先度を設定（high）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値は警告してデフォルトにフォールバック。
    - 監視用途の DB は環境にかかわらず本番 sqlite_path を使用（monitoring データは常に本番 DB を参照する設計）。
    - monitoring DB の初期化（init_monitoring_db）を行う。

- 監視用 DB 初期化ユーティリティ
  - monitoring_db.init_monitoring_db を利用して監視テーブルが存在することを保証（冪等）。

- ユーティリティ（kabusys.utils）
  - process_priority モジュールを追加。
    - set_process_priority(level) で Windows / POSIX 系を透過的に設定（psutil を使用）。
    - set_cpu_affinity(cpu_count) でプロセスを先頭 N コアにピン留め可能。
    - 権限不足や未対応プラットフォーム時は警告してスキップするフェイルセーフ。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルを score 降順、同点なら signal_rank 昇順でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分。全銘柄のスコア合計が 0 の場合は等金額配分へフォールバック（警告ログあり）。
  - risk_adjustment:
    - apply_sector_cap: 同一セクター集中を防ぐため、既存保有比率が閾値を超えているセクターの新規候補を除外。unknown セクターは制限の対象外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未定義レジームは警告のうえ 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に応じた発注株数算出。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）調整、cost_buffer を考慮した保守的見積り、スケールダウン時の端数分配ロジックを実装。
    - price 欠損や 0 の取り扱いやログ出力を考慮。

- 研究・ファクター（kabusys.research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを参照してモメンタム・ボラティリティ・バリュー要素を計算。
    - 長期MAやATRなどのウィンドウチェック時に不足する場合は None を返す安全設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（複数ホライズン同時取得）を計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコードが3未満なら None）。
    - factor_summary / rank: 基本統計量とランク化ユーティリティを実装。
  - duckdb 接続を受け取る純粋関数群として設計（外部 APIにアクセスしない）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとのスコアを ai_scores テーブルへ書き込む機能を追加。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
  - 記事集約、銘柄ごとの最大記事数・最大文字数でトリム、最大 20 銘柄/チャンクで API コール、JSON Mode 想定の出力を検証して書き込み。
  - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ、API キー未設定時は ValueError を送出。
  - スコアは ±1.0 にクリップし、部分失敗を許容する更新戦略（対象コードだけ置換）を採用。
  - フェイルセーフ設計（API 失敗時はスキップして継続）。

- CLI ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成コマンドラインツールを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、閾値に基づく PASS/FAIL 判定を行う。
    - --from / --to / --db オプションで期間・DBパスを指定可能。PAPER_TRADING_SQLITE_PATH 環境変数も参照。
    - P95 算出や各種フォーマット出力を実装。データ欠損時の N/A 表示をサポート。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 環境変数や入力値の検証を強化（不正な MONITOR_POLL_INTERVAL / PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL などは警告または例外で処理）。
- .env 読み込み失敗時は warnings.warn を使用して安全に継続。

### Removed
- 該当なし。

### Security
- OpenAI API キー等の機密情報は環境変数経由で取得する設計。未設定時は明示的なエラーを出す（news_nlp）。

### Notes / Known issues / TODO
- position_sizing.calc_position_sizes:
  - 将来的には銘柄毎の lot_size をサポートする設計に拡張する予定（現状はグローバルな lot_size）。
- apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされブロックが外れる可能性がある旨をコメントに記載（将来的に前日終値や取得原価でのフォールバックを検討）。
- process_priority:
  - 権限不足や未対応プラットフォーム時は警告して処理をスキップするため、期待通りに優先度が反映されない場合がある。
- DuckDB の executemany に関する挙動（空 params の問題）を考慮した実装上の注意書きを news_nlp に記載。
- ai/news_nlp.py は API 呼び出しの最終的な書き込みロジックや一部のトランザクション処理で部分失敗時の振る舞いを想定しているが、運用環境での堅牢性確認が必要。

---

参考: この CHANGELOG は、ソースコード内のコメントや実装内容から推測して作成しています。実際のリリースノートとして利用する場合は、運用上の変更点・互換性・移行手順などを追加で明記してください。