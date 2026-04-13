# KabuSys

日本株自動売買システムの軽量コンポーネント群（ライブラリ + 実行スクリプト群）

このリポジトリは、注文管理・実行エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI を使ったニュース NLP などの機能を持つモジュール群を提供します。設計は「本番 DB と Paper Trading を分離」「ルックアヘッドバイアス対策」「フェイルセーフ重視（API失敗時は安全側で継続）」を重視しています。

主要機能や実行スクリプトの概要は以下を参照してください。

## 主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker client の抽象化と Factory（本番/モック切替）
  - OrderManager / OrderRepository による注文状態管理
  - Reconciler による起動時のリコンシリエーション（ブローカーとの突合）
  - RiskManager によるポジション・利用率等のリスク制御（設定あり）
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス存在チェック、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: フラグファイルを書いて ExecutionEngine を安全停止させる仕組み
  - AlertManager: LINE Push API によるアラート送信（クールダウン管理）
  - MonitoringEngine / run_monitoring.py によるポーリング実行
  - Streamlit ダッシュボード（簡易可視化）
- Portfolio construction
  - 候補選定、等金額/スコア重み、セクター制限、レジーム乗数、株数決定（単元丸め、aggregate cap）
- Research
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）
  - news_nlp: ニュースを LLM（gpt-4o-mini 想定）でセンチメント化して ai_scores に格納
  - regime_detector: ETF（1321）MA200 とマクロニュースを合成して日次レジーム判定
- ツール
  - paper_verification_report: Paper Trading のログ（SQLite）から検証レポートを生成

---

## 要件（開発・実行環境）
- Python 3.10 以上（型ヒントに | を使用しているため）
- ライブラリ（主要）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- 標準ライブラリ: sqlite3, logging, argparse など

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（プロジェクトに requirements.txt があればそちらを使用してください）

---

## 簡単セットアップ手順
1. リポジトリをクローン／配置
2. 仮想環境を作成して依存をインストール（上記参照）
3. 必要なディレクトリを作成
   ```bash
   mkdir -p data
   ```
4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし OS 環境変数が優先）。
   - 自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
5. 代表的な環境変数（.env 例）
   ```
   KABUSYS_ENV=development          # development | paper_trading | live
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   MONITOR_POLL_INTERVAL=60        # run_monitoring のポーリング間隔（秒）
   ```

6. DB 初期化
   - 実行スクリプトは起動時に必要な monitoring テーブルを冪等に初期化します（init_monitoring_db を内部で呼ぶ）。
   - DuckDB / SQLite のデータファイルはデフォルトで `data/` 配下に作成されます。

---

## 実行方法（代表的なコマンド）

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV で切替）
  ```bash
  # Paper Trading（MockBroker を使用）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution

  # Live / development
  export KABUSYS_ENV=live
  python -m kabusys.run_execution
  ```

  注意:
  - KABUSYS_ENV=paper_trading の場合、Execution は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離して動作します。
  - 起動時にプロセス優先度を `high` に設定しようとします（プラットフォームにより成功しない場合は警告が出ます）。

- Monitoring を起動（ポーリング監視）
  ```bash
  # 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で上書き可能（デフォルト 60 秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  動作:
  - SystemMonitor / TradeMonitor / RiskMonitor を用いて定期チェックを行い、SQLite（monitoring.db）へログを残します。
  - 監視は KABUSYS_ENV に関係なく本番用の sqlite_path を使用します（監視ログは本番 DB を想定）。

- Streamlit 監視ダッシュボード起動
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポートの生成
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

---

## 設定と挙動のポイント
- 自動 .env ロード
  - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索します。
  - .env（優先度低）→ .env.local（優先度高）を読み込み、既に OS 環境変数にあるキーは保護されます。
  - 自動ロードを停止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- 環境モード
  - KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれかでなければなりません。
  - Paper Trading はブローカー呼び出しをモックに差し替え、専用 SQLite を使用して本番 DB と分離します。

- プロセス優先度・CPU Affinity
  - 起動スクリプトは最初に set_process_priority("high") を呼び出します。プラットフォーム依存で動作します（psutil を利用）。
  - 設定に失敗した場合は警告としてスキップされます。

- Kill Switch / PID
  - ExecutionEngine 用の PID ファイル（デフォルト data/execution.pid）を監視し、stale PID を検出すると警告＋削除します。
  - RiskMonitor のしきい値を超えた場合、KillSwitch が `data/kill.flag` を書き込み Execution を停止する仕組みがあります。`KILL_FLAG_CLEAR_ON_START` により起動時にフラグをクリアする挙動を制御できます。

---

## API キー / 機密情報（主な環境変数）
- OPENAI_API_KEY: OpenAI API を使う機能（news_nlp, regime_detector）で必要
- JQUANTS_REFRESH_TOKEN: J-Quants API（リサーチ等）で使用
- KABU_API_PASSWORD / KABU_API_BASE_URL: kabuステーション API の認証情報
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）用
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行制御関連ファイルパス
- PAPER_FILL_MODE: Paper Trading の模擬約定モード（instant/partial/never/reject）

---

## ディレクトリ構成（主要ファイル）
以下は主要モジュールを抜粋した構成です（src/kabusys 配下）。

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / 設定管理
    - run_execution.py                 — ExecutionEngine 起動スクリプト
    - run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py                    — ニュース NLP / OpenAI バッチ処理
      - regime_detector.py             — 市場レジーム判定（MA200 + マクロニュース）
    - execution/
      - order_manager.py
      - reconciler.py
      - order_repository.py
      - order_record.py
      - broker_factory.py
      - broker_api.py
      - execution_engine.py
      - risk_manager.py
      - ...                            （発注関連コンポーネント）
    - monitoring/
      - __init__.py
      - monitoring_db.py               — SQLite 永続化層（テーブル初期化含む）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py         — streamlit ダッシュボード
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - tools/
      - __init__.py
      - paper_verification_report.py    — Paper Trading 検証レポート生成
    - data/
      - pipeline.py (参照される想定)
    - utils/
      - __init__.py
      - process_priority.py

（実際のリポジトリには上記以外の補助モジュールやテスト・マイグレーション等のファイルが存在する可能性があります）

---

## 使い方の例（ワークフロー）
1. 環境を整え、.env に必要なキーをセットする
2. 監視プロセスを常時稼働させる
   - `python -m kabusys.run_monitoring`（MONITOR_POLL_INTERVAL で間隔調整）
3. ExecutionEngine を別プロセスで起動
   - `python -m kabusys.run_execution`（KABUSYS_ENV により paper/live を切り替え）
4. 動作確認
   - Streamlit ダッシュボードや paper_verification_report でログ・統計を確認
5. Paper Trading の検証
   - Paper Trading を実行 → ログ（data/paper_trading.db）からレポート生成

---

## 開発 / テストにおける注意点
- DuckDB / SQLite テーブルスキーマやマイグレーションは monitoring_db.init_monitoring_db により冪等的に初期化・更新されます。
- LLM 呼び出し部分（OpenAI）はリトライやフェイルセーフを持っていますが、API キーの設定・レート制限に注意してください。
- 実機での稼働（live）時は取引 API の資格情報および取引リスク管理設定を慎重に調整してください（RiskManager の設定など）。
- Paper Trading モードは本番 DB と分離されますが、設定ミスに注意してください（PAPER_TRADING_SQLITE_PATH を確認）。

---

必要であれば、README をベースに「デプロイ手順」「Systemd ユニット例」「docker-compose 例」「CI テストの書き方」などの追加ドキュメントも作成します。どの情報を優先して追加しますか？