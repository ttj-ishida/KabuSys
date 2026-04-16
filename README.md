# KabuSys

日本株自動売買システムの軽量モジュール群（ライブラリ／起動スクリプト／監視ツール類）。  
この README はコードベースに含まれる主要コンポーネントの概要・セットアップ・使い方・ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は以下の機能を持つ自動売買プラットフォームのコンポーネント群です（実運用のための要素を想定した設計）：

- 注文管理（OrderManager / ExecutionEngine）
- 発注・ブローカー連携（Broker クライアント抽象化、Paper Trading 用モック）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- 監視ログ永続化（SQLite）
- 監視ダッシュボード（Streamlit）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量解析）
- ニュース NLP（OpenAI を用いたニュースセンチメント）
- レジーム判定（ETF MA と LLM を合成）
- 検証ツール（Paper Trading 検証レポート生成）

設計上の特徴：
- DuckDB / SQLite を用いたデータ層
- 環境切替（development / paper_trading / live）
- Paper Trading は本番 DB と完全分離（専用 SQLite）
- LLM 呼び出しはフェイルセーフ（API失敗時はスキップ或いはフォールバック）
- プロセス優先度設定や kill/stop フラグによる外部停止制御をサポート

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager / Reconciler（注文同期 / 再起動後リコンシリエーション）
  - RiskManager（ポジション上限・利用率など）

- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク / プロセス生存・データ鮮度）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン・ポジション上限検出）
  - KillSwitch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
  - AlertManager（LINE へのプッシュ通知）
  - MonitoringEngine（上記を束ねたポーリングループ）
  - Streamlit ダッシュボード（監視データ可視化）

- Research / Portfolio
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・特徴量サマリ
  - 候補選定、重み計算、単元株丸めを含むポジションサイズ計算
  - セクター制約、レジーム乗数

- AI
  - ニュースセンチメント（OpenAI を使った銘柄別スコア、ai_scores テーブルへ書き込み）
  - レジーム判定（ETF MA200 とマクロセンチメントの合成）

- Tools
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## 動作要件（例）

以下は本リポジトリで使われている主要パッケージ（バージョンは目安／環境に合わせて調整してください）：

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)
- sqlite3（標準ライブラリ）
- その他：logging, pathlib, threading など標準ライブラリ

pip でのインストール例（requirements.txt がない場合の参考）:
```bash
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン／展開する。

2. 仮想環境を作成して依存パッケージをインストールする（上記参照）。

3. プロジェクトルートに .env（または .env.local）を配置して環境変数を設定する（下記参照）。自動読み込みはデフォルトで有効。テスト等で自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. data ディレクトリを作成（必要に応じて）:
```bash
mkdir -p data
```

5. Paper Trading を使う場合は（任意） paper DB を作成／用意：
- デフォルトパス: data/paper_trading.db
- Monitoring DB（本番監視用）デフォルト: data/monitoring.db
- DuckDB データファイルデフォルト: data/kabusys.duckdb

6. 必須の環境変数（運用に必要なもの）:
- JQUANTS_REFRESH_TOKEN（J-Quants API）
- KABU_API_PASSWORD（kabuステーション API）
- OPENAI_API_KEY（AI 機能を使う場合）
必要に応じて LINE の通知用変数なども設定します（下記「環境変数一覧」参照）。

---

## 環境変数（主なもの）

このプロジェクトは .env / .env.local から環境変数を自動で読み込みます（OS 環境変数優先）。重要な変数：

- KABUSYS_ENV: 起動環境（development / paper_trading / live）デフォルト: development
  - paper_trading の場合、run_execution は MockBrokerClient を使用し、paper_trading 用 SQLite を利用
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuAPI パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定なら送信はスキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグ（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
- CPU / MEMORY / DISK 閾値: CPU_THRESHOLD_PCT 等（Settings により参照）

設定ファイルのパースは `kabusys.config` モジュールに実装されています。`.env` は `.git` または `pyproject.toml` のある親ディレクトリをプロジェクトルートとして探索して自動読込します。

---

## 使い方

### 1) 監視プロセスの起動（Monitoring）
監視専用のポーリングループを起動します（Monitoring は常に本番の sqlite_path を使います）:

```bash
python -m kabusys.run_monitoring
```

- ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
- 停止はプロジェクトルートの `data/stop_requested.flag` を作成すると検知して終了します。

### 2) 実行エンジンの起動（Execution）
ExecutionEngine（発注エンジン）を起動します:

```bash
python -m kabusys.run_execution
```

- `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を用い `data/paper_trading.db` に書き込みます（本番 DB と完全分離）。
- 実行中に `data/stop_requested.flag` を作成するとエンジンを停止します。
- 起動時に `data/kill.flag` が既に存在する場合は起動をスキップします（安全措置）。

