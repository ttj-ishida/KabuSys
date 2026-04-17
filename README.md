# KabuSys

日本株自動売買システムの実装（ライブラリ＋運用スクリプト群）の抜粋リポジトリ用 README（日本語）。

以下は本コードベースに含まれる主要機能、セットアップ方法、起動方法、ディレクトリ構成の概要です。

---

## プロジェクト概要

KabuSys は日本株用の自動売買プラットフォーム向けユーティリティ群です。  
主な機能は以下を含みます。

- 注文作成・管理（ExecutionEngine 周りのコンポーネント）
- 監視（System / Trade / Risk モニタリング、アラート、Kill Switch）
- ポートフォリオ構築ロジック（候補選定・比率計算・ポジションサイズ算出）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- AI 支援（ニュースセンチメント / 市場レジーム判定：OpenAI を利用）
- 運用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計上のポイント:
- DuckDB / SQLite をデータ層に利用（prices_daily 等は DuckDB、監視ログは SQLite）
- 設定は環境変数（.env / .env.local を自動読み込み）で管理
- Paper trading は本番 DB と明確に分離（専用 SQLite ファイル）
- LLM 関連処理は失敗に寛容（API失敗時はフォールバックして継続）

---

## 機能一覧（抜粋）

- Execution
  - OrderManager, Reconciler, RiskManager, ExecutionEngine（起動スクリプト: run_execution.py）
  - Paper Trading モードで MockBroker を使用し data/paper_trading.db に記録

- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
  - AlertManager（LINE API へのプッシュ通知）
  - MonitoringEngine / run_monitoring.py（ポーリングループ起動）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

- Portfolio（純粋関数）
  - 候補選定、等配分/スコア配分、セクター制限、ポジションサイズ計算

- Research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / 統計サマリー）

- AI（OpenAI）
  - news_nlp.score_news: raw_news を LLM でセンチメント評価して ai_scores に書き込み
  - regime_detector.score_regime: MA200 とマクロニュースの LLM 評価を合成して market_regime に書き込み

- Tools
  - tools/paper_verification_report.py: Paper Trading DB の実績を集計して検証レポート出力

---

## 前提 / 必要環境

- Python 3.10 以上（型注釈の `X | Y` を使用）
- OS: Linux / macOS / Windows（プロセス優先度設定などで差分あり）
- 必要な Python パッケージ（主なもの）
  - duckdb
  - psutil
  - requests
  - streamlit
  - openai
- SQLite（Python 標準ライブラリに含まれる）
- （任意）LINE Messaging API のチャネル設定（アラートを使う場合）
- （AI 機能を使う場合）OpenAI API キー

インストール例（仮の requirements がない場合）:
```bash
python -m pip install duckdb psutil requests streamlit openai
```

---

## 設定（環境変数）

設定は環境変数から読み込みます。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（デフォルト含む）:

- 基本
  - KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO

- API キー
  - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須の設定がある場合）
  - KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション API 用

- データベース / ファイルパス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用フラグ（デフォルト: data/kill.flag）

- Monitoring
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 閾値（%）

- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

注意:
- run_monitoring（監視）は KABUSYS_ENV にかかわらず Settings.sqlite_path（=デフォルト data/monitoring.db）を使用します（コード内の運用ポリシー）。
- run_execution は KABUSYS_ENV が `paper_trading` の場合に paper_sqlite_path（data/paper_trading.db）を使用して本番 DB と分離します。

---

