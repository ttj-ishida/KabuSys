Keep a Changelog
=================

すべての重要な変更をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。<https://keepachangelog.com/ja/1.0.0/>

注: 日付は本コードベース解析時点 (2026-04-12) を使用しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-12
--------------------

Added
- プロジェクト初回リリース (パッケージバージョン: 0.1.0)。
- 起動スクリプト / デーモン類
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient（paper 用 DB に記録）を使用して本番 DB と分離する挙動をサポート。
- 設定管理
  - kabusys.config: .env/.env.local 自動読み込み（OS 環境変数優先、.env.local は上書き）、プロジェクトルート探索（.git または pyproject.toml 基準）、行パーサの実装（export 形式や引用符、コメント処理に対応）。
  - Settings クラスに多数のプロパティを追加（DB パス、PID/kill フラグ、閾値、環境種別検証、paper_trading 関連設定など）。無効値時の検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実装。
- モニタリング / ツール
  - monitoring DB 初期化ユーティリティを起動スクリプトから呼び出すことで監視用テーブルの存在を保証。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL を判定。P95 計算、日付フィルタ、DB 存在チェック、CLI オプション（--from/--to/--db）を提供。
- ポートフォリオ構築関連（純粋関数、DB 非依存）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。全スコア 0 の場合は等分配にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap（当日売却予定の銘柄を除外できる、"unknown" セクターは制限対象外）、市場レジームに応じた資金乗数 calc_regime_multiplier（未知レジームはフォールバック 1.0）。
  - portfolio/position_sizing.py: position sizing 実装（risk_based / equal / score モード）、単元株丸め、銘柄別上限、aggregate cap スケーリングと端数の再配分ロジック、コストバッファ対応。
- 研究（Research）モジュール
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を実装（DuckDB 接続を受け prices_daily / raw_financials を参照）。MA200、ATR20、各種リターンなどを計算し、データ不足時には None を返す設計。
  - research/feature_exploration.py: 将来リターン calc_forward_returns、スピアマンランク相関による IC 計算 calc_ic、rank・factor_summary を実装。外部依存を避け標準ライブラリのみで実装。
  - research/__init__.py に主要関数群をエクスポート。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化して ai_scores に書き込む処理を追加。処理は銘柄ごと集約・バッチ（最大 20 銘柄）・トークン肥大対策（記事・文字数制限）・リトライ（429/ネットワーク/5xx に対する指数バックオフ）・レスポンス検証・スコアクリップを備える。API キー未設定時は明示的なエラーを返す。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows と POSIX の差分吸収、アクセス権限や未対応 OS の場合は警告を出してスキップ。set_cpu_affinity で最初 N コアにピン留め可能。

Changed
- 初回リリースのため該当なし。

Fixed
- 各所での堅牢化／フォールバック実装
  - MONITOR_POLL_INTERVAL の不正値を検出してデフォルトへフォールバック（警告出力）。
  - .env パーサで引用符・エスケープ・インラインコメントを考慮することで現実的な .env フォーマットに対応。
  - position_sizing のスケールダウン時の端数処理で安定した再配分ロジックを実装し再現性を担保（残差ソートの安定化）。
  - factor_research / volatility 等でデータ不足時に None を返すことで downstream のエラーを回避。
  - tools/paper_verification_report: DB が存在しない場合のわかりやすいエラーメッセージを追加。

Removed
- 初回リリースのため該当なし。

Deprecated
- なし

Security
- ai/news_nlp.score_news: OpenAI API キーの未設定時は ValueError を送出。環境変数 OPENAI_API_KEY または引数での明示指定が必須。

Notes / 備考
- paper_trading 環境は本番 DB とファイルを完全に分離している（PAPER_TRADING_SQLITE_PATH / settings.is_paper）。
- 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。プロジェクトルートが特定できない場合は自動ロードをスキップする。
- 実行系スクリプトは起動時にプロセス優先度を "high" に設定しようとするが、権限不足などで失敗した場合は警告を出して継続する。
- ロギングレベルと環境種別は Settings により厳密に検証され、不正な値は ValueError を発生させる。
- DuckDB / SQLite を用いる設計のため、ローカルの DB ファイルを前提としている。tools/paper_verification_report や研究機能は DuckDB 接続に依存する。

開発者向けメモ
- バージョン番号は kabusys.__init__.__version__ = "0.1.0" にて管理。
- ai/news_nlp の OpenAI クライアントは OpenAI Python SDK を使用（OpenAI クラス）。API レート制御やエラーハンドリングの拡張は今後の課題。
- position_sizing の lot_size は現状グローバル共通（デフォルト 100）。将来的には銘柄別 lot 情報を導入する予定。

以上。