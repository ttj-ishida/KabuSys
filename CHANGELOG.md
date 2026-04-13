CHANGELOG
=========

すべての重要な変更はここに記録します。本書式は "Keep a Changelog" に準拠しています。

0.1.0 - 2026-04-13
------------------

Added
- 全体
  - 初期リリース（バージョン 0.1.0）。モジュール群（実行・監視・ポートフォリオ構築・リサーチ・AI ニューススコアリング等）を追加。
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"

- 起動スクリプト
  - run_monitoring.py を追加
    - SystemMonitor のポーリングループを起動する CLI スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 監視用 DB は KABUSYS_ENV にかかわらず production の sqlite_path を使用する設計。
    - プロセス優先度を設定する（set_process_priority を呼び出し）。
  - run_execution.py を追加
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて実行。

- 設定・環境
  - config.py を追加
    - .env/.env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パーサの強化: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - Settings クラスを提供し、各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス、PAPER_FILL_MODE 等）をプロパティ経由で取得・検証。
    - PAPER_FILL_MODE（instant/partial/never/reject）・KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL のバリデーション。

- ツール
  - tools/paper_verification_report.py を追加
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI ツール。
    - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計して PASS/FAIL 判定を表示。
    - --from / --to / --db CLI オプションをサポート。DB 存在チェックとテーブル存在時の堅牢な例外処理（OperationalError からのフォールバック）を実装。

- ポートフォリオ構築
  - kabusys.portfolio パッケージを追加
    - portfolio_builder.py: select_candidates（スコア降順で上位 N 選抜）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等分配にフォールバック）。
    - risk_adjustment.py: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）。
    - position_sizing.py: calc_position_sizes（risk_based / equal / score の割当方式を実装、lot_size 単位の丸め、aggregate cap によるスケールダウンと残差分配処理、cost_buffer 考慮）。

- リサーチ（ファクター計算・特徴量解析）
  - kabusys.research パッケージを追加
    - factor_research.py: calc_momentum（1M/3M/6M、MA200乖離）、calc_volatility（ATR/流動性指標）、calc_value（PER/ROE）。
    - feature_exploration.py: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関による IC）、rank（同順位は平均ランク）、factor_summary（基本統計量）。
    - DuckDB を用いた SQL + Python 処理により、prices_daily / raw_financials テーブルのみ参照して計算（外部依存なし）。

- AI ニュース NLP
  - kabusys.ai.news_nlp モジュールを追加（ニュースセンチメントスコアリング）
    - raw_news / news_symbols を集約し、OpenAI API（デフォルト gpt-4o-mini）へバッチ送信して銘柄毎のスコアを ai_scores テーブルへ書き込み。
    - バッチサイズ、最大記事数／文字数、リトライ（指数バックオフ）、レスポンス検証、スコアクリッピング（±1.0）、部分失敗時の保護（対象コードで DELETE→INSERT）などを考慮した堅牢な実装方針。
    - calc_news_window でニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST 相当）を正確に算出。
    - API キー未設定時は ValueError を送出。

- ユーティリティ
  - utils/process_priority.py を追加
    - set_process_priority(level) — Windows / POSIX を吸収してプロセス優先度を設定（"high" / "normal" / "low"）。
    - set_cpu_affinity(cpu_count) — カレントプロセスを最初の N コアに固定するユーティリティ。
    - psutil の権限不足や未対応 OS に対するフォールバックログを実装。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Breaking changes（運用上の注意）
- run_monitoring.py の挙動について
  - 監視プロセスは「監視用 DB」として Settings.sqlite_path（デフォルト data/monitoring.db、つまり本番想定のパス）を用いる実装になっています。KABUSYS_ENV の値に依存せず本番用 sqlite_path を使用するため、paper_trading 環境で監視プロセスを動かす際は DB パスに注意してください。
- 設定バリデーション
  - Settings 内のいくつかのプロパティは環境変数の値を厳密に検証します（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。無効値だと ValueError が発生するため、環境変数の設定に注意してください。
- OpenAI API
  - AI ニューススコアリング機能は OPENAI_API_KEY（または score_news 呼び出し時の api_key 引数）を必須とします。API のエラーやレートリミットに対するリトライはある程度実装されていますが、API 使用に伴うコスト・レート制限に注意してください。
- CLI / ツールのファイル入出力
  - tools/paper_verification_report.py はデフォルトで data/paper_trading.db を参照します。別ファイルを使う場合は --db または PAPER_TRADING_SQLITE_PATH 環境変数で指定してください。

既知の改善余地 / TODO
- position_sizing.calc_position_sizes:
  - lot_size を銘柄毎に持たせる設計への拡張（現在は全銘柄共通の lot_size）。
  - price 欠損時のフォールバック（前日終値や取得原価等）の検討（risk_adjustment と position_sizing に TODO コメントあり）。
- ai.news_nlp:
  - 大規模運用でのスケーリング・エラー処理の監視・再試行ポリシーのさらなる強化が望まれる。
- .env パーサ:
  - 現状多くのケースに対応するが、特殊ケースのパース互換性は運用中に追加調整の可能性あり。

―――

（初回リリースのため、機能追加や設計方針の記載が中心になっています。以後の変更はセマンティックバージョニングに従い本ファイルに記録します。）