# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

全般的な注記:
- 本リリースではローカル DB（SQLite）と分析 DB（DuckDB）を組み合わせた自動売買 / 研究用ユーティリティ群と実行・監視エントリポイント、及びニュース NLP スコアリングを含む初期機能群を導入します。
- 環境変数による設定を重視しており、.env/.env.local 自動読み込み、各種挙動の環境変数による上書きが可能です。

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージおよびバージョン情報を追加
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)

- 実行・監視用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine を起動するためのスクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用し、本番 DB から分離。
    - BrokerClientFactory を使ってブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、EngineConfig を与えて engine.run_session() を実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログを出してデフォルトにフォールバック。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。

- 設定管理モジュールを追加
  - config.py
    - .env / .env.local の自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml ベース）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止。
    - 環境変数の堅牢なパース処理（クォート、エスケープ、コメント処理など）。
    - Settings クラスで各種設定プロパティを提供（DB パス、PID / KILL フラグパス、閾値、PAPER_FILL_MODE の検証、env/log レベル検証など）。
    - 必須値未設定時は明示的に ValueError を送出する _require() を実装。

- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし、メモリ内計算）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコアで上位 N を選択（タイブレーク: signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用して候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear、未知は 1.0 にフォールバック）。
    - セクター別既存エクスポージャ計算の際、価格欠損時の注意点をコメントで明示。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・リスクベース等に応じて発注株数を計算。lot_size（単元）丸め、per-position 上限、aggregate cap（available_cash）によるスケールダウン、残差配分の実装を含む。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - cost_buffer による手数料・スリッページの保守的見積りをサポート。

- 研究 / ファクター計算モジュールを追加（DuckDB を利用）
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率。
    - calc_value: latest raw_financials 結合による PER / ROE 計算（EPS 欠損時は None）。
    - DuckDB を用いたウィンドウ関数活用で効率的な取得を実装。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで取得（horizons の検証あり）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算（有効レコード数 < 3 の場合は None）。
    - rank / factor_summary: ランク作成（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）。
  - research/__init__.py で主要関数をエクスポート（zscore_normalize は kabusys.data.stats からインポート）。

- ニュース NLP（OpenAI）によるセンチメントスコアリングを追加
  - ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ格納するフローを実装。
    - チャンク処理（最大 20 銘柄/コール）、トークン肥大化防止（記事・文字数上限）、エクスポネンシャルバックオフ対応、レスポンスバリデーション、スコアクリップ（±1.0）等を実装。
    - calc_news_window でターゲット日のニュース集計ウィンドウ（JST→UTC 変換）を提供。
    - API キー未設定時に ValueError を送出。

- ユーティリティを追加
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定（"high"|"normal"|"low"）。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能。アクセス権限や未対応 OS の場合は警告でスキップ。
    - psutil の例外（AccessDenied 等）をハンドリングして安全にスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・リスク却下数・レイテンシ指標（avg/max/P95）を算出し、閾値と比較して PASS/FAIL を出力。
    - デフォルト閾値: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用。未設定時は明示的にエラーを返す（漏洩防止のため環境変数指定を推奨）。

### Notes / Caveats / Known limitations
- run_monitoring.py は監視用 DB として Settings.sqlite_path（本番 DB 想定）を使用します。監視データは環境に依らず本番パスで管理される点に注意してください。
- calc_position_sizes / apply_sector_cap のいくつかの箇所で price が欠損（0.0）だとエクスポージャや算出が過小評価されるため、将来的には価格フォールバック（前日終値など）を導入することを想定しています（TODO コメントあり）。
- .env 自動ロードはプロジェクトルートの検出に依存する（.git または pyproject.toml）。プロジェクトルートが見つからない場合は自動ロードをスキップします。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- research モジュールは DuckDB の存在と prices_daily / raw_financials テーブルを前提とします。実運用では該当テーブルの準備が必要です。
- news_nlp の処理は外部 API（OpenAI）に依存するため、レートリミットや API の仕様変更により挙動が変わる可能性があります。リトライ・バックオフは実装されていますが長時間の遅延や部分失敗が発生し得ます。
- paper_verification_report は DuckDB ではなく paper_trading 用 SQLite を参照してレポートを生成します。DB スキーマが存在しない場合は一部指標が N/A になります。

If you need a translation to English or a more detailed migration guide / upgrade notes for integrating this release into an existing deployment,教えてください。