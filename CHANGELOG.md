CHANGELOG
=========

このファイルは "Keep a Changelog" の形式に準拠します。  
主要な変更点は上から新しい順に記載しています。

[Unreleased]
------------

Added
- MONITOR_POLL_INTERVAL 環境変数から監視ループのポーリング間隔を設定可能に（デフォルト: 60 秒）。不正な値（0 以下や非整数）は警告してデフォルトにフォールバック。（src/kabusys/run_monitoring.py）
- CPU affinity 設定ユーティリティを追加（set_cpu_affinity）。指定コア数でプロセスを固定可能（権限やプラットフォーム非対応時は警告してスキップ）。（src/kabusys/utils/process_priority.py）
- Paper Trading 向け検証レポート生成ツールを追加。期間指定や DB 指定オプションを備え、稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定を出力。（src/kabusys/tools/paper_verification_report.py）
- ニュース NLP スコアリング（OpenAI 経由のセンチメント集約・バッチ送信・JSON 検証・スコアクリップ・リトライ/バックオフ）を追加。API キーの明示・環境変数参照、タイムウィンドウ定義等を実装。（src/kabusys/ai/news_nlp.py）
- DuckDB を利用したリサーチ／ファクター計算機能を追加（Momentum / Volatility / Value ファクター、将来リターン・IC・統計サマリー等）。SQL と純粋関数で実装し、標準ライブラリのみで完結する設計。（src/kabusys/research/*）
- ポートフォリオ構築関連の純関数群を追加：
  - 候補選定、等配分／スコア加重の重み算出（src/kabusys/portfolio/portfolio_builder.py）
  - セクター集中制限、レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
  - ポジションサイズ決定（リスクベース／等配分／スコア配分、単元株丸め・スケーリングロジック）（src/kabusys/portfolio/position_sizing.py）
- 実行エンジン起動スクリプトを追加。Paper Trading 環境では MockBroker を用いて本番 DB と分離（専用 SQLite を使用）。Engine の組み立て（OrderRepository / OrderManager / RiskManager / Reconciler）とセッション実行を行う。（src/kabusys/run_execution.py）
- 監視（SystemMonitor）起動スクリプトを追加。プロセス優先度設定、監視 DB 初期化、ポーリングループを備える。（src/kabusys/run_monitoring.py）
- 環境変数読み込みの自動ロード機能を実装（.env / .env.local）。プロジェクトルート検出（.git / pyproject.toml）に基づく読み込み・既存 OS 環境変数保護の仕組みを提供。export 形式やクォート付き値、インラインコメント処理などをサポート。（src/kabusys/config.py）

Changed
- 監視プロセス（run_monitoring）の DB 接続は KABUSYS_ENV に依存せず、本番 sqlite_path を使用するよう明示（監視データは本番監視 DB に集約）。（src/kabusys/run_monitoring.py）
- run_monitoring / run_execution 起動時に最初にプロセス優先度を "high" に設定するよう変更（パフォーマンス安定化目的）。（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）
- .env 自動ロードの優先順位を OS 環境 > .env.local > .env として明確化。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化を追加。（src/kabusys/config.py）
- position_sizing のスケーリングロジックを保守的に見積もるため cost_buffer を導入（手数料・スリッページを見込んだキャッシュ計算）。（src/kabusys/portfolio/position_sizing.py）
- ニューススコアリングのタイムウィンドウ（JST に基づく）を厳密に定義し、UTC に変換して DB クエリで使用するようにした。（src/kabusys/ai/news_nlp.py）
- research モジュールの関数は DuckDB 接続を受け取り外部 API に依存しない設計に統一。（src/kabusys/research/*）

Fixed
- 環境変数パーサーのクォート処理を強化：クォート内のバックスラッシュエスケープに対応し、インラインコメントが誤検出されないように改善。（src/kabusys/config.py）
- .env 上書き時に OS 環境変数を保護する機構を追加（protected set）。これによりテスト時等の意図しない上書きを防止。（src/kabusys/config.py）
- position_sizing の端数処理で単元株（lot_size）単位での丸め・再配分を安定化。残余キャッシュを用いた再割当てで順序が再現性を保つよう安定ソートを採用。（src/kabusys/portfolio/position_sizing.py）
- factor_research / feature_exploration の統計関数で None・非有限値を除外するよう堅牢化。サンプル不足時の戻り値を None に統一。（src/kabusys/research/*）
- process_priority のプラットフォーム互換性とエラーハンドリングを改善。未対応 OS や権限不足時は警告して処理をスキップするように変更。（src/kabusys/utils/process_priority.py）
- paper_verification_report のレポート生成で、データ欠損時（テーブルが存在しない等）に例外を投げずデフォルト値で出力するよう改善。（src/kabusys/tools/paper_verification_report.py）

Removed
- （現時点のコードからは該当なし）

Security
- 環境変数必須項目のチェックを追加（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。未設定時は ValueError を投げて早期検出。（src/kabusys/config.py）
- OpenAI API キー未設定時は明確なエラーを出力して処理を中断（news_nlp）。キーは引数または OPENAI_API_KEY 環境変数で供給可能。（src/kabusys/ai/news_nlp.py）

[0.1.0] - 2026-04-13
--------------------

Added
- 初期公開リリース。以下の主要機能を含む：
  - 自動売買実行エンジン基盤（ExecutionEngine, OrderManager, RiskManager, Reconciler 等の骨格）
    （src/kabusys/execution/* — Engine 実装は本リリースの基盤を提供）
  - 監視基盤（SystemMonitor, monitoring DB 初期化、起動スクリプト run_monitoring）。（src/kabusys/run_monitoring.py, src/kabusys/monitoring/*）
  - Portfolio 構築ライブラリ（候補選定、重み算出、セクター制限、ポジションサイズ計算）。（src/kabusys/portfolio/*）
  - リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー）とファクター評価ツール（IC, 統計サマリ）。DuckDB 統合。（src/kabusys/research/*）
  - ニュース NLP を用いた銘柄別センチメントスコア取得（OpenAI 連携の基礎実装）。（src/kabusys/ai/news_nlp.py）
  - 環境変数管理（.env 自動ロード、堅牢なパーシング、必須チェック）。（src/kabusys/config.py）
  - プロセス優先度・CPU 設定ユーティリティ（クロスプラットフォーム考慮）。（src/kabusys/utils/process_priority.py）
  - Paper Trading 用の専用 DB 分離・検証ツール（run_execution の paper_trading 分岐、paper_verification_report）。（src/kabusys/run_execution.py, src/kabusys/tools/paper_verification_report.py）
  - パッケージ初期バージョン情報 __version__ = "0.1.0"。（src/kabusys/__init__.py）

Changed
- コードベース設計方針の明文化：
  - DuckDB はリサーチ用途（prices_daily, raw_financials 等）専用、SQLite は監視・発注ログ等のトランザクショナル DB に使用する想定。
  - リサーチ / ニュース処理は本番の発注 API を参照しない（フェイルセーフ設計）。
  - 日付処理はルックアヘッドバイアスを避けるため、date/datetime の直接参照を避ける設計方針を明示。

Fixed
- 初期実装段階での基本的な例外処理とログ出力を整備し、トレースが容易になるようにした。

Security
- 環境変数の未設定による誤動作を避けるため、必須項目の早期チェックを導入。

注記
- 本 CHANGELOG はコードベース（src 以下）からの推測に基づいて作成しています。実際のコミット履歴やリリースノートとは異なる場合があります。必要に応じて日付やバージョン、詳細を差し替えてご利用ください。