# Changelog

すべての変更は Keep a Changelog のフォーマットに従っています。  
このファイルはコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-16

### Added
- 基本アプリケーションパッケージを追加
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境設定・自動 .env ロード
  - src/kabusys/config.py
    - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索）。
    - .env/.env.local の自動読み込みを実装（OS 環境変数を保護して上書き制御）。
    - export 形式、クォート、インラインコメントなどに対応した行パーサを実装。
    - Settings クラスを追加し、各種設定（J-Quants, kabu API, LINE, DB パス、監視閾値、環境判定等）をプロパティ経由で提供。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等の Paper Trading 用設定をサポート。

- 実行エントリスクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用し本番と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成を実装。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の取り扱いを追加。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors など）を初期化し、初期ポートフォリオ値はブローカーから取得。

- 監視エントリスクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor を定期実行する監視ループを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔（デフォルト 60 秒）上書きをサポート。0 以下や不正値は警告してデフォルトにフォールバック。
    - 監視は環境 (KABUSYS_ENV) にかかわらず本番 sqlite_path を使用する設計。
    - stop フラグ、例外ハンドリング、DuckDB/SQLite の初期化・クローズ処理を実装。

- プロセス優先度 / CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) を実装（Windows / POSIX の差分を吸収）。
    - set_cpu_affinity(cpu_count) を実装（指定が None の場合は無変更）。権限不足や未対応環境では警告してスキップ。

- ポートフォリオ構築関連（純関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全てが 0 の場合は等金額配分にフォールバックし警告を出力。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) を実装。既存ポジションに基づくセクター別エクスポージャ計算と候補フィルタを提供。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピング、未知の場合は警告して 1.0 にフォールバック）。
    - 「unknown」セクターはセクター上限の対象外とする仕様を採用。

  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、総投下上限（max_utilization）やコストバッファを考慮したスケーリングを実装。
    - aggregate cap を超える場合のスケーリングと remainder に基づく追加配分ロジックを実装。

- リサーチ・ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 経由で計算する関数を追加。
    - データ不足時の None 処理やスキャン範囲、ウィンドウサイズに関する設計上のコメントを明示。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン対応）を実装。
    - スピアマンランク IC を計算する calc_ic、およびランク付けユーティリティ rank を実装。
    - factor_summary による基本統計量サマリー関数を追加。
    - 外部ライブラリに依存せず標準ライブラリのみで実装する方針を採用。

  - src/kabusys/research/__init__.py
    - 主要な関数を公開 API としてエクスポート。

- Paper Trading 検証レポートツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からレポートを生成する CLI ツールを追加。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ等を計算。
    - Pass/Fail 基準を導入（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - DB スキーマが存在しない等のケースを考慮した例外処理を組み込み。

- ニュース NLP スコアリング（OpenAI 経由）
  - src/kabusys/ai/news_nlp.py（実装の大部分を追加）
    - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを生成・ai_scores に書き込むフローを実装。
    - バッチサイズ、チャンクごとの文字数制限、リトライ（指数バックオフ）、JSON レスポンスのバリデーション、スコアの ±1.0 クリップ等を導入。
    - ニュース収集ウィンドウ（JST→UTC 変換）を calc_news_window で定義し、ルックアヘッドバイアスを避ける設計。
    - API キー未設定時は明示的な例外を投げる。

- パッケージ API 整備
  - src/kabusys/portfolio/__init__.py, src/kabusys/research/__init__.py, src/kabusys/tools/__init__.py, src/kabusys/utils/__init__.py を追加し、主要関数を公開。

### Changed
- モジュール責務の明確化
  - 監視・実行・検証・研究・ポートフォリオ計算などの責務を分割し、純関数群（DB 非依存）と DB を扱う処理を明確に分離。

- デフォルト挙動・安全性の強化
  - MONITOR_POLL_INTERVAL の不正値に対する警告＆デフォルトフォールバックを追加。
  - process_priority と set_cpu_affinity は権限不足や未対応 OS を安全にスキップしログ出力するように変更。
  - calc_score_weights は全スコアが 0 の場合に等配分にフォールバックして警告。

### Fixed
- DB 初期化の冪等性
  - run_execution.py と run_monitoring.py で監視テーブルの初期化（init_monitoring_db）を起動時に行い、テーブルが存在しない場合でも安全に開始できるようにした。

- CLI ツールの堅牢性
  - paper_verification_report において DB ファイル存在チェック、SQL 実行時の OperationalError をハンドリングしてデフォルト値（N/A）を返すようにし、ツール実行中に発生する例外で処理が停止しないように改善。

### Security
- 環境変数の取り扱い
  - .env 自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入し、意図しない上書きを防止。

### Notes
- run_monitoring と run_execution はプロセス優先度を最初に上げる実装を行っていますが、権限によってはスキップされる場合があります（ログに警告を出力します）。
- ai/news_nlp.py は API 経路やレスポンス構造に強い前提（JSON モードで results キーを返す等）を持っています。API 側の仕様変更時は影響を受けます。
- 一部ファイル（ai/news_nlp.py）は長大な処理のため抜粋で提供されています。完全実装時に細部挙動が変わる可能性があります。

---

以上がこのコードベースから推測した初期リリース (0.1.0) の変更点一覧です。必要であれば各項目をさらに詳細化（ファイル毎の変更行レベルやサンプルログ出力など）できます。どの程度の詳細が必要か教えてください。