## セットアップ / クイックスタート

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo-root>
```

2. 依存パッケージをインストール
```bash
python -m pip install -r requirements.txt   # もし requirements.txt がある場合
# または必要パッケージを個別に
python -m pip install duckdb psutil requests streamlit openai
```

3. .env を作成（.env.example を参考に必要な環境変数を設定）
例（最低限の例）:
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

4. 実行前準備
- データディレクトリを作成（自動で作られる処理もあるが明示的に作成可）
```bash
mkdir -p data
```

5. 実行方法は次項を参照

---

## 実行方法（主要スクリプト）

※ パッケージとしてインストールしていない場合、`src` を PYTHONPATH に含めるかプロジェクトルートから実行してください。

推奨: プロジェクトルートで以下を実行:
```bash
export PYTHONPATH=./src
```
（Windows PowerShell では `setx PYTHONPATH .\src` 等）

### 監視ループ（Monitoring）
- 起動スクリプト: src/kabusys/run_monitoring.py
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）

起動例:
```bash
export PYTHONPATH=./src
MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
```

停止:
- 監視ループはプロジェクトルートの `data/stop_requested.flag` の存在を検出すると終了します（手動で作成することで安全停止）。
- ExecutionEngine へ終了シグナルを送る場合は `data/kill.flag` を KillSwitch が書き込みます。

### Execution Engine（発注実行）
- 起動スクリプト: src/kabusys/run_execution.py
- Paper Trading モード: KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し data/paper_trading.db に記録

起動例:
```bash
export PYTHONPATH=./src
# 本番相当（設定に応じて）
python -m kabusys.run_execution

# Paper Trading
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

停止:
- `data/stop_requested.flag` の存在を検出してエンジン停止処理を行います。
- また KillSwitch による `data/kill.flag` 書き込みが行われると次回ループで検知し停止できます。

### Streamlit ダッシュボード（監視 UI）
起動:
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
オプション `--db` で読み込む SQLite パスを指定できます（既定は data/monitoring.db）。

### Paper Trading 検証レポート
ツール: src/kabusys/tools/paper_verification_report.py

実行例:
```bash
export PYTHONPATH=./src
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB 指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

### AI / Regime / News スコアリング（ライブラリ呼び出し）
コード上の関数を直接呼んで使用します（例: スクリプトから import して使用）。

- news_nlp.score_news(conn, target_date, api_key=None)
- regime_detector.score_regime(conn, target_date, api_key=None)

api_key を引数で渡すか、環境変数 `OPENAI_API_KEY` を設定してください。API 呼び出しの失敗はフォールバック（ゼロスコア）する実装です。

---

## 運用に関する注意点

- PID / フラグファイル
  - ExecutionEngine は起動時に PID ファイル（デフォルト data/execution.pid）を作成します。SystemMonitor はこの PID を参照してプロセスが生きているかを監視します。
  - 停止リクエストは `data/stop_requested.flag`（外部で作成）で行えます。KillSwitch は `data/kill.flag` を書き込み ExecutionEngine に停止指示を出します。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブルと一部カラムの追加（ALTER TABLE）を行います。初回実行で必要スキーマを準備します。

- Paper Trading
  - Paper Trading 時は本番 DB と完全に分離して `PAPER_TRADING_SQLITE_PATH` を使用します。`PAPER_FILL_MODE` によってモック約定挙動を制御できます。

- セキュリティ
  - API キー等は .env に保存する場合でも管理に注意してください。

---

## ディレクトリ構成（抜粋）

以下はこのコードベースで提供されている主なファイル・モジュール構成の抜粋です（src/kabusys 以下）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 execution 関連モジュール: broker_factory, execution_engine, order_repository, etc.)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/            (ランタイムに生成される想定)
      - monitoring.db (デフォルト)
      - paper_trading.db
      - kabusys.duckdb
      - execution.pid
      - kill.flag
      - stop_requested.flag

（上記は抜粋。実際のファイル一覧はリポジトリを参照してください）

---

## 開発者向けメモ

- Settings クラス（kabusys.config）により .env 自動読み込みが行われます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- process_priority.py はプラットフォーム差分（Windows / POSIX）を吸収しますが、権限不足等で設定に失敗する可能性があります（警告ログが出ます）。
- LLM 呼び出し部分（news_nlp, regime_detector）は API レート制限・一時エラー対処のためにリトライロジックがあります。テスト時は `_call_openai_api` をモックしてください。
- 監視／運用系はログを重視しています。運用時には LOG_LEVEL や LINE 通知設定を適切に行ってください。

---

## サポート / 参考

この README はコードベースの抜粋から作成しています。詳細な仕様（API インタフェース、ExecutionEngine の内部挙動、Broker 実装、Strategy ドキュメント等）は別途ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）を参照してください。

不明点・実行で問題が発生する場合は、実行ログを確認のうえ該当モジュール（例: monitoring.log、Streamlit 表示、STDOUT）を参照してください。