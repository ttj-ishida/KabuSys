# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
日付はリポジトリの現時点（2026-04-13）に合わせてあります。コード内容から推測して機能追加・改善点をまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-13
初回公開リリース。本リリースでは自動売買システム「KabuSys」の主要コンポーネント（実行エンジン、監視、ポートフォリオ構築、リサーチ、ニュースNLP、ユーティリティ、検証ツール等）を実装しています。

### 追加 (Added)
- 全体
  - パッケージの初期バージョンを追加（kabusys v0.1.0）。
- 実行/運用
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading モードでは専用の MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db など）へ記録することで本番 DB と分離。
    - ExecutionEngine の組立（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）とデフォルトの RiskConfig を定義。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理
  - config.py: Settings クラスを追加。
    - .env / .env.local の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）。
    - 強化された .env パーサ（コメント、export プレフィックス、クォートとバックスラッシュエスケープ対応）。
    - 必須項目取得ユーティリティ (_require)、各種設定プロパティ（DB パス、PID/kill flag、閾値、環境判定、paper_trading 関連など）。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の検証処理を実装。
- ポートフォリオ構築
  - portfolio モジュールを追加（純粋関数群で副作用なし）。
    - portfolio_builder: 候補選定(select_candidates)、等金額/スコア加重の重み計算(calc_equal_weights, calc_score_weights)。
    - risk_adjustment: セクター上限適用(apply_sector_cap)、市場レジームに基づく乗数(calc_regime_multiplier)。
    - position_sizing: 発注株数算出(calc_position_sizes) — risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケーリング。
- リサーチ / ファクター
  - research パッケージを追加。
    - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL 実装）。
    - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（Spearman）計算(calc_ic)、ファクター統計サマリー(factor_summary)、ランク変換(rank)。
    - research.__init__ で kabusys.data.stats の zscore_normalize と上記関数を公開。
- ニュースNLP（AI）
  - ai/news_nlp.py: raw_news を OpenAI (gpt-4o-mini) でセンチメント評価して ai_scores に書き込む処理を実装。
    - タイムウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST 相当の UTC 範囲）。
    - 記事集約・トリム（最大記事数／文字数制限）、銘柄ごとのバッチ（最大 20 銘柄/コール）。
    - レスポンス検証、スコアを ±1.0 にクリップ。API エラーに対する指数バックオフリトライ実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は例外を送出。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - 指定期間の system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、レイテンシ（P95 など）を出力。
    - 合格基準（稼働率 99% など）を定義し PASS/FAIL を表示。
    - DB 存在チェック、SQL エラーに対するフォールバックを実装。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux / macOS / FreeBSD）の差分吸収。
    - set_process_priority(level)、set_cpu_affinity(cpu_count) を実装。権限不足などのケースは警告でスキップ。

### 変更 (Changed)
- なし（初回リリースのため該当なし）。ただし設計注記や TODO コメントを随所に記載済み（例: price フォールバック、lot_size 拡張等）。

### 修正 (Fixed)
- 設計上の堅牢性強化（初期実装段階での防御的コーディング）
  - run_monitoring: MONITOR_POLL_INTERVAL の不正値に対するフォールバックと警告表示を追加（time.sleep に不正値を渡さないようガード）。
  - config._load_env_file / _parse_env_line: .env のパースを堅牢化（クォート内エスケープ、インラインコメントの扱い、export プレフィックス対応、存在しないファイルや読み取りエラーの際に警告）。
  - utils/process_priority: 未対応 OS や権限不足時に例外を握りつぶして警告出力するようにし、起動の継続性を確保。
  - ai/news_nlp: API 呼び出しでの 429 / タイムアウト / ネットワーク断 / 5xx に対するリトライ（上限）とバックオフを実装、部分失敗時に他銘柄の既存スコアを保護する更新方法（対象コード絞り込みで DELETE→INSERT）を採用。
  - paper_verification_report: 対象 DB が存在しない場合の明示的エラーメッセージ、SQL 実行時の OperationalError を捕捉して既定値を使うフォールバック処理を実装。
  - DuckDB/SQLite の接続は finally ブロックで確実にクローズするよう修正（リソースリーク防止）。

### 既知の制限 (Known issues / Notes)
- portfolio.position_sizing の price が欠損（0.0）の場合にエクスポージャーが過少見積もられる点をコメントで指摘。将来的に前日終値や取得原価でのフォールバックを検討する旨を記載。
- ニュースNLP は OpenAI の API を利用するため、利用時は API キーとコストに注意すること。
- research モジュールは DuckDB の prices_daily / raw_financials 等のテーブルに依存するため、適切なデータ投入が必要。
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされる（テスト等で KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能）。

---

今後の予定（推測）
- 単体テスト・統合テストの拡充、CI 設定、リリースバージョンの増加。
- ポートフォリオ構築周りの拡張（銘柄別 lot_size、コスト見積りの強化）。
- monitoring / metrics の可視化・アラート連携（LINE など）。
- AI スコアリングの入力文生成テンプレート改善とより厳密なレスポンス検証。

---------------------------------------------------------------------
（本 CHANGELOG は、与えられたコード内容から実装機能・保守上の注意点を推測して作成しています。実際のコミット履歴や設計ドキュメントに基づく正式な履歴とは異なる場合があります。）