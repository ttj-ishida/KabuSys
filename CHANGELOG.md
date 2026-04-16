CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、安定した公開・運用のためにセクションを分けて記載します。

Unreleased
----------
(現在なし)

[0.1.0] - 2026-04-16
--------------------
初回リリース。自動売買・リサーチ・監視・実行基盤のコア機能を実装しました。

Added
- 起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグファイルによる安全終了、起動時にプロセス優先度を上げる処理を実装。
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。paper_trading モード時は MockBrokerClient を用いて paper_trading 専用 DB に分離して動作する。停止フラグ・PID ファイル管理・スレッド監視を含む。

- 設定管理
  - kabusys.config.Settings: 環境変数／.env 自動読み込み機能（.env, .env.local、OS 環境変数の保護）、各種設定プロパティ（DB パス、API キー、閾値、環境判定等）を実装。PAPER_FILL_MODE のバリデーションや KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - .env パーサーの強化: export 形式、クォート文字とエスケープ、インラインコメント処理などに対応。

- モニタリング関連
  - monitoring_db の初期化呼び出しを起動フローで行い、監視テーブルが存在することを冪等的に保証。

- 実行系コンポーネント骨子
  - ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager 組み立てと起動フローを実装（run_execution から利用）。RiskConfig のデフォルト値や初期ポートフォリオ値取得処理を含む。

- Portfolio 構築ライブラリ
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等加重（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア合計が 0 の場合は等加重にフォールバックして警告を出す。
  - portfolio.position_sizing: position size（発注株数）計算を実装。risk_based / equal / score の複数方式、lot_size 単位丸め、max_position_pct／max_utilization／aggregate cap（投下資金スケーリング）や cost_buffer を考慮した計算ロジックを実装。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。未知レジームは警告の上でフォールバック。

- Research（ファクター計算・探索）
  - research.factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、出来高指標）、バリュー（PER, ROE）を DuckDB を用いて計算する関数を追加。営業日ベースのウィンドウや欠損データへの配慮を実装。
  - research.feature_exploration: 将来リターン取得（複数ホライズン）、Spearman ランク相関による IC 計算、ファクター統計サマリー（count/mean/std/min/max/median）、ランク化ユーティリティを実装。外部ライブラリ非依存の純粋Python実装。

- AI ニューススコアリング
  - ai.news_nlp: raw_news を集約して OpenAI (gpt-4o-mini) を用いた銘柄別センチメントスコアを生成・ai_scores テーブルへ書き込む機能を追加。記事ウィンドウ計算（JST→UTC 変換）、バッチサイズ制御、トークン肥大化対策（記事数・文字数トリム）、429/ネットワーク/5xx のエクスポネンシャルバックオフ、レスポンスバリデーション、スコアの ±1.0 クリップなどを実装。API キー解決ロジック（引数または環境変数）を備える。

- ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティを実装（set_process_priority）。set_cpu_affinity による CPU コア固定機能も追加。許可不足や未対応環境での安全なフォールバックを実装。

- ツール
  - tools.paper_verification_report: Paper Trading DB から稼働率・注文成功率・送信率・レイテンシ指標を集計して PASS/FAIL 判定するコマンドラインツールを追加。閾値はソース内定数で定義（稼働率 99% など）。日付フィルタ・DB パス指定オプションをサポート。

Changed
- データベース接続ポリシー
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データの一貫性確保）。
  - 実行エンジンは paper_trading モード時に専用 SQLite を使用する（本番 DB と分離）。

- ロギング・エラーハンドリング
  - run_monitoring のポーリングループで check_once() の例外をキャッチしてログ出力し、次のポーリングへ継続するフェイルセーフ挙動を採用。
  - .env 読み込み失敗時に警告を出すなど、起動時の堅牢化を実施。

Fixed
- 環境変数・設定周りの堅牢性改善
  - MONITOR_POLL_INTERVAL の値が不正（非整数・0 以下）の場合にデフォルトにフォールバックし、警告ログを出す処理を実装（run_monitoring 内 _get_poll_interval）。
  - PAPER_FILL_MODE の不正値に対する明示的な例外とメッセージを追加（Settings.paper_fill_mode）。

- 数値計算・丸めの安定化
  - position_sizing のスケーリング処理において lot_size 単位での丸め・残差配分ロジックを実装し、合計投下資金が利用可能現金を超えた際に安定してスケールダウンするよう修正。

Documentation / Notes
- 各モジュールに詳細な docstring を追加し、設計方針や外部依存（DuckDB, OpenAI 等）、期待されるテーブル構造や入力・出力形式を明記。
- PortfolioConstruction.md、StrategyModel.md 等の設計ドキュメント参照をソース内コメントで示し、将来的な拡張点（lot_size 銘柄別サポート、価格フォールバック等）を注記。

Security
- OpenAI API キーは引数または環境変数から解決し、未設定時は明示的な例外を投げて処理を停止（誤ったキー運用を防止）。

Acknowledgements / Known limitations
- ai.news_nlp の処理はネットワークや API の失敗に対してリトライ/スキップでフェイルセーフ化しているが、API 使用量やコスト・レスポンスフォーマットの変化に依存するため運用上の監視が必要です。
- research モジュールは DuckDB 上のテーブル構成（prices_daily, raw_financials 等）を前提にしており、テーブルスキーマが異なる環境では動作しません。
- 一部機能（例: ai.news_nlp の完全なエラーハンドリング・部分的な DB 書き込み戦略）は本リリース時点で運用監視のもと実運用することを想定しています。

今後の予定（例）
- 単元株情報を銘柄ごとに管理する拡張（lot_size の銘柄別マップ）
- price フォールバック（前日終値や取得原価）を用いたエクスポージャー推定改善
- ai.news_nlp の処理結果の監査ログ／部分失敗リカバリ機能の強化

変更点に関する問い合わせや誤記/追記希望は issue を立ててください。