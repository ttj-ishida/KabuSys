Keep a Changelog
=================

すべての重要な変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」準拠です。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 破壊的変更 (Removed / Deprecated) — 該当があれば記載

[Unreleased]
------------

- 今後の改善メモ（コード中の TODO / 注意点に基づく）
  - position_sizing: 価格欠損時のフォールバック（前日終値や取得原価）を用いる拡張を検討中。
  - 将来的な拡張として銘柄別単元（lot_size）のサポートを検討中（現在は全銘柄共通単元を仮定）。
  - DuckDB に対する executemany の制約に関する扱いやエラーハンドリングの追加検討。
  - ニュース NLP の API 呼び出し部分について、より詳細な部分失敗時の部分リトライ/ロールバック戦略の整備を検討中。

0.1.0 - 2026-04-12
------------------

Added
- 基本設定と環境変数ロード機能を追加（kabusys.config.Settings）
  - プロジェクトルート自動検出（.git / pyproject.toml）に基づく .env / .env.local の自動読み込み機能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - .env の堅牢なパーサー実装（export 形式、クォート文字列、インラインコメントの扱い、保護キー対応）。
  - 各種設定プロパティ（DB パス、PID/KILL フラグパス、しきい値、環境判定、PAPER_FILL_MODE の検証等）。

- 実行用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を用いた完全分離された paper trading DB を使用し、MockBrokerClient を採用する設計に対応（BrokerClientFactory）。
    - 実行前にプロセス優先度を設定（utils.process_priority.set_process_priority）。
    - ExecutionEngine, OrderRepository, OrderManager, RiskManager, Reconciler 等の組み立てと起動処理を実装。
    - RiskManager に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値に broker.get_available_cash() を利用。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境に関係なく本番 sqlite_path を参照して監視テーブルを初期化（init_monitoring_db）。
    - duckdb との接続確立とクリーンアップ。

- モニタリング DB 初期化ユーティリティ（init_monitoring_db）を使用する運用フローを導入。
  - 監視テーブルの存在保証（冪等な初期化を行う設計）。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights（全銘柄のスコアが 0 の場合は等金額にフォールバック）。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の allocation_method に対応した株数決定ロジック実装。
    - 単元株（lot_size）への丸め、per-position および aggregate のキャップ処理、cost_buffer を考慮したスケーリングロジックを実装。
    - aggregate cap 超過時のスケールダウンと残差に基づく追加配分ロジックを実装（再現性確保のため安定ソートを使用）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター暴露を計算し、max_sector_pct を超えるセクターの新規候補を除外するフィルタを実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返すユーティリティ（未知のレジームは警告出力して 1.0 にフォールバック）。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB 上で計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（欠損ハンドリングを明示）。
    - calc_value: raw_financials からの最新財務データと株価を組み合わせて PER / ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト: 1,5,21 営業日）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関による Information Coefficient を実装（None 値や有効レコード不足のハンドリング）。
    - factor_summary / rank: 基本統計量、ランク付けユーティリティを実装。
  - DuckDB 接続を受け取り SQL と標準ライブラリのみで完結する実装方針。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ格納するワークフローを実装。
  - バッチ処理（最大 _BATCH_SIZE=20）・1銘柄あたりの記事/文字数トリム、429/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリッピングを実装。
  - calc_news_window: 対象ニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）算出ユーティリティを追加。
  - API キーの解決（引数優先、未設定時は環境変数 OPENAI_API_KEY を参照）と未設定時の例外処理。

- ユーティリティ（kabusys.utils）
  - process_priority:
    - set_process_priority(level): Windows / POSIX を吸収したプロセス優先度設定。権限不足や未対応 OS の場合は警告を出力してスキップ。
    - set_cpu_affinity(cpu_count): 指定数コアにピン留めする機能（引数検証、権限不足時の警告）。
  - これにより run_* スクリプトで起動直後に優先度を高く設定する一貫した動作を提供。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを SQLite（paper_trading.db）から生成する CLI スクリプトを追加。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg, max, P95）。閾値と Pass/Fail 判定ロジックを定義。
    - 日付フィルタ (--from / --to) と --db オプションを提供。
    - P95 計算ユーティリティ、データ欠損時の N/A 表示を実装。

Changed
- プロジェクト構成（初期リリース）として、各モジュールを明確に分離して公開。
  - データ処理（DuckDB）、実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニューススコアリング、ユーティリティ、運用ツールの各レイヤーを分離。

Fixed
- 監視・実行フローに対するリソースクリーンアップ（sqlite / duckdb 接続の close）を確実に行うように実装。

Notes / Known limitations
- price fallback: apply_sector_cap 内の price が 0.0 の場合、エクスポージャーが過小見積りされる可能性がある旨の TODO コメントあり。将来的にフォールバック価格の導入を検討。
- lot_size: 現時点では全銘柄共通の lot_size を仮定。銘柄別単元対応は未実装。
- DuckDB executemany: コメントにある通り、DuckDB のバージョン依存の挙動に注意が必要。
- ニュース NLP の API 実行は外部サービス依存のため、API キー・レート制限・課金に注意。

その他
- パッケージバージョン: __version__ = "0.1.0"

参考
- 環境変数の主要なもの:
  - KABUSYS_ENV (development | paper_trading | live)
  - SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH
  - MONITOR_POLL_INTERVAL
  - OPENAI_API_KEY
  - PAPER_FILL_MODE
  - PID_FILE_PATH / KILL_FLAG_PATH
  - LOG_LEVEL

もし CHANGELOG に特定のコミット日や PR 番号を付与したい場合や、リリースノート文言（日本語のトーンや詳細度）を変更したい場合は指示してください。