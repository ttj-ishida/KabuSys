CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、重要度の高い変更をカテゴリ別に整理しています。

Unreleased
----------

（現在のスナップショットには未リリースの作業はありません）

0.1.0 - 2026-04-17
------------------

Added
- 基本パッケージ初期実装
  - パッケージメタ情報を追加（kabusys.__version__ == 0.1.0）。
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。  
    - 環境変数 KABUSYS_ENV により paper_trading モードを判定し、paper_trading 時は専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。  
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。  
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動/停止制御を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。  
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒、0 以下は無効扱いでフォールバック）。  
    - Monitoring は実行環境にかかわらず本番 sqlite_path（data/monitoring.db デフォルト）を参照して監視データを記録。停止フラグ検知でループを終了。
  - 共通: 起動時にプロセス優先度を設定（set_process_priority("high")）する仕組みを導入。
- 設定管理
  - config.py: .env / .env.local の自動読み込み実装（OS 環境変数優先、.env.local は上書き、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。  
  - Settings クラスを導入し、各種設定（API トークン、DB パス、各種閾値、環境判定フラグ等）をプロパティ経由で提供。PAPER_FILL_MODE のバリデーションや KABUSYS_ENV / LOG_LEVEL の検証を実装。
- Portfolio（銘柄選定・配分・サイズ決定）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額・スコア加重の重み計算（calc_equal_weights / calc_score_weights）を実装。スコア全てが 0 の場合のフォールバック警告あり。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）を実装。既存保有のセクターエクスポージャ計算、売却予定銘柄の除外、"unknown" セクターは制限適用外。市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear -> 1.0/0.7/0.3、未知は警告とフォールバック 1.0）。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）を実装。  
    - allocation_method に応じた計算（risk_based / equal / score）。  
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer による保守的コスト見積りを実装。スケールダウン時の端数再配分（lot 単位）ロジックあり。
- Research（ファクター・解析）
  - research.factor_research: Momentum / Volatility / Value ファクター計算を実装（DuckDB を用いた SQL ベースの実装）。200 日移動平均、ATR、出来高平均、PER/ROE などを計算。データ不足時は None を返す振る舞い。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）・ランク化ユーティリティ（rank）およびファクター統計サマリ（factor_summary）を実装。外部依存（pandas 等）なしで実装。
  - research.__init__: 公開 API を整理してエクスポート。
- AI ニュース NLP
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングする設計を実装。  
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）、記事集約、バッチ送信（上限 20 銘柄）、リトライ（429/ネットワーク/5xx に対して指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）および ai_scores テーブルへの安全な置換戦略を記載。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。  
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。閾値（稼働率 99%、成立率 90% 等）を定義。
- ユーティリティ
  - utils.process_priority: set_process_priority により Windows / POSIX の差分を吸収して優先度変更をサポート。set_cpu_affinity による CPU affinity の固定機能も追加。権限不足や未対応環境では警告を出してスキップする堅牢さを確保。

Changed
- DB 関連の分離設計
  - Paper Trading と本番の SQLite をデフォルトで明確に分離（settings.paper_sqlite_path / settings.sqlite_path）。run_execution は paper_trading モードで PAPER_TRADING_SQLITE_PATH を優先して使用。
- 設定ロード順序
  - .env の自動読み込みを導入し、.env.local を .env より優先（上書き）する挙動に統一。

Fixed
- 入力バリデーション強化
  - MONITOR_POLL_INTERVAL のパースで不正値を検出してログを残しデフォルトにフォールバックするよう改善。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の値検証を導入し、不正値で早期に明確なエラーを出すように変更。
- レポート・集計の耐障害性
  - paper_verification_report の各クエリ呼び出しを try/except で保護し、テーブルが存在しない場合でもレポート生成を続行できるようにした。

Security
- 環境変数の読み込みに際して OS 環境変数を保護（protected set）する仕組みを導入。自動ロード時に既存の OS 環境変数が意図せず上書きされないよう配慮。

Notes / Migration
- 監視（run_monitoring）・実行（run_execution）プロセスは起動時に高優先度へ変更を試みますが、権限が無い場合は警告が出て処理は継続します。
- Paper Trading を利用する場合、必ず PAPER_TRADING_SQLITE_PATH を設定するか KABUSYS_ENV=paper_trading を指定してください。paper_trading モードで本番の monitoring DB と混ざらないよう注意してください。
- ai.news_nlp は OpenAI API（OPENAI_API_KEY）を必要とします。API キー未設定時は score_news が ValueError を送出します。

開発者向け補足
- DuckDB を用いるファクター計算 / ニュース集約の実装により、大量時系列データの集計をローカルで効率的に実行できます。prices_daily / raw_financials / raw_news 等のスキーマに依存しているため、テスト用 DB を用意して動作確認を行ってください。
- calc_position_sizes や apply_sector_cap 等のアルゴリズムは将来的に銘柄別単元（lot_size）や価格フォールバックロジックを取り込む余地を残しています（TODO コメントあり）。

--- 
今後の予定: エンドツーエンドの統合テスト、AI スコアリングの部分的失敗時のロールバック戦略強化、銘柄別 lot_size サポート等。