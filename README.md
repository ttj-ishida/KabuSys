# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・研究・監視ツール群（KabuSys）のコア実装です。  
README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

※ 本 README は src/kabusys 以下のコードを元に作成しています。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提（依存関係）
- セットアップ手順
- 環境変数（主なもの）
- 使い方（コマンド／スクリプト）
- ファイル・ディレクトリ構成
- 運用上の注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。主な目的は次の通りです。

- 市場データの集約・研究（DuckDB を用いたファクター計算）
- シグナルからポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 実際の注文発行（kabuステーション 等）およびペーパートレード用の分離された処理
- 実行中のシステムや注文の監視（監視ループ、kill switch）
- ニュースを用いた LLM ベースのスコアリング（OpenAI）
- 運用検証レポート生成（Paper Trading 検証）

設計上、研究モジュールは本番 DB / 発注 API にアクセスしないように分離し、発注系は環境（本番 / ペーパー）に応じた挙動切替が可能です。

---

## 主な機能一覧

- 設定管理
  - .env ファイル自動ロード（プロジェクトルートを検出）、対話式セットアップ（config_setup）
  - 設定検証 CLI（validate_config）

- 実行エンジン（Execution）
  - run_execution: ExecutionEngine の起動スクリプト
  - paper_trading モードでは MockBrokerClient を使用し、専用の SQLite（data/paper_trading.db）へ記録

- 監視（Monitoring）
  - run_monitoring: SystemMonitor ポーリングループ起動（デフォルト 60 秒）
  - 各種 Monitor（SystemMonitor, TradeMonitor, RiskMonitor）を束ねる MonitoringEngine
  - kill switch（data/kill.flag）および停止フラグ（data/stop_requested.flag）によるプロセス停止制御
  - 監視ログ永続化（SQLite、monitoring_db）

- ポートフォリオ構築
  - 銘柄選定（select_candidates）
  - 重み計算（等金額・スコア加重）
  - セクター集中制限・レジーム調整
  - ポジションサイズ計算（単元株丸め、リスクベース等）

- 研究・特徴量
  - ファクター計算（momentum, volatility, value）
  - 将来リターン / IC 計算、統計サマリー

- AI（OpenAI）統合
  - ニュース NLP による銘柄ごとのセンチメントスコアリング（news_nlp）
  - マクロニュース＋MA200 を用いた市場レジーム判定（regime_detector）
  - OpenAI API の呼び出しはフェイルセーフ設計（再試行・部分失敗耐性）

- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成（稼働率・注文成功率・レイテンシ等）

---

## 前提（依存関係）

最低限必要なライブラリ（一例）：

- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML — validate_config の YAML 検証に使用

インストール例：
```
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開

2. Python 環境を準備し、依存ライブラリをインストール

3. 初期設定
   - 対話式ウィザードで .env を作成：
     ```
     python -m kabusys.config_setup
     ```
     生成される .env はプロジェクトルートに配置されます（git にコミットしないでください）。

   - 自動ロードを無効にしたい場合は環境変数を設定:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 設定検証（起動前チェック）：
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```

5. データベースの準備
   - デフォルトで使用される DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 使用時）
   - これらの親ディレクトリは自動作成される場合がありますが、validate_config は存在チェックを行い警告を出します。

---

## 環境変数（主なもの）

- KABUSYS_ENV
  - development / paper_trading / live（default: development）
  - paper_trading: MockBrokerClient を使い、発注はペーパートレード DB に記録
  - live: 実発注（注意）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（default: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能利用時に必要）

- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）

- LOG_LEVEL（default: INFO）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアする場合は 1、推奨は 0）

- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）を上書き、デフォルト 60）

自動読み込み
- 起動時、プロジェクトルートに .env / .env.local があれば自動的に読み込まれます。OS 環境変数は保護され上書きされません。
- 自動読み込みを停止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（コマンド例）

基本的にモジュールは -m オプションで起動します。

- 実行エンジン起動（ExecutionEngine）
  ```
  # 本番や開発は環境変数 KABUSYS_ENV によって動作が変わります
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録されます。
  - 実行中、停止指示は data/stop_requested.flag の作成によって行います（Monitoring や運用ツールから生成する想定）。

- 監視ループ起動（SystemMonitor の単体起動）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます。
    例: export MONITOR_POLL_INTERVAL=30
  - 監視は常に本番用の sqlite_path（.env の SQLITE_PATH）を使用します（monitoring は環境に依存しない本番 DB を参照する設計）。

- 環境設定ウィザード（.env の生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定と DB 指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI 機能（ライブラリ呼び出し）
  - ニューススコアリングをプログラムから呼ぶ例：
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - 市場レジーム判定：
    ```python
    from datetime import date
    from kabusys.ai.regime_detector import score_regime
    import duckdb

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

- ライブラリ API
  - ポートフォリオ関連: kabusys.portfolio.*
  - 研究: kabusys.research.*
  - 監視 DB 操作: kabusys.monitoring.monitoring_db.MonitoringDB

---

## 運用制御（フラグファイル等）

- 停止フラグ（run_monitoring, run_execution が参照）
  - data/stop_requested.flag : 存在すると監視ループや実行ループが停止処理を行います。
  - data/execution.pid : ExecutionEngine が PID を書き込むパス（Settings.pid_file_path）

- Kill Switch
  - data/kill.flag : Monitoring の評価結果により作成されると ExecutionEngine に停止シグナルを送るために使われます。
  - Settings.kill_flag_clear_on_start が 1 に設定されていると起動時に kill.flag を自動削除します（本番では 0 を推奨）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要な構成です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数読み込み・Settings
  - config_setup.py                — 対話式 .env ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py          — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py             — 監視用 SQLite 永続化レイヤ
    - system_monitor.py            — システム状態 / データ鮮度監視
    - trade_monitor.py             — 注文滞留・約定異常監視
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — kill.flag 書き込みロジック
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン
    - alert_manager.py             — （アラート送信の責務を担う想定モジュール）
  - execution/
    - order_repository.py
    - order_manager.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
    - ...（発注・注文管理関連）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                   — ニュースからの LLM センチメント処理
    - regime_detector.py            — レジーム判定（MA200 + マクロ NLP）
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI

ランタイムファイル（デフォルト）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/kill.flag
- data/stop_requested.flag

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では設定と権限を十分に確認してください。validate_config は live に対する追加警告を出します。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI を用いる機能は API キー・コストの点で注意が必要です。API エラー時はフェイルセーフで処理継続する実装ですが、利用制限・費用は運用側で管理してください。
- run_execution と run_monitoring はそれぞれ別プロセスとして実行する想定です（監視は実行エンジンを監視する役割）。
- Paper Trading は本番 DB と完全に分離されるよう設計されています。必ず KABUSYS_ENV=paper_trading と PAPER_TRADING_SQLITE_PATH を確認してください。
- プロセス優先度や CPU affinity の設定は OS に依存します。アクセス権限がない場合は警告が出てスキップされます。

---

README はここまでです。必要であれば以下を追加できます：

- 具体的な設定例（.env.example を基にしたサンプル）
- 各モジュール / API の詳細な使い方（docstring をベースにした関数一覧）
- CI・デプロイ手順（systemd / supervisor でのユニット定義例）

どの追加情報が必要か教えてください。