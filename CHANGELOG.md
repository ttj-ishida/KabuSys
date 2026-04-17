# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージ内の __version__（0.1.0）に合わせています。

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加。
  - パッケージメタ情報: __version__ = 0.1.0 を追加。

- 起動スクリプト
  - run_monitoring.py を追加
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止制御用にプロジェクト data/stop_requested.flag を監視。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視データは本番 DB を参照）。
  - run_execution.py を追加
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の MockBrokerClient を利用し、data/paper_trading.db に記録して本番 DB と分離。
    - 停止フラグ、PID ファイル制御、別スレッドでの実行・安全停止処理を実装。

- 設定管理
  - config.py を追加
    - 環境変数/.env/.env.local の自動ロード機能（プロジェクトルート検出：.git または pyproject.toml を基準）。
    - .env パーサーは export 形式、クォート、エスケープ、行末コメントに対応。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し各種設定取得メソッドを実装（DB パス、API トークン、監視閾値、環境種別判定等）。
    - 入力検証を行う（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- 監視・ユーティリティ
  - utils/process_priority.py を追加
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定ユーティリティ（set_process_priority）。
    - CPU affinity を設定する set_cpu_affinity を追加（コア数指定、利用不可時は警告でスキップ）。
    - 権限不足や未対応 OS 時の安全ハンドリングを実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py を追加
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全てが 0 の場合に等金額配分へフォールバックしてログを出力。
  - portfolio/risk_adjustment.py を追加
    - セクター集中上限適用（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。
    - "unknown" セクターの扱いやログ出力の方針を明記。
  - portfolio/position_sizing.py を追加
    - ポジションサイズ決定ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）単位で丸め、per-stock 上限・aggregate cap（available_cash）のスケールダウン、cost_buffer（手数料/スリッページ緩和）を考慮した算出。
    - 価格欠損時のスキップやスケール調整時の端数配分アルゴリズムを実装。

- リサーチ機能
  - research/factor_research.py を追加
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日ATR、出来高指標）、Value（PER/ROE）などのファクター計算を DuckDB 経由で実装。
    - データ不足時は None を返す堅牢な実装。
  - research/feature_exploration.py を追加
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を提供。
    - 外部依存ライブラリに依存せず標準ライブラリのみで実装。
  - research/__init__.py を追加して主要 API を公開。

- AI / ニュース NLP
  - ai/news_nlp.py を追加（ニュース記事の OpenAI によるセンチメントスコア付与）
    - raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとの ai_score を生成・書き込み。
    - バッチサイズ、トークン肥大化対策（最大記事数・文字数制限）、429/5xx/ネットワーク時の指数バックオフによる再試行、レスポンス検証、スコアクリッピング（±1.0）を実装。
    - タイムウィンドウ計算（JST ベース→UTC への変換）を util 的に提供（calc_news_window）。
    - API キーの未設定時は ValueError を送出。
    - （注）実装の続き/ファイル切断箇所あり（今回提供コードは途中で終端）。

- ツール
  - tools/paper_verification_report.py を追加
    - Paper Trading 用の検証レポート生成スクリプト（CLI）。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL 判定を出力。
    - CLI オプション: --from, --to, --db。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200ms）を設定。
    - SQL 実行時のテーブル欠如に対して例外捕捉して N/A を扱う耐障害設計。

- DB / 監視
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを run_monitoring と run_execution に追加し、監視テーブルの存在を冪等に保証。

### Changed
- 設定ロードの優先順位を明確化
  - OS 環境変数 > .env.local > .env の順で読み込み。既存 OS 環境変数は保護され、.env.local で上書き可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化できる。

- 実行フロー
  - run_execution: 環境に応じて paper_trading 用 DB を使い、本番 DB と分離する挙動を採用（テスト/検証の安全性向上）。
  - run_monitoring: 監視は常に本番 sqlite_path を参照する仕様を明記（監視データの一元化）。

### Fixed
- 環境変数の数値パース堅牢化
  - MONITOR_POLL_INTERVAL が不正（0 以下 / 非数）な場合にデフォルトにフォールバックして warning を出すように修正（time.sleep での ValueError 回避）。
  - PAPER_FILL_MODE の検証を実装し、無効値は ValueError を送出するように修正。

- DuckDB 実行時の注意事項
  - ai/news_nlp の設計において executemany 前に params が空でないことを想定（DuckDB の制約回避）。（実装コメント）

### Security
- OpenAI API キーの取り扱いを明示
  - news_nlp.score_news は API キーが未設定の場合に明示的にエラーを投げ、誤った公開や未設定を早期検出。

### Notes / Implementation details
- 多くのモジュール（portfolio, research 等）は「純粋関数」設計であり、DB 参照が不要なものはメモリ内計算のみで副作用を発生させない実装となっている（ユニットテストしやすい設計）。
- OS や権限に依存する操作（プロセス優先度設定、CPU affinity 設定）は失敗してもログ出力してスキップするフェイルセーフを採用。
- ai/news_nlp.py は大きな処理を伴うため、フェイルセーフ（API エラー時は処理をスキップして継続）を採用している。ファイル末尾が切れている箇所は今後の実装継続を想定。

---

今後の予定（例）
- ai/news_nlp の完全実装とテスト、OpenAI レスポンス検証ロジックの強化。
- run_monitoring / run_execution のより詳細なログ出力・メトリクス収集追加。
- portfolio の lot_size を銘柄別に設定可能にする拡張（コメントにTODOあり）。
- ユニットテスト、CI 設定の整備。

もし特定ファイルや変更箇所について、より細かい差分や実装意図を知りたい箇所があれば教えてください。