KabuSys — 日本株自動売買システム (README)
=========================================

概要
---
KabuSys は日本株の自動売買／研究プラットフォームのシンプルな実装です。  
主な目的は以下です。

- データ収集・分析（DuckDB を用いたファクタ計算・特徴量探索）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 注文実行（本番 / ペーパートレードの分離）
- 監視・アラート（システム状態、注文/リスク監視、Kill Switch）
- AI 支援（ニュースセンチメント / レジーム判定：OpenAI API を利用）

コードは純粋関数的な計算部と、実行／監視用の起動スクリプト群に分かれています。

主な機能一覧
--------------
- 環境設定ウィザード: .env ファイルの対話的生成 (kabusys.config_setup)
- 設定検証 CLI: 環境変数 / config/*.yaml の事前検証 (kabusys.validate_config)
- 実行エンジン起動スクリプト: run_execution.py（KABUSYS_ENV により本番／ペーパー切替）
  - paper_trading では MockBroker を使用し専用 DB（data/paper_trading.db）へ記録
- 監視ループ起動スクリプト: run_monitoring.py（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）
- 監視機能:
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度
  - TradeMonitor: 注文滞留・約定異常など（trade_logs を参照）
  - RiskMonitor: ドローダウン / ポジション数上限の監視とリスクログ
  - KillSwitch: 条件に合致したら data/kill.flag を書いて Execution を停止
  - MonitoringEngine: 各 Monitor をまとめてポーリング、アラート通知
- ポートフォリオ構築:
  - 候補選定、等重・スコア重み付け、リスク調整（セクター制限・レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap、リスクベース配分）
- 研究用モジュール:
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI モジュール（OpenAI 利用）:
  - news_nlp.score_news: 新聞記事から銘柄ごとのセンチメントを生成して ai_scores に書込
  - regime_detector.score_regime: ma200 とマクロニュースの LLM スコアを合成してレジーム判定
- 公開ツール:
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート生成

前提・依存ライブラリ（主なもの）
---------------------------------
（プロジェクトの requirements.txt があればそちらを優先してください）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (config/*.yaml の解析検証を行いたい場合)
- SQLite (標準ライブラリ)

セットアップ手順
-----------------
1. リポジトリをクローン
   - 本 README はパッケージ配下 src/kabusys を前提としています。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は最低限 duckdb, psutil, openai をインストール）

4. 環境変数の作成 (.env)
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を手作業で作成する。
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - 任意 / デフォルト:
     - KABUSYS_ENV=development|paper_trading|live （デフォルト development）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL=INFO
     - LOG_DIR=logs
     - OPENAI_API_KEY（AI 機能を利用する場合）

5. 設定検証（必須ではないが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いにできます。

6. データ・ログディレクトリ
   - data/ や logs/ は自動作成されることが多いですが、権限等で作成に失敗する場合は手動で作成してください。

使い方（起動・操作）
--------------------

- Execution（注文実行）を起動する
  - 本番・ペーパーは KABUSYS_ENV による切替:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 特記事項:
    - paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
    - エンジンはデーモン的にスレッドで run_session を実行し、pid ファイル（data/execution.pid など）を作成します。
    - 停止は data/stop_requested.flag を作成することで実行中のエンジンに通知されます（run_execution は起動時に既に stop フラグが存在する場合は起動しません）。

- Monitoring（監視ループ）を起動する
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path（settings.sqlite_path）を使用して監視テーブルを初期化します（init_monitoring_db）。

- Kill Switch（自動停止）について
  - RiskMonitor の評価結果により KillSwitch が data/kill.flag を書き込むと、運用側はこれを検知して Execution を停止する仕組みです。
  - 手動で停止したい場合はデータディレクトリに stop_requested.flag を置くと run_execution/run_monitoring のループが終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- AI 機能
  - OpenAI API を使うモジュール（news_nlp, regime_detector）は OPENAI_API_KEY を必要とします。
  - API 呼び出しはコストが発生するため注意してください。失敗時は基本的にフェイルセーフ設計（スコア 0 またはスキップ）です。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
- LOG_LEVEL — デフォルト INFO
- LOG_DIR — デフォルト logs/
- OPENAI_API_KEY — AI 機能を使う場合に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下を示します。プロジェクトルートには data/, logs/, config/ 等が配置されます）

- kabusys/
  - __init__.py                      — パッケージ情報
  - config.py                        — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py                  — .env 対話式ウィザード
  - validate_config.py               — 起動前設定検証ツール
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py                    — ニュースセンチメント（OpenAI）
    - regime_detector.py             — 市場レジーム判定（ma200 + マクロニュース）
    - __init__.py

  - monitoring/
    - monitoring_db.py               — SQLite 監視 DB 永続化層 / MonitoringDB
    - system_monitor.py              — システム状態 / データ鮮度監視
    - trade_monitor.py               — (注文監視) ※コードベースにあり（省略）
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag の読取/書込ロジック
    - monitoring_engine.py           — 各 Monitor の統合ポーリング
    - alert_manager.py               — (アラート送信) ※（ファイル存在想定）

  - execution/
    - execution_engine.py            — 実行エンジン本体（EngineConfig, run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py              — BrokerClient の生成（本番/Mock 切替）
    - (その他実行関連)

  - portfolio/
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 株数決定・資金配分ロジック
    - risk_adjustment.py             — セクター制限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py             — momentum/volatility/value 等のファクター計算
    - feature_exploration.py         — IC/統計サマリ等の研究ユーティリティ
    - __init__.py

  - data/                             — データ用ディレクトリ（実行時に生成されることが多い）
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)

  - tools/
    - paper_verification_report.py    — ペーパートレード検証レポート生成
    - __init__.py

  - utils/
    - logging_setup.py                — 一貫したログ設定ユーティリティ
    - process_priority.py             — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

注意事項 / 運用上のポイント
--------------------------
- KABUSYS_ENV によって動作が大きく変わります。live（本番）では特に KILL_FLAG_CLEAR_ON_START 等の設定に注意してください。
- AI 機能は外部 API（OpenAI）を呼び出します。キーの管理・呼び出し回数・レートリミット・コストに注意してください。
- run_monitoring は監視用 DB（SQLITE_PATH）のパスを常に使用します。Monitoring は環境にかかわらず本番 sqlite_path を用いる設計です。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗するとコンソールのみ出力にフォールバックします。
- データ鮮度チェック等は DuckDB 上の prices_daily などのテーブルに依存します。適切なデータ投入が必要です。

貢献 / 拡張案
--------------
- 注文実行のブローカープラグインを追加して別の証券会社 API に対応
- 単元株数を銘柄別にサポート（現在は全銘柄共通 lot_size）
- monitoring のアラート送信先（LINE / Slack 等）の実装強化
- DuckDB のスキーマ管理・マイグレーション仕組みの整備

ライセンス
----------
リポジトリに記載されているライセンスに従ってください（本 README にはライセンス情報は含まれていません）。

最後に
------
この README はソースコード（src/kabusys）に基づいた概要ドキュメントです。実際に運用する際は .env / config/*.yaml の内容を必ず確認し、validate_config で検証を行ってください。質問があれば、どの部分を詳しく知りたいか教えてください。