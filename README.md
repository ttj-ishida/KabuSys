# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買・リサーチ・監視ツール群「KabuSys」の実装です。README ではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買（Execution）、モニタリング、ポートフォリオ構築、ファクター計算、ニュース NLP を用いたセンチメント評価、リサーチ向けユーティリティなどを含む統合システムです。設計上、以下の点を重視しています。

- 本番/ペーパートレードの分離（環境変数で切替）
- DuckDB + SQLite を利用したデータ処理 / 監視ログの永続化
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントやレジーム判定
- プロセス優先度や CPU affinity の制御（psutil）
- Streamlit ダッシュボードによる監視 UI

主要なエントリポイント:
- 実行（ExecutionEngine）起動スクリプト: run_execution.py
- 監視（SystemMonitor 等）ポーリング起動スクリプト: run_monitoring.py
- Paper Trading 検証レポート生成スクリプト: tools/paper_verification_report.py
- Streamlit ベースの監視ダッシュボード: monitoring/streamlit_dashboard.py

---

## 機能一覧

- Execution
  - Broker クライアント抽象化（本番 / モック切替）
  - OrderManager による注文状態管理、リコンシリエーション
  - RiskManager によるポジション上限・ドローダウン管理
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス・データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の判定と alert ログ
  - MonitoringEngine: 上記を束ねたポーリングループ、KillSwitch を通じて Execution 停止シグナル生成
  - AlertManager: LINE Messaging API による一方向通知（クールダウン管理）
  - Streamlit ダッシュボード：監視データの可視化
- Portfolio（純粋関数群）
  - 銘柄選定、重み計算（等重・スコア重み）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元丸め、aggregate cap）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - news_nlp: ニュースを OpenAI でセンチメント評価、ai_scores に書き込み
  - regime_detector: ma200 とマクロニュースセンチメントを合成して market_regime を判定
- Tools
  - paper_verification_report: Paper Trading DB を解析して運用検証レポートを出力

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を準備:
   - 仮想環境作成例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS/Linux
     .\.venv\Scripts\activate    # Windows PowerShell
     ```

2. 必要パッケージをインストール:
   - 要件ファイルがない場合は最低限これらを入れてください:
     ```
     pip install duckdb psutil openai requests streamlit
     ```
   - 実行用のブローカークライアント等は別途依存関係がある場合があります。

3. プロジェクトルートに `.env`（任意）を置く:
   - config モジュールはプロジェクトルート（.git または pyproject.toml の配下）を自動検出して `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 代表的な環境変数（例）:
     ```
     KABUSYS_ENV=development | paper_trading | live
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     PAPER_FILL_MODE=instant
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     DUCKDB_PATH=data/kabusys.duckdb
     PID_FILE_PATH=data/execution.pid
     KILL_FLAG_PATH=data/kill.flag
     LOG_LEVEL=INFO
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     ```
   - `.env` のパースルールは shell の簡易形式（export あり/なし、シングル・ダブルクォート対応、行末コメントの一部対応）です。

4. データディレクトリの作成:
   - デフォルトで `data/` 以下に SQLite / DuckDB ファイル等を置きます。存在しない場合は各スクリプトがファイルを作成・更新しますが、適切なパーミッションを確認してください。

---

## 使い方

### 1) 監視ループを起動（SystemMonitor 等）
- デフォルトでは 60 秒ごとにポーリングします。間隔は環境変数で上書き可能:
  ```
  export MONITOR_POLL_INTERVAL=30  # 秒
  ```
- 実行:
  ```
  python -m kabusys.run_monitoring
  ```
  - run_monitoring は Settings から sqlite_path/duckdb_path/pid_file を読み、Monitoring DB を初期化して SystemMonitor のポーリングを開始します。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは本番 DB に記録される想定）。

### 2) 実行（ExecutionEngine）を起動
- Paper Trading モード（実際のブローカーを叩かずにモックを使う）:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - paper_trading の場合、settings.is_paper が True となり、paper_sqlite_path（デフォルト: data/paper_trading.db）を用いて DB を分離します。
  - 設定によって MockBrokerClient の動作（PAPER_FILL_MODE）を変更できます:
    ```
    export PAPER_FILL_MODE=instant  # instant | partial | never | reject
    ```

