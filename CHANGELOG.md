Keep a Changelog に準拠した変更履歴（日本語）
======================================

フォーマット: https://keepachangelog.com/ja/1.0.0/ に準拠しています。

Unreleased
----------
- 注意: news_nlp モジュールの実装が途中で切れている箇所があります（ファイル末尾の断片）。AI ニューススコアリング処理は概ね実装方針・API 呼び出し・バッチ処理・リトライなどを備えていますが、一部関数の実装完了が必要です（WIP）。詳細は該当ソースの TODO / コメントを参照してください。

[0.1.0] - 2026-04-17
-------------------

Added
- 基本アプリケーションパッケージを追加。
  - パッケージ名: kabusys、バージョン __version__ = "0.1.0"
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、ブローカーファクトリ、OrderManager/OrderRepository、RiskManager、Reconciler を組み立ててデーモンスレッドでエンジンを起動する仕組みを提供。paper_trading 環境時は paper 用 SQLite DB を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止は data/stop_requested.flag ファイルで制御。
- 設定・環境管理
  - config.py: プロジェクトルート自動検出（.git または pyproject.toml）、.env / .env.local の自動ロード（優先順位: OS > .env.local > .env）と柔軟なパース機能（クォート、エスケープ、コメント処理対応）を実装。各種設定プロパティ（DB パス、PID/kill フラグ、閾値、環境種別、paper_trading 関連設定等）を提供。
- 監視関連
  - monitoring/monitoring_db 初期化呼び出しを実行スクリプトに組み込み（監視テーブルの冪等初期化）。
- ポートフォリオ構築関連（純粋関数モジュール）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
  - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加（レジームマッピング: bull/neutral/bear）。
  - portfolio.position_sizing: 各銘柄の発注株数計算（risk_based / equal / score）、lot_size 単位丸め、aggregate cap によるスケーリングロジックを実装。cost_buffer による保守的見積りをサポート。
- リサーチ / ファクター計算
  - research.factor_research: モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）ファクター計算を実装。DuckDB を用いた SQL + Python の設計。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）およびファクター統計サマリー（factor_summary）とランクユーティリティ（rank）を実装。標準ライブラリのみで完結。
  - research.__init__ に zscore_normalize を含めたエクスポート整備。
- AI ニュース NLP（実装方針・処理フロー実装）
  - ai.news_nlp: raw_news を OpenAI (gpt-4o-mini) でスコアリングするためのモジュールを追加。バッチ送信、最大記事数/文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、結果の ai_scores テーブルへの安全な置換ロジックなどを設計・実装（ただし前述の通りファイル末尾に途中の断片あり）。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。コマンドライン引数（--from/--to/--db）対応。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。しきい値はスクリプト内で定義（稼働率99%、成功率90%、送信率95%、P95 200ms）。
- ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）向けのプロセス優先度設定と CPU affinity 固定関数を追加。psutil に基づく実装で、アクセス権や未対応プラットフォームの場合は警告ログでフォールバック。

Changed
- DB/環境分離:
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用することで paper 環境と live を明確に分離（data/paper_trading.db がデフォルト）。
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを一元管理。
- .env ロード挙動:
  - OS 環境変数を保護するため protected set を導入。デフォルトで .env/.env.local を自動ロードするが KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- 環境変数のバリデーション:
  - PAPER_FILL_MODE の有効値チェックを導入（instant/partial/never/reject）。不正値で ValueError を投げるように変更。
  - KABUSYS_ENV / LOG_LEVEL の許容値検証を追加。
- ポジションサイジングの安定化:
  - aggregate cap スケーリングのアルゴリズムを実装（小数点切捨て・lot 単位丸め・残差配分）し、利用可能現金に応じた安全な株数決定を行うように改善。
- 監視ループの堅牢化:
  - MONITOR_POLL_INTERVAL 環境変数のパースを改善し、不正な値（0/負数/非整数）はデフォルト値にフォールバックして警告ログを出力。
  - check_once() 実行時に例外捕捉してループを継続するフェイルセーフを追加。
- CLI/レポート:
  - paper_verification_report は日付フィルタを ISO8601 UTC 文字列に変換して DB クエリに使用するよう実装。DB 不在時のエラーメッセージを明確化。

Fixed
- 環境変数パースの改善:
  - .env のクォートされた値内のバックスラッシュエスケープ、コメント処理、export KEY=val 形式に対応して誤ったパースを修正。
- プラットフォーム例外対策:
  - psutil による優先度/affinity 設定で AccessDenied / NotImplementedError 等を捕捉して警告ログとともにスキップするようにし、起動失敗を回避。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を参照する設計。未設定時は ValueError を投げ、秘密情報の誤使用リスクを低減。

Known issues / Notes
- ai/news_nlp.py の末尾が途中で切れており、記事取得フェーズ以降の処理が未完です。実運用前に該当箇所の実装・テストが必要です。
- apply_sector_cap の注記: price_map に price が欠損（0.0）の場合にエクスポージャーが過少見積りされる点が未対処。将来的に前日終値や取得原価でのフォールバックを検討する旨がコメントに残っています。
- position_sizing: lot_size は現在全銘柄共通（default 100）。将来的には銘柄別 lot_map に拡張する TODO が存在します。
- DuckDB / executemany の制約により、news_nlp のパラメータ組立時に空 params を渡さないチェックが必要である旨の注意書きが残っています。
- run_monitoring / run_execution はファイルフラグ (data/stop_requested.flag) による停止を受け入れる設計のため、ファイルベースの運用ルールに従ってください。

作者・連絡
- ソース内のモジュール docstring とコメントを参照してください。README / ドキュメントがあればそちらを優先してください。

以上。