# KabuSys

KabuSys は日本株の自動売買システムのコンポーネント群です。本リポジトリには取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント / レジーム判定）などの主要機能が含まれます。

以下はソースコード（src/kabusys 以下）に基づく README です。

---

## プロジェクト概要

- 目的: 日本株の自動売買システムを構成するライブラリおよび実行スクリプト群を提供する。
- 主な機能:
  - 注文管理・実行エンジン（実ブローカー / Paper Trading 用 Mock）
  - モニタリング（システム状態・注文滞留・リスク監視）
  - ポートフォリオ構築（候補選定・重み計算・株数計算）
  - リサーチ（ファクター計算・IC 等の統計）
  - AI モジュール（ニュースの NLP スコアリング、レジーム判定）
  - ツール: Paper Trading の検証レポート生成、Streamlit ダッシュボード

---

## 主な機能一覧（抜粋）

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントの抽象化（本番／Mock の切り替え）
  - OrderManager / Reconciler（再起動後の自動復旧）
  - RiskManager（発注時の各種制約）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度を監視
  - TradeMonitor: 注文滞留・約定価格の異常を検出
  - RiskMonitor: ドローダウン / ポジション数上限などを監視してリスクログを残す
  - KillSwitch: リスク条件に応じて停止フラグ（data/kill.flag）を作成
  - AlertManager: LINE によるプッシュ通知（任意）
  - Streamlit ダッシュボード（監視データの可視化）

- Portfolio
  - 候補選定（select_candidates）
  - 等重・スコア重み計算
  - リスク調整（セクター制限、レジーム乗数）
  - 株数決定（単元丸め・利用可能キャッシュに基づくスケーリング）

- Research
  - Momentum / Volatility / Value などのファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- AI
  - ニュース NLP（OpenAI API を利用）で銘柄ごとのセンチメントを算出し ai_scores テーブルに格納
  - レジーム判定（ETF の MA200 とマクロニュースの LLM センチメントを合成）

- Tools
  - paper_verification_report: Paper Trading DB を解析して検証レポートを生成

---

## 必須・推奨依存パッケージ

（実行環境に合わせて適宜インストールしてください）

- Python 3.10+（ソースでの型ヒントに union 型 (|) を使用）
- duckdb
- psutil
- requests
- streamlit（ダッシュボードを使う場合）
- openai（AI 機能を使う場合）
- sqlite3（標準ライブラリ）

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests streamlit openai
```

※ requirements.txt はリポジトリに含めていないため、使用する機能に応じて必要パッケージを追加してください。

---

## 設定（環境変数）

Settings クラスは環境変数を参照します。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

主な環境変数（デフォルト値や用途も記載）:

- KABUSYS_ENV: 動作環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading` の場合、run_execution は MockBroker を使用し DB は data/paper_trading.db を使用します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag パス（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）※ run_monitoring スクリプトで参照

.env の例（簡易）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
LOG_LEVEL=INFO
```

.env.local は .env を上書きする（優先度が高い）。

---

## セットアップ手順

1. リポジトリをチェックアウトして src を PYTHONPATH に含めるかパッケージとしてインストールする
   - 開発中は PYTHONPATH を指定してモジュールを実行するのが簡単です。

2. 仮想環境の作成と依存パッケージのインストール:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests streamlit openai
```

3. 必要な環境変数を .env/.env.local で設定（上の例参照）。必須のもの（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は設定してください。

4. データディレクトリの準備（任意）:
```bash
mkdir -p data
# 実行時に SQLite / DuckDB ファイルは自動作成されますが、パーミッションなどを確認してください
```

---

## 使い方（主なスクリプト）

開発中はリポジトリルートから `PYTHONPATH=src` を付けて実行するか、パッケージをインストールしてください。

- ExecutionEngine を起動する（実取引 or Paper Trading）:
```bash
# 通常: development / live / paper_trading を .env で指定
PYTHONPATH=src python -m kabusys.run_execution
```
挙動のポイント:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます。
- 起動前に data/stop_requested.flag が存在すると起動をスキップします。
- 実行中、data/execution.pid に PID を書きます。停止指示は kill flag（data/kill.flag）を書き込むことで行います（KillSwitch 経由）。

