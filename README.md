# KabuSys

日本株自動売買システムの一部を実装したリポジトリ。戦略のリサーチ/ファクター計算、ポートフォリオ構築、注文実行（実運用／ペーパートレード切替）、監視・アラート、AI（ニュースセンチメント・レジーム判定）、および運用支援ツール群を含みます。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール化された自動売買基盤です。

- 日次・リアルタイムのデータを用いたファクター計算（DuckDB を想定）
- 銘柄選定・配分・数量決定（ポートフォリオ構築）
- ExecutionEngine による注文送信（本番は kabuステーション、paper_trading では Mock ブローカー）
- 監視サブシステム（System / Trade / Risk モニタ）、Kill Switch による安全停止
- OpenAI を用いたニュースセンチメント（ai.news_nlp）および市場レジーム判定（ai.regime_detector）
- ペーパートレード検証レポート生成ツール

設計上のポイント：
- 環境変数 / .env を通じて設定を管理（Settings クラス）
- DB は DuckDB（分析）と SQLite（監視 / 発注ログ）を併用
- 本番・ペーパートレードは設定 `KABUSYS_ENV` により切替え
- 自動化・運用を想定したフラグファイル（data/kill.flag, data/stop_requested.flag, pid ファイル）を利用

---

## 主な機能一覧

- config
  - .env の自動ロード / ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- execution
  - ExecutionEngine（run_execution.py から起動）
  - ブローカークライアント抽象化（本番 / mock 切替）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等
- monitoring
  - SystemMonitor（CPU/Mem/Disk、プロセス監視、データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件に応じて kill.flag を作成）
  - AlertManager（LINE Push による通知）
  - MonitoringEngine（定期ポーリング）
- research
  - ファクター計算（momentum, volatility, value）
  - 研究向けユーティリティ（forward returns, IC 計算, summary）
- portfolio
  - 候補選定・重み算出・単元丸め・ポジションサイズ計算・セクター制約
- ai
  - ニュース NLP：OpenAI を使った銘柄別センチメント算出（ai_scores テーブルへ書込）
  - レジーム検出：ETF MA200 とマクロニュースの LLM 評価を合成してレジーム判定
- tools
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成

---

## 必要条件（推奨）

- Python 3.9+
- DuckDB Python パッケージ（duckdb）
- psutil（プロセス優先度・CPU affinity 用）
- openai（AI 機能を使う場合）
- requests（LINE 通知）
- PyYAML（validate_config の YAML 検証を有効にする場合）

実行に必要なパッケージはプロジェクトの requirements.txt にまとめてください（リポジトリに無ければ手動でインストール）。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests pyyaml
```

---

## 環境変数 / 設定項目（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録します
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒。デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視・停止関連）

.env の生成・更新は `python -m kabusys.config_setup` を使うと対話式に作成できます。
作成後は必ず `python -m kabusys.validate_config` でチェックしてください。

簡易 .env 例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx (AI を使う場合)
```

---

## セットアップ手順（推奨）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 必要なパッケージをインストール（duckdb, psutil, openai, requests, pyyaml 等）
4. .env を作成
   - 対話式: `python -m kabusys.config_setup`
   - 手動: `.env` をプロジェクトルートに配置
5. 設定検証: `python -m kabusys.validate_config`（`--strict` で警告も失敗扱い）
6. DuckDB / SQLite の DB ファイルは起動時に必要なテーブルが自動生成されます（monitoring の初期化は実行スクリプト内で行われます）。

---

## 使い方（主要スクリプト）

- 監視（Monitoring）を起動:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 監視ループは data/stop_requested.flag の存在で終了します。

- ExecutionEngine を起動:
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 停止指示:
    - data/kill.flag を監視側（KillSwitch）で生成すると ExecutionEngine に停止シグナルを送れます（監視エンジンから書き込まれる）。
    - 外部から強制停止する場合は stop_requested.flag を置くことで run_execution 側で検知して停止します（実装上 stop_requested.flag を使っている箇所があります）。

- .env 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラム内 API）:
  - ニュースセンチメント: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、必要に応じて OPENAI_API_KEY（または引数 api_key）を参照します。

注意:
- run_monitoring/run_execution は起動時にプロセス優先度を上げようとします（psutil に依存）。権限がない場合は警告が出ますが処理自体は継続します。
- DB 初期化（監視テーブル等）は実行時に自動的に行われます（冪等）。

---

## 停止 / キルスイッチの運用

- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch が条件を満たすとこのファイルを書き込み、ExecutionEngine の停止を促します。
  - 本番で自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は危険なのでデフォルトは 0。

- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring/run_execution の起動ループはこのファイルの存在をチェックして優雅に終了します。運用中に外部から停止したい場合に利用可能。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py     — SQLite テーブル初期化・アクセスラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/              — （発注関連。コードベースの一部は省略）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/monitoring_db.py
  - tools/
    - paper_verification_report.py

（上記は本リポジトリにある主要モジュールの抜粋です。細かいファイルは実装に応じて追加されています。）

---

## 開発・運用上の注意点

- 本番稼働時は KABUSYS_ENV=live を使用し、設定・LINE 通知先・DB パス等を慎重に確認してください。validate_config の live チェックが補助します。
- OpenAI を用いる機能は API 料金・レート制限に注意してください。429 や 5xx はリトライロジックを持ちますが、運用コストには注意が必要です。
- DuckDB / SQLite のファイルは運用中にバックアップを検討してください（特に分析 DB）。
- PID ファイル / stop/kill フラグファイルの運用ルールをドキュメント化しておくと安全です。
- 単体テストや CI を整備して、外部 API 呼び出し部分はモックパターンでテスト可能になっています（ソース中に patch 用フックあり）。

---

以上がこのコードベースの README です。追加して欲しい説明（例: ExecutionEngine の詳細な起動パラメータ、注文フロー図、運用手順書テンプレートなど）があれば教えてください。