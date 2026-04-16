# Keep a Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※この CHANGELOG は与えられたソースコードの内容から推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-16
初回リリース。以下の主要機能を含みます。

### Added
- パッケージ初期化
  - kabusys パッケージ定義とバージョン設定（__version__ = "0.1.0"）。

- 実行・監視用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV に応じて本番/ペーパートレード用の SQLite を切り替え（paper_trading 環境では専用 DB を使用し、本番 DB と分離）。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）の検知処理、PID ファイル (data/execution.pid) の扱い、デーモンスレッドでの実行制御を実装。
    - デフォルトの RiskManager 設定（max_position_pct 等）を定義し、初期 available_cash を broker.get_available_cash() で取得して設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。不正値は警告を出しデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して monitoring テーブルを初期化。
    - 停止フラグ検知によるループ終了、例外発生時はログ出力して次ポーリングへ継続。

- 設定管理
  - config.py に Settings クラスを実装。
    - .env / .env.local の自動ロード（プロジェクトルートの検出: .git または pyproject.toml を基準）。OS 環境変数を保護する仕組みを持つ。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化。
    - .env パース機能を強化（export 形式対応、クォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN 等の必須変数取得、DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH、PID/KILL フラグパス、閾値設定、env/log_level 判定など）。
    - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレーク: signal_rank）。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は警告を出して等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用し、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を実装（bull/neutral/bear、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: weight/candidates/portfolio_value/available_cash 等を元に銘柄ごとの発注株数を計算。risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）で丸め、per-stock 上限および aggregate cap（available_cash）に合わせてスケールダウンするアルゴリズムを実装。cost_buffer を考慮。

- 研究・ファクター計算
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily/raw_financials テーブルを参照して各種ファクター（モメンタム、MA200乖離、ATR、平均売買代金、PER/ROE 等）を計算。データ不足時の None ハンドリングあり。
  - research.feature_exploration
    - calc_forward_returns: target_date から指定ホライズン先までの将来リターン計算（複数ホライズン同時取得）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算。データ不足（有効レコード < 3）の場合は None を返す。
    - rank, factor_summary: ランキング・統計サマリー関数を実装。
  - research.__init__ で主要関数と zscore_normalize をエクスポート。

- AI ニュース NLP（初期実装）
  - ai.news_nlp
    - raw_news から銘柄ごとに記事を集約して OpenAI API（gpt-4o-mini）でセンチメント（-1.0〜1.0）を算出し ai_scores テーブルに書き込む機能を追加（バッチ処理、最大記事数/文字数トリム、最大銘柄バッチ 20）。
    - API 呼び出しは 429/5xx/接続断に対して指数バックオフでリトライ。レスポンスは JSON 検証、スコアは ±1.0 にクリップ。
    - calc_news_window により JST ベースのニュース収集ウィンドウを計算（前日15:00〜当日08:30 JST を UTC に変換して扱う）。
    - 注意: 実装はフェイルセーフ設計（API 失敗時はスキップして継続）。

- ツール
  - tools.paper_verification_report
    - ペーパートレード DB（デフォルト data/paper_trading.db）向けの検証レポートを追加。稼働率/注文成功率/送信率/レイテンシ（P95）などを算出し PASS/FAIL 判定を出力する CLI（--from/--to/--db オプション）。
    - P95 計算、SQL クエリの堅牢化（テーブル未存在時の例外捕捉）を実装。
    - 判定基準（稼働率 >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 <= 200 ms）を定義。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) を実装（Windows と POSIX を吸収）。アクセス権限不足や未対応 OS はログ警告で安全にスキップ。
    - set_cpu_affinity(cpu_count) を実装（1 未満は ValueError、アクセス権限・未実装ケースは警告してスキップ）。

### Changed
- なし（初回リリース）

### Fixed
- 環境変数/設定の堅牢化
  - MONITOR_POLL_INTERVAL の値が不正な場合に警告してデフォルトにフォールバックする処理を追加。
  - .env パーサーで export= 形式・クォート内エスケープ・インラインコメント等への対応を追加し、より柔軟に .env を扱えるように改善。
  - PAPER_FILL_MODE の無効値検出と ValueError の導出を追加（誤設定を早期に検出）。
  - research.calc_forward_returns や factor 関数群でデータ不足時に None を返すことで downstream での例外を回避。

### Security
- なし

### Deprecated
- なし

### Removed
- なし

### Known issues / Notes
- ai/news_nlp.py の実装は本リリース時点でファイル末尾が途中で切れている（与えられたコードの末尾が不完全）。完全な DB 書き込み処理や一部ロジックの続きが存在しないため、本機能の一部は未完の可能性があります。利用時は該当ファイルの完全実装を要確認。
- portfolio.risk_adjustment.apply_sector_cap は price が欠損（0.0）だった場合にエクスポージャーが過少評価される可能性がある旨の TODO コメントあり。将来的に前日終値等のフォールバック実装が推奨されている。
- position_sizing モジュール内にも将来の拡張を示す TODO や想定（銘柄別 lot_size マスタなど）が残っている。
- .env 自動ロードはプロジェクトルートの検出が失敗するとスキップされる。テスト環境等で自動ロードを抑制するために KABUSYS_DISABLE_AUTO_ENV_LOAD を使用可能。

---

この CHANGELOG はソースコードから見える実装・設計方針を元に作成しています。実際のリリースノートやユーザー向けドキュメントを作成する際は、実際のコミット履歴・差分・テスト結果を参照して調整してください。