- Monitoring（SystemMonitor のポーリング）を起動する:
```bash
PYTHONPATH=src python -m kabusys.run_monitoring
# ポーリング間隔を上書きする:
MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
```
挙動のポイント:
- 監視は Settings.sqlite_path を使い（環境に関係なく本番 sqlite_path を使用）、監視ログ・リスクログを記録します。
- MONITOR_POLL_INTERVAL（秒）でポーリング、デフォルト 60 秒。
- 停止はプロジェクトルートの data/stop_requested.flag の存在で検知します。

- Streamlit ダッシュボード（監視結果の可視化）:
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- Paper Trading 検証レポート生成:
```bash
PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合:
PYTHONPATH=src python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

---

## ファイル／フラグ（重要なパス）

- data/monitoring.db — 監視ログ SQLite（デフォルト）
- data/paper_trading.db — Paper Trading 用 SQLite（paper_trading 時）
- data/kabusys.duckdb — DuckDB（価格データ等）
- data/execution.pid — ExecutionEngine の PID ファイル
- data/stop_requested.flag — run_monitoring / run_execution が外部停止要求を検知するためのフラグ
- data/kill.flag — KillSwitch が作成する停止フラグ（ExecutionEngine に対する安全停止シグナル）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ初期化（バージョン等）
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースから銘柄ごとのセンチメントを計算して ai_scores に書き込む
  - regime_detector.py — レジーム判定と market_regime 書き込み
- monitoring/
  - monitoring_db.py — 監視用 SQLite のスキーマと DB 操作（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE でのアラート通知
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- execution/
  - order_manager.py — 注文状態管理 API
  - reconciler.py — 起動時の注文・ポジション照合ロジック
  - ...（Broker 抽象など）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出ロジック
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC 計算など
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成ツール
- utils/
  - process_priority.py — プロセス優先度・CPU affinity のユーティリティ

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下のソースを参照してください）

---

## 運用上の注意点 / 実装上の要点

- 環境区分
  - KABUSYS_ENV により挙動が変わります。paper_trading は実取引とデータを完全分離するよう設計されています。
- フェイルセーフ
  - AI API 呼び出し失敗時はフェイルセーフとしてスコア等をデフォルト値にフォールバックし、処理を継続する設計です（部分失敗でシステム全体が停止しないように設計）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等で実行でき、既存テーブルに不足カラムがある場合の簡易マイグレーション（ALTER TABLE）も含みます。
- 権限
  - process priority / cpu affinity の設定は OS に依存しアクセス権が必要な場合があります。失敗時は警告ログを出してスキップします。
- 時刻の扱い
  - AI / レポート等ではルックアヘッドバイアスを避けるため日付や時間の扱いに注意した実装方針が採用されています（target_date を外部から渡すなど）。

---

## トラブルシュート（よくある質問）

- 起動時に .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認してください。
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行われます。ディレクトリ構造が変わっていると自動検出がスキップされます。

- run_monitoring が起動しない / すぐ終了する
  - data/stop_requested.flag が存在すると直ちに終了します。不要なら削除してください。

- run_execution が起動しない（Paper Trading でないのに paper DB を使っている）
  - KABUSYS_ENV を確認してください。paper_trading 時は PAPER_TRADING_SQLITE_PATH を使用します。

- OpenAI API 呼び出しで失敗する
  - OPENAI_API_KEY の設定とネットワーク、API レート制限状況を確認してください。ライブラリのバージョンやサーバー側エラーによりリトライが発生します。

---

この README はソースコードの主要部分からの抜粋に基づいて作成しています。さらに詳しい設計仕様（PortfolioConstruction.md、StrategyModel.md 等）やブローカー実装の詳細は別ドキュメントを参照してください。追加で README に載せたい内容（例: サンプル .env.example、CI／テストの実行手順、詳細な API 仕様など）があれば指示ください。