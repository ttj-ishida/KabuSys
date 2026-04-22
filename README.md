# KabuSys

日本株自動売買システムの一部を示すコードベース向け README（日本語）。

本リポジトリは取引実行エンジン、監視・アラート基盤、ポートフォリオ組成、研究用ファクター計算、ニュース NLP / レジーム判定などのモジュール群を含みます。ここではプロジェクトの概要、主要機能、セットアップ・起動手順、使い方、およびディレクトリ構成を説明します。

重要: これはサンプル実装の README です。実際に本番で利用する場合は設定とガード（APIキー、Kill Switch の運用、ログ監視など）を十分に検討してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したコンポーネント群です。主な責務は以下のとおりです。

- ExecutionEngine: ブローカーとの通信、注文管理、リスク管理、約定照合
- Monitoring: システム状態（CPU/メモリ/ディスク）、プロセス有無、注文の健全性、ドローダウン監視、Kill Switch 発動
- Portfolio construction: 候補選定、重み計算、ポジションサイズ計算（等金額／スコア加重／リスクベース）
- Research: DuckDB を用いたファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- AI モジュール: ニュースの LLM によるセンチメント評価（OpenAI）や市場レジーム判定
- CLI ユーティリティ: .env 作成ウィザード、設定検証ツール、Paper Trading レポート生成

設計上の特徴:
- 設定は環境変数（.env）中心で管理。Settings クラスで安全に取得・検証。
- Paper Trading モードでは本番 DB と分離（data/paper_trading.db を使用）。
- DuckDB を分析用データベースに使用、SQLite を監視・発注ログに使用。
- ログ設定、プロセス優先度設定等のユーティリティを提供。

---

## 主な機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド（デフォルト 60 秒）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- portfolio モジュール: 候補選定、重み算出、ポジションサイズ計算、セクター上限・レジーム補正
- research モジュール: ファクター計算（momentum/value/volatility）、将来リターン・IC 計算
- ai モジュール:
  - news_nlp.score_news: OpenAI を使ってニュースを銘柄ごとにスコアリングして ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF の MA とマクロニュースでレジーム判定し market_regime テーブルへ書込
- monitoring: MonitoringDB（SQLite）を中心とした永続化、リスク監視、キルスイッチ、アラート処理

---

## 前提・依存パッケージ

最低限の依存（例）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（config YAML 検証を行う場合、任意）

例: 開発環境にインストールする場合
```
pip install duckdb psutil openai pyyaml
```

注意: 実際のプロジェクトでは requirements.txt / poetry / pipenv 等で依存管理してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

2. Python 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. 環境変数の初期設定
   - 対話ウィザードを使って .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - または .env を手動で作成。必要な主な環境変数:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading の場合の DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、監視スクリプトから参照可能）

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も含めて厳密にチェックする場合
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 使い方（基本コマンド）

- 実行エンジンを起動
  - 本番・開発・ペーパートレードは KABUSYS_ENV で切替え
  - 例: ペーパートレード起動
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 例: 本番起動（注意: 実際に注文が送信されます）
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```

- 監視ループを起動
  - ポーリング間隔を変更したい場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 停止は data/stop_requested.flag を作成するか、実行プロセスを停止（Ctrl+C）。監視スクリプトは data/stop_requested.flag を検知して正常終了します。

- .env の作成 / 更新（対話）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラム・モジュール呼び出し）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、関数呼び出し時に引数で渡す
  - 例（Python から呼ぶ）:
    ```
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, datetime.date(2026, 4, 1), api_key="sk-...")
    ```

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
  - paper_trading: ブローカーはモックを使用し、発注ログは PAPER_TRADING_SQLITE_PATH に記録
  - live: 実際に発注を行う
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- OPENAI_API_KEY: OpenAI を利用する際に必要
- LOG_LEVEL: ログレベル（デフォルト INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の Fill モード（instant|partial|never|reject）

既定値や詳細は kabusys.config.Settings クラスのプロパティ参照。

---

## 運用上のポイント

- 監視からの Kill Switch:
  - RiskMonitor / KillSwitch により data/kill.flag が書かれると、ExecutionEngine 側で停止シグナルとして扱います。KillSwitch はドローダウンやポジション上限などの条件でフラグを出力します。
  - kill.flag の存在は Settings.kill_flag_path（デフォルト data/kill.flag）で確認されます。
- stop_requested.flag:
  - run_monitoring / run_execution は data/stop_requested.flag を監視して終了します（運用者が作成することで安全に停止可能）。
- Paper Trading と本番 DB の分離:
  - paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）へ記録し、本番 sqlite_path とは分離されます。
- ログ:
  - logs/<app_name>.log に日次ローテートで出力。setup_logging によりコンソールとファイル両方に出力。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼び出します。権限不足などで設定できない場合は警告になります。

---

## ディレクトリ構成（主要ファイル）

以下はコードベース内の主要ファイル／モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/  （発注関連コンポーネント、Engine, BrokerFactory, OrderManager など）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送信の実装想定)
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/  （ランタイムで生成されることが多い: monitoring DB, paper_trading DB, pid/flag ファイル 等）
  - logs/  （ログ）

（注）実際のリポジトリでは execution や alert の詳細実装ファイルが存在します。ここでは主要なモジュールとスクリプトを抜粋しています。

---

## 補足（開発者向けメモ）

- 設定ファイル（config/*.yaml）は任意。validate_config では存在確認と YAML パース検証を行います（PyYAML が必要）。
- DuckDB の接続はモジュール間で共有可能です。research / ai モジュールは DuckDB 接続を受け取り SQL と Python を組み合わせて処理します。
- AI（OpenAI）呼び出し部はリトライ・パースの保護処理を含み、失敗時はフェイルセーフ（スコア 0.0 等）で継続する設計です。ただし API キーの漏洩・誤使用に注意してください。
- 単体テストやモック化は容易に行えるように、API 呼び出し関数（_call_openai_api 等）を patch して差し替えられる設計になっています。

---

README は以上です。プロジェクトの追加情報や特定のモジュールの詳しいドキュメントが必要であれば、どの箇所を詳述するか教えてください。