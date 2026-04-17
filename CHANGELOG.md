# Changelog

すべての変更は「Keep a Changelog」形式に従って記載しています。  
このファイルはコードベース（src/ 以下）の実装内容から推測して作成した変更履歴です。

目次
- [Unreleased]
- [0.1.0] - 2026-04-17

## [Unreleased]
注意: ソースコード内のコメントや TODO から推測した「今後の改善・未完事項」を列挙しています。次バージョンでの対応候補です。

### Added
- news_nlp モジュールの処理フローと API 呼び出し周りの設計を反映（バッチング、リトライ、クリッピング等）。ただし一部関数（記事取得部分など）は実装が途中のため未完成。
- position_sizing / risk_adjustment に関する追加改善点の設計メモ（銘柄別 lot_size マッピングや価格フォールバックの検討など）を反映。

### Changed
- なし（次リリースでの改善予定項目を記載）。

### Fixed
- なし（既知の改善点・TODO を参照）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

## [0.1.0] - 2026-04-17
初回公開（コードベースから推測）。以下は実装済みの主要機能・モジュールの要約です。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env の行パーサーは `export KEY=val` 形式、クォート文字列、インラインコメント等に対応。
  - OS 環境変数を保護するための override / protected ロジックを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）。
  - PAPER_FILL_MODE のバリデーション（instant, partial, never, reject）を追加。
  - env（development / paper_trading / live）や LOG_LEVEL の値検証を実装。
  - settings インスタンスをエクスポート。

- 実行・監視用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（プロセス優先度を High に設定）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて Engine 起動。
    - 停止フラグ（data/stop_requested.flag）の検出および PID ファイル管理、デーモンスレッドでの実行と安全停止処理を実装。
    - 監視テーブル（init_monitoring_db）は冪等に初期化。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、無効値時はフォールバックして警告を出力）。
    - Monitoring は環境設定にかかわらず本番 sqlite_path を使用する旨を明記。
    - 停止フラグ検出、例外捕捉によるループ継続、KeyboardInterrupt ハンドリングを実装。

- DB / 分析基盤
  - DuckDB 接続を利用する設計を各所で採用（research / ai / 実行ログ解析等）。
  - 監視テーブル初期化ユーティリティ（monitoring_db）を使用して監視関連テーブルの存在を保証。

- 取引（Execution）周り
  - RiskManager, OrderManager, OrderRepository, Reconciler, ExecutionEngine の組み立てロジック（run_execution にて使用する構成）を実装。
  - RiskConfig によるリスク制限パラメータ（max_position_pct, max_utilization, rate_limit_per_sec 等）を標準値で設定し、初期ポートフォリオ値は broker.get_available_cash() から初期化。

- ポートフォリオ構築（src/kabusys/portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。スコアが全て 0 の場合は等配分にフォールバックし警告を出す。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数計算（calc_regime_multiplier）を実装。unknown セクターの扱い、レジーム別デフォルト値（bull/neutral/bear）を定義。
  - position_sizing: allocation_method（risk_based / equal / score）に基づく発注株数決定を実装。ロット丸め（lot_size, デフォルト 100）、最大ポジション上限、aggregate cap（利用可能現金を超える場合のスケーリング）をサポート。cost_buffer による保守的なコスト見積りと残差配分ロジックを実装。
  - 上記はメモリ内純粋関数群（DB 参照なし）として実装。

- 研究・ファクター計算（src/kabusys/research）
  - factor_research: Momentum、Volatility、Value などの定量ファクターを DuckDB SQL で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。ウィンドウサイズ・欠損ハンドリング・カウント条件を丁寧に管理。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリ（factor_summary）を提供。外部ライブラリに依存せず標準ライブラリのみで実装している点が特徴。
  - research パッケージは zscore_normalize（kabusys.data.stats から）を再エクスポート。

- AI / ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news テーブルを基に OpenAI（gpt-4o-mini）でセンチメント分析を行い、銘柄毎の ai_score を ai_scores テーブルへ書き込む設計を実装。
  - 処理の設計点: ニュースウィンドウ計算（JST 表記 → UTC 変換）、銘柄ごとの記事集約（最大記事数 / 最大文字数トリム）、最大 20 銘柄バッチ、429/ネットワーク/5xx に対する指数バックオフ、レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップ、部分更新（該当コードのみ DELETE→INSERT）による安全性確保。
  - calc_news_window と score_news のインターフェースと一部実装を追加（API キー解決、例外条件、ウィンドウ定義）。（コード末尾にて記事取得関数の実装が途切れているため部分実装扱い）

- ツール（src/kabusys/tools）
  - paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を実装（--from/--to/--db オプション対応）。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を計算し、閾値に基づく PASS/FAIL 判定を実行。
    - DB 存在チェック、SQL クエリでの集計、P95 算出、出力フォーマットを実装。
    - 既知閾値（稼働率 99% など）を定数化。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - プラットフォームを透過してプロセス優先度設定を行うユーティリティ関数（set_process_priority）を実装。Windows と POSIX（Linux/Mac/FreeBSD）を考慮し、アクセス権限や未サポート OS の場合は警告ログを出す。
  - set_cpu_affinity によりプロセスを最初の N コアに固定する機能を実装（例外時は警告ログ化）。
  - psutil に依存した実装で、権限不足や未実装例外を穏やかに扱う。

### Changed
- 新規リリースのため特段の「変更」は無し（初期実装のまとめ）。

### Fixed
- なし（初期リリース）。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キー取得時に明示的なエラーメッセージを出す等、秘密情報未設定時の判定を明確化（news_nlp）。

---

備考（実装上の注意・既知の改善点）
- news_nlp モジュールは設計が詳細に書かれている一方、記事取得（_fetch_articles 等）で実装途切れが見られます。実稼働前に未完成部分の実装・テストが必要です。
- position_sizing のコメントには price が欠損時のフォールバック（前日終値や取得原価など）や銘柄別 lot_size 管理の TODO があり、これらは将来の機能改善候補です。
- run_monitoring は環境にかかわらず本番 sqlite_path を使う旨が明記されており、環境間データ分離ポリシー（paper_trading 用 DB の利用）は run_execution 側で担保しています。運用時は意図した DB パスが設定されていることを確認してください。
- process_priority / cpu_affinity は権限や OS に依存するため、CI や権限の低い環境での実行時は警告が出る点に注意してください。

（以上）