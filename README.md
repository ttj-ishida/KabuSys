# KabuSys

日本株向け自動売買システムのコアライブラリ群。ポートフォリオ構築、発注エンジン、監視・リスク管理、AI を使ったニュースセンチメント評価、Research/分析ユーティリティなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。主な目的は次のとおりです。

- 戦略に基づく銘柄選定・配分・株数決定（純粋関数として実装）
- 発注エンジン（実際のブローカーまたはモックでのペーパートレード）
- システム稼働監視・取引監視・リスク監視・Kill Switch（自動停止）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- 研究用のファクター計算・特徴量探索ユーティリティ
- 運用・開発を支援する設定ウィザード・設定検証ツール・レポート出力

設計は安全性（本番とペーパーの分離、Kill Switch、ダッシュボード/ログ）、再現性（DuckDB/SQLite 経由のデータ）、テスト容易性（副作用を抑えた関数群）を重視しています。

---

## 主な機能一覧

- ポートフォリオ構築
  - 銘柄候補選定（スコア順／上位 N）
  - 等金額／スコア加重配分
  - セクター上限適用、レジーム乗数
  - 単元株丸め、リスクベースのポジションサイズ計算

- Execution（発注）関連
  - BrokerClientFactory による実ブローカー / モックの切替
  - OrderManager / ExecutionEngine / Reconciler / RiskManager（発注の管理・制限）
  - Paper Trading は専用 SQLite（デフォルト: `data/paper_trading.db`）に分離

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度
  - TradeMonitor: 発注・約定の監視（滞留注文、異常約定検出）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: しきい値超過で `data/kill.flag` を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ

- AI モジュール
  - news_nlp: raw_news を集約し OpenAI で銘柄ごとのセンチメントを算出して `ai_scores` に保存
  - regime_detector: ETF の MA とマクロニュースの LLM センチメントを合成して市場レジーム判定

- Research / Tools
  - ファクター計算（Momentum/Value/Volatility）
  - 特徴量探索（forward returns、IC、統計サマリー）
  - Paper Trading 検証レポート生成ツール（`kabusys.tools.paper_verification_report`）

- ユーティリティ
  - .env ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）
  - ロギングセットアップ、プロセス優先度設定ユーティリティ

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - pyyaml（設定検証で YAML パースを行う場合）
- 推奨: 仮想環境（venv / pyenv など）

例（venv + pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai pyyaml
```

必要なパッケージはプロジェクト側に requirements ファイルがあればそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動。

2. 仮想環境の作成と依存関係インストール（上記参照）。

3. .env の作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 本番で OpenAI を使う場合:
     - OPENAI_API_KEY を設定

4. 設定検証（任意／推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ
   - デフォルトでは `data/` 配下に SQLite / DuckDB / PID/flag ファイルが作られます。
   - 必要なら `.env` の `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` を調整。

---

## 使い方（主な実行例）

- 監視ループ（SystemMonitor の起動）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に本番用の sqlite_path を使用（環境にかかわらず監視 DB は本番パスを参照）。

- ExecutionEngine（発注エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し、`data/paper_trading.db` に記録されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動しません。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は `data/paper_trading.db`。`--db` で指定可能。

- AI モジュール（プログラムから呼び出す例）
  - OpenAI API キーが必要（`OPENAI_API_KEY` または関数引数で指定）
  - news_nlp:
    ```python
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn: duckdb.connect(...)
    # target_date: datetime.date(...)
    score_news(duckdb_conn, target_date, api_key="sk-...")
    ```

- 設定のクイック検証
  ```
  python -m kabusys.validate_config
  ```

---

## 重要な環境変数（代表）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ログレベルとログ出力先
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

---

## 実行中の停止・Kill Switch

- キルフラグ: `data/kill.flag` を作成すると ExecutionEngine に停止を促す Kill Switch が働きます。
- 停止要求: `data/stop_requested.flag` を作成すると run_execution / run_monitoring のループが検知して終了します。
- PID ファイル: `data/execution.pid` などにプロセス ID を書き出します（設定によりパスを変更可能）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env のロードと Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねる
    - ...（alert_manager, trade_monitor 等の実装が含まれる想定）
  - execution/ — ExecutionEngine と発注関連（OrderManager 等）
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
  - tools/
    - paper_verification_report.py

---

## 開発・運用上の注意

- 本番（KABUSYS_ENV=live）での起動は注意深く（LINE通知設定や Kill Switch 設定を確認してください）。
- .env は秘密情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI を用いる機能は API 使用料が発生します。テスト時はモック化することを推奨します（モジュール内で API 呼び出し関数を差し替え可能）。
- ログは標準出力とファイル（日次ローテート）に出力されます。ログディレクトリが作成できない場合はファイル出力が無効化されます。

---

この README はコードベースの主要コンポーネントを要約したものです。より詳しい設計や仕様（PortfolioConstruction.md、StrategyModel.md 等）が別資料として存在する想定です。質問や追加ドキュメント化したい箇所があればお知らせください。