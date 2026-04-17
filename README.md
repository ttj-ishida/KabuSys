# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋実行スクリプト群）。  
このリポジトリは戦略構築・ポートフォリオ構成、発注エンジン、監視、AI を使ったニューススコアリング／レジーム判定、検証ツール等を含みます。

---

## プロジェクト概要

KabuSys は以下の機能領域を持つモジュール群で構成されています。

- 発注・実行エンジン（ExecutionEngine 相当）および Order 管理（OrderManager / OrderRepository）
- 監視サブシステム（System / Trade / Risk モニタ、アラート、kill-switch、ストリームリットダッシュボード）
- ポートフォリオ構築ユーティリティ（候補選定、重み付け、位置サイズ計算、セクター制限）
- リサーチ／ファクター計算（DuckDB に格納された時系列データを参照）
- AI モジュール（OpenAI を用いたニュースセンチメント / 市場レジーム判定）
- 運用補助ツール（Paper Trading 検証レポート等）

設計上のポイント：
- DuckDB / SQLite をローカル DB として利用（データ永続化、分析）
- 環境変数 / .env による構成管理（`kabusys.config.Settings`）
- 実行プロセスの優先度や PID / フラグファイルを使った停止制御をサポート
- Paper Trading（テスト）と Live（本番）を環境で分離

---

## 主な機能一覧

- monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・Execution プロセス検知
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン、ポジション上限監視、ダッシュボード更新
  - AlertManager: LINE へプッシュ通知（クールダウン管理）
  - KillSwitch: 条件により `data/kill.flag` を生成して ExecutionEngine を停止
  - MonitoringEngine: 上記モニタをまとめて定期実行
  - streamlit_dashboard: 監視データの可視化 UI

- execution
  - OrderManager / OrderRepository / Reconciler: 発注ライフサイクル、リコンシリエーション
  - BrokerFactory（環境に応じて MockBroker を使い分け）

- portfolio
  - 候補選定・重み計算（等配分・スコア加重）
  - セクター上限の適用
  - 位置サイズ計算（ロット丸め、リスクベース配分、aggregate cap）

- research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 特徴量探索（将来リターン計算、IC、統計サマリ）

- ai
  - news_nlp: raw_news を OpenAI に送り銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector: ma200 とマクロニュースの LLM 判定を合成して市場レジーム判定

- tools
  - paper_verification_report: Paper Trading DB を集計して Pass/Fail 判定の検証レポートを出力

---

## セットアップ手順（開発環境）

※ プロジェクトルートを想定（`pyproject.toml` / `.git` がある場所）。ソースは `src/` 下にあります。

1. Python 環境（推奨: 3.9+）を用意
2. 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. 依存パッケージをインストール（最低限）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   - 実運用で他の依存がある場合は requirements.txt を参照してください（本サンプルでは明示的な requirements ファイルは付属していません）。
4. 作業用データディレクトリを作成
   ```
   mkdir -p data
   ```
   デフォルトの DB ファイル:
   - 監視用 SQLite: `data/monitoring.db`（Settings.sqlite_path のデフォルト）
   - DuckDB: `data/kabusys.duckdb`（Settings.duckdb_path のデフォルト）
   - Paper Trading DB: `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH のデフォルト）

5. 環境変数設定
   - `.env` または `.env.local` をプロジェクトルートに置くと自動で読み込まれます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 重要な環境変数（一例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
     - KABUSYS_ENV: execution/monitoring の実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper トレード時の約定挙動 ("instant"|"partial"|"never"|"reject")
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を行う場合
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔秒（run_monitoring で上書き、デフォルト 60）
     - PID/KILL フラグ関連:
       - PID_FILE_PATH（デフォルト data/execution.pid）
       - KILL_FLAG_PATH（デフォルト data/kill.flag）

---

## 使い方（主要コマンド）

実行は以下のいずれかの方法で行います。開発中は `PYTHONPATH=src` を設定して `-m` モジュール実行するか、パッケージを editable インストールしてください。

例（プロジェクトルートで）:
```
PYTHONPATH=src python -m kabusys.run_monitoring
PYTHONPATH=src python -m kabusys.run_execution
```

- 監視ループ起動（Monitoring）
  - スクリプト: `src/kabusys/run_monitoring.py`
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒で上書き可（デフォルト 60）
  - 監視は常に本番の sqlite_path（`Settings.sqlite_path`）を使います（環境にかかわらず）
  - 停止方法:
    - 実行プロセスを Ctrl+C（KeyboardInterrupt）
    - あるいはプロジェクトの `data/stop_requested.flag` ファイルを作成するとポーリングループが検知して終了します

- 実行エンジン起動（ExecutionEngine）
  - スクリプト: `src/kabusys/run_execution.py`
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB (`data/paper_trading.db` 既定) に記録します（本番と完全分離）。
  - 起動前に `data/stop_requested.flag` が存在すると起動をスキップします。
  - 実行中に `data/stop_requested.flag` を作成するとエンジン停止を試みます。
  - PID ファイル: `data/execution.pid`（`Settings.pid_file_path` で上書き可）

- Streamlit ダッシュボード
  - ファイル: `src/kabusys/monitoring/streamlit_dashboard.py`
  - 起動:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - read-only モードで SQLite を開きます。MonitoringEngine が DB を更新していることが前提です。

- Paper Trading 検証レポート
  - スクリプト: `src/kabusys/tools/paper_verification_report.py`
  - 実行例:
    ```
    PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
    ```
  - 短い期間を指定して Paper Trading の稼働率、注文成功率、レイテンシなどを検証できます。

- AI モジュール（ニュース / レジーム）
  - OpenAI を利用するため `OPENAI_API_KEY` が必要
  - 単体で呼び出す関数:
    - `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## 停止・制御方法

