# Changelog

すべての重要な変更点をここに記録します。本ドキュメントは Keep a Changelog の形式に準拠します。
履歴はセマンティック バージョニングに従います。

なお、本リリースはソースコードから推測した変更点をまとめたものであり、
実際のコミット履歴ではありません。差分・実装の意図に基づいて注釈を付しています。

## [Unreleased]

（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-04-16

初回リリース。自動売買システム「KabuSys」の基礎機能群を追加しました。
以下は実装済みの主な機能・モジュールと挙動のまとめです。

### Added
- パッケージメタ情報
  - kabusys.__init__.py にてバージョンを `0.1.0` として定義。

- 設定管理
  - kabusys.config.Settings: 環境変数・.env 自動ロード機能を提供。
    - プロジェクトルートを .git / pyproject.toml を基準に探索して .env, .env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - 複数種の設定プロパティを提供（DB パス、KABUSYS_ENV、ログレベル、しきい値、Paper Trading 関連設定など）。
    - .env パースロジックはクォート・エスケープ・コメントを考慮した堅牢な実装。

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor を起動するポーリングループ。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計（監視データを本番 DB に記録）。
    - 停止フラグ（data/stop_requested.flag）検知、例外処理を含む安全なループ実行。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト（スレッド実行）。停止フラグ検知でエンジン停止。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立てとエンジン起動を実装。
    - エンジンは PID ファイルを扱う（data/execution.pid 相当のパス）。

- 監視データベース初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を利用して監視用テーブルの冪等初期化を行う呼び出しを実装（スクリプト側で使用）。

- プロセス優先度 / CPU アフィニティユーティリティ
  - kabusys.utils.process_priority.set_process_priority/set_cpu_affinity を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する実装。権限不足時は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順に選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア全て 0 の場合はフォールバックで等配分）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応。lot_size（単元）丸め、aggregate cap によるスケールダウン、手数料等を見越した cost_buffer 対応。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限判定による候補除外ロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（未定義レジームは警告して 1.0 にフォールバック）。

- リサーチ / ファクター計算
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（DuckDB の prices_daily を使用）。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比などを計算。
    - calc_value: raw_financials と prices_daily を組合せて PER / ROE を算出（最新の財務レコードを target_date 以前で参照）。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic / rank / factor_summary: スピアマンランク相関（IC）の計算、ランク付け、統計サマリーを標準ライブラリのみで実装。
  - research パッケージ・エクスポートを整備（zscore_normalize もエクスポートに含む）。

- AI ニュース NLP（OpenAI 統合）
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、トリム制限（記事数・文字数）、429/ネットワーク/5xx に対する指数バックオフリトライ実装、結果バリデーション、スコアクリップ（±1.0）、部分書き換えで部分失敗から既存スコアを保護する戦略を採用。
    - OpenAI API キー必須（引数 api_key または環境変数 OPENAI_API_KEY）。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）などを集計し、PASS/FAIL の簡易判定を行う。
    - コマンドライン引数 --from / --to / --db をサポート。デフォルト DB は data/paper_trading.db。
    - P95 計算、各種 None 値の扱い、SQLite のテーブル不在に対する例外回避（OperationalError を捕捉して N/A 表示）を実装。

- DB 接続
  - DuckDB と SQLite を併用する設計（duckdb は主に時系列・リサーチ用途、sqlite は取引ログ・監視用途を想定）。
  - 実行スクリプトは duckdb_conn / sqlite_conn を適切にクローズ。

### Changed
（初回リリースにつき変更履歴はありません）

### Fixed
（初回リリースにつき修正履歴はありません）

### Notes / Implementation details / 動作上の注意
- 環境変数
  - 主要な環境変数:
    - KABUSYS_ENV: development | paper_trading | live（無効値はエラー）
    - MONITOR_POLL_INTERVAL: 監視ポーリング秒数（正整数、デフォルト 60）
    - PAPER_FILL_MODE: paper_trading 時の MockBroker 挙動（instant/partial/never/reject）
    - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
    - SQLITE_PATH: 監視用 DB（デフォルト data/monitoring.db）
    - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
    - OPENAI_API_KEY: OpenAI API キー（news_nlp で必要）
  - .env 読み込みは OS 環境変数を保護（.env.local は上書き可）。自動読み込みを無効化するフラグあり。

- Paper Trading 分離
  - paper_trading 環境では DB を分離し、MockBrokerClient を用いる設計。これにより本番データの混入を防止。

- 失敗に対するフェイルセーフ
  - ニュース NLP/API呼び出し、監視ループ内の check_once() などで例外が発生してもログ出力のうえ処理継続するよう保護コードあり（例外のキャッチとログ）。

- 時刻・タイムゾーン
  - news_nlp はニュースウィンドウを JST 基準で定義し、内部で UTC に変換して DB クエリ（naive datetime を使用する仕様）。

- 制約・既知の注意点
  - position_sizing:
    - price が欠損（0.0）の場合、現在はスキップしてしまいエクスポージャーが過少見積りされる可能性がある（TODO 注釈あり）。
  - CPU affinity / プロセス優先度:
    - 権限がない環境や未対応 OS では警告を出して操作をスキップする。
  - DuckDB バージョン依存:
    - news_nlp の一括書き込み等は DuckDB の executemany の制約を考慮して実装されている（params が空でないことを確認）。

---

今後の予定（候補）
- テストカバレッジの追加（ユニット / 統合）
- broker/client 周りの抽象化強化と mock の拡充
- エラー監視・アラート連携（LINE / Slack など）の追加
- ファンクションに対するドキュメント / 型注釈の拡充

もし別途コミットメッセージや変更差分（git の履歴）が提供できれば、より正確な CHANGELOG を作成できます。必要であればその履歴を渡してください。