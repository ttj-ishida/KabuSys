# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。  
本リポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を分離して実装しています。

- ExecutionEngine: ブローカークライアントを通じた発注・注文管理・リスク管理・整合処理
- Monitoring: システム状態・注文状態・リスクの定期チェック、Kill Switch（停止フラグ）とアラート送信
- Portfolio: 候補選定、重み計算、ポジションサイジング、セクター制限などの純粋関数群
- Research: DuckDB 上の価格・財務データからファクター計算・解析を行うモジュール
- AI: OpenAI を使ったニュースセンチメント評価（news_nlp）と市場レジーム判定（regime_detector）
- Tools: ペーパートレード検証レポート生成などのユーティリティスクリプト
- Utilities: ロギング設定、プロセス優先度設定、環境読み込み等の共通ユーティリティ

設計上のポイント:
- 本番用 DB とペーパートレード用 DB を分離可能
- 環境変数 & .env による設定管理（自動ロード機能あり）
- OpenAI 呼び出しは堅牢なリトライ/バリデーションを実装
- DuckDB を分析用 DB として利用

---

## 主な機能一覧

- Execution
  - ブローカークライアントの抽象化（本番 / モック切替）
  - OrderManager / RiskManager / Reconciler による発注制御
- Monitoring
  - system_status, trade_logs, risk_logs, dashboard などの永続化（SQLite）
  - SystemMonitor: CPU/メモリ/ディスク・プロセス検知・データ鮮度確認
  - TradeMonitor: 注文滞留・約定異常検知（ログ参照）
  - RiskMonitor: ドローダウン・ポジション上限監視と自動記録
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各モニタを束ねてポーリング
- Portfolio
  - 候補選定（score / rank）、等金額・スコア加重配分
  - ポジションサイズ計算（リスクベース / 等分配 / スコアベース）
  - セクターキャップ、レジーム乗数適用
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - ニュースを銘柄毎に集約して OpenAI でセンチメント評価し ai_scores に書き込む
  - ETF とマクロニュースを組み合わせて市場レジームを判定・永続化
- Tools
  - Paper Trading 検証レポート（成功率・稼働率・レイテンシ等を集計）
- Utilities
  - 統一的なログ設定（コンソール + 日次ローテート）
  - OS 横断なプロセス優先度・CPU affinity 設定
  - .env 対話式ウィザードと設定検証 CLI

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (cmd)
   ```

3. 必要な依存パッケージをインストール  
   （requirements.txt が無ければ以下を参考にインストールしてください）
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - duckdb: 分析 DB
   - psutil: システム情報取得・プロセス操作
   - openai: ニュース NLP / レジーム判定
   - PyYAML: 設定検証で YAML をパースする場合に必要

4. .env を作成  
   対話式ウィザードで作成できます:
   ```
   python -m kabusys.config_setup
   ```
   代表的な環境変数（.env）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - OPENAI_API_KEY (AI 機能使用時必須)
   - DUCKDB_PATH（例: data/kabusys.duckdb）
   - SQLITE_PATH（例: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
   - PAPER_FILL_MODE（instant | partial | never | reject）
   - LOG_LEVEL（DEBUG/INFO/...）
   - KILL_FLAG_CLEAR_ON_START（0/1）

5. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリを準備（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 使い方

起動スクリプトはモジュールとして実行します。適切に .env を用意し、依存パッケージをインストールしてから実行してください。

- ExecutionEngine を起動（本番 / ペーパートレードの動作は KABUSYS_ENV を参照）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - ログは logs/execution.log に出力（LOG_DIR 環境変数で変更可）。
  - 起動中は data/execution.pid に PID を書きます。

- Monitoring を起動（ポーリング監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可（デフォルト: 60 秒）。
  - Monitoring は常に本番 sqlite_path を使用して監視ログを保存（環境にかかわらず）。
  - 停止は data/stop_requested.flag を作成するか Ctrl+C。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB パス: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で変更可）

- .env の対話式作成 / 更新
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（再掲）
  ```
  python -m kabusys.validate_config
  ```

- AI 機能（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  これらは DuckDB 接続を受け取る関数で、スクリプトから直接は CLI エントリが定義されていません。API キーは引数または環境変数 OPENAI_API_KEY を使用します。

運用上の注意:
- KABUSYS_ENV=live の場合は本番発注を行うためキー・設定に細心の注意を払ってください。
- KILL_FLAG_CLEAR_ON_START=1 は本番環境では危険（Kill Switch が自動クリアされます）。0 を推奨。
- logs ディレクトリや data ディレクトリの所有権と権限設定に注意してください。

停止操作:
- ExecutionEngine を優雅に停止するには監視プロセス（または手動）で data/kill.flag を書き込ませるか（KillSwitch の条件で書かれる）、data/stop_requested.flag を作成して監視スクリプト・実行スクリプトに検知させます。

環境変数の主要一覧（要点のみ）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- KABUSYS_ENV — development / paper_trading / live
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant 等）

---

## ディレクトリ構成

主要ファイル・ディレクトリを抜粋しています（完全な一覧はリポジトリ参照）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート
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
    - news_nlp.py             — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py      — 市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ & 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート送信ラッパー、実装に依存）
  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory, Reconciler, RiskManager 等)
      ※詳細は該当モジュールを参照
  - utils/
    - logging_setup.py        — 共通ロギング設定
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - __init__.py

その他:
- data/                      — SQLite や pid / flag ファイルのデフォルト配置（実行時に作成）
- logs/                      — ログファイル格納（デフォルト）

---

## 開発・運用に関する補足

- データベース
  - 分析用: DuckDB（DUCKDB_PATH）
  - 監視/トレードログ: SQLite（SQLITE_PATH）
  - ペーパートレードは専用 SQLite（PAPER_TRADING_SQLITE_PATH）で本番 DB と分離されます

- ロギング
  - setup_logging() により stdout と日次ローテートファイル（logs/<app>.log）に出力
  - ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御

- 安全策
  - validate_config の警告/エラーで起動前に設定ミスを検出
  - KillSwitch による自動停止（ドローダウンやポジション上限）
  - ExecutionEngine 起動時に kill flag をクリアする挙動は設定で制御可能（KILL_FLAG_CLEAR_ON_START）

---

必要であれば、この README をベースに以下を追加できます:
- サンプル .env.example
- systemd / supervisor 用のサービス unit サンプル
- 詳細な API ドキュメント（関数シグネチャーと例）
- テスト実行手順 & CI 設定例

ご希望の追加内容を教えてください。