KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
戦略の研究（ファクター計算・特徴量探索）・ポートフォリオ構築・ポジションサイズ計算・実際の発注（本番 / ペーパートレード）・システム監視・アラート・AI（ニュース NLP / レジーム判定）などを含む、モジュール化された実装群を提供します。

主な設計方針
- DuckDB / SQLite を中心にデータを保持・解析（本番データは分離）
- モジュールは極力純粋関数／副作用を限定してテストしやすくする
- 実行スクリプトから共通ロギング・プロセス優先度設定を行う
- Paper Trading は本番 DB と完全分離（data/paper_trading.db）
- OpenAI（LLM）連携はフェイルセーフ、バッチ/リトライを実装

機能一覧
--------
- 実行（ExecutionEngine）
  - 本番 / ペーパートレードを切替可能（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBroker を用意）
  - リスク管理（ポジション上限・ドローダウン等）
  - 注文管理・リコンシリエーション
- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク）のポーリング記録
  - 注文ログ / リスクログの永続化（SQLite）
  - Kill Switch（条件により Execution を停止）
  - アラート出力（LINE 等連携を想定）
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算・IC（Information Coefficient）等の統計
- ポートフォリオ構築
  - 候補選定、等重・スコア加重、セクター制限、ポジションサイズ算出
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースのセンチメント評価（ai_scores に保存）
  - マクロニュース + ETF MA200 を組み合わせたレジーム判定
- ツール
  - config_setup: .env を対話的に作成
  - validate_config: 起動前の設定検証 CLI
  - paper_verification_report: ペーパートレード検証レポート生成

前提（Prerequisites）
--------------------
- Python 3.10+
- 標準ライブラリ: sqlite3 等
- 必須外部パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- 推奨: 仮想環境（venv, poetry など）

例: 必要パッケージの簡易インストール
- pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローンしてワークツリーへ移動
2. 仮想環境を用意して依存をインストール
3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - あるいは .env を手動作成（下記に主要キー例を記載）
4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い
5. 必要ディレクトリの作成（通常はスクリプトが自動作成）
   - data/, logs/ が使用されます

主要環境変数（例）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 選択 / 上書き可能
  - KABUSYS_ENV — execution モード (development | paper_trading | live)（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で利用。デフォルト 60）

例 (.env の一部)
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO
- OPENAI_API_KEY=sk-...

使い方（起動 / CLI）
--------------------
1. .env 作成 / 設定検証
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. 監視プロセス起動
   - python -m kabusys.run_monitoring
   - 動作: Settings から DB/パスを読み、SystemMonitor のポーリングを開始
   - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒で上書き可能（デフォルト 60）

3. 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading とすると MockBrokerClient を使用し、data/paper_trading.db に記録
   - 起動時に data/stop_requested.flag がある場合は起動をスキップ
   - 実行停止は stop flag（data/stop_requested.flag）を作る/監視が検知して停止

4. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で別 DB パス指定可（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）

5. AI（ニュース NLP / レジーム判定）呼び出し（プログラムから）
   - DuckDB 接続を用意し、モジュールの関数を呼び出す:
     - from kabusys.ai import score_news
     - score_news(duckdb_conn, target_date, api_key="...") など
   - API キーが必要（OPENAI_API_KEY）

停止 / Kill Switch
- run_monitoring/run_execution はプロセス優先度を上げて実行します。
- 停止を要求するにはプロジェクトの data/stop_requested.flag を作成してください（監視ループが検知して終了します）。
- Kill Switch（監視 -> kill.flag）はリスク条件（ドローダウンやポジション上限）で自動的に data/kill.flag を書き込み、Execution の停止を促します。
- KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ログ
---
- 共通ロギング設定: kabusys.utils.logging_setup.setup_logging(app_name="...") を各起動スクリプトから呼び出します。
- デフォルトログディレクトリ: logs/
- ローテーション: 日次、30日保持
- LOG_LEVEL 環境変数で出力レベルをコントロール可能

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数・設定読み込み
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py  — ペーパートレード検証レポート
- ai/
  - news_nlp.py                   — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py            — 市場レジーム判定
- monitoring/
  - monitoring_db.py              — SQLite 永続化層
  - monitoring_engine.py          — 各 Monitor を束ねるエンジン
  - system_monitor.py             — システム・データ鮮度監視
  - risk_monitor.py               — ドローダウン / ポジション数監視
  - kill_switch.py                — kill.flag 管理
  - (trade_monitor.py 等)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py

（注）上記は主要ファイルの抜粋です。細かいサブモジュール（execution、data、strategy 等）は機能別に整理されています。

開発時のヒント / 注意点
- KABUSYS_ENV は development / paper_trading / live のいずれかに設定してください。live は本番なので十分注意して使用してください。
- Paper Trading モードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API 呼び出しは外部コストが発生します。テスト時はモック化して呼び出しを回避してください（モジュール内の _call_openai_api を patch すると簡単です）。
- config/*.yaml（strategy 等）は PyYAML を用いて検証できます（validate_config でチェック）。存在しない場合は警告になります。
- ログディレクトリ作成やファイル作成に失敗しても、コンソール出力のみで継続する設計になっています。

ライセンス / バージョン
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

お問い合わせ
------------
ソース内の docstring や関数コメント（日本語）を優先して参照してください。実装の詳細や拡張については該当モジュール（monitoring, ai, portfolio, research）を直接ご確認ください。

以上がこのリポジトリの概要と基本的な使い方です。追加で「運用手順書」や「デプロイ手順（systemd / cron 例）」などが必要であれば教えてください。