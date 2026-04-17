# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
重大なバージョンの変更ポリシーは SemVer に準拠します。

## [Unreleased]

### Added
- 監視・実行用の起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）を検知して安全に停止する。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB を使用し、本番 DB と分離して実行可能。停止フラグ・実行 PID 管理に対応。

- 設定読み込み・検証機能を追加（kabusys.config）
  - プロジェクトルート自動探索（.git または pyproject.toml 基準）を実装し、.env / .env.local を自動ロード（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサの強化: export プレフィックス、クォート文字内のバックスラッシュエスケープ、インラインコメントの扱い、無効行のスキップなどに対応。
  - 設定値取得クラス Settings を提供。DB パス、Paper Trading 設定、監視閾値、環境（KABUSYS_ENV）とログレベルの検証などを行う。
  - PAPER_FILL_MODE の入力検証（有効値: instant|partial|never|reject）と PAPER_TRADING_SQLITE_PATH の設定を追加。

- ポートフォリオ構築関連の純粋関数群を追加（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - position_sizing: 株数決定ロジック（calc_position_sizes）を追加。risk_based / equal / score の各割当方式、lot_size による丸め、コストバッファを考慮した aggregate cap スケーリング等に対応。

- リサーチ・ファクタ計算モジュールを追加（kabusys.research）
  - factor_research: モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB を使用して prices_daily / raw_financials を参照）。
  - feature_exploration: 将来リターン計算（複数ホライズン）、Information Coefficient（Spearman）計算、ファクター統計サマリー、ランク処理ユーティリティを追加。
  - DuckDB 接続を受け取り SQL + Python で高速に計算する設計。

- ニュース NLP（AI）スコアリングモジュールを追加（kabusys.ai.news_nlp）
  - raw_news / news_symbols からニュースを集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメント（-1.0〜1.0）を算出して ai_scores に格納する処理を実装。
  - タイムウィンドウ計算、記事トリム（最大記事数・最大文字数）、バッチ処理、エラー時の指数バックオフリトライ、レスポンス検証、スコアのクリップ（±1.0）をサポート。
  - OPENAI_API_KEY が未設定の場合は明示的にエラーを返す設計。

- ユーティリティ追加（kabusys.utils）
  - process_priority: プロセス優先度設定(set_process_priority) と CPU affinity 設定(set_cpu_affinity) を提供。Windows / POSIX の差分吸収、権限不足や未対応環境でのフォールバック処理あり。

- 検証レポートツールを追加（kabusys.tools.paper_verification_report）
  - Paper Trading 用の検証レポートを生成する CLI スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを計算し PASS/FAIL 判定を表示。PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB 指定が可能。
  - P95 計算、および DB の存在チェックと SQL 実行時の OperationalError 耐性を実装。

### Changed
- 監視ループのデフォルト挙動
  - run_monitoring: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計となっていることを明示（運用上の注意）。
- ExecutionEngine の起動フロー調整
  - run_execution: 起動前に監視停止フラグをチェックし、既に停止フラグが立っている場合は起動を回避するように変更。エンジンは別スレッドで実行し、停止フラグ検知時にエンジン.stop() を呼び安全に終了する。
- Settings の自動読み込み順序
  - OS 環境変数 > .env.local > .env の優先順位を明確化。既存の OS 環境変数を保護するため protected パラメータを導入（.env の上書きを抑制）。

### Fixed
- .env パーサの不具合回避
  - クォート内のバックスラッシュエスケープやインラインコメントの誤解釈を修正し、より現実的な .env 記述に耐性を持たせた。
- データ不足に対する安全処理
  - research / tools / portfolio の各計算で入力データが不足する場合（NULL, 0, 行不足など）に None を返す、またはロギングを行って処理を継続するように堅牢化。
  - paper_verification_report のクエリは OperationalError をキャッチしてデフォルト値にフォールバックするように改善。

### Security
- OpenAI API キーの取り扱いに関する明示
  - news_nlp.score_news は api_key パラメータまたは環境変数 OPENAI_API_KEY を必要とし、未設定時は ValueError を発生させることでキーの意図しない漏れや未設定を検出しやすくした。

## [0.1.0] - Initial release
リリース日: 未設定

### Added
- 初期実装として上記の主要機能をまとめてリリース:
  - コアパッケージ初期バージョン（__version__ = "0.1.0"）
  - 実行・監視スクリプト、設定管理、ポートフォリオ構築、ポジションサイジング、リスク調整、リサーチ / ファクター計算、特徴量解析ユーティリティ、ニュース NLP、プロセス優先度ユーティリティ、Paper Trading 検証レポートツール 等を含む。

### Changed
- 初期リリースにあわせた設計ドキュメント参照（コメント内）と実装の整合性を確保。

---

注記:
- 本 CHANGELOG はコードベース（src/ 以下）から機能・動作を推測して作成しています。実際の公開リリース履歴やコミット単位の差分はリポジトリの Git 履歴を参照してください。
- 運用上の注意:
  - run_monitoring は本番 DB を直接参照するため、テスト環境で実行する場合は設定に注意してください。
  - set_process_priority / set_cpu_affinity は実行環境の権限・OS に依存し、失敗時は警告ログでフォールバックします。