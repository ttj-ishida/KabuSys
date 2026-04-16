CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はリポジトリの現状（コードベース）から推測して設定しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-16
--------------------

Added
- 基本アプリケーション骨格を追加（パッケージメタ情報、バージョン定義）。
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 実行用エントリスクリプトを追加。
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - KABUSYS_ENV による paper_trading モード切替をサポート。paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグファイル (data/stop_requested.flag) の検出で安全にシャットダウン。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを行う。
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor を初期化して定期的に check_once() を呼ぶポーリングループを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用 sqlite_path（data/monitoring.db デフォルト）を使用する旨を明示。
    - 停止フラグによる終了検知と KeyboardInterrupt へのハンドリングを実装。
- 設定管理モジュールを追加 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env パーサの実装（export プレフィックス、クォート処理、インラインコメント処理、エスケープ対応）。
  - 環境変数の検証ロジック（KABUSYS_ENV, LOG_LEVEL の許容値など）。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE トークン / DB パス / 監視閾値 等）。
  - PAPER_FILL_MODE の値検証（instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH のサポート。
- プロセス制御ユーティリティを追加 (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) により Windows / POSIX を吸収して優先度を設定（アクセス権限エラーを安全に無視）。
  - set_cpu_affinity(cpu_count) によりプロセスの CPU affinity 固定をサポート（None で未設定）。
- ポートフォリオ構築関連の純粋関数モジュールを追加（DB 参照なし、メモリ計算のみ）
  - portfolio_builder (src/kabusys/portfolio/portfolio_builder.py)
    - シグナル選定 select_candidates、等重み calc_equal_weights、スコア加重 calc_score_weights を提供。全スコアが 0 の場合は等重みへフォールバックする警告を追加。
  - risk_adjustment (src/kabusys/portfolio/risk_adjustment.py)
    - セクター集中制限 apply_sector_cap（sell予定銘柄を除外して既存保有のセクター比率を計算、"unknown" セクターは上限チェック対象外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear マッピング、未知レジームは 1.0 でフォールバック）。
  - position_sizing (src/kabusys/portfolio/position_sizing.py)
    - allocation_method に応じた発注株数計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合スケールダウン）および remainder による追加配分ロジックを実装。
    - 手数料/スリッページ見積り用の cost_buffer サポート。
- リサーチ・ファクター計算モジュールを追加 (src/kabusys/research/)
  - factor_research: calc_momentum, calc_volatility, calc_value — DuckDB の prices_daily / raw_financials を利用したモメンタム・ボラティリティ・バリュー計算。
  - feature_exploration: calc_forward_returns, calc_ic（スピアマンランク相関）, factor_summary, rank — 将来リターン算出やファクター有効性評価、統計サマリー。
  - モジュールは外部ライブラリに依存せず、DuckDB 接続を受けて高性能に集計する設計。
- Paper Trading 検証レポートツールを追加 (src/kabusys/tools/paper_verification_report.py)
  - SQLite の paper_trading DB を読み取り、稼働率・注文成功率・送信率・API レイテンシ(P95) 等を集計してレポート出力。
  - 閾値を定義して PASS/FAIL 判定を行う（稼働率 99%、fill_rate 90%、send_rate 95%、P95 <= 200 ms 等）。
  - 日付フィルタ（--from / --to）および DB パス指定オプションをサポート。
- ニュース NLP（OpenAI 経由）モジュールを追加 (src/kabusys/ai/news_nlp.py)
  - raw_news + news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信、銘柄ごとにセンチメントスコア（-1.0〜1.0）を計算して ai_scores へ格納するフローを実装。
  - 処理ウィンドウ（JST 基準の前日 15:00 ～ 当日 08:30）計算ユーティリティ calc_news_window を提供。
  - バッチサイズ、最大記事文字数、リトライ（429/5xx/タイムアウト に対する指数バックオフ）など実運用向けのフォールトトレラント設計。
  - API キー検証、レスポンスの厳密な JSON 検証、スコアの ±1.0 クリップを実装。
- パッケージレベルのエクスポートを追加（portfolio / research API の __all__ を整備）。

Changed
- .env 自動読み込みの挙動を明確化（プロジェクトルート探索・.env と .env.local の読み込み順・OS 環境変数保護）。
  - OS 環境変数は保護され、.env.local の override フラグでも上書きできない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
- run_monitoring のデフォルトポーリング間隔の取り扱いを堅牢化。
  - MONITOR_POLL_INTERVAL が不正（非整数、0 以下など）の場合にログ警告を出しデフォルト 60 秒へフォールバック。
- position_sizing のスケールダウンロジックを細かく実装（端数処理、優先順位の安定化）。
- apply_sector_cap の挙動: sector_map に存在しないコードは "unknown" 扱いとしてセクターキャップの除外対象にする（既存保有計算時に unknown を無視）。

Fixed
- process_priority と CPU affinity の実装で、権限不足（AccessDenied）や未対応プラットフォームで例外を握り潰して安全にスキップするように修正（スクリプト起動時のクラッシュを防止）。
- research / factor 計算クエリで NULL 値や不足データの取り扱いを明示的に扱うように修正（必要行数未満の場合は None を返す）。
- paper_verification_report の統計算出でテーブル欠如や OperationalError 発生時にデフォルト値で継続してレポートを出力するように堅牢化。

Security
- OpenAI API キーは明示的に引数または環境変数で指定しない限り使用不可とし、未設定時はエラーを返すことで誤った公開を防止（news_nlp）。

Notes / その他
- 多くのモジュールは外部の永続化層（DuckDB / SQLite）を接続引数で受け取る設計になっており、ユニットテスト時の差し替えが容易です。
- run_monitoring は「監視」は常に本番の monitoring DB を参照する方針で実装されています。paper_trading 用に監視DBを分離したい場合は設定の変更が必要です。
- news_nlp のファイルは大きな処理フローを含み、API 呼び出しや DB 書き換えの扱いに慎重なロジック（部分成功時の保護）が実装されています（ファイル末尾が切れている部分は実装継続の余地あり）。

今後の改善候補（参考）
- price の欠損時のフォールバック（position_sizing / apply_sector_cap の TODO に記載）。
- 銘柄毎の lot_size をサポートして単元違いを扱う拡張。
- news_nlp の部分実装の補完と e2e のリトライ/ロールバック戦略のテスト強化。
- モニタリング・ログ・メトリクスの外部エクスポート（Prometheus 等）検討。

----  
この CHANGELOG は現行ソースコードの内容から推測して作成しています。実際のリリースノートや変更履歴として使用する際は、コミット履歴や PR の説明を参照して補正してください。