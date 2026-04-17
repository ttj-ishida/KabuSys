KabuSys — 日本株自動売買システム
================================

本書はリポジトリの主要機能・セットアップ・実行方法・ディレクトリ構成をまとめた README です。  
コードは軽量な自動売買エンジン（ExecutionEngine）と監視・リスク管理・研究用ユーティリティ群で構成されています。

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。主な役割は次のとおりです。
- 戦略に基づく銘柄選定とポジション構築（ポートフォリオ構成）
- ExecutionEngine による発注・約定管理（本番 / ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk）による稼働監視と Kill Switch
- DuckDB を使ったファクター計算・研究モジュール
- OpenAI を用いたニュース NLP（センチメント）・市場レジーム判定の補助
- ペーパートレード結果の検証レポート生成ツール

主な機能一覧
-------------
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB に記録
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - 監視ループ、ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（秒）
- 監視エンジン（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- ポートフォリオ構築ユーティリティ（選定・重み付け・ポジションサイズ計算・セクター制限）
- 研究モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI 関連:
  - ニュースの LLM によるセンチメントスコアリング（kabusys.ai.news_nlp）
  - マクロ + MA200 による市場レジーム判定（kabusys.ai.regime_detector）
- ペーパートレード検証レポート生成（python -m kabusys.tools.paper_verification_report）

前提条件 / 必要環境
------------------
- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証で使用）  
  例: pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb psutil openai PyYAML
   - （必要に応じてその他パッケージを追加）

4. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成します（.env は絶対にリポジトリにコミットしないこと）

5. 設定検証（任意、起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading 時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant, partial, never, reject）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH — PID / Kill Flag のパス（デフォルト data/ 以下）

使い方（主要スクリプト）
-----------------------

1) 環境ウィザード
- python -m kabusys.config_setup
  - 対話式で .env を生成 / 更新します。

2) 設定検証
- python -m kabusys.validate_config
- 厳密モード: python -m kabusys.validate_config --strict

3) ExecutionEngine を起動（発注エンジン）
- python -m kabusys.run_execution
  - KABUSYS_ENV により本番/ペーパーを切り替えます。
  - data/execution.pid に PID を書き込みます。
  - data/stop_requested.flag が存在すると起動・継続を停止します。

4) Monitoring を起動（監視プロセス）
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御
  - 監視結果は monitoring DB（SQLite）へ永続化
  - Stop フラグ: repository ルートの data/stop_requested.flag を検知して停止します

5) ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡単なパス/指標（稼働率・成功率・P95 レイテンシなど）を表示します

AI 関連 (OpenAI)
- ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（DuckDBPyConnection）を渡して実行。api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。
- 市場レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意点・運用上のポイント
-----------------------
- .env は機密情報を含むため Git 管理しないこと（config_setup でも注意書きあり）。
- KABUSYS_ENV=paper_trading は本番 DB と分離して動作します（paper_trading DB を利用）。
- Kill Switch（data/kill.flag）は ExecutionEngine 停止のためのフラグです。KillSwitch は RiskMonitor 等の結果に応じて書き込まれます。Execution 側は kill.flag の存在で停止します。
- Stop フラグ（data/stop_requested.flag）は run_* スクリプトの外部停止フラグです（プロセスを優雅に停止するために使用）。
- Process priority（優先度）設定は起動時に high を試みますが、権限や OS により失敗することがあります（警告が出ます）。
- DuckDB 操作や executemany に関する互換性（空リスト不可等）に配慮した実装があります。

内部モジュール（簡易説明）
------------------------
- kabusys.config — .env 自動ロード・Settings クラス（環境変数のラップ）
- kabusys.config_setup — .env 対話式ウィザード
- kabusys.validate_config — 起動前の設定検証 CLI
- kabusys.run_execution — ExecutionEngine 起動スクリプト
- kabusys.run_monitoring — SystemMonitor のポーリング起動スクリプト
- kabusys.monitoring.* — monitoring_db, system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, alert_manager 等
- kabusys.execution.* — 発注関連（broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager 等）
- kabusys.portfolio.* — portfolio_builder, risk_adjustment, position_sizing（純粋関数群）
- kabusys.research.* — factor_research, feature_exploration（DuckDB を使った研究用関数群）
- kabusys.ai.* — news_nlp（ニュース NLP）、regime_detector（市場レジーム判定）
- kabusys.tools.paper_verification_report — ペーパートレード検証レポート生成

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py                          — パッケージ初期化（バージョン等）
- config.py                            — Settings, .env 自動読み込みロジック
- config_setup.py                      — .env 対話式ウィザード
- validate_config.py                   — 設定検証 CLI
- run_execution.py                     — ExecutionEngine 起動スクリプト
- run_monitoring.py                    — SystemMonitor 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py                      — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py                     — CPU/メモリ/ディスク/データ鮮度 / PID チェック
- trade_monitor.py                      — 滞留注文・約定異常検出
- risk_monitor.py                       — ドローダウン・ポジション数監視
- kill_switch.py                        — kill.flag の管理
- monitoring_engine.py                  — 各 Monitor をまとめたポーリングループ
- alert_manager.py                      — （アラート送信ロジック: 実装ファイル参照）

src/kabusys/portfolio/
- portfolio_builder.py                  — 候補選定・等重/スコア重み
- position_sizing.py                    — 株数決定・aggregate cap
- risk_adjustment.py                    — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py                    — Momentum / Volatility / Value 等ファクター計算
- feature_exploration.py                — 将来リターン・IC・統計サマリー

src/kabusys/ai/
- news_nlp.py                           — ニュースを LLM でスコア化し ai_scores へ書込
- regime_detector.py                    — MA200 + マクロセンチメントからレジーム判定

src/kabusys/tools/
- paper_verification_report.py          — ペーパートレード検証レポート生成

ユーティリティ
- src/kabusys/utils/process_priority.py  — プロセス優先度 / CPU affinity 設定ユーティリティ

補足（トラブルシューティング）
--------------------------------
- OpenAI API キー未設定の場合、AI 機能は動作しません（score_news / score_regime は例外を投げます）。テスト時はモック化可能です。
- SQLite / DuckDB のファイルパスは Settings で上書きできます（.env 参照）。
- Windows / Linux でプロセス優先度や CPU affinity の挙動が異なるため、権限不足で警告が出ることがあります。

最後に
------
この README はコード内の docstring と実装から要点を抽出してまとめています。実運用前に必ず python -m kabusys.validate_config で設定検証を行い、.env の値（特に本番時の KABUSYS_ENV=live、LINE 通知設定等）を慎重に確認してください。