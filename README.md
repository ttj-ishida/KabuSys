# KabuSys — 日本株自動売買システム (README)

本リポジトリは日本株向けの自動売買および関連ツール群をまとめたライブラリ/アプリケーションです。  
主に以下の機能を持ち、実運用・検証・リサーチの各フェーズで利用できるよう設計されています。

- 注文発行・状態管理（ExecutionEngine / OrderManager）
- 監視・アラート（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築ロジック（候補選定・重み付け・株数算出）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- ニュース NLP による銘柄センチメント（OpenAI を利用した ai_scores）
- レジーム判定（市場レジームの合成指標）
- Paper Trading 用の分離 DB と検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

以下にセットアップ方法、実行例、ディレクトリ構成などを記載します。

---

## 機能一覧（主なもの）

- Execution
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - OrderManager / Reconciler / RiskManager などの発注・復旧ロジック
  - Paper Trading モード（KABUSYS_ENV=paper_trading）時は MockBroker を利用して本番 DB と分離
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - SQLite に監視ログ保存（monitoring.db）
  - kill.flag による ExecutionEngine 停止（KillSwitch）
  - streamlit によるダッシュボード: src/kabusys/monitoring/streamlit_dashboard.py
- Research / Data
  - DuckDB を用いた prices_daily / raw_financials に対する各種ファクター計算
  - feature_exploration（IC 計算、統計サマリ等）
- AI
  - news_nlp.score_news: ニュース記事を OpenAI でスコア化して ai_scores に書き込む
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して市場レジーム判定
- Tools
  - Paper Trading 検証レポート: src/kabusys/tools/paper_verification_report.py

---

## 前提 / 必要環境

- Python 3.9+
- 依存ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
  - その他標準ライブラリ

（requirements.txt は本リポジトリに含まれていない場合があるため、上記を pip でインストールしてください。）

例:
```
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数 / .env

アプリケーションは環境変数とプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化）。自動読み込みは .git または pyproject.toml を基準にプロジェクトルートを探します。

主に利用する環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必須）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- PAPER_FILL_MODE — paper_trading 時のモック約定挙動（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート送信用の LINE Messaging API 設定

簡単な .env の例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   （必要に応じて他の依存を追加）
4. .env を作成して必要な環境変数を設定（.env.example を参考に）
5. data ディレクトリを作成
   - mkdir -p data
   - 実行中に .pid や .flag が data 配下に作成されます

注:
- 自動で DB スキーマを初期化する処理（init_monitoring_db）が run_* スクリプト内で呼ばれるため、特別なマイグレーション作業は基本不要です。

---

## 使い方（実行例）

### 監視ループの起動（Monitoring）
監視プロセスをポーリングで実行します。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。

```
python -m kabusys.run_monitoring
# または
python src/kabusys/run_monitoring.py
```

- 停止: data/stop_requested.flag を作成すると監視ループは検知して終了します。
- MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

監視は本番の sqlite_path を使用します（KABUSYS_ENV に関係なく同一の監視 DB を使う実装です）。

### ExecutionEngine 起動（発注エンジン）
実際の発注エンジンを起動します。Paper Trading（KABUSYS_ENV=paper_trading）時は MockBroker を使い、paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。

```
python -m kabusys.run_execution
# または
python src/kabusys/run_execution.py
```

- 起動時に data/execution.pid を書きます（pid ファイルの場所は PID_FILE_PATH）。
- 停止: data/stop_requested.flag を作成するとエンジン停止処理が走ります。
- Paper Trading: export KABUSYS_ENV=paper_trading

### Streamlit ダッシュボード
監視結果を可視化する簡易ダッシュボードです。

```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

dashboad は監視データベースを読取専用で開きます（起動中の MonitoringEngine がデータを書きます）。

### Paper Trading 検証レポート
paper_trading DB に記録されたトレードログを集計してレポートを出力します。

```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# 別 DB を指定する場合:
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

出力は標準出力に整形された検証レポートを表示します。

### AI 関連（プログラムから呼び出す）
- ニューススコアの実行: kabusys.ai.score_news(conn, target_date, api_key=None)
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

どちらも OpenAI API キー（OPENAI_API_KEY）を環境変数に設定するか、api_key 引数で渡してください。

---

## 停止・制御フラグ

- data/stop_requested.flag — run_monitoring.py / run_execution.py がループで監視する停止フラグ。作成するとプロセスは終了処理を行います（冪等的）。
- data/kill.flag — KillSwitch が閾値超過で書き込む。ExecutionEngine 停止用のシグナルとして利用します（KillSwitch.write により作成）。

ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定しておくと、起動時に既存の kill.flag を自動で削除する設定が利用可能です（Settings.kill_flag_clear_on_start）。

---

## 注意点 / 運用メモ

- process_priority: run_* スクリプトは起動時に set_process_priority("high") を試みます。権限不足などで失敗する場合は警告が出ます（psutil 使用）。
- Paper Trading は本番 DB と分離するよう設計されています。KABUSYS_ENV=paper_trading を利用してください。
- OpenAI 呼び出しは外部 API に依存するため、レート制限やネットワーク障害を考慮したリトライ実装が入っていますが、API キーは厳重に管理してください。
- DuckDB / SQLite の接続はファイル単位で扱われます。運用時はバックアップやローテーションを検討してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化ユーティリティ
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — LINE 通知
  - kill_switch.py — kill.flag 書き込みロジック
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py 等 — 発注周りの実装
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- research/
  - factor_research.py, feature_exploration.py — ファクター計算・解析
- ai/
  - news_nlp.py — ニュース NLU スコアリング
  - regime_detector.py — 市場レジーム判定
- data/ (実行時生成・使用)
  - monitoring.db (デフォルト) / paper_trading.db / kabusys.duckdb / *.pid / *.flag

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## 開発・テストのヒント

- 環境変数ロードを無効化してテストしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出し関数はモジュール内部で分離されており、テスト時は該当関数をモックできます（例: unittest.mock.patch）。
- MonitoringDB.init_monitoring_db は冪等で、既存 DB に不足カラムがあれば簡単なマイグレーション（ALTER TABLE ADD COLUMN）を行います。

---

必要に応じて README に追記します。特定の起動方法（systemd / Docker / コンテナ化）や CI 設定などを追加したい場合は要件を教えてください。