# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。リリースごとに追加・変更・修正をカテゴリ分けして記載しています。コード内容から推測し作成しています。

なお、日付は本リリース作成日（2026-04-12）を使用しています。

## [Unreleased]
- 今のところ未リリースの変更はありません（将来的な改善点はソース内の TODO コメントに記載されています）。

## [0.1.0] - 2026-04-12
初期リリース — 基本的な自動売買・リサーチ・監視ツール一式を実装。

### Added
- プロジェクト基盤
  - パッケージ情報を追加（kabusys/__init__.py, __version__ = "0.1.0"）。
  - Settings クラス（src/kabusys/config.py）を導入し、.env ファイルの自動読み込み（.env, .env.local）・環境変数の取得と検証を提供。
    - .env ファイルの堅牢なパース（コメント、クォート、export 形式への対応）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 各種環境変数の検証（KABUSYS_ENV、有効な LOG_LEVEL、PAPER_FILL_MODE の有効値チェック等）。
    - DB パスや PID / kill flag など運用に必要な設定プロパティを提供（DUCKDB_PATH/SQLITE_PATH/PAPER_TRADING_SQLITE_PATH/PID_FILE_PATH 等）。
- 実行・監視ランナー
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - 起動時にプロセス優先度を設定する処理を追加（utils.process_priority.set_process_priority を利用）。
    - ブローカークライアント生成（BrokerClientFactory）、OrderManager・OrderRepository・RiskManager・Reconciler を組み立てて ExecutionEngine を起動。
    - 初期化時に監視テーブルの存在を保証するため init_monitoring_db を呼び出す（冪等）。
  - SystemMonitor 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒、無効値時は警告出してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を High に設定。
    - DuckDB 接続を確立して SystemMonitor を初期化、例外を握りつぶしてループ継続するフェイルセーフ設計。
- 監視・モニタリング DB
  - init_monitoring_db（監視テーブルの初期化）を利用して起動時に監視テーブルの存在を保証。
- ユーティリティ
  - process priority / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して nice 値 / HIGH_PRIORITY_CLASS を切り替え。
    - set_cpu_affinity を提供（指定したコア数にプロセスをピン留め）。
    - 権限や未対応環境での失敗は警告ログでフェイルセーフに処理。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定／重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N 件を選択、同点時は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等金額にフォールバックして警告）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター暴露を計算し、閾値超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（未知レジームは警告の上 1.0 にフォールバック）。
  - ポジションサイズ算出（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の配分方式をサポートし、lot_size（単元）で丸め、per-stock 上限・aggregate cap（available_cash）を考慮してスケーリングおよび端数配分を実装。
    - cost_buffer による手数料・スリッページ見積り考慮。
    - price 欠損時や不正値をスキップする安全処理を追加。
- リサーチ / ファクター計算（DuckDB ベース）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。データ不足時は None を返却。
    - calc_volatility: ATR20 / 相対 ATR / 20日平均売買代金 / 出来高比率を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新の報告日レコードを銘柄ごとに取得）。
  - 研究支援（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（任意ホライズンサポート・入力検証あり）。
    - calc_ic / rank / factor_summary: スピアマンランク相関（IC）計算、ランク付け（同順位は平均ランク）、各種統計量サマリーを提供。外部依存は使用せず標準ライブラリで実装。
  - research パッケージのエクスポートを用意（zscore_normalize を含む）。
- AI ニュース NLP（OpenAI 統合）
  - src/kabusys/ai/news_nlp.py を追加。
    - raw_news / news_symbols を銘柄別に集約し、OpenAI（gpt-4o-mini）へバッチ（最大 20 銘柄）で送信してセンチメントスコアを算出。
    - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して扱う（calc_news_window）。
    - API 呼び出しに対するリトライ（429 / ネットワーク / 5xx）を指数バックオフで実装。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ、DuckDB の ai_scores テーブルへの安全な置換（部分失敗時にも既存スコアを保護）を想定した処理設計。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
- 運用ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - CLI（--from / --to / --db）を提供して期間フィルタ付きレポートを標準出力に出力。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計して PASS/FAIL 判定を行う（閾値はソース内定義）。
    - DB が存在しない場合やテーブルが欠けている場合のフォールバック処理（OperationalError を捕捉して N/A を出力）。
    - P95 計算、フォーマットヘルパー関数を実装。
- パッケージエクスポート
  - portfolio / research / utils など主要関数を __init__ でエクスポートして使いやすく整理。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーなど機密情報は Settings 経由で環境変数管理を想定。.env 自動読み込みでは OS 環境変数を保護（protected set）して上書きを制御。

### Notes / Known limitations
- news_nlp.score_news はネットワークや API の失敗時にフェイルセーフでスキップする設計だが、部分失敗時の詳細ロールバック処理やトランザクション管理は追加検討が必要。
- position_sizing: price が欠損（0.0）だとエクスポージャーや算出が過少見積りになる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討中（ソースに TODO コメントあり）。
- .env パーサは多くのケースをカバーするが、非常に複雑なケース（複数行値・特殊エスケープ等）は未テスト。
- research モジュールは DuckDB に依存するため、prices_daily / raw_financials 等のテーブル品質に依存する。

---

発見したその他の設計意図・挙動（参考）
- run_monitoring は MONITOR_POLL_INTERVAL に 0 以下や不正文字列が設定された場合、警告を出して 60 秒にフォールバックする（time.sleep に渡す不正値対策）。
- Settings の env / log_level / paper_fill_mode は不正値で ValueError を送出して早期に misconfiguration を検出する。
- process_priority の設定は権限不足時に警告のみ出して起動を継続する（スケジューラ等での無停止運用を想定）。

もし特定のリリース日や追加のリリース履歴（たとえばパッチやマイナーアップデート）を反映したい場合は、対象のコミットや変更点を教えてください。それに基づいて CHANGELOG を拡張・補正します。