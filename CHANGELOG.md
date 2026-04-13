CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
重大な変更はセクションごとに分類しています（Added / Changed / Fixed / Removed / Security）。

[Unreleased]
-----------

- なし

[0.1.0] - 2026-04-13
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークのコア機能群を追加。
  - 実行・監視ランナースクリプト
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。環境変数 KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用し、MockBrokerClient を通じて本番 DB と分離して動作する。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番 sqlite_path を使用する挙動を明記。
  - 設定管理
    - config.py: .env 自動ロード（.env, .env.local、OS 環境変数の保護）、プロジェクトルート探索(.git / pyproject.toml) の実装。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。各種環境変数取得用の Settings クラスを追加（値検証を含む）。
    - サポートされる環境: development / paper_trading / live。LOG_LEVEL, PAPER_FILL_MODE 等の検証ロジックを実装。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 信号の候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数算出 (calc_regime_multiplier) を追加。
    - portfolio.position_sizing: 各銘柄の発注株数計算 (calc_position_sizes) を追加。risk_based / equal / score の配分方式、単元株 round、aggregate cap によるスケーリング、cost_buffer の考慮などを実装。
    - portfolio パッケージの __all__ を整備。
  - リサーチ機能（DuckDB ベース）
    - research.factor_research: Momentum / Volatility / Value ファクター計算関数（calc_momentum / calc_volatility / calc_value）を追加。prices_daily / raw_financials を参照して計算する設計。
    - research.feature_exploration: 将来リターン計算(calc_forward_returns)、IC（calc_ic）計算、rank/統計サマリー(factor_summary) を追加。外部ライブラリに依存しない実装。
    - research パッケージのエクスポートを整備（zscore_normalize を data.stats からエクスポート）。
  - AI ニューススコアリング
    - ai.news_nlp: raw_news + news_symbols からニュースを集約し、OpenAI (gpt-4o-mini) へバッチ送信して銘柄別センチメント(ai_scores) を生成するモジュールを追加。バッチサイズ、トークン肥大化対策、リトライ（429/ネットワーク/5xx の指数バックオフ）、レスポンス検証、スコアクリッピング、部分成功時の DB 保護（対象コードのみ DELETE→INSERT）などのフェイルセーフ設計を実装。
    - ニュース収集ウィンドウ計算（calc_news_window）により、ルックアヘッドバイアスを避ける設計を採用。
  - モニタリング・ツール
    - monitoring.monitoring_db: 監視用 DB 初期化ユーティリティ（run スクリプトから利用）。
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計・判定する CLI（--from/--to/--db オプション）。閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 <= 200ms）と Pass/Fail 判定を実装。
  - ユーティリティ
    - utils.process_priority: クロスプラットフォームでのプロセス優先度設定(set_process_priority) と CPU affinity 設定(set_cpu_affinity) を追加。Windows と POSIX 系の差分を吸収し、権限不足や未サポート環境では警告を出して安全にスキップするよう実装。
  - パッケージメタ
    - kabusys.__init__.py に __version__ = "0.1.0" を設定。

Changed
- N/A（初回リリースのため該当なし）。

Fixed
- N/A（初回リリースのため該当なし）。

Removed
- N/A（初回リリースのため該当なし）。

Security
- OpenAI API キーの取り扱いに関する注意:
  - ai.news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY を必要とする。未設定時は ValueError を送出して明示的に失敗する実装により、キー未設定時の誤操作を防止。

Notes / Implementation details / Known limitations
- .env パーサは export 形式やクォート／エスケープ、インラインコメントの扱いをかなり厳密に実装していますが、全ての .env 方言をカバーするものではありません。
- calc_score_weights は全銘柄のスコアが 0.0 の場合に等重配分へフォールバックします（WARNING を出力）。
- apply_sector_cap は sector_map に存在しない銘柄を "unknown" とみなし、セクター上限チェックから除外します（"unknown" を制限しない挙動）。
- calc_position_sizes の lot_size は現状全銘柄共通の前提（将来的に銘柄別単元への拡張を想定）。
- run_monitoring は監視テーブルの DB 初期化後、duckdb 接続も確立します。監視は本番 sqlite_path を使用する点に注意してください（paper_trading と分離しない設計）。
- ai.news_nlp の実際の API 呼び出し・レスポンス処理は外部ネットワーク・API の可用性に依存します。失敗時は部分的にスキップして継続する設計ですが、完全な再実行やロギング運用ルールは運用側での設定が必要です。

Contact
- 問題報告・提案はリポジトリの Issue へお願いします。