# KabuSys

日本株自動売買システムのコードベース。  
ポートフォリオ構築、発注実行、監視、リサーチ、AI を用いたニュースセンチメント評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（バックエンドライブラリ）です。  
主な目的は次のとおりです。

- 戦略に基づく銘柄選定・配分・株数決定
- 発注エンジン（実売買 / ペーパートレード切替）
- 実行・注文・約定の監視とリスク管理（Kill Switch）
- DuckDB/SQLite を用いたデータ分析とログ永続化
- ニュースの LLM（OpenAI）によるセンチメント評価と市場レジーム判定
- Paper Trading 検証レポート生成、研究用ファクター計算

この README はリポジトリの主要な使い方・セットアップ方法・ディレクトリ構成を説明します。

---

## 機能一覧

- portfolio
  - 候補選定（select_candidates）
  - 等金額・スコア加重の重み計算
  - ポジションサイズ計算（リスクベース／等配分）
  - セクター集中制限、レジーム乗数
- execution
  - ExecutionEngine を起動して発注処理を行う（Kabu API 連携、Paper トレード用 Mock ブローカーなど）
  - OrderManager / RiskManager / Reconciler 等の組み立て
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）書き込み
  - MonitoringEngine: 上記を定期ポーリングしてアラート/kill を処理
- research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（将来リターン、IC、統計サマリ）
- ai
  - news_nlp: raw_news を OpenAI で評価して ai_scores に書き込み
  - regime_detector: ETF とマクロニュースを用いた市場レジーム判定
- tools
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを生成
- 各種ユーティリティ（プロセス優先度設定、設定ロード、.env ウィザード、設定検証）

---

## 必要条件（依存ライブラリ）

- Python 3.9+（型注釈や一部モダン API を想定）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config ファイル検証を行う場合に推奨）

インストール例（仮の requirements がない場合）:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／展開
2. 仮想環境を作成・有効化（推奨）
3. 必要パッケージをインストール（上記参照）
4. データディレクトリを作成
```
mkdir -p data
```
5. 環境変数設定（.env ファイル）
   - 対話式ウィザードで .env を生成できます:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な変数（よく使うもの）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番通知（任意）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
     - KILL_FLAG_CLEAR_ON_START: 0（安全）/1（起動時に kill.flag を自動クリア）
6. 設定検証（起動前チェック）
```
python -m kabusys.validate_config
# 警告もエラー扱いにする場合（CI 等）
python -m kabusys.validate_config --strict
```

---

## 使い方

### Execution（発注エンジン）を起動
- 通常起動:
```
python -m kabusys.run_execution
```
- 挙動サマリ
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い、`data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と完全に分離）。
  - 停止には `data/stop_requested.flag` を作成するか、監視側から kill.flag が書かれることで停止処理されます。
  - エンジン実行中は PID を `data/execution.pid` に書きます。

### Monitoring（監視ループ）を起動
```
python -m kabusys.run_monitoring
```
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定できます（デフォルト: 60）。
- 監視は常に（KABUSYS_ENV に関係なく）本番 sqlite_path を使用して monitoring DB にログを書きます（監視のログは一元化）。
- 停止フラグ（data/stop_requested.flag）を検知するとループを終了します。

### Kill Switch（外部からの停止シグナル）
- `KillSwitch` は条件（ドローダウン閾値超過等）で `data/kill.flag` を書き込みます。ExecutionEngine はこれを検出して安全停止します。
- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると自動で `kill.flag` を消去します（本番では危険なので 0 を推奨）。

### Paper Trading 検証レポート
- Paper Trading の SQLite DB（PAPER_TRADING_SQLITE_PATH, デフォルト: data/paper_trading.db）から検証レポートを生成します。
```
python -m kabusys.tools.paper_verification_report
# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パス指定
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

### AI 系（OpenAI）機能
- news_nlp（ニュースセンチメント）および regime_detector（市場レジーム判定）は OpenAI API キーが必要です。環境変数 `OPENAI_API_KEY` または各関数の api_key 引数で指定してください。
- 失敗時はフォールバック動作（スコア=0.0 等）で継続するよう設計されていますが、API キーがないとそもそも実行できない処理があります。

---

## 主要な環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — 分析 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI 使用時に必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

---

## 注意事項 / 運用上のポイント

- .env は絶対に Git にコミットしないこと。
- 本番（KABUSYS_ENV=live）では LINE 通知設定や kill flag 設定を慎重に確認してください。validate_config で live 向けの警告チェックを行えます。
- Monitoring は monitoring DB（SQLite）へログを書きます。run_monitoring はどの環境でも同じ本番 sqlite_path を使用する点に注意してください。
- Execution は `paper_trading` 時に DB を分離するため、本番 DB を汚染するリスクは低くなっていますが、設定ミスに注意してください。
- OpenAI 呼び出しはレートリミット・一時エラーに対して指数バックオフ＋リトライ処理を持ちます。API 負荷やコストに注意してください。

---

## ディレクトリ構成（抜粋）

以下は `src/kabusys` 以下の主要ファイル/ディレクトリ構成です（リポジトリに合わせて適宜変更してください）。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数/.env ロード・Settings
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 起動前設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py  (実装はここに続く)
  - utils/
    - __init__.py
    - process_priority.py

その他、execution パッケージ（order_manager, order_repository, execution_engine など）があり、実際の発注処理ロジックが含まれます（コードベース内参照）。

---

## よく使うコマンドまとめ

- .env を生成/更新:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  python -m kabusys.run_monitoring
  # ポーリング間隔を上書き
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README を拡張して、CI/CD、詳細な設定例、各モジュールの API ドキュメントや設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）へのリンクを追加してください。必要なら各セクションをより詳しく展開します。