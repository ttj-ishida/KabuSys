# Keep a Changelog
全ての変更は https://keepachangelog.com/ja/ に従って記載しています。

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買フレームワーク「KabuSys」の基礎機能群を追加しました。
以下はコードベースからの機能／設計上の特徴の要約です（実装ファイル群を参照して推測）。

### Added
- 基本情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。

- 設定管理
  - 環境変数および .env/.env.local の自動ロード機能を追加（src/kabusys/config.py）。
    - プロジェクトルートは .git または pyproject.toml を基準に検出。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - export KEY=val 形式、シングル／ダブルクォート、行コメントの扱いに対応したパーサを実装。
    - Settings クラスで各種設定値（DBパス、APIトークン、閾値、環境種別など）をラップし、バリデーションを実装。

- 実行スクリプト
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用して DB 初期化を行う（init_monitoring_db）。
    - 停止フラグファイル data/stop_requested.flag の存在でループを終了。
    - 起動直後にプロセス優先度を "high" に設定（utils/process_priority を使用）。

  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB を使用して本番と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組立て。
    - RiskManager に対するデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、など）を定義。
    - エンジンは別スレッドで run_session を実行、停止フラグ監視で安全停止処理を実施。
    - PID ファイルを管理（data/execution.pid）。

- 監視／モニタリング関連
  - 監視 DB 初期化ユーティリティ参照（monitoring_db.init_monitoring_db を想定）。

- ツール
  - Paper Trading 用検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 検証項目：稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなど。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - コマンドライン引数 --from / --to / --db をサポート。
    - 判定基準（閾値）はソース内に定義（稼働率 99.0% など）。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、signal_rank によるタイブレーク）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、全スコアが 0 の場合は等配分にフォールバック）
  - セクター制約・レジーム係数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮してセクター集中を除外、"unknown" セクターは除外対象外）
    - calc_regime_multiplier（regime に応じた投下資金乗数: bull/neutral/bear）
  - 株数決定・丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes（risk_based / equal / score に対応）
    - lot_size（単元株）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap とスケーリング実装
    - 端数配分アルゴリズム（残余キャッシュで lot 単位の追加配分を行う）

- 研究用モジュール（DuckDB 前提）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum：1M/3M/6M リターン、MA200 乖離率（データ不足時は None）
    - calc_volatility：ATR20、ATR 相対値、20日平均売買代金、出来高比率
    - calc_value：財務データ（raw_financials）を用いた PER / ROE（target_date 以前の最新財務を使用）
    - 全て DuckDB 接続を受け取り SQL で完結する実装
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns：将来リターン（指定ホライズン）計算（デフォルト [1,5,21]）
    - calc_ic：Spearman ランク相関（IC）計算（rank ユーティリティを含む）
    - factor_summary：count/mean/std/min/max/median を算出
    - 実装は標準ライブラリのみで依存を最小化

- AI ニュース NLP（下書き／実装中のモジュール）
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメントスコア化し ai_scores に書き込む処理の設計を追加（src/kabusys/ai/news_nlp.py）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算するユーティリティ（calc_news_window）。
    - バッチサイズ、トークン肥大化対策、リトライ（429/5xx/API 接続エラー）などの設計（冪等性と部分成功保護を考慮）。
    - API キー解決ロジック（引数優先、環境変数 OPENAI_API_KEY）と未設定時の例外。
    - （注）ソースは途中で切れているため、いくつかの内部関数実装が未完または省略されている可能性あり。

- ユーティリティ
  - process_priority（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供
    - 権限不足や未対応環境では警告ログを出して安全にスキップ

### Changed
- （初期リリースのため該当なし） — 既存コードの改変履歴はなし。

### Fixed
- （初期リリースのため該当なし） — バグ修正履歴はなし。ただし各モジュールでエラー時のフォールバックや警告出力を広く採用し、フェイルセーフ設計となっている。

### Notes / Known limitations
- news_nlp.py はソースが途中で切れているため、記事取得・API 呼び出し・DB 書き込みの具体的な実装やエラーハンドリングの詳細は不完全な箇所がある可能性があります。実運用前に該当ファイルの完成とテストを推奨します。
- position_sizing の価格欠損（price が 0 の場合）に関する TODO コメントあり：現在は 0 として扱い、過少見積りにつながる可能性があるため、前日終値等のフォールバック導入を検討してください。
- .env パーサは多くのケースに対応しますが、極端な入れ子クォートや複雑なエスケープケースでは予期しない動作をする可能性があります。
- DuckDB/SQLite のスキーマ（prices_daily, raw_financials, trade_logs, system_status, ai_scores, raw_news 等）は本 CHANGELOG に含めていません。各 SQL クエリが参照するカラムが存在することを前提としています。

### Security
- 環境変数と .env の取り扱いに注意してください。Settings._require により必須トークンが未設定の場合は起動時に例外を投げます。OpenAI API キー等の秘密情報は OS 環境変数での管理を推奨します。

---

今後のリリース候補（例）
- ツールの追加改善（paper report の CSV/JSON 出力、期間集計の改善）
- news_nlp の完成（記事フェッチ、API 結果バリデーション、部分成功時のトランザクション処理）
- モニタリングのアラート送信（LINE 連携の実装）
- テストケース追加（各純粋関数、DB クエリ、エッジケース）

（以上）