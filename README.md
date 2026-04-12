# KabuSys

日本株自動売買システムの一部（ライブラリ・監視・実行エンジン・リサーチ・AIユーティリティ群）。

この README はコードベース（src/kabusys 以下）を対象に、プロジェクト概要・機能一覧・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム用に設計された Python モジュール群です。主要な責務は以下：

- 戦略のためのファクター計算・リサーチ（DuckDB を利用）
- ポートフォリオ構築・ポジションサイズ計算（純粋関数群）
- 実行エンジン（ブローカー接続・リスク管理・注文管理）
- 実行状態・注文・リスクの監視（SQLite に永続化）
- AI を使ったニュース NLP（OpenAI）および市場レジーム判定
- 運用支援ツール（監視ダッシュボード、Paper Trading 検証レポート 等）

設計方針として、安全性（クラッシュ耐性・冪等性）、フェイルセーフ、ルックアヘッドバイアス回避（外部に現在時刻を参照しない実装方針）が考慮されています。

---

## 主な機能一覧

- monitoring
  - system_monitor: CPU/メモリ/Disk、データ鮮度、Execution プロセスの存在を監視しログ化
  - trade_monitor: 注文滞留・約定価格異常を検出しリスクログ化
  - risk_monitor: ドローダウン・ポジション上限の判定・アラート化
  - kill_switch: フラグファイル（data/kill.flag）を書き込み Execution 停止を指示
  - alert_manager: LINE Push による一方向通知（クールダウン管理）
  - MonitoringEngine: 各モニタを束ねるポーリングループ
  - streamlit_dashboard: 監視ダッシュボード（Streamlit）
- execution
  - OrderManager / OrderRepository / Reconciler / ExecutionEngine（起動スクリプトあり）
  - Broker クライアントの抽象化 + Paper Trading 用の分離ストレージ
- research
  - factor_research: momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration: forward returns, IC 計算、統計サマリー
- portfolio
  - portfolio_builder: 候補選定・重み計算（等金額・スコア加重）
  - position_sizing: 株数算出・lot 単位丸め・集約上限のスケールダウン
  - risk_adjustment: セクター上限・レジーム乗数
- ai
  - news_nlp: raw_news を LLM に問い合わせて銘柄ごとのセンチメントを ai_scores に書込
  - regime_detector: ETF MA とマクロニュースの LLM 結果を合成して日次レジーム判定
- tools
  - paper_verification_report: Paper Trading DB（data/paper_trading.db）から検証レポートを生成

---

## 前提・依存関係

- Python 3.10+
- SQLite（標準ライブラリ）
- 必要な Python パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- （推奨）仮想環境の使用（venv / pyenv / poetry 等）

インストール例（venv を使用）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

プロジェクトに requirements.txt があればそちらを利用してください。

---

## 環境変数と設定 (Settings)

実行時の設定は環境変数（または .env / .env.local）で与えます。プロジェクトルートを自動検出し .env を自動ロードします（無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

主な環境変数（重要なもの）：

- KABUSYS_ENV: 起動環境。development / paper_trading / live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用
- KABU_API_PASSWORD: （必須）kabuステーション API 用
- OPENAI_API_KEY: OpenAI を使う機能で必要（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視ログ SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill フラグファイル（デフォルト: data/kill.flag）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒、デフォルト: 60）

Settings クラスは `kabusys.config.Settings` で型安全にアクセスできます。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. 仮想環境作成・依存インストール：

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb psutil requests openai streamlit
   ```

3. 環境変数を用意（.env をプロジェクトルートに作成）。最低限必要なもの：
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - （OpenAI 機能を使う場合）OPENAI_API_KEY

   例（.env）:

   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   ```

4. データディレクトリ作成（必要に応じて）:

   ```bash
   mkdir -p data
   ```

5. DuckDB / SQLite の初期化は起動スクリプトが必要なテーブルを自動作成します（init_monitoring_db を参照）。

---

## 使い方

### 監視ループを起動（Monitoring）

MonitoringEngine 単体の起動スクリプト:

