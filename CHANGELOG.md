CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- なし（初回公開相当の状態を元に作成）

0.1.0 - 2026-04-13
-----------------

### Added
- 初期リリースを追加。プロジェクト名: KabuSys（日本株自動売買システム）。
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、MockBrokerClient による分離運用をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。常に本番 sqlite_path を監視用 DB に使用する。
- 設定管理（kabusys.config）を追加
  - Settings クラスにより環境変数をラップ。DUCKDB/SQLite パス、PID/kill フラグパス、しきい値等をプロパティとして提供。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込み。OS 環境変数を保護する挙動（.env.local は上書き可）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env のパースは export プレフィックス、クォート（バックスラッシュエスケープ含む）、インラインコメントなどに対応。
- ポートフォリオ構築機能（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - position_sizing: ポジションサイズ計算（calc_position_sizes）を実装。allocation_method 支持（risk_based / equal / score）、単元株丸め、全体キャップに対するスケーリング、cost_buffer による保守見積りなどをサポート。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research: モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）ファクターを DuckDB 上の prices_daily / raw_financials を参照して計算。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換（rank）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - zscore_normalize の再エクスポートを含むモジュール統合。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から記事を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を実装。
  - バッチ処理（最大 20 銘柄／リクエスト）、記事数・文字数トリム、JSON モード期待、レスポンス検証、スコアクリップ（±1.0）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
  - API キー未設定時は明示的にエラーを返す設計（api_key 引数または OPENAI_API_KEY 環境変数）。
- 運用補助ツール（kabusys.tools）
  - paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等の統計を計算して CLI 出力。--from/--to/--db 引数をサポート。既定値は data/paper_trading.db。
- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収し、安全にフォールバックする実装。
- DB 初期化ユーティリティ
  - init_monitoring_db が存在し、監視用テーブルの冪等な初期化を実現（実行前に存在確認して作成）。

### Changed
- run_execution.py / run_monitoring.py の挙動
  - 起動直後にプロセス優先度を "high" に設定するよう変更（set_process_priority を早期実行）。
  - run_execution は paper_trading 環境判定で専用 SQLite を使用して本番 DB と分離。
  - run_monitoring のポーリングループは check_once() 内の例外を捕捉してログ出力し、ループを継続するフェイルセーフを実装。
  - ログの基本設定は INFO レベルに設定（logging.basicConfig(level=logging.INFO)）。
- .env ロードの優先順位: OS 環境 > .env.local > .env（.env.local は上書き許可）。既存 OS 環境変数は保護される。
- duckdb / sqlite を組み合わせたデータ処理基盤を明確化（DuckDB は主に価格・ファクタ計算、SQLite は監視・発注ログなどのトランザクション系に利用する想定をコード上で表現）。

### Fixed
- .env 読み込みでの例外ハンドリング強化: ファイル読み込み失敗時に warnings.warn で警告を出力して処理を継続するように。
- .env パースにおけるクォート・エスケープ・インラインコメントの処理を改善して、実運用でよくあるフォーマットに対応。
- position_sizing の aggregate cap スケーリングでの端数処理ロジック整備（単元株単位での追加配分アルゴリズムを実装）。
- news_nlp: タイムウィンドウ計算（JST→UTC 変換）を明確化。API バッチ取得失敗時に他銘柄のスコアを保護するための部分置換戦略（DELETE/INSERT）を採用（設計コメント）。

### Security
- news_nlp の API キー管理: OpenAI API キーは環境変数（OPENAI_API_KEY）または関数引数で明示的に供給する必要があり、未設定時は ValueError を送出して不正な公開アクセスを防止。

### Notes
- 多くの関数は「純粋関数」設計（DB 参照を明示的に受け取る / メモリ内計算）でテスト容易性を考慮。DuckDB 接続を引数に受け取り SQL と Python を組み合わせて計算する方針を採用。
- 一部に TODO コメントあり（例: position_sizing の銘柄別 lot_size 拡張、sector exposure の price フォールバック等）。
- __version__ は 0.1.0 に設定。

今後の予定（想定）
- ドキュメント整備（PortfolioConstruction.md 等の参照ドキュメントの公開）。
- 単体テスト・CI の追加、エラーハンドリングのより詳細な強化。
- 銘柄別単元・手数料モデルの導入、OpenAI 呼び出しの非同期化などのパフォーマンス改善。