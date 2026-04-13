# KabuSys README

※このドキュメントは与えられたコードベース（src/kabusys）を元に作成した概要ドキュメントです。実行例や環境変数の説明を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買およびそれを支える研究・監視ツール群です。  
主要な目的は以下の通りです：

- 戦略（ファクター計算、特徴量解析）およびポートフォリオ構築ロジックの提供
- 発注・リスク管理・実行（ExecutionEngine 相当）のための実装（ブローカーファクトリ／OrderManager 等）
- モニタリング（System / Trade / Risk）とアラート（LINE）機能
- Paper Trading 用の検証レポート生成ツール
- OpenAI（LLM）を使ったニュースセンチメント評価や市場レジーム判定（AI モジュール）
- DuckDB / SQLite を用いたデータ・監視ログの永続化と Streamlit ダッシュボード

設計上、研究用コンポーネントは本番発注ロジックやネットワーク I/O に依存しないように分離されています。Paper Trading（KABUSYS_ENV=paper_trading）モードでは本番 DB と分離して動作します。

---

## 主な機能一覧

- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス死活、株価データ鮮度の監視
  - TradeMonitor: 滞留注文や約定価格の異常検出
  - RiskMonitor: ドローダウンやポジション数の監視、kill.flag 生成
  - AlertManager: LINE Push によるアラート送信（クールダウン管理）
  - MonitoringEngine: 上記モニタを束ねて定期実行
  - streamlit_dashboard: 監視用ダッシュボード（Streamlit）

- 実行（execution）
  - OrderManager / Reconciler / ExecutionEngine（起動・同期・自動リカバリ）
  - BrokerClientFactory により本番 / モックブローカーを選択（Paper Trading は分離）

- ポートフォリオ構築（portfolio）
  - 候補選定、等金額/スコア加重、リスク調整（セクター制限、レジーム乗数）
  - ポジションサイズ計算（単元株丸め・aggregate cap）

- 研究（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（ai）
  - news_nlp: raw_news をまとめて OpenAI に投げ、銘柄ごとのセンチメントスコアを ai_scores に書き込み
  - regime_detector: ETF（1321）の MA200 乖離 + マクロニュースセンチメントを合成して市場レジーム判定

- ツール
  - paper_verification_report: Paper Trading DB を集計し検証レポートを生成

---

## 必要環境 / 依存パッケージ

（requirements.txt はリポジトリ内にない想定のため、直接インストールするパッケージ例）

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit
- sqlite3（標準ライブラリ）
- その他（ローカル環境に応じたパッケージ）

インストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをチェックアウトする（プロジェクトルートに `pyproject.toml` または `.git` が存在する想定）。
2. 仮想環境を作成して必要パッケージをインストール（上記参照）。
3. 環境変数を準備する：
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要な環境変数（抜粋）：
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合は必須）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - SQLITE_PATH（監視ログ DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知用、未設定なら通知はスキップ）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
     - PID_FILE_PATH, KILL_FLAG_PATH（それぞれデフォルト: data/execution.pid, data/kill.flag）
4. データディレクトリを作成：
```bash
mkdir -p data
```

---

## 使い方

以下は主要なスクリプトと起動方法の例です。

- 監視ループ（SystemMonitor をポーリングして SQLite に記録）
```bash
python -m kabusys.run_monitoring
# ポーリング間隔を変更する場合:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
説明:
- MONITOR_POLL_INTERVAL は秒数（1 以上）。不正な値はデフォルト 60 秒にフォールバックします。
- 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（monitoring 用 DB は共通）。

- 実行エンジン（ExecutionEngine）起動
```bash
python -m kabusys.run_execution
```
説明:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）に保存され、本番 DB と分離されます。
- 起動時にプロセス優先度を `high` に設定しようとします（psutil を利用。権限不足の場合は警告が出ます）。

- Streamlit ダッシュボード（監視データの可視化）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- `--db` で監視 DB パスを指定できます。既定は `data/monitoring.db`。

- Paper Trading 検証レポートの生成
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB パス指定:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- 出力は標準出力にレポートを表示。指標の閾値（稼働率・成功率・P95 レイテンシ等）に基づいて PASS/FAIL を判定します。

- AI モジュール（ニューススコア / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡して銘柄毎センチメントを ai_scores テーブルに書き込む。
  - regime_detector.score_regime(conn, target_date, api_key=None) — market_regime テーブルにレジームを書き込む。
  - これらは CLI スクリプトではなく関数として呼ばれます。使用時は OPENAI_API_KEY を設定してください（関数引数で指定可）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（必須ではないが妥当な値である必要あり）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

注意:
- 設定はプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（既存 OS 環境を保護する仕組みあり）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・モジュール構成（リポジトリ内ファイルを元に作成）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - data/                         — （外部データ・DuckDB / SQLite 等、実行時生成）
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite テーブル作成 / MonitoringDB クラス（読み書き）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py         —（Orders DB 参照想定）
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - ...（発注関連）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - process_priority.py

（上記は主要ファイルのみ。実際のリポジトリに他の補助モジュールが存在する可能性があります）

---

## 運用上の注意 / 補足

- Monitoring DB（SQLite）は init_monitoring_db() によりテーブル作成と簡単なマイグレーション（カラム追加）を行います。起動時に呼び出して DB スキーマを確保してください。
- PID ファイル（ExecutionEngine）を使用してプロセスの存在チェックを行います。古い（stale）PID ファイルは SystemMonitor により検出・削除され、risk_logs に記録されます。
- KillSwitch は RiskMonitor の検出に応じて `data/kill.flag` を作成します。ExecutionEngine 側でこのフラグファイルを検出して安全に停止する想定です。起動時にフラグをクリアするための設定（KILL_FLAG_CLEAR_ON_START）があります。
- process priority / CPU affinity の設定には psutil を利用します。OS による差分（Windows / POSIX）を吸収しますが、権限不足や未対応 OS の場合は警告ログが出ます。
- AI（OpenAI）関連は API 呼び出しにリトライやレスポンス検証を組み込み、失敗時はフェイルオープン（安全側動作）で処理を継続する設計です。ただし API キーは必須です。
- Paper Trading モードは本番と DB を分離して動かせるため、実運用テストに便利です。

---

## さらに調べるべき場所（導入後の参照）

- 発注関連の詳細（src/kabusys/execution）：OrderRepository、Broker API 実装、ExecutionEngine のワークフロー
- 研究関連（src/kabusys/research）：ファクター設計や zscore 正規化（kabusys.data.stats 参照）
- monitoring と alert の閾値や dedup（risk_logs）のデフォルト設定（Settings の各プロパティ）
- AI モジュールのプロンプトやバッチ処理ロジック（src/kabusys/ai）

---

README の内容はコードベースのコメントと docstring を元に作成しています。実際に運用する際は環境変数や依存パッケージのバージョン、ブローカー実装（本番の API エンドポイント等）を確認してください。必要に応じて README をプロジェクト固有の情報（requirements.txt、起動サービス定義 systemd / supervisor 等）で拡張してください。