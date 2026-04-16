# KabuSys

日本株向け自動売買基盤（ライブラリ/実行・監視ユーティリティ群）

このリポジトリは、シグナル → 発注 → モニタリングまでを含む自動売買システムのコア部品群です。ポートフォリオ構築、ポジション計算、リスク制御、監視・アラート、Paper Trading 検証、LLM ベースのニュースセンチメント等の機能を備えています。

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine / OrderManager / Reconciler による発注実行と自動復旧
  - Paper Trading モード（本番 DB と分離された data/paper_trading.db）対応
  - RiskManager によるリスク制御（ポジション上限、利用率等）

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/DISK/プロセス・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検知
  - RiskMonitor: ドローダウン監視、ポジション上限検出
  - KillSwitch / AlertManager: 条件に応じた停止フラグ作成と LINE への通知
  - MonitoringEngine: 各モニタをまとめてポーリング
  - Streamlit ダッシュボードで監視データ可視化

- Portfolio（銘柄選定・サイズ計算）
  - 候補選定、等金額 / スコア加重配分
  - セクター上限適用、レジーム乗数
  - 発注株数計算（単元丸め・集計キャップ等）

- Research / AI
  - ファクター計算（Momentum / Volatility / Value 等、DuckDB ベース）
  - Feature exploration（forward return, IC 等）
  - ニュース NLP（OpenAI を用いたセンチメントスコアリング）
  - Market regime 判定（ETF MA とマクロニュースを組合せ）

- Utilities
  - process priority / CPU affinity 設定ユーティリティ
  - .env 自動読み込みロジック（Settings）

- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）

---

## 前提 / 必要環境

- Python 3.10+
- SQLite（標準ライブラリで利用）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - requests
  - openai (AI 機能を利用する場合)
  - streamlit (ダッシュボードを使う場合)

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（実際のプロジェクトでは requirements.txt を用意して pip install -r requirements.txt を推奨します）

---

## セットアップ手順

1. リポジトリをクローン：
   - git clone ...

2. 仮想環境を作成して依存パッケージをインストール（上記参照）。

3. data ディレクトリ作成（必要ファイルはスクリプト起動時に自動作成されることが多いですが、明示的に作ると良い）:
```
mkdir -p data
```

4. 環境変数 / .env の準備：
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (通知に必要)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB。デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定挙動
     - MONITOR_POLL_INTERVAL (監視ループの秒間隔、デフォルト 60)
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

   例 .env（最小）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DB の初期化：
   - 監視用 SQLite テーブルは起動スクリプト（run_monitoring.py / run_execution.py）が自動で init_monitoring_db を呼びます。手動で初期化したい場合は Python REPL 等から init_monitoring_db を実行してください。

---

## 使い方（主要エントリポイント）

- 監視ループの起動（Monitoring）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 停止はプロジェクトルート data/stop_requested.flag を作成することで安全にループを抜けます。
  - 起動コマンド:
    ```
    python -m kabusys.run_monitoring
    ```
  - 監視は Settings にかかわらず本番 sqlite_path（SQLITE_PATH）を使用してログを永続化します。

- 実行エンジンの起動（Execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます。本番 DB と分離されます。
  - 起動コマンド:
    ```
    python -m kabusys.run_execution
    ```
  - 実行中は data/execution.pid に PID を書き、data/stop_requested.flag が作成されるとエンジンを停止します。
  - ExecutionEngine はリコンシリエーション（起動時自動復旧）や RiskManager を組み合わせて安全に動作します。

- Paper Trading 検証レポート生成
  - data/paper_trading.db を参照して各種指標（稼働率、注文成功率、P95 レイテンシ等）を計算して標準出力に出します。
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - --db オプションで DB パスを指定可能（優先度: --db > 環境変数 > デフォルト data/paper_trading.db）

- Streamlit ダッシュボード（監視データ可視化）
  - 起動コマンド:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 読み取り専用で SQLite を開くため、MonitoringEngine 実行中にダッシュボードを安全に参照できます。

---

## 重要な運用トピック

- 環境モード（KABUSYS_ENV）
  - development / paper_trading / live の3つが有効値。paper_trading は発注先をモックにして DB を分離します。

- 停止と強制停止
  - 正常停止シグナル: data/stop_requested.flag — run_monitoring / run_execution はこのファイルを検出して安全に終了します。
  - KillSwitch: リスク閾値超過時に data/kill.flag を書き込み、外部からエンジン停止を要求できます（KillSwitch によりファイルを書き込む処理は用意されています）。Settings.kill_flag_clear_on_start を利用して起動時に既存フラグを自動削除できます。

- PID ファイル
  - data/execution.pid に実行エンジンの PID を格納して存在チェックを行います。stale PID（既に死んでいるプロセスが示されるファイル）は SystemMonitor により検出・削除されます。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブル作成と簡単なカラム追加（マイグレーション）を実行します。

- OpenAI / API エラー耐性
  - news_nlp / regime_detector の OpenAI 呼び出しはリトライやフェイルセーフ（API 失敗時のデフォルト）を組み込んでいますが、API キー未設定だと例外を投げます（使用しない場合は環境変数を設定しないでください）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理 (.env 自動読み込み)
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - execution_engine.py, broker_factory 等（発注周りの実装）

  - monitoring/
    - monitoring_db.py — SQLite 永続層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各モニタ統合
    - streamlit_dashboard.py — Streamlit UI

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

  - data/ (作成される/参照されるファイル例)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - execution.pid
    - stop_requested.flag
    - kill.flag

  - tools/
    - paper_verification_report.py

---

## サンプルワークフロー（簡易）

1. .env を用意して依存をインストール。
2. 監視を起動:
   - python -m kabusys.run_monitoring
3. 実行エンジンを起動（別プロセス/ホスト）:
   - python -m kabusys.run_execution
4. モニタリングダッシュボードをブラウザで確認:
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
5. Paper Trading の検証レポートを出力:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## トラブルシューティング / 注意点

- Python バージョンは 3.10 以上を推奨（| 型アノテーション等の使用）。
- OpenAI / LINE などの外部サービスを使う機能は、対応する環境変数が未設定だと警告・例外になります（AI 機能は API キー必須）。
- psutil による優先度設定は権限が必要になる場合があります（AccessDenied の場合は警告ログを出してスキップします）。
- DuckDB への書き込みや executemany の挙動はバージョンに依存することがあるため、DuckDB のバージョン互換性に注意してください。
- monitoring は基本的に永続 DB にログを書きます。運用時はバックアップ・容量監視を行ってください。

---

必要でしたら README に含めるサンプル .env.example、requirements.txt、デプロイ手順（systemd ユニットやコンテナ化）なども追加で作成します。どの情報を詳しく書き足すか指示してください。