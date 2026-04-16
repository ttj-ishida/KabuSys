# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般:
- 日付はコミット/リリース相当日を想定して記載しています（コードベースから推測）。
- 環境変数や挙動はソースコードのコメント・実装に基づいて記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-16
初回リリース相当。日本株自動売買システム「KabuSys」のコア機能群を実装。

### Added
- コマンド / デーモン起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリーポイントを追加。BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンをスレッド実行する実装を提供。
    - 停止フラグ (data/stop_requested.flag) を検出して安全に停止する仕組みを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離する挙動を導入。
    - プロセス優先度を起動直後に "high" に設定する処理を導入（utils.process_priority 経由）。
  - run_monitoring.py
    - SystemMonitor を定期ポーリングで実行する監視デーモンの起動スクリプトを追加。デフォルトポーリング間隔 60 秒。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（不正値は警告してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様を明示的に実装。
    - 停止フラグの検出と例外発生時のロギングを備えた堅牢なループを実装。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を優先順でロード。OS 環境変数は保護）。
    - .env パーサーを強化（コメント、export 形式、クォートとエスケープの扱い、インラインコメント処理）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - Settings クラスに多数のプロパティを実装（DB パス、PaperTrading 関連、監視閾値、環境バリデーション等）。PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV と LOG_LEVEL の検証を追加。

- ポートフォリオ構築モジュール
  - kabusys.portfolio
    - portfolio_builder.py: 候補選定(select_candidates)、等金額/スコア加重の重み計算(calc_equal_weights / calc_score_weights)を実装。スコア全0時のフォールバックも含む。
    - risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数(calc_regime_multiplier)を実装。
    - position_sizing.py: position sizing（risk_based / equal / score）実装。単元株（lot_size）丸め、max_position_pct、max_utilization、aggregate cap（投下資金超過時のスケールダウン）、cost_buffer を考慮した安全な配分ロジックを提供。

- 研究・ファクター群
  - kabusys.research
    - factor_research.py: Momentum / Volatility / Value ファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算。
    - feature_exploration.py: 将来リターン calc_forward_returns、IC 計算 calc_ic、ランク関数 rank、統計サマリ factor_summary を実装。外部依存を持たない純 Python 実装。
    - research.__init__ で必要関数を公開。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news と news_symbols を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を実装。
    - バッチサイズ、トークン肥大対策（記事数/文字数トリム）、JSON レスポンス厳格バリデーション、スコアクリップ（±1.0）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）などのフェイルセーフを備える。
    - ニュース収集ウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で提供。
    - API キー未設定時は ValueError を投げる（引数 or 環境変数 OPENAI_API_KEY）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを実装（コマンドラインから使用可）。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、閾値による PASS/FAIL 判定を行う。
    - DB が存在しない、またはテーブルがない場合も例外処理で N/A を出力する堅牢な実装。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定（set_process_priority）を実装。Windows / POSIX（Linux/Mac/FreeBSD）対応。アクセス権限不足等で失敗しても警告してスキップする。
    - set_cpu_affinity を実装し、指定したコア数へプロセスを固定する機能を提供（権限不足や未対応 OS は警告してスキップ）。

- データベース / クエリ
  - DuckDB と SQLite の両方を使用する設計を導入（DuckDB は分析用、SQLite は監視・paper_trading 用など）。
  - 監視テーブル初期化用の init_monitoring_db 呼び出しを run_execution/run_monitoring の起動時に行い、冪等にテーブル存在を保証。

### Changed
- 環境分離 / DB パス運用
  - run_execution: paper_trading 環境では Paper 用 SQLite を使用して本番 DB とデータを分離する運用方針を明確化。
  - run_monitoring: 監視は環境にかかわらず本番 sqlite_path を使用するように実装（意図的な設計）。

- .env 読み込みの安全性
  - OS 環境変数は保護され、.env.local は .env を上書きするが OS 環境変数は上書きしない実装により、意図しない上書きを防止。

- ロギング / フェイルセーフ
  - monitor.check_once() や ExecutionEngine スレッド実行時の例外はキャッチしてログ出力し、プロセスを即時終了させずに継続する堅牢化を行った。

### Fixed
（初回リリースのため主に新規実装。コード内で扱われている既知の不整合や将来対応メモはコメントとして残している）
- position_sizing 等で価格欠損時の扱いに関するログ／スキップ処理を実装（price が欠損した場合はスキップして過大評価を防止）。
- .env ファイル読み込みでファイルアクセス失敗時に警告を出すようにし、致命的な例外を回避。

### Documentation
- モジュールレベルの docstring やコード内コメントを充実させ、設計意図（PortfolioConstruction.md / StrategyModel.md 等の参照を想定）や使用上の注意を明示。
- tools/paper_verification_report や ai/news_nlp に使用方法・引数・環境変数の説明を追加。

### Security
- 設定値取得時に必須環境変数が未設定である場合は明示的に例外を送出する実装（_require）。API キー等の必須項目の未設定を早期に検出。

---

将来のリリースでは以下の改善が想定されています（ソース内コメントに基づく提案）
- price 欠損時のフォールバック価格（前日終値・取得原価など）の導入。
- 銘柄ごとの lot_size を持つ拡張（stocks マスタからの取得）。
- ai/news_nlp の部分失敗時のトランザクション制御強化やより詳細なバッチ失敗ハンドリング。
- ExecutionEngine 周りの監視・PID 管理・再起動戦略の整備。

以上。