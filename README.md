KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部をまとめた Python コードベースです。  
主に以下の責務を持ちます：

- 発注エンジン（ExecutionEngine）の起動・管理（本番 / ペーパートレード対応）
- システム・発注・リスク監視（Monitoring）
- ポートフォリオ構築（候補選定、配分、ポジションサイズ算出、セクター制限）
- 研究向けファクター計算（momentum, volatility, value など）
- AI を使ったニュースセンチメント・レジーム判定（OpenAI）
- ペーパートレード検証レポート生成 など

主な特徴
---------
- 環境別分離：KABUSYS_ENV により development / paper_trading / live を切替可能。paper_trading は本番 DB と分離。
- フェイルセーフ設計：LLM API 呼び出し失敗や DB 欠損時は安全にフォールバック。
- 監視・Kill Switch：ドローダウンやポジション上限で停止フラグ（data/kill.flag）を書き、Execution を停止可能。
- DuckDB + SQLite を用いたデータ処理・ログ永続化。
- テストや手動実行向け CLI ツール（設定ウィザード、設定検証、レポート生成）。

前提（推奨）
------------
- Python 3.10+
- 推奨パッケージ（最低限）：duckdb, psutil, openai
- 追加（任意）：PyYAML（config/*.yaml の検証に使用）
- OS: Linux / macOS / Windows（プロセス優先度はプラットフォーム差分を吸収）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb psutil openai
   - （YAML 検証を行う場合）pip install PyYAML

   ※ requirements.txt がある場合は pip install -r requirements.txt

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 本番用に LINE 通知を使う場合は LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID を設定
   - 生成後: python -m kabusys.validate_config で検証（--strict オプションで警告も失敗扱い）

5. データディレクトリを準備（通常は自動作成されますが手動で用意する場合）
   - data/
     - monitoring.db（デフォルト）
     - kabusys.duckdb（デフォルト）
     - paper_trading.db（paper_trading 用、必要な場合）
     - logs/（ログ出力先）

使い方（主要コマンド）
--------------------

- 設定ウィザード（.env を作る）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - ※ KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 停止は data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）による停止トリガーで行われます。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - Monitoring は常に本番用 sqlite_path を使用します（環境に依存しない）

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / ニューススコアリング（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは OPENAI_API_KEY 環境変数か api_key 引数で渡す必要があります。

重要な環境変数（一部）
---------------------
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数）
- OPENAI_API_KEY（AI モジュール用）
- PAPER_FILL_MODE（paper_trading の約定動作: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（本番で kill.flag を自動クリアするか: 0/1）

監視・停止フロー（重要）
-----------------------
- Monitoring が RiskMonitor 等の結果に基づき KillSwitch を発動すると data/kill.flag が書き込まれます。
- ExecutionEngine / Monitoring の起動スクリプトは data/stop_requested.flag の存在を検知してループを終了します（停止フラグ）。
- ExecutionEngine は起動時に PID ファイル（data/execution.pid 等）を出力します。

主要コンポーネント（概要）
-----------------------
- run_execution.py
  - ExecutionEngine の組み立てと起動。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、専用 DB に記録。

- run_monitoring.py
  - SystemMonitor を定期実行し、system_status 等をログに保存。MONITOR_POLL_INTERVAL で間隔指定。

- config.py / config_setup.py / validate_config.py
  - 環境変数の読込・管理、.env 生成ウィザード、起動前検証ツール。

- monitoring/*
  - monitoring_db.py: SQLite スキーマと読み書きラッパー（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - trade_monitor.py（コードベースにあり）：発注ログの監視（滞留注文、約定異常等）
  - risk_monitor.py: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - kill_switch.py: kill.flag の作成・クリア
  - monitoring_engine.py: 上記 Monitor を束ねアラート発行

- portfolio/*
  - portfolio_builder.py: 候補選定（スコア順）、等ウェイト / スコア加重計算
  - position_sizing.py: 各銘柄の株数算出（risk_based / equal / score）
  - risk_adjustment.py: セクター上限適用、レジーム乗数
  - これらは純粋関数で DB 参照なし（メモリ内計算のみ）

- research/*
  - factor_research.py: momentum / volatility / value などのファクター計算（DuckDB 経由）
  - feature_exploration.py: 将来リターン計算、IC（Spearman）の算出、統計サマリー

- ai/*
  - news_nlp.py: raw_news を OpenAI に送り銘柄別センチメントを ai_scores に書込む
  - regime_detector.py: ETF MA200 と LLM マクロセンチメントを合成して market_regime に書込む
  - LLM 呼び出しは失敗時にフォールバック（安全処理）を行う

- utils/*
  - logging_setup.py: stdout + 日次ローテートファイルの統一的ロギング設定
  - process_priority.py: プロセス優先度（nice / Windows 優先度）と CPU affinity 設定

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py
    config_setup.py
    validate_config.py
    run_execution.py
    run_monitoring.py
    tools/
      __init__.py
      paper_verification_report.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py (実装がある場合)
    utils/
      logging_setup.py
      process_priority.py
      __init__.py
    execution/         (発注関連モジュール群)
    data/              (実行時生成ファイル: *.db, *.pid, kill.flag 等)
    ...

注意事項 / 運用上のヒント
------------------------
- 本番（KABUSYS_ENV=live）では .env の取り扱いに注意してください（絶対に Git にコミットしない）。
- validate_config のワーニングは本番では深刻な問題を示すことがあります。--strict で厳密チェックを推奨します。
- OpenAI の API 呼び出しにはコストとレイテンシが伴います。rate-limit や失敗時の挙動を理解した上で運用してください。
- DuckDB / SQLite のファイルは必ず定期バックアップを推奨します。
- ロギングは logs/<app_name>.log に日次ローテーションで保存されます。ログ保存に失敗した場合はコンソールのみ出力されます。

開発 / 拡張のガイド
-------------------
- research, portfolio, ai モジュールは純粋関数や明確な副作用境界で設計されているため、ユニットテストの対象にしやすい構造です。
- OpenAI 呼び出しは _call_openai_api のような関数をモックすることでテスト可能です。
- monitoring_db.init_monitoring_db は冪等でスキーママイグレーション（列追加）に対応しています。

ライセンス・バージョン
---------------------
- パッケージの __version__ は 0.1.0（src/kabusys/__init__.py）

最後に
------
この README はコードベースに含まれるスクリプト・モジュールの概要と基本的な使い方をまとめたものです。さらに詳細な設計原則や運用手順はリポジトリ内のドキュメント（存在する場合）や注釈コメントを参照してください。質問や追加してほしいセクションがあれば教えてください。