- stop_requested.flag
  - `data/stop_requested.flag` を作成すると、run_monitoring.py / run_execution.py が検知して安全に終了または停止します（監視ループ／エンジンの実装に基づく）。

- kill.flag（KillSwitch）
  - 監視側の KillSwitch が `data/kill.flag` を生成すると ExecutionEngine 側の kill フラグ検査ロジック（Settings.kill_flag_path に準拠）で実行停止を促します。
  - KillSwitch はドローダウンやポジション上限などのルールに基づきフラグを書き込みます。

---

## 主要な設定（環境変数まとめ）

必須 / 重要なもの（例）:

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- OPENAI_API_KEY — OpenAI を使用する場合
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — instant|partial|never|reject（paper_trading 用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知を有効にする際に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング秒数（run_monitoring のオーバーライド）
- PID_FILE_PATH / KILL_FLAG_PATH — ファイルパス指定（Defaults under data/）

注意:
- `.env` 自動読み込みはプロジェクトルートが見つかった場合に行われます（`.git` または `pyproject.toml` が目印）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## ディレクトリ構成

（重要ファイルに絞った簡易ツリー）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / Settings 管理
    - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - ai/
      - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py           — 市場レジーム判定（LLM + MA200）
      - __init__.py
    - monitoring/
      - monitoring_db.py             — monitoring DB 初期化・読み書き層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
      - __init__.py
    - execution/
      - order_manager.py
      - reconciler.py
      - order_repository.py (一部)
      - execution_engine.py (一部)
      - broker_factory.py (一部)
      - ...
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
- data/                                 — 実行時生成の DB / PID / flag 等（git 管理外推奨）
  - monitoring.db
  - kabusys.duckdb
  - paper_trading.db
  - execution.pid
  - kill.flag / stop_requested.flag

---

## 開発・運用上の注意点

- DB マイグレーション
  - `monitoring_db.init_monitoring_db()` は冪等でテーブル作成と簡易マイグレーション（列追加）を行います。
- 権限
  - プロセス優先度（高）へ変更する処理があり、権限不足で警告が出ることがあります（`psutil` の AccessDenied をログ出力してスキップ）。
- LLM 呼び出しの堅牢化
  - OpenAI 呼び出しはリトライ・バリデーションを実装しており、失敗時はフェイルセーフ（0相当など）で継続する設計です。
- テスト/CI
  - 環境変数の自動ロードはテスト時に影響するため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。
- Paper Trading
  - Paper 環境（KABUSYS_ENV=paper_trading）は本番 DB と分離されるよう設計されています。Paper 用 DB パスは `PAPER_TRADING_SQLITE_PATH` で指定可能です。

---

## よくあるコマンドまとめ

- 監視起動（60秒間隔）
  ```
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```
- 監視起動（30秒間隔）
  ```
  MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
  ```
- 実行エンジン起動（Paper trading）
  ```
  KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
  ```
- Streamlit ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
- Paper 検証レポート
  ```
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

---

必要であれば、README にサンプル .env テンプレート、依存パッケージの固定バージョン（requirements.txt）、および簡易デプロイ手順（systemd ユニット例など）を追加できます。どの情報がさらに欲しいか教えてください。