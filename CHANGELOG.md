# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

なお本ファイルは、提供されたソースコードの内容から推測して作成した変更履歴です（実際のコミット履歴ではありません）。実装上の注釈や既知の制限も併記しています。

## [Unreleased]

### Added
- 自動環境変数読み込み機能の実装（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込み。
  - OS 環境変数は保護され、.env.local による上書きや .env の未定義キーのセット動作を制御。
  - 複数の .env フォーマット（コメント、export 形式、シングル/ダブルクォート、エスケープ）に対応するパーサを実装。
  - 必須環境変数取得時に未設定なら ValueError を投げるユーティリティを提供。

- 実行/監視用エントリポイントスクリプトを追加
  - run_execution.py：ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用し、本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の起動処理を実装。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用する挙動を明記。

- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates：シグナルのスコア降順ソートと上位 N 抽出。
    - calc_equal_weights / calc_score_weights：等金額配分・スコア加重配分（スコア合計 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap：セクター集中上限を判定して候補銘柄をフィルタ（"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数（未知レジームは 1.0 で警告）。
  - position_sizing:
    - calc_position_sizes：allocation_method（risk_based / equal / score）に基づく発注株数算出。lot_size による丸め、per-position 上限、aggregate cap のスケーリングロジック、cost_buffer を考慮した保守的見積りを実装。

- 研究 / ファクター計算モジュールを追加（kabusys.research）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value：DuckDB 上の prices_daily / raw_financials を用いたモメンタム・ボラティリティ・バリュー計算。
    - ウィンドウ長や欠損データ時の None 処理を明確に設計。
  - feature_exploration:
    - calc_forward_returns：複数ホライズンの将来リターンを一括算出する SQL 実装。
    - calc_ic：ファクターと将来リターンのスピアマンランク相関（IC）算出（有効レコード 3 未満で None）。
    - factor_summary / rank：統計サマリと同順位の平均ランク処理（丸めによる ties 対策）。

- AI ニュース NLP（部分実装）を追加（kabusys.ai.news_nlp）
  - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとに -1.0〜1.0 の ai_score を ai_scores テーブルへ書き込む設計。
  - バッチサイズ、トークン肥大化対策、リトライ／バックオフ、レスポンス検証、スコアクリップ等の仕様を実装。
  - ニュース時間ウィンドウ（JST ベース → UTC 変換）を明示。
  - 注意: ソースは途中で切れており（fetch_articles 呼び出し直後で未完）、完全実装は未達。

- ツール群を追加（kabusys.tools）
  - paper_verification_report.py：Paper Trading の検証レポート生成スクリプト
    - system_status / trade_logs / risk_logs を元に稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを計算してテキストレポート出力。
    - 基準値（稼働率・成功率・P95）を定義し、PASS/FAIL 判定を行う。
    - DB 存在チェックや SQL の OperationalError に対するフォールバック処理を実装。

- プロセス優先度ユーティリティを追加（kabusys.utils.process_priority）
  - set_process_priority：Windows / POSIX（Linux/Mac/FreeBSD）に対応した優先度設定を実装（権限不足時は警告してスキップ）。
  - set_cpu_affinity：プロセスの CPU affinity を設定するユーティリティ（引数検証・権限不足時の安全ハンドリングを実装）。

- パッケージメタ情報
  - パッケージ初期バージョンを __version__ = "0.1.0" に設定。

### Changed
- 環境変数読み込みの優先順位と保護ポリシーを明確化（OS 環境 > .env.local > .env）。
- run_monitoring/run_execution 起動時にプロセス優先度を最初に設定するように仕様統一。

### Fixed
- calc_score_weights: 全スコアが 0 の場合は等金額配分にフォールバックして分母ゼロを回避。
- _get_poll_interval: MONITOR_POLL_INTERVAL の不正値（非数・0・負数）を警告してデフォルトへフォールバック。

### Known issues / Notes
- news_nlp（kabusys.ai.news_nlp）はソースが途中で切れており、記事取得部分（_fetch_articles 等）の実装が未完です。現状では利用不可。
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性がある旨をコメントで指摘しており、将来的に価格フォールバックを導入する予定。
- position_sizing:
  - lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map への対応が TODO として残る。
- Settings のバリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）は厳格化されており、値が不正だと ValueError を投げます。運用環境の env 設定に注意してください。
- 自動 .env ロードはプロジェクトルートが特定できない場合スキップされます（配布後や非標準配置の環境での挙動に注意）。

## [0.1.0] - 2026-04-17

初期リリース（推定）。上記 "Added" の機能群を実装したバージョン相当として記載。

- 主要機能
  - 環境設定管理（.env パーサ、Settings クラス）
  - 実行エンジン起動と監視ループ（run_execution, run_monitoring）
  - 注文管理・リスク管理・和解処理の組立て（実行系コンポーネントの雛形）
  - ポートフォリオ構築（候補選定・配分・ポジションサイズ算出・セクター制約・レジーム調整）
  - 研究系モジュール（ファクター計算・将来リターン・IC・統計サマリ）
  - AI ニュース NLP（設計と一部実装）
  - Paper Trading 向け検証レポート出力ツール
  - プロセス優先度 / CPU affinity ユーティリティ
  - DuckDB / SQLite を利用するデータアクセス設計

- 品質・堅牢性
  - 多くの関数で入力検証・欠損値（None）ハンドリングを実装。
  - DB クエリ実行時の OperationalError を受けたフォールバックを実装（tools.report）。
  - 外部 API（OpenAI）呼び出しでのリトライ設計や部分成功を許容する方針。

---

この CHANGELOG はソースコードを元に推測してまとめたものです。実際の変更履歴（コミットログ）を基にしたい場合は、git の履歴から差分を抽出して正確な年代・責任者・コミット単位で更新することを推奨します。