# KabuSys — README (日本語)

概要
-
KabuSys は日本株の自動売買 / 研究 / 監視を目的としたモジュール群です。  
このリポジトリには、取引実行エンジン（ExecutionEngine）、監視コンポーネント（MonitoringEngine）、ポートフォリオ構築ユーティリティ、ファクター計算・研究ツール、ニュース NLP による AI スコアリングなどが含まれます。モジュールはなるべく副作用を抑え、DB（SQLite / DuckDB）や外部 API（kabuステーション / OpenAI）とのインタフェースを明確に分離しています。

主な特徴
-
- Execution
  - 実際のブローカー/モックブローカーに対する発注・状態管理（ExecutionEngine、OrderManager、Reconciler 等）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では本番 DB と分離して data/paper_trading.db を使用
- Monitoring
  - システム状態（CPU / メモリ / ディスク）と Execution プロセス可用性を定期記録（SystemMonitor）
  - 注文滞留・約定異常・ドローダウン・ポジション上限の監視（TradeMonitor、RiskMonitor）
  - kill.flag による ExecutionEngine 停止や LINE 通知（AlertManager）へのフック
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- Portfolio / Portfolio Construction
  - 候補選定、等配分 / スコア加重 / リスクベースのポジションサイズ計算、セクター上限、レジーム乗数などの純粋関数群
- Research
  - DuckDB を用いたファクター計算（モメンタム / バリュー / ボラティリティ）や特徴量探索（IC、将来リターン等）
- AI
  - OpenAI を用いたニュースセンチメント解析・市場レジーム判定（news_nlp, regime_detector）
  - バッチ処理・リトライ・レスポンス検証など実運用向けの堅牢な実装

セットアップ手順
-
前提
- Python 3.10 以上（コード内での型 | 演算子の使用に依存）
- Git（任意）

仮想環境の作成（推奨）
- python -m venv .venv
- source .venv/bin/activate  （Windows: .venv\Scripts\activate）

依存パッケージのインストール（例）
- pip install duckdb psutil openai requests streamlit

（プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

環境変数 / .env
- Settings クラスは環境変数を読み取ります。プロジェクトルートに .env / .env.local を置くと自動読み込みされます（CWD に依らず __file__ を起点にプロジェクトルートを探索）。
- 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な必須 / 重要な環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API 用（必須）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector 等）を利用する場合に必須
- KABUSYS_ENV — 動作環境: development | paper_trading | live（デフォルト: development）
- PAPER_FILL_MODE — paper_trading の約定挙動: instant | partial | never | reject（デフォルト: instant）
- SQLITE_PATH — 監視 DB のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 専用 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB のパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH 等（デフォルトは data/ 以下）

簡易 .env の例
- JQUANTS_REFRESH_TOKEN=あなたのtoken
- KABU_API_PASSWORD=あなたのpassword
- OPENAI_API_KEY=sk-...
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

初期ディレクトリ / データ準備
- data/ ディレクトリを作成（DB やフラグファイルがここに置かれます）
  - mkdir -p data

使い方（主要スクリプト）
-
ExecutionEngine を起動
- python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在するとエンジンは起動せず終了
  - data/execution.pid に PID ファイルを書く（停止時や stale PID 検出時に削除）

Monitoring を起動（監視ポーリング）
- python -m kabusys.run_monitoring
- オプション / 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視は本番 DB を参照）
- 停止:
  - プロジェクトルート/data/stop_requested.flag を作成すると監視ループが終了します

Streamlit ダッシュボード（監視 UI）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 既存の monitoring DB を読み取り専用で開く（DB が存在しなければエラー表示）

Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db /path/to/paper_trading.db
- 出力: 標準出力に統計（稼働率、注文成功率、P95 レイテンシ等）と PASS/FAIL 判定を表示

AI 機能（ニュース NLP / レジーム判定）
- kabusys.ai.score_news (news_nlp.score_news): DuckDB 接続と target_date を与えて ai_scores を更新
  - OPENAI_API_KEY が必要
  - 失敗時は安全にフォールバック（部分失敗・APIエラーはログに出力して継続）
- kabusys.ai.regime_detector.score_regime: market_regime テーブルへ書き込み

