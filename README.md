# KabuSys

日本株自動売買システムの小規模フレームワーク。  
ポートフォリオ構築、ポジションサイズ計算、監視・リスク管理、ExecutionEngine（発注処理）や監視ループ、Paper Trading 検証レポート生成、LLM を用いたニュースセンチメント / レジーム判定などのユーティリティを含む。

バージョン: 0.1.0

---

## 概要

このリポジトリは以下を目的としたモジュール群を備えています。

- 市場・銘柄選定（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、配分・リスク調整、株数決定）
- ExecutionEngine（ブローカークライアントを通じた発注処理、paper_trading モード対応）
- 監視（システム状態・注文ログ・リスク監視、Kill Switch）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- 各種ツール（Paper Trading の検証レポート生成、設定ウィザード、設定検証）

設計方針の一部：
- 実行スクリプトと内部モジュールは環境変数 / .env 経由で設定を取得
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用に、SQLite を監視・履歴用に使用
- OpenAI API 呼び出しは外部依存（OPENAI_API_KEY が必要）

---

## 主な機能一覧

- config_setup: 対話式で `.env` を生成・更新するウィザード（python -m kabusys.config_setup）
- validate_config: `.env` と config/*.yaml の事前検証（python -m kabusys.validate_config）
- run_execution: ExecutionEngine 起動スクリプト（発注・リスク管理・オーダー管理）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（paper DB に記録）
- run_monitoring: SystemMonitor ポーリングループ起動（監視ログを SQLite に記録）
- monitoring_engine: System/Trade/Risk の各 Monitor を束ねるエンジン
- monitoring_db: 監視用 SQLite のスキーマ管理・読み書きユーティリティ
- tools.paper_verification_report: Paper Trading の検証レポート生成
- portfolio モジュール: 候補選定・重み計算・ポジションサイズ計算・セクターキャップ等
- research モジュール: ファクター計算（momentum/value/volatility）、将来リターン・IC 計算
- ai.news_nlp / ai.regime_detector: OpenAI を用いたニュースセンチメント / レジーム判定

---

## 要件

主な Python パッケージ（例）:
- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証に任意で使用）

※ 実際の `requirements.txt` がある場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをチェックアウトし、仮想環境を作成・有効化します。
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 依存パッケージをインストールします（プロジェクトに合わせて調整してください）。
   ```
   pip install duckdb psutil openai PyYAML
   # または requirements.txt があれば
   # pip install -r requirements.txt
   ```

3. 初期設定（.env）の作成
   ```
   python -m kabusys.config_setup
   ```
   ウィザードに従って必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力してください。

4. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合
   python -m kabusys.validate_config --strict
   ```

5. 必要に応じて logs/ や data/ ディレクトリを確認（通常は自動作成されます）。
   - デフォルト DB/ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

---

## 主要な環境変数（抜粋）

Settings クラスで参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN（任意）
- LINE_USER_ID（任意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 用: instant|partial|never|reject、デフォルト: instant）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- LOG_DIR（ログ保存先。デフォルト: logs/）
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒。デフォルト 60）
- OPENAI_API_KEY（AI モジュール利用時に必要）

その他、monitoring 用しきい値等の設定も Settings クラスで提供されています（CPU/MEM/DISK しきい値等）。

.env 自動ロードについて:
- プロジェクトルートに `.env` / `.env.local` があれば自動で読み込まれます（OS 環境変数を上書きしない）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（代表的なコマンド）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動（本番/ペーパー両対応）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録します。
  - プロセス優先度を「high」に設定し、PID ファイル（デフォルト: data/execution.pid）を使用します。
  - data/stop_requested.flag が存在すると起動しない・実行中は停止処理を実行します。

- Monitoring 起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）。
  - 監視ログは `SQLITE_PATH`（デフォルト data/monitoring.db）へ記録されます。
  - run_monitoring は常に本番 sqlite_path を使用（環境にかかわらず）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定を上書きする場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（プログラム内で利用）
  - ニュース NLP スコアリング:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。

---

## 実行上の注意点 / オペレーション

- Paper Trading は DB を分離します。実環境（live）では本番 DB に書き込まれるので取り扱いに注意してください。
- Kill Switch:
  - KillSwitch は `KILL_FLAG_PATH`（デフォルト data/kill.flag）へ文字列を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - `KILL_FLAG_CLEAR_ON_START=1` は本番で危険なのでデフォルトは 0 を推奨。
- Stop フラグ:
  - run_execution/run_monitoring は `data/stop_requested.flag` の存在を監視し、存在時には起動拒否または実行中に停止動作を開始します。
- ログ:
  - ログは標準出力（stdout）と日次ローテーションされるログファイル（logs/<app_name>.log）へ出力されます。
  - ログディレクトリ作成に失敗した場合はコンソールのみで継続します。

---

## サンプル最低限 .env (例)

以下は最小限のサンプルです（実運用では必ず適切な値を設定してください）。

```
# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

# API
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# DB / ファイル
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag

# OpenAI（AI 機能を使うとき）
OPENAI_API_KEY=sk-...
```

`.env` は機密情報を含むため Git へコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。

---

## ディレクトリ構成

（重要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定の読み取り・Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照: trade モニタ / ロジック)
    - kill_switch.py
    - alert_manager.py (アラート送信ロジック)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - data/ (実行時に生成される想定)
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - logs/
    - execution.log
    - monitoring.log
    - ...（日次ローテーション）

---

## 開発 / テストに関するメモ

- 多くの関数は副作用を持たない純粋関数として設計されている（portfolio, research など）ためユニットテストが容易です。
- OpenAI 呼び出しや外部 API 呼び出しは抽象化されており、ユニットテスト時はモックや monkeypatch で差し替え可能です（例: news_nlp._call_openai_api を patch）。
- DuckDB / SQLite を利用する処理はローカル DB に対する読み書きが発生するため、テスト時は一時 DB を利用してください。

---

## 問い合わせ / 貢献

バグ報告や改善提案は Issue を立ててください。  
プルリクエスト歓迎 — コードスタイル・テストを含めてください。

---

以上。README の内容はコードベースの主要コンポーネントに基づいています。運用前には `python -m kabusys.validate_config` による検証と、.env の値（特に KABUSYS_ENV, KILL_FLAG_CLEAR_ON_START, OPENAI_API_KEY）を慎重に確認してください。