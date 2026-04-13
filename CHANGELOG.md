CHANGELOG
=========

このプロジェクトは "Keep a Changelog" の形式に従って変更履歴を管理します。  
日時や内容はコードベースから推測して記載しています。

Unreleased
----------

- 追加予定 / 注意点
  - ai/news_nlp.score_news(): OpenAI API 呼び出しの部分で部分失敗した場合に既存スコアを保護するため、更新は対象コードのみを削除→挿入する方式を採用。API キー未設定時は ValueError を送出するためデプロイ時に環境変数 OPENAI_API_KEY の設定が必要。
  - research モジュール: DuckDB のテーブル依存 (prices_daily / raw_financials 等)。データ不足時に None を返す挙動や計算境界（ホライズン上限など）を明確化する予定。
  - portfolio モジュール: lot_size を将来的に銘柄別対応する設計への拡張 (TODO コメントあり)。
  - process_priority.set_cpu_affinity(): 指定コア数が利用可能コア数を超えた場合の振る舞い・エラーメッセージ改善を検討中。
  - .env 自動ロード: プロジェクトルート検出失敗時は自動ロードをスキップする仕様だが、ドキュメントの補足を追加予定。

[0.1.0] - 2026-04-13
--------------------

Added
- 基本パッケージ情報
  - パッケージメタ: kabusys.__version__ = "0.1.0" を導入。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。プロセス優先度を設定し、SQLite/ DuckDB に接続して実行エンジンを起動するワークフローを提供。
    - 環境変数 KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - RiskManager にデフォルトの RiskConfig を設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 設定等）。初期の available cash は broker.get_available_cash() を使用。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。プロセス優先度設定、SQLite (monitoring) と DuckDB 接続の初期化を行う。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はログ警告の上デフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（注意点として明記）。

- 設定管理
  - config.Settings クラスを追加（settings インスタンスをエクスポート）。
    - .env/.env.local の自動読み込み機構（プロジェクトルート判定: .git or pyproject.toml を探索）。
    - 環境変数のパースロジックを独自実装（コメント、export、クォート、バックスラッシュエスケープ対応）。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / PID/KILL フラグ / モニタ閾値 / 環境種別・ログレベル判定等）。
    - PAPER_FILL_MODE のバリデーション（instant / partial / never / reject）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。

- ユーティリティ
  - utils.process_priority.set_process_priority / set_cpu_affinity を実装。
    - Windows と POSIX（Linux/Mac/FreeBSD）での優先度設定の差を吸収。psutil を使用し、権限不足時には警告ログでスキップ。
    - CPU affinity を最初の N コアに固定する機能（引数検証あり）。

- ポートフォリオ構築（純粋関数 API）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア重み付け（全スコア 0 の場合は等分配にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用（既存保有・当日売却予定の除外対応）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear 対応、未知レジームは警告とフォールバック 1.0）。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の各配分方式を実装。lot_size（単元）に丸め、per-position 上限や aggregate cap（available_cash に基づくスケーリング）を実装。cost_buffer を考慮した保守的見積り、端数配分の再配分ロジックを備える。

- 研究用モジュール（Research）
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value: DuckDB (prices_daily, raw_financials) を用いたモメンタム・ボラティリティ・バリュー指標計算を追加。各種ウィンドウ長や欠損時の None 戻り挙動を明記。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン計算（複数ホライズン対応、入力検証あり）。
    - calc_ic / rank / factor_summary: IC（Spearman）、ランク付け、統計サマリー実装。外部ライブラリ非依存で標準ライブラリのみ使用。
  - research.__init__ で zscore_normalize を含む主要エクスポートを整備。

- AI / ニュース NLP
  - ai.news_nlp
    - raw_news を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄単位のセンチメント ai_score を ai_scores テーブルへ書き込む処理を追加。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window。
    - バッチサイズ、トークン肥大化対策（記事数上限・文字数上限）、リトライ（429/ネットワーク/5xx）を考慮した実装。出力の JSON バリデーションと ±1.0 のクリッピングを実施。
    - API キーが未設定の場合は ValueError を送出。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ(P95) などを算出し、閾値に基づく PASS/FAIL 判定を行う。
    - DB パス解決 (--db > 環境変数 > デフォルト)、日付フィルタ(--from/--to)対応。
    - P95 計算、各クエリに対する sqlite3.OperationalError のフォールバック処理を実装。

Changed
- 環境変数パースの堅牢化
  - config._parse_env_line(): export 句、クォート・エスケープ、インラインコメントの扱いを詳細実装。これにより .env の多様な記法に対応。

Fixed
- 実行時の堅牢性向上
  - run_monitoring.main(): _get_poll_interval() で 0 以下や不正値をチェックしてデフォルトにフォールバックし、time.sleep に渡す不正値による例外を防止。
  - run_monitoring のポーリング内で monitor.check_once() が例外を投げてもループを継続し、スタックトレースをログ出力して次のポーリングへ移行するよう防御的に実装。

Security
- OpenAI API キーの扱い
  - ai.news_nlp.score_news() は api_key 引数または環境変数 OPENAI_API_KEY を必須とし、未設定時は明確にエラーを出すことで秘密情報の欠如を早期に検出。

Known issues / Notes
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様のため、監視用 DB を環境ごとに分けたい場合は運用手順またはコード側の変更が必要。
- portfolio.position_sizing の price 欠損（0.0）の場合、現状はスキップしておりエクスポージャーが過小評価される可能性あり（TODO にて将来的に前日終値等でフォールバックする方針）。
- process_priority の優先度設定および CPU affinity 設定は権限不足や未対応 OS でスキップされる。これらの警告はログに記録されるのみで例外とならない。
- DuckDB / SQLite に依存する研究・AI モジュールは適切なスキーマ・データが存在しないと None や空の結果を返す設計。テスト用データやマイグレーションを用意することを推奨。

参考
- 各モジュールの詳細な設計や注釈はソースコード内の docstring / コメントを参照してください。