監視 / Kill Switch
- KillSwitch は RiskMonitor の結果に基づき data/kill.flag を書き、ExecutionEngine に停止シグナルを与えます
- KillSwitch を使う際は Settings.kill_flag_path を指定して評価 / 書き込みを行います
- run_execution は起動時に KILL_FLAG_CLEAR_ON_START 設定を使ってクリアする挙動をサポートできます（Settings 経由）

主要コンポーネントの挙動メモ
-
- init_monitoring_db: monitoring DB の初期化（テーブル作成・マイグレーションを行う）
- MonitoringDB: system_status / trade_logs / positions / risk_logs / dashboard の読み書きを行う軽量ラッパ
- SystemMonitor: process PID チェック、データ鮮度（DuckDB の get_last_price_date を利用）などを監視し system_status に記録
- TradeMonitor: 注文滞留（stale）/ 約定価格異常をチェックして risk_logs に記録
- RiskMonitor: ダッシュボードからドローダウンやポジション数を評価し、必要なら risk_logs を記録
- AlertManager: LINE Push API を使った通知（クールダウンあり）。token/user_id が未設定だと送信はスキップしてログ出力

ディレクトリ構成（主要ファイル）
-
src/kabusys/
- __init__.py — パッケージ定義（バージョンなど）
- config.py — Settings クラス（.env 自動ロード、環境変数管理）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- order_manager.py — 発注管理（OrderManager）
- reconciler.py — 起動時リコンシリエーション
- order_repository.py / order_record.py / broker_api.py 等（実装の一部は省略ファイルとして存在）

src/kabusys/monitoring/
- monitoring_db.py — DB スキーマ初期化・永続化 API（MonitoringDB）
- system_monitor.py — システム状態監視
- trade_monitor.py — 注文監視
- risk_monitor.py — ドローダウン・ポジション監視
- kill_switch.py — kill.flag 管理
- alert_manager.py — LINE 通知
- monitoring_engine.py — 各 Monitor を束ねるエンジン
- streamlit_dashboard.py — Streamlit ダッシュボード

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定 / 配分重み
- position_sizing.py — 株数計算・スケーリング・単元丸め
- risk_adjustment.py — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py — momentum / value / volatility 計算（DuckDB）
- feature_exploration.py — 将来リターン・IC・統計サマリー

src/kabusys/ai/
- news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
- regime_detector.py — 市場レジーム判定（ETF + マクロニュース + LLM）

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成 CLI

運用上の注意点 / トラブルシュート
-
- 権限: psutil によるプロセス優先度設定や CPU affinity は権限不足で失敗する場合があります。警告ログが出ますが、処理自体は継続されます。
- DB 同時アクセス: monitoring 用 SQLite と paper_trading 用 SQLite は分離しています。DuckDB は大規模分析向けに使います。
- OpenAI 呼び出し: OPENAI_API_KEY が未設定の場合、news_nlp/ regime_detector は ValueError を投げます（呼び出す側でキーを渡すか環境変数を設定してください）。API呼び出し時はリトライやフォールバックが組み込まれていますが、API 利用上限やネットワーク障害に留意してください。
- 停止/再開: data/stop_requested.flag や data/kill.flag の存在でプロセスの挙動が変わります。手動でフラグを操作する場合は内容を把握してから行ってください。

拡張 / 開発について
-
- DuckDB の SQL やファクター計算は関数単位で分離されているため、新たなファクターや統計を追加しやすい設計です。
- AI 部分は API 呼び出しとレスポンス処理を分離しており、テスト時に _call_openai_api をモックすることが容易です。
- 設定は Settings クラスから参照するため、テストで環境変数を差し替える・自動ロードを無効化することができます。

問い合わせ・貢献
-
- バグ報告や機能要望は Issue を立ててください。コントリビュート前に Issue で相談していただけると設計上の整合性が取りやすくなります。

以上がこのコードベースの概要と利用方法の要点です。必要であれば、特定コンポーネント（例: ExecutionEngine の設定、OrderRepository スキーマ、AI のプロンプト調整）について詳細なドキュメントを追加します。どの部分の詳述が欲しいか教えてください。