### 3) Paper Trading 検証レポート生成ツール
Paper Trading DB を解析して検証レポートを生成します：

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# デフォルト DB は data/paper_trading.db。--db で別パス指定可能。
```

主要チェック：
- 稼働率（uptime）
- 注文成功率 / 送信率
- レイテンシ（平均 / P95）
- リスク却下数 等

### 4) 監視ダッシュボード（Streamlit）
監視結果を可視化します（Monitoring DB を読み取り専用で開きます）:

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- DB が存在しない／開けないとエラー表示されます（MonitoringEngine の起動が前提）。

### 5) AI 関連関数の実行（プログラム経由）
コード内 API を直接呼ぶ例：

- ニュースの銘柄別スコアリング:
  - `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`  
    (DuckDB 接続を渡し、戻り値は書き込み件数。api_key を None にすると環境変数 OPENAI_API_KEY を使用)

- レジーム判定:
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

両者とも API キーが未設定だと ValueError を送出します。

---

## 管理ファイル（停止 / キルフラグ）

- data/stop_requested.flag — run_monitoring / run_execution が監視している停止フラグ（存在したら終了）。
- data/execution.pid — ExecutionEngine の PID（存在チェックでプロセス生存を確認）。
- data/kill.flag — KillSwitch が条件を満たした際に書き込まれるファイル。ExecutionEngine の起動時にクリアするオプションあり。

---

## トラブルシューティング（よくある事象）

- psutil の優先度設定で権限不足が出る:
  - ログに警告が出て処理は継続します。必要なら実行ユーザーの権限を確認してください。

- OpenAI API 呼び出しの失敗:
  - rate-limit / ネットワークエラー / 5xx はエクスポネンシャルバックオフで再試行しますが、最終的に取得できない場合はフォールバック（多くの箇所で 0.0 やスキップ）します。API キーとレート制限を確認してください。

- Streamlit が DB を開けない:
  - MonitoringEngine を起動して `data/monitoring.db` が存在するか確認、権限（読み取り）も確認してください。dashboard は DB を read-only で開きます。

- 設定ファイルが読み込まれない:
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml が存在する場所）を基準に行います。動作させたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の代表的なモジュールと役割です（抜粋）。

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数／Settings)
  - run_monitoring.py (SystemMonitor ポーリングループ起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)
- src/kabusys/monitoring/
  - monitoring_db.py (SQLite スキーマ初期化・永続化クラス MonitoringDB)
  - system_monitor.py (システム状態・データ鮮度監視)
  - trade_monitor.py (滞留注文・約定異常監視)
  - risk_monitor.py (ドローダウン・ポジション上限の監視)
  - kill_switch.py (kill.flag 書き込みロジック)
  - alert_manager.py (LINE 通知)
  - monitoring_engine.py (各 Monitor を束ねる)
  - streamlit_dashboard.py (Streamlit ダッシュボード)
- src/kabusys/execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py (エンジン本体)
  - broker_factory.py / broker_api.py（ブローカー抽象）
- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/
  - news_nlp.py (ニュース NLP スコアリング)
  - regime_detector.py (レジーム判定)
- src/kabusys/tools/
  - paper_verification_report.py (Paper Trading 検証レポート生成)

（上記は抜粋です。リポジトリの全ファイルを参照してください。）

---

## 開発メモ / 設計上の注意点

- Settings は .env/.env.local を自動読み込みします。OS 環境変数は保護され、.env.local は上書きされます。
- Paper Trading モードは本番と DB を分離する設計になっています（安全）。
- LLM 呼び出しは外部サービス依存があるためフェイルセーフ（失敗時はスキップやゼロフォールバック）で設計されています。
- Monitoring の DB マイグレーションは init_monitoring_db() が冪等に行うため、初回起動時の DB 作成やカラム追加が自動化されています。
- プロセス優先度設定・CPU affinity 設定は psutil を経由して行います。環境により権限不足でスキップされることがあります。

---

## よく使うコマンドまとめ

- 監視開始:
  - python -m kabusys.run_monitoring
- 実行エンジン開始:
  - python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

質問や追加のドキュメント化（各モジュールの詳細な API ドキュメントやシーケンスフロー、DB スキーマ詳細など）が必要であれば、目的に合わせて追記します。