- 本番モード:
  ```
  export KABUSYS_ENV=live
  python -m kabusys.run_execution
  ```
  - 本番利用時は必ず適切な環境変数（KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN など）を設定してください。

### 3) Paper Trading 検証レポート出力
- 指定期間の Paper Trading DB（デフォルト: data/paper_trading.db）を解析して標準出力へレポートを出力します。
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

### 4) Streamlit による監視ダッシュボード
- 監視 DB の読み取り専用ビューを提供します（MonitoringEngine がデータを書き込んでいることが前提）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - DB を read-only URI で開く実装になっています。MonitoringEngine を先に起動してください。

### 5) AI 系（ニュースセンチメント / レジーム判定）
- OpenAI API を利用する機能は `OPENAI_API_KEY` の設定が必須です（もしくは各関数に api_key を渡す）。
- ニューススコア算出:
  - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
- レジーム判定:
  - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
- 実運用では API エラーに対してフェイルセーフ（スコア 0.0 等）やリトライが実装されていますが、API キーとコスト管理に注意してください。

---

## 主要設定（ポイント）

- .env 自動ロード:
  - OS 環境 > .env.local > .env の順で読み込まれます。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- KABUSYS_ENV:
  - 有効値: `development`, `paper_trading`, `live`
  - ペーパートレード時は専用 DB を使用して本番 DB と分離します。

- デフォルトファイルパス:
  - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
  - Monitoring SQLite: data/monitoring.db（Settings.sqlite_path）
  - Paper trading SQLite: data/paper_trading.db（Settings.paper_sqlite_path）
  - PID ファイル: data/execution.pid（Settings.pid_file_path）
  - Kill flag: data/kill.flag（Settings.kill_flag_path）

- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔を秒で上書きできます（デフォルト 60 秒）。
  - 0 以下や不正な値は無視されデフォルトにフォールバックします。

---

## ディレクトリ構成

以下は主なファイルとディレクトリのツリー（抜粋）です:

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / 設定管理（.env ロード含む）
    - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - utils/
      - __init__.py
      - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - __init__.py
      - monitoring_db.py             — SQLite 監視ログ層（スキーマ初期化・CRUD）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 Execution 系モジュール: broker_factory 等)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py

各モジュールは責務を分離しており、純粋関数（ポートフォリオ・リサーチ）／永続化層（monitoring_db）／外部 API 呼び出し（OpenAI・Broker・LINE）などが明確に分かれています。

---

## 運用上の注意

- 本番運用では必ず環境変数やシークレット（API キー、ブローカー認証情報等）の管理に注意してください（.env をバージョン管理しない等）。
- Paper Trading は運用検証用であり、挙動は本番ブローカーとは異なる可能性があります。PAPER_FILL_MODE の動作を理解した上で使用してください。
- OpenAI など外部 API はレートリミット・コストが発生します。API キーと利用量を管理してください。
- Monitoring は監視 DB に書き込みを行います。DB のバックアップ / 保守を考慮してください。
- psutil による優先度変更や CPU affinity 設定は権限が必要な場合があります。権限エラーはログで警告され、処理は継続します。

---

## トラブルシューティング

- .env が自動ロードされない:
  - プロジェクトルートが .git または pyproject.toml によって特定されるため、ワーキングディレクトリの場所に注意してください。
  - 自動ロードを無効化している場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認。
- SQLite / DuckDB ファイルにアクセスできない:
  - ファイルパスとパーミッションを確認してください。Streamlit ダッシュボードは read-only URI を試行します。
- OpenAI 呼び出しでエラーが発生する:
  - `OPENAI_API_KEY` が正しいか、ネットワーク疎通、レート制限状況を確認してください。モジュール側でリトライ・フェイルセーフが実装されていますが、API 側の制約は運用で対応する必要があります。

---

必要に応じて README に追記します。例えば、実際の ExecutionEngine の詳細な設定方法（ブローカープラグインの導入、OrderManager のシグナル入力方法）、CI/デプロイ手順、テストの実行方法などを追加できます。どの項目を詳しく追加しますか？