- 直接（スクリプト）:
  ```bash
  python src/kabusys/run_monitoring.py
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可（秒）。デフォルト 60 秒。
  - Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を使用します（監視ログは環境に依存しない）。

### 実行エンジンを起動（Execution）

Execution エンジン起動スクリプト:

```bash
python src/kabusys/run_execution.py
```

- KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録します。本番 DB と完全に分離されます。
- 起動時にプロセス優先度を高くする処理を行います（psutil を使用）。

### Streamlit ダッシュボード（監視）

ローカルで簡易ダッシュボードを表示するには：

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

監視 DB を読み取り専用で開くため、MonitoringEngine が先に動いていることが望ましいです。

### Paper Trading 検証レポート

Paper Trading の検証レポートを生成する CLI ツール:

```bash
python -m kabusys.tools.paper_verification_report
# 期間指定:
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パス指定:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

出力は標準出力に人間向けレポートとして表示されます。指定がない場合はデフォルト DB path = data/paper_trading.db を参照します。

### AI 機能（ニュース NLP / レジーム判定）

- OpenAI API キーが必要（OPENAI_API_KEY）。
- API コールを行う関数は `kabusys.ai.news_nlp.score_news` / `kabusys.ai.regime_detector.score_regime` です（DuckDB 接続と target_date を渡して呼び出す）。
- リトライ・バックオフ、部分失敗時のフェイルセーフなどを備えています。

---

## 運用上のポイント

- PID / Kill フラグ
  - ExecutionEngine は起動時に pid をファイル（Settings.pid_file_path, デフォルト data/execution.pid）へ書きます。SystemMonitor はこの PID ファイルを監視し、プロセスが存在しなければ stale PID とみなし削除・アラートします。
  - KillSwitch は data/kill.flag を生成することで ExecutionEngine に停止を要求します。ExecutionEngine 側はこのフラグを監視して安全停止する設計です。
- Paper Trading
  - KABUSYS_ENV=paper_trading のとき、orders 等は data/paper_trading.db に記録され、本番 DB と完全分離されるようになっています。
  - PAPER_FILL_MODE により約定挙動（instant/partial/never/reject）を変更可能。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等なテーブル作成に加え、既存 DB に対する簡単なマイグレーション（カラム追加）を含みます。

---

## ディレクトリ構成（主なファイルと簡単な説明）

（コードベースは src/kabusys/ 以下）

- src/kabusys/__init__.py
  - パッケージメタ情報とエクスポート

- src/kabusys/config.py
  - 環境変数ロード / Settings クラス（アプリ設定）

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading による分離対応）

- src/kabusys/monitoring/
  - monitoring_db.py: SQLite を使った永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py: システム・データ鮮度監視
  - trade_monitor.py: 注文滞留 / 約定異常監視
  - risk_monitor.py: ドローダウン / ポジション上限監視
  - kill_switch.py: kill.flag 書き込みユーティリティ
  - alert_manager.py: LINE Push 通知
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: Streamlit ダッシュボード

- src/kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory など
  - 注文状態管理・ブローカー抽象化・再同期ロジック（Reconciler）

- src/kabusys/portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数決定・集約制限
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py: momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration.py: forward returns, IC, 統計サマリー

- src/kabusys/ai/
  - news_nlp.py: raw_news→OpenAI→ai_scores 書き込み
  - regime_detector.py: ma200 とマクロニュースを合成して market_regime に書き込み

- src/kabusys/tools/
  - paper_verification_report.py: Paper Trading 検証レポート生成 CLI

- src/kabusys/utils/
  - process_priority.py: プラットフォーム差分を吸収したプロセス優先度 / CPU affinity 設定

---

## 開発・拡張のヒント

- DuckDB 接続を渡すことで、research モジュールは外部 API にアクセスせずデータソースだけで計算可能です（オフラインでの検証が容易）。
- OpenAI API 呼び出し部分は明確に分離され、テスト時は該当関数をモックできます（unittest.mock.patch を想定）。
- SQLite の monitoring DB は軽量なのでローカル検証・CI でのモックに適しています。

---

## 参考コマンドまとめ

- 監視プロセス起動:
  - python src/kabusys/run_monitoring.py
- 実行エンジン起動:
  - python src/kabusys/run_execution.py
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に「環境変数の完全一覧」「サンプル .env.example」「requirements.txt」「起動例の systemd ユニット例」などを追記できます。どの項目を追加しますか？