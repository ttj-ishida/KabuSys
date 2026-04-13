CHANGELOG
=========

すべての注目すべき変更はここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-13
-------------------

Added
- 初回リリースを追加。
- コア情報
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"（src/kabusys/__init__.py）。
- 実行 / エンジン
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を起動時に "high" に設定。
    - 環境変数 KABUSYS_ENV が paper_trading の場合は paper_trading 専用の SQLite DB（data/paper_trading.db 既定）を使用して本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() で実行開始。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10 等）を組み込み。
- 監視
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出す。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を参照して監視 DB を初期化。
    - プロセス優先度を "high" に設定してから監視ループを開始。
- 設定管理
  - 環境変数 / .env ファイル読み込みロジックを実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env/.env.local を順に読み込む（OS 環境変数を保護する設計）。
    - export KEY=val、クォート文字、エスケープ、インラインコメントなどを考慮した .env パーサーを実装。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD オプションを追加。
    - Settings クラスを実装し、各種設定プロパティを提供（DB パス、PID/KILL フラグパス、閾値、env/log_level 検証等）。PAPER_FILL_MODE の妥当性チェックを実装。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重を実装。全スコア 0 の場合は等配分にフォールバックして警告。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター曝露が閾値を超える場合に、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を実装（bull/neutral/bear、未知は警告の上 1.0 フォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の各 allocation_method を実装。
    - 単元株（lot_size）で丸め、per-stock 上限や aggregate cap（available_cash）を考慮したスケーリングと端数配分アルゴリズムを実装。
    - cost_buffer による保守的なコスト見積りをサポート。
- 研究（research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB SQL で算出。データ不足時は None を返す。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新財務レコードを取得）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで取得（horizons の検証あり）。
    - calc_ic / rank / factor_summary: Spearman 的なランク相関（IC）計算、同順位の平均ランク処理、基本統計量サマリを実装。
  - research パッケージのエクスポートを追加（src/kabusys/research/__init__.py）。
- ニュース NLP（AI）
  - OpenAI を使ったニュースセンチメントスコアリング機能を追加（src/kabusys/ai/news_nlp.py）。
    - 指定 target_date に対するニュース収集ウィンドウの計算（JST → UTC 変換）を提供。
    - raw_news と news_symbols を集約して銘柄ごとにテキストをトリムし、最大20銘柄/チャンクで OpenAI API（gpt-4o-mini）へリクエスト。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフによるリトライ、レスポンスバリデーション、スコア ±1.0 へのクリップ、書き込みは部分失敗に配慮した差分置換方式を想定。
    - OPENAI_API_KEY の必須チェックを実装（引数または環境変数）。
- ツール
  - Paper Trading 検証レポート生成 CLI を追加（src/kabusys/tools/paper_verification_report.py）。
    - レポート指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数 等。
    - 日付フィルタ (--from / --to)、--db オプション、PAPER_TRADING_SQLITE_PATH 環境変数をサポート。
    - DB が存在しない / テーブルがない場合でも安全に処理し、N/A 表示やデフォルト値でフォールバック。
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - set_process_priority(level): Windows / POSIX を吸収して優先度を設定。サポート外 OS は警告してスキップ。権限不足等は警告で無視。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能（権限不足や未サポート環境では警告でスキップ）。
  - パッケージの __all__ エクスポートを整理（portfolio / research / utils 等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キー未設定時の明示的なエラーを追加（ai/news_nlp.py）し、誤った実行を防止。

Notes / その他
- DuckDB / SQLite を使うコンポーネントは接続クローズ処理を適切に行うよう実装されています（run_monitoring/run_execution 等）。
- .env パーサーは export 構文、クォート、エスケープ、インラインコメント等に細かく対応しており、配布後の動作を想定してカレントワーキングディレクトリに依存しない実装になっています。
- 一部の設計は将来拡張（lot_size の銘柄別対応、価格フォールバックなど）を想定した TODO コメントが残されています。

今後
- 単体テスト、CI、ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）の追加を推奨。
- エラー監視・アラート（LINE 通知など）や細かいリトライポリシーの調整、AI スコア結果の保存方式の堅牢化を予定。