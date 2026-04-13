CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載されています。  
安定版リリースや主要な機能追加・改善をコードベースから推測してまとめています。

※ 日付はコード解析時点 (2026-04-13) を用いています。実際のリリース日やバージョン管理履歴がある場合は適宜差し替えてください。

Unreleased
----------
- なし（次回リリースに向けた未確定の変更点はここに記載します）

[0.1.0] - 2026-04-13
--------------------

Added
- パッケージ初版を追加
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。環境変数 KABUSYS_ENV に応じて paper_trading 用 DB を分離（paper_trading の場合は専用 SQLite DB を使用）。実行開始時にプロセス優先度を設定し、DuckDB と SQLite 接続を確立して各コンポーネント（Broker, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッションを実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
- 設定管理
  - config.py: .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml 基準）。.env/.env.local の読み込み順を実装（OS 環境変数を保護）。詳細な .env パーサ（export 形式、クォート、インラインコメントの扱い）を実装。多くの設定プロパティ（DB パス、API トークン、PAPER_FILL_MODE 検証、閾値、PID / KILL フラグ等）と入力検証を提供。
- 監視関連
  - monitoring_db 初期化呼び出しを実行スクリプトに組み込み（監視テーブルの存在を保証）。
  - モニタリングループの例外ハンドリング（check_once の例外をログ出力して次ループへ継続）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート出力ツールを追加。期間フィルタ、稼働率・注文成功率・送信率・レイテンシ（P95 等）の集計ロジックを実装。閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL 判定を行う。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順、タイブレーク処理）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター上限の適用ロジック（既存ポジションのセクター別時価算出。unknown セクターは適用対象外）と市場レジームに応じた乗数計算（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py: position size の計算（risk_based / equal / score）、単元株（lot_size）丸め、1 銘柄上限や aggregate cap によるスケールダウン、コストバッファを考慮した安全な配分ロジックを実装。投下量スケーリング時に端数処理（lot 単位で再配分）を行う。
  - portfolio/__init__.py: 主要関数をエクスポート。
- 研究・ファクター計算
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を DuckDB を用いて実装（prices_daily / raw_financials を参照）。200日移動平均、ATR、出来高平均、PER・ROE 取得など。
  - research/feature_exploration.py: 将来リターン（forward returns）計算、IC（Spearman ランク相関）計算、ファクター列の統計サマリーを実装。外部ライブラリに依存せず純 Python 実装。
  - research/__init__.py: 主要関数と zscore_normalize を再エクスポート。
- AI ニューススコアリング
  - ai/news_nlp.py: raw_news と news_symbols を元に OpenAI (gpt-4o-mini) へバッチ送信してセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む処理を実装。機能概要:
    - ニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）
    - 銘柄ごとに記事を集約（上限記事数・文字数でトリム）
    - 最大 20 銘柄/回でバッチ送信、JSON Mode 期待、レスポンス検証
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライ
    - スコアを ±1.0 にクリップ、部分成功時は該当コードのみ置換して既存スコアを保護
    - API キー未設定時のエラー通知
- ユーティリティ
  - utils/process_priority.py: プロセス優先度と CPU affinity の設定ユーティリティを追加。Windows/Linux/Mac (POSIX) の差分を吸収し、アクセス権限不足や未対応 OS の場合は警告でスキップする。set_process_priority と set_cpu_affinity を実装。
  - utils/__init__.py を追加（パッケージ化）。

Changed
- 環境変数ロードの振る舞い
  - .env の自動読み込みを実装。既存 OS 環境変数は保護され、.env.local は .env の上書きとして優先読み込みされる。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数により自動ロードを無効化可能（テスト用途想定）。
- DB パスの扱い
  - Settings によりデフォルトの DuckDB/SQLite パスを提供（data/kabusys.duckdb / data/monitoring.db）。paper_trading 用は PAPER_TRADING_SQLITE_PATH で上書き可能。
- Execution と Monitoring の挙動明確化
  - 実行時にプロセス優先度を最初に "high" に設定するよう統一。
  - 監視は常に本番 sqlite_path を使用する仕様を明記（環境に依存しない監視 DB）。

Fixed
- .env パーサの堅牢化
  - export キーワード対応、シングル/ダブルクォート中のエスケープ処理、クォートなしの場合のインラインコメント扱いなどを考慮してパースする実装により .env の微妙な記法差を吸収。
- ポートフォリオ・ポジション算出の端数処理と上限チェック
  - lot_size 単位での丸め・再配分ロジックにより、総投資額が available_cash を超過するケースの保守的な制御を導入。
- 各種 NULL / データ不足時の安全策
  - research モジュール、レポート生成、ニューススコアリング等でデータ欠損時に None を返す・例外を捕捉して判定を N/A にする等のフェイルセーフを組み込み。

Security
- OpenAI API キー等の必須情報は Settings/_require を通して取得する設計。キー未設定時は明示的な ValueError を投げるようにして不意な情報漏洩を防止。

Notes / Known limitations / TODO
- ai/news_nlp.py の処理は API レスポンスの検証や部分成功時の DB 操作を配慮しているが、実運用でのスロットリングやコスト面の考慮、API レスポンス仕様変更への対応は運用時に注意が必要。
- portfolio/position_sizing.calc_position_sizes の価格欠損時（価格が 0 や None）の挙動には TODO コメントが残っており、フォールバック価格や銘柄別 lot_size を将来的にサポートする検討が示唆されている。
- monitoring の SystemMonitor 実装詳細や execution の各コンポーネント（BrokerClientFactory, ExecutionEngine, OrderManager など）の内部実装はここでは省略しているため、それらの振る舞い変更は別途記載が必要。
- 現在の CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、本ファイルを正式履歴に合わせて置き換えてください。