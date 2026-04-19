README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の軽量実装です。  
主な機能は「実行エンジン（注文発行）」「監視（モニタリング・Kill Switch）」「ポートフォリオ構築」「ファクター計算／研究」「ニュースの NLP スコアリング（OpenAI を利用）」などです。パーツはモジュール化されており、紙上（ペーパートレード）環境と本番環境を切り替えて利用できます。

特徴
----
- 実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレード切替（ペーパー時は MockBroker を利用し DB を分離）
  - リスク管理（ポジション上限、利用率、サーキットブレーカー等）
  - 注文管理・再突合（reconciler）など

- 監視（Monitoring）
  - システム資源監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（prices_daily 等の最新日付確認）
  - 取引ログ監視（滞留注文・約定異常等）
  - リスク監視（ドローダウン・ポジション数）
  - Kill Switch（条件により data/kill.flag を書き込み Execution を停止）

- ポートフォリオ構築
  - 候補選定、等金額／スコア加重配分
  - セクター制限、レジーム乗数、バリュー・ボラティリティ考慮
  - 株数計算（複数方式 / lot 単位で丸め、aggregate cap のスケールダウン）

- リサーチ（Research）
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ

- AI（OpenAI）連携
  - ニュース記事を LLM（gpt-4o-mini）でセンチメント評価して ai_scores に格納
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定

- ツール
  - 設定ウィザード（.env の対話式作成）
  - 設定検証 CLI（.env と config/*.yaml の検証）
  - Paper Trading 検証レポート生成スクリプト

前提 / 必要パッケージ
-------------------
（プロジェクトに直接の requirements.txt は含まれていませんが、少なくとも以下が必要になります）
- Python 3.9+（型注釈等の仕様に依存）
- duckdb
- psutil
- openai
- PyYAML（config.yaml 検証を使う場合。なくても動作はする）
その他、任意機能に応じたパッケージが必要です。

セットアップ
-----------
1. リポジトリルート（README と同階層）で作業することを想定しています。

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

4. PYTHONPATH を設定して実行するか、開発用インストールを行う
   - 開発時の手軽な方法:
     - export PYTHONPATH=src  (Windows PowerShell: $env:PYTHONPATH="src")
     - その後 python -m kabusys.config_setup 等で各スクリプトを実行
   - 望ましくはパッケージ化して pip install -e .（setup.cfg/pyproject がある場合）

環境変数（.env）
----------------
config.py はプロジェクトルートの .env / .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。対話式で .env を作成するには:

- python -m kabusys.config_setup

主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合）
- KABUSYS_ENV: development | paper_trading | live （既定: development）
  - paper_trading: MockBroker を使用し DB を data/paper_trading.db に分離
- DUCKDB_PATH（既定: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、既定: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、既定: INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知用、任意）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1、既定: 0）
- MONITOR_POLL_INTERVAL（監視ループの秒数を上書き、既定: 60）

注: run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使います（監視用 DB は共通の想定）。

基本的な使い方（CLI）
-------------------
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit code 1）

- 監視ループ起動（Monitoring）
  - export PYTHONPATH=src
  - python -m kabusys.run_monitoring
  - (環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更)

- 実行エンジン起動（ExecutionEngine）
  - export PYTHONPATH=src
  - python -m kabusys.run_execution
  - ペーパートレード実行時は KABUSYS_ENV=paper_trading を指定すると MockBroker を使用し data/paper_trading.db に書き込み

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db でパスを明示するか、PAPER_TRADING_SQLITE_PATH 環境変数で指定

- プログラム的に利用する関数例
  - AI ニューススコア生成: from kabusys.ai.news_nlp import score_news
  - レジーム判定: from kabusys.ai.regime_detector import score_regime
  - リサーチ関数: from kabusys.research import calc_momentum, calc_volatility, calc_value

停止 / Kill Switch / PID
-----------------------
- 停止フラグ (run_monitoring / run_execution 用)
  - data/stop_requested.flag : ライフサイクル管理（停止要求）
  - data/kill.flag : Kill Switch（監視から書き込まれ、Execution 側が検出して停止）
- 実行エンジンの PID ファイル: data/execution.pid
- Execution 起動時に kill.flag が既に存在する場合は起動しない設定が組み込まれています。

ログ
---
- ログ出力は kabusys.utils.logging_setup.setup_logging により統一管理されます。
- デフォルトで stdout と logs/<app_name>.log（日次ローテーション・30日保持）に出力します。
- ログディレクトリは環境変数 LOG_DIR または既定の logs/ を使用します。

開発メモ
-------
- .env の自動読み込みは config.py により行われます。テストや一時的に無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config/*.yaml の雛形生成スクリプトや追加ツールがある想定（validate_config は config/*.yaml の存在とパースを確認します。PyYAML がない場合は検証をスキップします）。
- OpenAI 連携部分は API の呼び出しで失敗した場合にフェイルセーフ（スコア 0.0 やスキップ）をする設計です。負荷低減のためバッチ処理とリトライロジックを実装済みです。

ディレクトリ構成（主要ファイル）
------------------------------
以下はプロジェクトの主要なファイル／モジュール（抜粋）です。実際は src/kabusys 以下に配置されています。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / .env 読み込み・Settings 定義
  - config_setup.py                 — .env 対話式ウィザード（CLI）
  - validate_config.py              — 設定検証 CLI
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — プロセス優先度・CPU アフィニティ設定
  - monitoring/
    - monitoring_db.py              — SQLite ベースの永続層
    - system_monitor.py             — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py              — 取引ログの監視（存在） ※コードベースに含まれるはずの monitor の一部
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - kill_switch.py                — kill.flag の書き込み管理
    - monitoring_engine.py          — 各 Monitor を束ねる Engine
    - alert_manager.py              — 通知／アラート送信（LINE 等） ※実装ファイルがあればここに
  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory, RiskManager 等のモジュール) ※一部ファイルを参照する
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py                    — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py             — マクロ + ETF MA によるレジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート生成
    - __init__.py
  - data/                            — 実行時に生成される DB / フラグ / PID 等（data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid 等）
  - logs/                            — ログファイル出力先（デフォルト）

補足
----
- 設定や DB パスは Settings（config.py）を通じて一元管理されており、環境変数で上書き可能です。
- ペーパートレードは本番 DB と分離され、内部で MockBrokerClient を利用します。実際の証券会社 API を利用する場合は BrokerClientFactory が適切なクライアントを返すよう設定してください。
- OpenAI API を用いる機能は API キーと通信コストが必要です。使用時はレート制限や料金に注意してください。

ライセンス／バージョン
---------------------
- パッケージバージョン: __version__ = 0.1.0（src/kabusys/__init__.py）

以上。README に不明点や追記したいセクションがあれば教えてください。必要に応じてサンプル .env.example を生成します。