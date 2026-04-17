CHANGELOG
=========

すべての重要な変更を時系列で記録します。形式は "Keep a Changelog" に準拠しています。

リリース日: 2026-04-17

[0.1.0] - 2026-04-17
--------------------

初回リリース — 基本的な自動売買 / リサーチ / 監視ユーティリティ群を実装しました。

### 追加
- 全体
  - パッケージ kabusys を初期実装。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - DuckDB と SQLite を併用するデータ基盤の採用（各処理でそれぞれ接続を受け取る設計）。
- 設定管理（src/kabusys/config.py）
  - .env / .env.local を自動読み込みする仕組みを実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env パース処理を強化（export プレフィックス対応、クォート内のエスケープや行末コメント処理など）。
  - Settings クラスを実装し、環境変数からアプリ設定を提供（DB パス、API トークン、Paper Trading 切替等）。
  - 環境値のバリデーションを実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine 起動エントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を利用し、MockBrokerClient を利用する設計（本番 DB と分離）。
    - 実行の PID ファイル管理、data/stop_requested.flag による安全な停止フローを実装。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で安全停止を行う。
    - Execution に必要なコンポーネント（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立てる。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データの一元化）。
    - data/stop_requested.flag による停止および KeyboardInterrupt による終了処理を実装。
- Portfolio（src/kabusys/portfolio）
  - portfolio_builder.py: 銘柄選定および重み計算ユーティリティを追加（select_candidates / calc_equal_weights / calc_score_weights）。
  - position_sizing.py: 株数決定ロジック（risk_based / equal / score）を実装。ロット丸め、aggregate cap によるスケールダウン、コストバッファ考慮など。
  - risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
  - パブリック API を kabusys.portfolio でエクスポート。
- Research（src/kabusys/research）
  - factor_research.py: モメンタム・ボラティリティ・バリュー系ファクターの計算関数を追加（calc_momentum / calc_volatility / calc_value）。DuckDB 上の prices_daily / raw_financials を参照する設計。
  - feature_exploration.py: 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー等を追加（calc_forward_returns / calc_ic / factor_summary / rank）。
  - research パッケージで zscore_normalize（data.stats 由来）等をエクスポート。
- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI API（gpt-4o-mini）でスコアリングするロジックを実装。
  - タイムウィンドウ計算、記事集約、バッチ送信、リトライ（指数バックオフ）、レスポンス検証、スコアクリッピング、部分更新（対象コードのみ DELETE→INSERT）などの設計方針を実装。
  - API キー解決（引数優先、環境変数 OPENAI_API_KEY フォールバック）と未設定時のエラーを実装。
- ツール（src/kabusys/tools）
  - paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
- ユーティリティ（src/kabusys/utils）
  - process_priority.py: プロセス優先度設定と CPU affinity 設定ユーティリティを追加（Windows と POSIX の差を吸収）。エラー時は警告を出して処理をスキップするフェイルセーフ。
- 監視 DB 初期化
  - monitoring_db.init_monitoring_db を各起動スクリプトで呼び出すことで、監視用テーブルが存在することを保証（冪等性）。
- その他
  - DuckDB 接続を関数引数で受け渡す設計により、リサーチ / AI / ツールが同一 DB を再利用可能。

### 変更
- 設計/運用
  - 環境変数読み込みの優先順位を明文化（OS > .env.local > .env）。既存 OS 環境変数は保護され、.env.local は上書き可能。
  - run_monitoring では MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）は警告してデフォルト 60 秒にフォールバックする保護を追加。
  - Execution エンジンの risk_manager デフォルト設定を明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 関連など）。
  - Paper Trading 用 DB を明確に分離（settings.paper_sqlite_path）。paper_trading 環境では本番データベースにアクセスしない。
  - News NLP の出力は厳密な JSON を想定（システムプロンプトで明示）。
  - position_sizing の aggregate cap ロジックを追加し、残余現金で lot_size 単位の再配分を行うように改善。

### 修正（バグ修正 / 安全性向上）
- .env パーサーの強化により、次のケースを正しく扱うようになりました：
  - export KEY=val 形式のサポート。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
  - クォートなしでのインラインコメントの誤検出の緩和（'#' の前にスペースがある場合のみコメント扱い）。
- run_execution / run_monitoring における接続クローズや例外ハンドリングを改善（finally ブロックでの接続クローズや、check_once 内の例外キャッチ）。
- process_priority / set_cpu_affinity で権限不足やプラットフォーム未対応時に警告してスキップするようにし、起動失敗を避ける動作に。

### 既知の問題（注意事項）
- ai/news_nlp.py の実装は大部分が整っているものの、ファイル末尾が不完全に見える箇所があり（ソースが途中で切れている）、記事取得部分（_fetch_articles から以降）やバッチ送信ループの完全な実装・統合が必要です。OpenAI API 呼び出し周りの細かい検証ルーチンは設計されているものの、実行前に未完成部分の実装確認を推奨します。
- position_sizing.calc_position_sizes 内の price が欠損（0.0）の場合のフォールバック処理は TODO コメントとして残してあります。前日終値や取得原価を使ったフォールバックを将来的に検討してください。
- tools.paper_verification_report は DuckDB ではなく Paper Trading の SQLite DB（デフォルト data/paper_trading.db）を参照します。DB ファイルが存在しない場合はエラーメッセージを出力して終了します。
- DuckDB の executemany 周りの制約（バージョン依存）に注意する実装注記がいくつかに存在します（ai/news_nlp の部分更新設計等）。
- run_monitoring は監視 DB として settings.sqlite_path を使用するため、監視データの分離やバックアップ方針を運用側で整備してください。
- process_priority の適用は OS と権限に依存します。権限が不足する場合は警告が出るだけで続行しますが、期待どおりに優先度が設定されない可能性があります。

### マイグレーション / 実行上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings によって必須扱いとなります（実行前に .env を用意してください）。
  - OPENAI_API_KEY は news_nlp を利用する場合に必要（関数呼び出しでキー指定も可）。
- 主要な環境変数（例）:
  - KABUSYS_ENV (development | paper_trading | live)
  - SQLITE_PATH（監視 DB）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - DUCKDB_PATH（DuckDB ファイル）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒）
  - PAPER_FILL_MODE（instant|partial|never|reject）
- 実行例:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

今後の予定
- ai/news_nlp の未実装部分を完成させ、エンドツーエンドのニューススコアリングを完了する。
- position_sizing の価格フォールバック実装（前日終値や取得価格の利用）。
- 単体テストと統合テストの整備、CI パイプラインの追加。
- ドキュメント（運用手順、環境変数一覧、監視ダッシュボード設計）の充実。

----- 
（本 CHANGELOG はソースコードの実装内容およびコメントをもとに推測して作成しています。運用上の正確な差分やマイグレーション手順は実行環境や追加の未提供コードに依存します。）