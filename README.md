# KabuSys

日本株自動売買システムの軽量モジュール群（監視・発注・ポートフォリオ構築・リサーチ・AI 補助）。  
この README はコードベース（src/kabusys 以下）を元に作成しています。

## プロジェクト概要
KabuSys は日本株の自動売買に関するコアロジックと運用周辺機能を集めたライブラリ兼実行スクリプト群です。主な目的は以下です。

- 注文・発注フローの管理（OrderManager / ExecutionEngine）
- ExecutionEngine の監視と運用停止（Monitoring, KillSwitch, AlertManager）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- リサーチ (ファクター計算・特徴量探索)
- AI を使ったニュースセンチメント評価と市場レジーム判定
- Paper Trading 用の分離 DB と検証レポート生成
- Streamlit を用いた監視ダッシュボード

本リポジトリはライブラリとしてもモジュール単位での CLI 実行にも対応しています。

---

## 機能一覧
主な機能（モジュール別）

- 実行 / 発注
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading では MockBroker を使用）
  - execution/*.py: ブローカー接続、注文管理、リコンシリエーション等

- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ開始スクリプト
  - monitoring/*: SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringDB（SQLite）
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード

- ポートフォリオ構築
  - portfolio/*: 候補選定、重み付け、セクター制限、ポジションサイズ計算

- リサーチ
  - research/*: ファクター計算（モメンタム・ボラティリティ・バリュー）、IC/統計解析ユーティリティ

- AI（OpenAI）
  - ai/news_nlp.py: ニュースを LLM でスコアリングして ai_scores に書き込み
  - ai/regime_detector.py: MA200 とマクロニュースで市場レジーム判定

- ユーティリティ
  - config.py: 環境変数 / .env 読み込み、Settings クラス
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成

---

## セットアップ手順（ローカル開発向け）
以下は一般的なセットアップ手順です。プロジェクトに requirements.txt がある前提での例を示します（存在しない場合は必要なパッケージを適宜インストールしてください）。

1. Python 仮想環境を作成・有効化（例: Python 3.10+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 必要パッケージ（主なもの）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit

3. プロジェクトルートに .env を配置（.env.example を参考に作成）
   - config.Settings が自動で .env を読み込みます（プロジェクトルートは .git または pyproject.toml を探して決定）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 主要な環境変数（Settings 参照）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート送信)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動
     - PID_FILE_PATH, KILL_FLAG_PATH 等
     - KABUSYS_ENV: development | paper_trading | live
     - LOG_LEVEL

   例 (.env):
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. データディレクトリ作成
   - mkdir -p data

6. 初回 DB 初期化
   - run_monitoring / run_execution を起動すると MonitoringDB テーブルは自動作成されます（init_monitoring_db により冪等に作成・マイグレーション）。

---

## 使い方（実行例）
以下は主要なスクリプト／コマンドの実行方法です。プロジェクトをパッケージとして扱うため、インタプリタからモジュールを実行します。

- ExecutionEngine を起動（本番または paper_trading）
  - KABUSYS_ENV を切り替えることで paper_trading モードが有効になります（paper では MockBroker を使用し DB を data/paper_trading.db に記録）。
  - 例（本番/開発）:
    - python -m kabusys.run_execution
  - 例（Paper Trading）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring を起動（SystemMonitor のポーリング）
  - ポーリング間隔は環境変数で調整可能（MONITOR_POLL_INTERVAL、秒。デフォルト: 60）
  - python -m kabusys.run_monitoring
  - 例（30秒間隔）:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - 日付指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI スコアリング / レジーム判定（ライブラリ API）
  - Python から呼び出して利用可能:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

- 注意点
  - run_execution は起動時にプロセス優先度を "high" に設定しようとします（psutil 権限により失敗する場合は警告）。
  - kill.flag（Settings.kill_flag_path）を用いた停止シグナルに対応。KillSwitch が書き込むと ExecutionEngine 停止を促します。

---

## 主要な設定項目（Settings まとめ）
config.Settings に定義されている主な環境変数一覧（一部）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意)
- OPENAI_API_KEY (AI 機能で必須)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (AlertManager)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject)
- PID_FILE_PATH (デフォルト data/execution.pid)
- KILL_FLAG_PATH (デフォルト data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (1|0)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|...)

---

## ディレクトリ構成（抜粋）
（ルートは src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite ベースの監視ログ永続化
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留 / 約定異常監視
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 制御
    - alert_manager.py        — LINE へのプッシュ通知
    - monitoring_engine.py    — 各モニタを束ねるループ（テスト用 run_once / run）
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - execution_engine.py
    - ...（ブローカー API / order_record 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py             — ニュースセンチメント評価（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA200 + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - data/                     — 既定のデータ格納先（READMEでは外部で作成）

---

## 運用上の注意 / ベストプラクティス
- Paper Trading と本番の DB は分離されています（Settings.paper_sqlite_path を参照）。
- run_execution/run_monitoring は PID ファイルを用いてプロセスの監視を行います。PID ファイル・kill.flag のパスは Settings で変更可能。
- AI 機能は OpenAI API を使います。API キーは環境変数 OPENAI_API_KEY で設定してください。API エラー時はフェイルセーフ（スコア 0.0 など）で継続する設計です。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- psutil による優先度設定や CPU affinity はプラットフォーム依存で権限が必要です。失敗時は警告を出してスキップします。

---

## 貢献 / テスト
- ユニットテスト・モックを組みやすいよう、外部 API 呼び出し（OpenAI 呼び出し等）はラップしており、テスト時にパッチ可能です（例: unittest.mock.patch）。
- DB 操作は冪等性を意識して設計されています（init_monitoring_db など）。
- 新機能や修正を行う場合は、既存の DB マイグレーションや外部 API のエラー処理を確認してください。

---

必要であれば、この README を基に環境ごとのセットアップ例（docker-compose、systemd ユニットファイル、requirements.txt、.env.example）や具体的な起動・運用手順を追記します。どの項目を優先して詳しくしたいか教えてください。