CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

※ 以下はリポジトリ内のソースコードから機能・振る舞いを推測して作成した変更履歴です。

Unreleased
----------

### Added
- なし（現時点ではソースツリーの初期まとまりを v0.1.0 として記録しています）。

0.1.0 - 2026-04-12
------------------

初回リリース。主な機能は以下の通りです。

### Added
- 実行・監視用エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB から完全分離して実行。
    - ブローカークライアントのファクトリ（BrokerClientFactory）により本番／モックの切替えを想定。
    - ExecutionEngine の起動前に監視テーブルの存在を保証するため init_monitoring_db を呼び出す。
    - duckdb 接続を利用して分析・ログ関連処理をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 監視は実行環境（KABUSYS_ENV）の値に関わらず本番 sqlite_path を使用して記録。

- 設定・環境変数管理
  - config.py に Settings クラスを追加。
    - .env / .env.local の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）。
    - export KEY=val 形式やクォート付き値、コメント付き行などを考慮した .env パーサを実装。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env 読み込み時に OS の既存環境変数を保護する仕組み（protected set）。
    - 必須環境変数未設定時に ValueError を送出する _require()。
    - 各種設定プロパティ（J-Quants / kabu API / LINE / DB パス / PID/KILL フラグ / しきい値 / 環境判定等）を提供。
    - PAPER_FILL_MODE の妥当性検証（instant/partial/never/reject のみ許可）。不正な値は ValueError。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応したプロセス優先度設定（set_process_priority）。
    - CPU Affinity 固定（set_cpu_affinity）を実装。
    - 権限不足や未サポート環境では警告を出して安全にスキップする。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順・タイブレーク: signal_rank）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全銘柄スコア合計が 0 の場合は等金額配分にフォールバックし WARNING を出力）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター別時価を計算し上限を超えるセクターの新規候補を除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes。
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）でのスケールダウン、
      cost_buffer を考慮した保守的評価、残差に基づく再配分ロジックを実装。

- 研究・リサーチ機能（DuckDB 前提）
  - research/factor_research.py
    - モメンタム（mom_1m/mom_3m/mom_6m）、MA200乖離率の計算（calc_momentum）。
    - ボラティリティ / 流動性ファクター（ATR20、相対ATR、avg_turnover、volume_ratio）（calc_volatility）。
    - バリューファクター（PER, ROE。raw_financials から最新レコード取得）（calc_value）。
    - DuckDB SQL を用いた高性能集計を採用。データ不足時は None を返す設計。
  - research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズンのリターンを一度のクエリで取得）。
    - IC（Spearman の ρ）計算 calc_ic（ランク相関、同順位は平均ランク、レコード不足時は None）。
    - factor_summary（count/mean/std/min/max/median）や rank ユーティリティを実装。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py
    - raw_news / news_symbols を基に OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリング機能（score_news）。
    - 処理の主な特徴:
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window。
      - 1 銘柄あたりの記事数・文字数上限（トークン肥大化対策）を実装（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 銘柄を最大 20 件ずつのバッチで API に送信（JSON Mode を想定）。
      - 429 / ネットワークエラー / タイムアウト / 5xx に対して指数バックオフでリトライ。
      - レスポンスのバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 書き換え方式（DELETE→INSERT）で他銘柄スコア保護。
      - OpenAI API キー未設定時は ValueError を送出。
      - ルックアヘッドバイアスを防ぐため datetime.today() / date.today() を直接参照しない設計指針。

- ユーティリティ・ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate_pct）、送信率（send_rate_pct）、P95 レイテンシ等を算出して PASS/FAIL を判定。
    - デフォルトの閾値を明示（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - SQL クエリで複数テーブル（system_status, trade_logs, risk_logs）を参照し、期間フィルタをサポート（--from/--to）。
    - レポートは標準出力にテキスト形式で出力。

- パッケージ初期化
  - kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - 各サブパッケージ（portfolio, research, tools, utils 等）のエクスポートを整備。

### Changed
- なし（初回リリースのため該当なし）。

### Fixed
- なし（初回リリースのため該当なし）。

Notes（実装上の注意点・既知事項）
--------------------------------
- .env パーサは多くのケース（export キーワード、シングル/ダブルクォート、エスケープ、インラインコメント）に対応するが、極端に複雑な .env 記述は想定外の動作をする可能性あり。
- portfolio.position_sizing では price が 0 または欠損の銘柄はスキップするロジックがあり、将来的に前日終値等のフォールバックが必要になるコメントあり。
- process_priority / set_cpu_affinity は権限や OS の制約により効果が得られないことがある（該当時は警告でスキップ）。
- ai/news_nlp の API 呼び出しは外部サービスに依存するため、API のレートや利用制限に注意が必要（リトライ実装ありだが無限復旧を保証するものではない）。

ライセンス、貢献、その他
-----------------------
- この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリースノートとして使用する場合は、実際のコミット履歴やリリース管理情報に基づいて調整してください。