# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。セマンティックバージョニングを使用します。

<!-- Unreleased セクションは将来の変更用に残します -->
## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-16

### Added
- 全体
  - プロジェクト初期リリース。ライブラリ名: KabuSys、バージョン 0.1.0。
  - パッケージ公開用の __version__ を `kabusys.__init__` に設定。
- 設定・環境読み込み (`src/kabusys/config.py`)
  - .env / .env.local の自動読み込み実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env パーサー実装: export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメントを考慮した堅牢な解析。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - Settings クラスを実装し、各種設定値（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境判定など）を環境変数から取得するユーティリティを提供。
  - 必須環境変数未設定時に明確なエラーを投げる `_require()` を実装。
  - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）を追加。
- 実行エントリポイント
  - ExecutionEngine 起動スクリプト `src/kabusys/run_execution.py`
    - プロセス優先度を設定して起動（High に設定）。
    - KABUSYS_ENV が `paper_trading` の場合、Paper 用専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClient のファクトリ利用、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと実行スレッド制御を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による外部制御に対応。
    - RiskManager のデフォルト設定（max_position_pct / max_utilization / rate_limit_per_sec / circuit_breaker 等）を搭載。
  - Monitoring 起動スクリプト `src/kabusys/run_monitoring.py`
    - SystemMonitor ポーリングループの起動と終了処理実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計（監視データは常に本番 DB に記録）。
    - 停止フラグによるループ終了、KeyboardInterrupt のハンドリングを実装。
- 監視 DB 初期化
  - `init_monitoring_db` を参照して監視用テーブルの冪等初期化を行う呼び出しを実装（monitoring コンポーネントとの連携）。
- ユーティリティ
  - `src/kabusys/utils/process_priority.py`
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収するプロセス優先度設定関数 `set_process_priority` を実装。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供。
    - 権限不足や未対応プラットフォームの場合に警告してスキップするフォールトトレラントな実装。
- ポートフォリオ構築（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定 (`select_candidates`)：スコア降順、同点時は signal_rank でタイブレーク。
    - 重み計算: 等金額配分 (`calc_equal_weights`) とスコア加重配分 (`calc_score_weights`)。全スコアが 0 の場合は等金額にフォールバックし警告出力。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限 (`apply_sector_cap`)：既存保有のセクター比率が閾値を超える場合、新規候補を除外（"unknown" セクターは制限対象外）。
    - レジーム乗数 (`calc_regime_multiplier`)：bull/neutral/bear に応じて投下資金乗数を返す（未知レジームは 1.0 にフォールバックし警告）。
  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数算出 (`calc_position_sizes`)：risk_based / equal / score の各方式を実装。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer（手数料/スリッページ見積り）を考慮したスケーリングアルゴリズムを実装。
    - 価格欠損時のスキップやログ出力による安全化。
- 研究（Research）モジュール（DuckDB ベース、外部 API 非依存）
  - `src/kabusys/research/factor_research.py`
    - Momentum / Volatility / Value ファクターの計算関数を実装（prices_daily / raw_financials テーブル参照、DuckDB を利用）。
    - 計算に必要なウィンドウ定数（1M/3M/6M, MA200, ATR20 等）とデータ不足時の None ハンドリングを実装。
  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン (`calc_forward_returns`) の一括取得（複数ホライズン対応、入力バリデーションあり）。
    - スピアマンランク相関による IC 計算 (`calc_ic`)、ランク変換ユーティリティ (`rank`)。
    - 基本統計量サマリー (`factor_summary`) を標準ライブラリのみで実装。
  - `src/kabusys/research/__init__.py` で主要関数をエクスポート。
- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の検証レポート生成スクリプト。コマンドライン引数で期間指定可能。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出して PASS/FAIL 判定を行う（閾値はファイル内定義）。
    - DB 存在チェック、SQL の OperationalError を捕捉してフォールバックする堅牢化。
- AI ニュース NLP スコアリング（設計・一部実装）
  - `src/kabusys/ai/news_nlp.py`
    - ニュース収集ウィンドウ計算 (`calc_news_window`) を実装（JST ベースのウィンドウを UTC に変換）。
    - OpenAI (gpt-4o-mini) を使った銘柄ごとのセンチメントスコアリングの設計を実装（バッチ処理、JSON Mode、スコアクリッピング、リトライ/バックオフ戦略、部分成功時の DB 更新戦術など）。
    - API キー解決ロジック（引数 > 環境変数）と未設定時のエラーを実装。
    - （注）ファイル末尾で処理途中で切れているが、設計としては記事集約、バッチ送信、レスポンス検証、ai_scores 書き込みを行う方針。

### Changed
- なし（初期リリースのため大規模な変更履歴は無し）

### Fixed
- 環境変数パースの振る舞いを改善:
  - 無効な MONITOR_POLL_INTERVAL 値の扱い: 負値や非整数時にログ出力してデフォルトにフォールバック。
  - .env のクォート内エスケープやコメント解釈を改善し、誤読による設定ミスを低減。

### Security
- 環境変数保護:
  - .env 読み込み時に既存 OS 環境変数を保護する仕組みを導入（protected set）。
  - 自動ロードを明示的に無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

### Notes / Known issues / TODO
- ai/news_nlp.py がファイル末尾で途中（_fetch_articles 呼び出しで切れている）になっており、完全実装のためには記事フェッチ部分と API 呼び出しループの続きが必要。
- position_sizing の価格欠損時（price == 0 や None）における保守的な挙動については TODO コメントが残っており、将来的に前日終値や取得原価でのフォールバックを検討。
- apply_sector_cap は "unknown" セクターを制限対象外として扱う仕様だが、この挙動が望ましくない場合は将来の改善を検討。
- Windows や権限の低い環境ではプロセス優先度／CPU affinity の設定が失敗することがあり、その際は警告を出してスキップする仕様になっている。

---

もし特定の変更やリリース日付を別にしたい場合、あるいは未実装箇所（ai/news_nlp の続きなど）に関する詳細な記載を追加したい場合はお知らせください。