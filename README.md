# KabuSys — 日本株自動売買システム (README)

本リポジトリは日本株を対象とした自動売買システムのコードベースです。戦略・ポートフォリオ構築、注文実行（本番／ペーパートレード分離）、監視・アラート、研究用ファクター計算、LLMを使ったニュース解析などのコンポーネントを含みます。

以下は簡易ドキュメント（日本語）です。起動前に必ず `.env` を作成し、`python -m kabusys.validate_config` で設定確認してください。

---

## プロジェクト概要

- 戦略から銘柄選定・配分（portfolio module）、ポジションサイズ算出（position_sizing）を行う計算ロジックを提供します。
- ExecutionEngine によりブローカー（本番 or Mock）へ発注を行います。KABUSYS_ENV により本番／ペーパーを切替可能。
- Monitoring サービスでプロセス・システム状態や注文ログの監視を行い、Kill Switch（フラグファイル書き込み）やアラート通知を行います。
- 研究（research）モジュールは DuckDB にロードされた市場データを用いてファクター計算や特徴量評価を行います。
- AI モジュール（ai）でニュースのセンチメント解析や市場レジーム判定を行い、DuckDB に結果を書き込みます。
- ツール群（tools）には Paper Trading の検証レポート生成などの CLI ユーティリティを含みます。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード/手動ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行（Execution）
  - ExecutionEngine（本番／ペーパートレード切替）
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は Mock を利用）
  - 注文管理・リコンシリエーション・リスク管理
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、プロセス生存監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン等の監視
  - MonitoringEngine: ポーリングループ、Kill Switch 評価、アラート発行
  - SQLite ベースの永続化（monitoring_db）
- ポートフォリオ構築
  - 候補選定、等重 / スコア加重、リスク調整（セクターキャップ・レジーム乗数）
  - 株数算出（単元株丸め・利用可能現金に合わせたスケール調整）
- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC 計算、ファクター統計
- AI（OpenAI）
  - ニュースセンチメント（news_nlp） → ai_scores テーブルへ
  - 市場レジーム判定（regime_detector）→ market_regime テーブルへ
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. Python 環境の準備（推奨: venv）
   - Python 3.9+（コードは型注釈等利用。実際のプロジェクト要件に合わせてください）

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージのインストール
   - 必要な主なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML の検証を行う場合）
   - requirements.txt がある場合はそれを利用してください。
   ```
   pip install duckdb psutil openai pyyaml
   ```

3. プロジェクトルートで .env を作成
   - インタラクティブウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動で作成（秘匿情報は Git にコミットしないでください）。

4. 設定検証（必須項目確認）
   ```
   python -m kabusys.validate_config
   # 警告を厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. 初期データディレクトリの作成（必要に応じて）
   - デフォルト DB / ログのパスは `data/` / `logs/` など。`.env` で上書き可能。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注は MockBrokerClient、DB は data/paper_trading.db（デフォルト）
- OPENAI_API_KEY: AI モジュール利用時に必要
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の注文挙動）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite データベースパス（既定: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（既定: data/monitoring.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（既定: INFO）
- LOG_DIR: ログ保存ディレクトリ（既定: logs/）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（既定: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch のフラグファイル（既定: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、既定: 60）

（詳細は kabusys.config.Settings のプロパティを参照してください）

---

## 使い方（起動・操作例）

- 監視ループ（SystemMonitor）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は設定された sqlite_path（monitoring DB）へログを永続化します。
  - 停止フラグ: data/stop_requested.flag が存在するとループを終了します。

- ExecutionEngine を起動（注文エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
  - 起動時に data/stop_requested.flag が既にある場合は起動を行わず終了します。
  - 実行中に data/stop_requested.flag を作成するとエンジン停止シーケンスが実行されます。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュール（プログラム的に呼び出す例）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=...)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=...)

  ※ OpenAI API キーが必要です（env: OPENAI_API_KEY または引数で指定）。

---

## 停止・Kill Switch の挙動

- run_monitoring / run_execution は両方ともプロジェクト内の `data/stop_requested.flag` を監視しています。フラグを作成すると安全に停止するよう試みます。
- Kill Switch（監視による自動停止）は `data/kill.flag` に理由文字列を書き込みます。ExecutionEngine 側では `KILL_FLAG_CLEAR_ON_START` の設定次第で起動時に自動クリアする挙動が制御されます（本番では自動クリアは推奨されません）。
- PID ファイル: `data/execution.pid`（デフォルト）に ExecutionEngine の PID を書きます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py           — .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — Monitoring の起動スクリプト
  - run_execution.py          — ExecutionEngine の起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py       — システム監視
    - risk_monitor.py         — ドローダウン / ポジション監視
    - trade_monitor.py        — （注文監視; コードベースに依存）
    - kill_switch.py          — kill.flag 書き込み
    - monitoring_engine.py    — 複数モニタを束ねるエンジン
    - alert_manager.py        — （アラート送信; 実装による）
  - execution/
    - execution_engine.py     — ExecutionEngine
    - broker_factory.py       — Broker クライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py      — ファクター計算
    - feature_exploration.py  — IC 等
    - __init__.py
  - ai/
    - news_nlp.py             — ニュースセンチメント
    - regime_detector.py      — 市場レジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
- data/                       — デフォルトの DB / flag / pid 置き場（実行時に作成される）
- logs/                       — ログ出力先（既定）

（実際のファイルは src/kabusys 以下を参照してください）

---

## 追加メモ / 運用上の注意

- 機密情報（API トークン・パスワード等）は .env に保存しますが、決して Git にコミットしないでください。
- production（KABUSYS_ENV=live）では Kill Switch、LINE 通知などの設定を十分に確認してください（validate_config は live 時に追加の警告を出します）。
- OpenAI API 呼び出しはネットワーク/レート制限を受けます。AI 関連処理はリトライ・フェイルセーフ設計になっていますが、API キーの使用状況に注意してください。
- DuckDB のスキーマ（prices_daily、raw_financials、raw_news 等）に依存するモジュールが多いため、データ投入とスキーマ整合を取り扱うスクリプトや手順を別途整備してください。

---

この README はコードベースの主要点をまとめたものです。各モジュールの詳細や追加の運用手順は該当するモジュールの docstring / ソースコメントを参照してください。必要であればドキュメントの項目を拡張します。