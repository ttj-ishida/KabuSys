CHANGELOG
=========

すべての重要な変更履歴はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠しています。
http://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在のコードベースに未リリースの変更がある場合はここに記載します。）

[0.1.0] - 2026-04-16
-------------------

Added
- 基本パッケージ初期リリース
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 実行・監視エントリポイント
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じた paper_trading モードの DB 分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組立て。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による安全な停止処理を実装。
    - 起動時にプロセス優先度を High に設定（utils.process_priority を使用）。
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は本番用 sqlite_path を環境に依らず使用する挙動。
    - stop フラグ検知、例外時のログ出力、DB（sqlite3）と DuckDB 接続管理を実装。
- 設定・環境変数管理
  - src/kabusys/config.py：.env 自動読み込み機構と Settings クラスを追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml）。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化。
    - export 付き行、クォート（シングル/ダブル）、インラインコメントの扱いに対応したパーサ実装。
    - 各種設定プロパティ（DB パス、PID path、各種閾値、KABUSYS_ENV / LOG_LEVEL の検証、PAPER_FILL_MODE の検証など）。
- ポートフォリオ構築ユーティリティ
  - portfolio.portfolio_builder：select_candidates、calc_equal_weights、calc_score_weights を追加（スコア基準・等配分）。
    - calc_score_weights は全スコアが 0 の場合に等配分へフォールバックし警告を出力。
  - portfolio.risk_adjustment：apply_sector_cap、calc_regime_multiplier を追加。
    - セクター集中制限（既存ポジションの時価ベース計算、sell_codes 除外、"unknown" セクターは免除）。
    - レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio.position_sizing：calc_position_sizes を追加。
    - risk_based / equal / score ベースの株数計算、単元株（lot_size）丸め、単銘柄上限・aggregate 上限（available_cash）でのスケーリング、cost_buffer による保守的見積り。
    - スケーリング時の端数配分アルゴリズム（残差順に lot 単位で追加配分）を実装。
- 研究／ファクター計算
  - research.factor_research：calc_momentum、calc_volatility、calc_value を追加（DuckDB 経由で prices_daily/raw_financials を参照）。
    - momentum：1M/3M/6M リターン、MA200 乖離（データ不足は None）。
    - volatility：20 日 ATR、ATR 比率、平均売買代金、出来高比率。
    - value：EPS に基づく PER、ROE（target_date 以前の最新財務データを使用）。
  - research.feature_exploration：calc_forward_returns、calc_ic（Spearman 相関）および factor_summary、rank を追加。
    - forward_returns は任意ホライズンに対応、結果は (date, code) 毎の辞書リストを返す。
    - calc_ic はランク相関（スピアマン）を実装し、有効レコード数が少ない場合は None を返す。
  - research パッケージのエクスポートを整備（zscore_normalize の再エクスポート含む）。
- ニュース NLP（AI）モジュール
  - ai.news_nlp：OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を追加。
    - タイムウィンドウ計算、記事集約、バッチ（最大 20 銘柄）送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分成功時の DB 保護的更新ロジックを実装。
    - OPENAI_API_KEY の未設定時は ValueError を送出（明示的なエラー）。
- ツール類
  - tools.paper_verification_report：paper trading DB に対する検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し閾値判定（PASS/FAIL）を行う。
    - P95 算出ユーティリティ、日付フィルタ組立、DB テーブル欠損時のフォールバックを実装。
- ユーティリティ
  - utils.process_priority：クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を実装（psutil 使用）。
    - サポート外 OS の場合はスキップして警告ログ、アクセス権限エラー等は警告でフォールバック。

Changed
- デフォルトのデータパス設定を明確化
  - DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH のデフォルトをコード内で定義。
- 環境変数の取り扱いを堅牢化
  - .env パーサの改善によりクォート内部のエスケープや export 形式、インラインコメントの扱いが正確に動作するように変更。
- run_execution / run_monitoring の起動フローを整理
  - 起動直後にプロセス優先度を設定するように統一。
  - DB 初期化（init_monitoring_db）は冪等に実行。

Fixed
- 空データに対する取り扱いを安全化
  - research.feature_exploration.rank / calc_ic / factor_summary 等で None / 空配列に対して安全に動作するように修正。
  - tools.paper_verification_report の P95 計算（空リストは None を返す）と DB テーブル欠損時のフォールバック対応を実装。
- calc_score_weights が全スコア 0 の場合にゼロ除算や不正な重みを返す問題を修正（等配分へフォールバックし警告ログ）。
- apply_sector_cap：セクター未登録（"unknown"）の銘柄はセクター上限チェックの対象外とすることで誤除外を防止。
- process_priority：対応外 OS や権限不足時に例外で終了しないよう例外処理と警告ログを強化。
- run_monitoring の MONITOR_POLL_INTERVAL のパースを堅牢化（0 以下や不正値はデフォルトにフォールバックして警告）。

Security
- ai.news_nlp：OpenAI API キーが未設定の場合は明示的にエラーを出して早期検出するように変更（キーの存在確認）。

Notes / Breaking Changes
- Settings.env は "development" / "paper_trading" / "live" のいずれかでなければ ValueError を送出します。既存環境変数の値がこれらに合致しない場合は起動時エラーになります。
- PAPER_FILL_MODE の値は "instant" / "partial" / "never" / "reject" のいずれかでなければ ValueError を送出します。
- 監視モジュールは環境にかかわらずデフォルト sqlite_path（data/monitoring.db）を使用する設計になっています。paper_trading 実行時の監視用途に注意してください。
- ai.news_nlp は OpenAI API を呼び出すため、運用環境では適切な API キー管理とコスト管理を行ってください。

Acknowledgements
- 本リリースでは DuckDB, psutil, openai 等の外部ライブラリを利用しています。運用環境における依存関係のインストールを忘れないでください。

---