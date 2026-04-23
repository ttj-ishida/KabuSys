# KabuSys

日本株自動売買システムのコアライブラリ群および運用ユーティリティ群です。  
このリポジトリは、発注・リスク管理・監視・リサーチ・AI（ニュースNLP）などのコンポーネントを含み、ローカル開発からペーパートレード、本番運用までを想定した設計になっています。

バージョン: 0.1.0

---

## 概要

主な責務：
- ExecutionEngine（発注エンジン）とそれを補助する OrderManager / RiskManager / Reconciler 等
- Monitoring（システム状態・注文状況・リスク監視）と Kill Switch（停止フラグ）
- Portfolio 構築（候補選定・重み計算・ポジションサイズ算出・セクター制限）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュースのセンチメントスコア、レジーム判定） — OpenAI API を利用
- 運用ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

設計上の特徴：
- 環境変数 / .env による柔軟な設定
- ペーパートレードは本番 DB と完全分離（デフォルトで `data/paper_trading.db`）
- DuckDB を分析（研究）用 DB として利用
- ログはコンソール出力と日次ローテーションファイル（logs/<app>.log）へ出力

---

## 機能一覧

- 実行・停止
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて Paper/Live を切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 設定管理
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: .env および config/*.yaml の静的検証 CLI
- 監視
  - monitoring_engine.py: 各 Monitor を束ねてポーリング、アラート発行、Kill Switch 評価
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 個別監視
  - monitoring_db.py: 監視用 SQLite DB 層（テーブル作成・読み書きユーティリティ）
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定・等重/スコア重み
  - portfolio.position_sizing: 株数決定・lot 単位丸め・aggregate cap
  - portfolio.risk_adjustment: セクターキャップ・レジーム乗数
- リサーチ
  - research.factor_research: Momentum/Volatility/Value 等のファクター計算（DuckDB 経由）
  - research.feature_exploration: 将来リターン計算、IC、統計サマリ等
- AI（OpenAI）
  - ai.news_nlp: ニュースを LLM に送り銘柄別センチメントを ai_scores テーブルへ書込
  - ai.regime_detector: ETF とマクロニュースを組合せて市場レジーム判定、market_regime へ書込
- 運用ツール
  - tools.paper_verification_report: Paper Trading のパフォーマンス検証レポート生成

---

## 必要条件

- Python 3.10 以上（| 型注釈等のため）
- 主な Python パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (validate_config の YAML 検証を有効にする場合)

インストール例（任意の仮想環境内で）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
（requirements.txt があれば `pip install -r requirements.txt` を利用してください）

SQLite は標準ライブラリに含まれます。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールします（上記参照）。

2. .env を作成する
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     これにより `.env` が作成（または更新）されます。重要な必須変数は後述。

3. 設定検証
   - 作成した .env の妥当性を確認:
     ```
     python -m kabusys.validate_config
     ```
     必須項目の欠落やパスの警告等を検出します。`--strict` を付けると警告も失敗扱い (exit code 1) になります。

4. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / PID / ログ保存先:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / Kill flag: data/execution.pid, data/kill.flag
     - ログ: logs/
   - これらは起動時に自動作成される場合がありますが、権限に注意して事前に作成しておくと安全です。

---

## 環境変数（主なもの）

必須（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用に関する主なオプション:
- KABUSYS_ENV — 実行環境（development | paper_trading | live）。デフォルト: development
  - paper_trading の場合、MockBrokerClient を使用し paper DB に書き込み（data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う機能（ai.news_nlp / ai.regime_detector）に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアする（0/1、デフォルト 0）

運用フラグ（ファイルベース）:
- data/kill.flag — Kill Switch のトリガー（存在時、ExecutionEngine は停止対象になる）
- data/stop_requested.flag — run_monitoring / run_execution のループ停止用（存在時ループを終了）

---

## 使い方（代表コマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（本番/ペーパートレードとも同じスクリプトで環境切替）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、データは paper_trading DB に記録されます。

- Monitoring 起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます。
  - 監視プロセスは設定された sqlite_path を使って永続化します（Monitoring は常に本番 sqlite_path を参照）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も参照します。

- AI 機能（プログラム内呼び出し）
  - ニューススコアリング:
    ```
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```
  - OpenAI API キーは引数または OPENAI_API_KEY 環境変数で与えます。

- ログ
  - デフォルトでコンソール出力と logs/<app>.log に日次ローテートで保存されます。
  - ログの設定は kabusys.utils.logging_setup.setup_logging を通じて行われます。

---

## 運用上の注意

- Kill Switch:
  - RiskMonitor が危険条件（例: ドローダウン閾値超過など）を検知した場合、KillSwitch が `data/kill.flag` を書き込みます。ExecutionEngine 側はこのフラグを参照して安全に停止する仕組みになっています。
- Paper Trading 分離:
  - ペーパートレード（KABUSYS_ENV=paper_trading）は本番 DB と分離され、データは `data/paper_trading.db`（または PAPER_TRADING_SQLITE_PATH）へ保存されます。
- 権限:
  - ログ / data ディレクトリへの書き込み権限を確認してください。
- OpenAI 呼び出し:
  - API のレートリミットや失敗に備え、内部ではリトライ・フォールバック処理がありますが、運用環境では API キーやコストに注意してください。

---

## ディレクトリ構成（主なファイル）

（リポジトリ内の `src/kabusys` を要約）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py           — Monitoring DB 層（SQLite）
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - system_monitor.py          — システム状態・データ鮮度監視
    - trade_monitor.py           — 注文・約定監視（省略）
    - risk_monitor.py            — ドローダウン・ポジション監視
    - kill_switch.py             — kill.flag の管理
    - alert_manager.py           — アラート送信（省略／実装参照）
  - execution/                   — 発注関連（Engine, OrderManager, BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py       — 候補選定・配分
    - position_sizing.py         — ポジションサイズ計算
    - risk_adjustment.py         — セクターキャップ等
  - research/
    - factor_research.py         — ファクター算出（DuckDB）
    - feature_exploration.py     — IC や統計解析
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI 呼出）
    - regime_detector.py         — レジーム判定（OpenAI + ETF MA）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py           — ログ初期化ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
    - その他ユーティリティ群

---

## よく使うコマンドまとめ

- .env を作る:
  ```
  python -m kabusys.config_setup
  ```

- 設定チェック:
  ```
  python -m kabusys.validate_config
  ```

- 発注エンジン起動:
  ```
  python -m kabusys.run_execution
  ```

- 監視ループ起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 付録・開発メモ

- validate_config は PyYAML がインストールされていない場合、config/*.yaml のパースチェックをスキップします（警告）。
- Logging はデフォルトで stdout と日次ローテートのファイル出力を行います。ログディレクトリ作成に失敗した場合はファイル出力を無効にしてコンソールのみで継続します。
- process_priority は OS に依存するため、権限不足や未対応 OS の場合は警告を出してスキップします。
- DuckDB 接続を受け取る関数群（research / ai）は、外部 I/O を最小限にして再現性のある計算を行えるように設計されています。

---

必要であれば、README に加える以下の情報も作成できます：
- 具体的な .env.example（テンプレート）
- 開発用の Dockerfile / docker-compose 定義（運用の自動化）
- Unit test の実行方法（pytest 等）
- 実行フロー図（ExecutionEngine と Monitoring の相互関係）  

ご希望があれば追記します。