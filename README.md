# KabuSys

日本株自動売買システムのライブラリ／ランタイムコード群。  
このリポジトリには取引エンジン起動スクリプト、監視コンポーネント、ポートフォリオ構築・リサーチ・AI 支援モジュールなどが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

- 目的: 日本株自動売買のための実行エンジン、監視・リスクガード、ポートフォリオ構築やファクター計算、ニュース NLU によるセンチメント評価などを提供する。
- 設計方針:
  - 実行系（ExecutionEngine）と監視系（Monitoring）は分離。監視は停止フラグ / kill スイッチ等で発注系を保護する。
  - 設定は環境変数 / `.env` で管理。`config_setup` のウィザードで初期作成が可能。
  - DuckDB / SQLite を利用した分析・トラッキング機能を提供。
  - OpenAI（gpt-4o-mini 等）を利用したニュース NLP / レジーム判定をサポート（APIキー必要）。
  - 多くのユーティリティはプラットフォームを吸収して安全に動作するよう実装（例: プロセス優先度設定、ロギング設定）。

---

## 主な機能一覧

- 実行エンジン起動: run_execution.py
  - 本番 / ペーパートレードを環境変数 `KABUSYS_ENV` により切替
  - ペーパートレード時は専用 SQLite（`data/paper_trading.db`）に分離
  - プロセス優先度の設定、pid ファイル管理、停止フラグ監視
- 監視（Monitoring）: run_monitoring.py / monitoring/* モジュール
  - システム状態（CPU / メモリ / ディスク）やデータ鮮度、注文ログの監視
  - リスク監視（ドローダウン / ポジション上限）と kill switch 書き込み
  - アラート管理フック（AlertManager 構造あり）
- AI モジュール（kabusys.ai）
  - news_nlp: ニュース集合を LLM でセンチメント判定し ai_scores に永続化
  - regime_detector: ma200 とマクロニュースを合成して市場レジーム判定
- リサーチ（kabusys.research）
  - ファクター（モメンタム、バリュー、ボラティリティ）計算、将来リターン、IC 計算、統計サマリー
  - DuckDB 接続を受けて SQL / Python で効率的に計算
- ポートフォリオ（kabusys.portfolio）
  - 候補選定、重み算出（等配分 / スコア加重）、ポジションサイジング（リスクベース）やセクターキャップ適用
- ツール
  - 環境設定ウィザード: kabusys.config_setup (対話式 `.env` 作成)
  - 設定検証 CLI: kabusys.validate_config (`--strict` あり)
  - Paper Trading 検証レポート生成: kabusys.tools.paper_verification_report

---

## 必要条件（例）

最低限必要な主要パッケージ（環境に応じて requirements を用意してください）:
- Python 3.8+
- duckdb
- psutil
- openai (OpenAI SDK)
- PyYAML（設定ファイル検証を行う場合）
- sqlite3（標準ライブラリ）

インストール例:
```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／配置する。
2. 必要パッケージをインストールする（上記参照）。
3. 初回は `.env` を作成する。2 通りの方法:
   - 対話式ウィザード（推奨）:
     ```bash
     python -m kabusys.config_setup
     ```
   - 手動で `.env` を作る（`.env.example` を参考にすること）。
4. 設定の検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も fail にしたい場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じて data/ ディレクトリやログディレクトリを作成（logging_setup が自動作成するため通常は不要）。

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live） デフォルト: development
- DUCKDB_PATH デフォルト: data/kabusys.duckdb
- SQLITE_PATH デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH デフォルト: data/paper_trading.db
- LOG_LEVEL デフォルト: INFO
- OPENAI_API_KEY（AI モジュールを使用する場合に必須）
- PAPER_FILL_MODE（paper_trading 用: instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリア、開発用）

ログ出力:
- デフォルトで logs/ ディレクトリに日次ローテート（30日）で保存。
- コンソール出力は stdout に出力されます。

---

## 使い方（主要コマンド）

- 実行エンジンを起動（本番 / ペーパーは KABUSYS_ENV で制御）:
  ```bash
  python -m kabusys.run_execution
  ```
  注意:
  - プロセス優先度を High に設定します（可能な場合）。
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します。
  - 停止は `data/stop_requested.flag` を作成するか、実行中のプロセスに SIGINT（Ctrl+C）等を送ります。
  - 実行時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

- 監視ループを起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔 (秒) を上書きできます（デフォルト 60）。
  - 監視は Settings に基づく sqlite_path（監視 DB）と DuckDB を接続します。
  - 監視は `data/stop_requested.flag` による停止を検知します。

- 設定ウィザード（.env 作成）:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラム内呼び出し例）
  - news_nlp:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from datetime import date
    score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
    ```
  - regime_detector:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
    ```

---

## 停止・安全マネジメント

- stop フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution がそれを検知して安全に終了します。
- kill flag（Kill Switch）:
  - `data/kill.flag` はリスク条件（例: ドローダウン超過）で監視系が書き込み、ExecutionEngine に停止シグナルとして機能します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動でクリアします（本番での自動クリアは推奨されません）。
- pid ファイル:
  - 実行時は `data/execution.pid` 等に PID を書き、監視はそれを参照してプロセスの生存を確認します（古いスタレ PID は監視が検出して処理します）。

---

## ディレクトリ構成

（src/kabusys 以下の主なファイル・ディレクトリ）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照実装がある想定)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送信の実装がある想定)
  - execution/                 — ExecutionEngine 関連（ブローカー／オーダー管理等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

備考: 一部ファイル（execution 内の具体的ブローカークライアント等）は実装依存です。本 README はリポジトリ内の主要モジュールに基づく概要です。

---

## 追加メモ・運用上の注意

- 本番で OpenAI を使う場合は API コストとレイテンシに注意。AI 呼び出しはリトライ/バックオフ実装済みだが、外部依存は失敗リスクを伴います。
- `.env` は絶対にリポジトリにコミットしないでください（config_setup の生成コメントにも注意書きあり）。
- DuckDB / SQLite のパスは Settings で上書き可能。監視 DB（monitoring）は環境にかかわらず同一の sqlite_path を利用する設計の箇所があります（run_monitoring 参照）。
- 開発時は KABUSYS_ENV=development を使用し、paper_trading での動作確認は paper_trading 環境で行ってください。live 環境は慎重に。

---

必要であれば、この README を実際の requirements.txt、起動例（systemd / supervisor / docker-compose 用のサンプル）や環境変数テンプレート（.env.example）を付けた形で拡張します。要望があれば教えてください。