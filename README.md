# KabuSys

日本株自動売買システムの一部（監視 / 実行エンジン / ポートフォリオ構築 / リサーチ / AI 補助）を含むコードベースの README（日本語）。

以下はこのリポジトリに含まれる主要な機能、セットアップ、起動方法、およびディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な責務は次の通りです。

- シグナルに基づく発注（ExecutionEngine）
- 発注・約定の整合性チェック（Reconciler / OrderManager）
- リスク管理（RiskManager / RiskMonitor）
- システム監視（SystemMonitor / MonitoringEngine）
- 監視データの永続化（SQLite）
- 財務・価格データを使ったファクター計算・リサーチ（DuckDB）
- ニュースを LLM（OpenAI）でスコアリングして意思決定に活用（news_nlp / regime_detector）
- 監視用の Streamlit ダッシュボード

設計方針の特徴：
- DuckDB / SQLite を用いたローカル DB ベースの分析と監視
- 環境変数 / .env による設定管理（自動ロード）
- Paper trading（モックブローカー）を用いた本番分離
- OpenAI を用いたニュースセンチメント / マクロ判定（失敗時はフェイルセーフ）

---

## 機能一覧（抜粋）

- Execution
  - Signal Queue ベースの発注フロー
  - OrderManager による二相永続化設計（OrderSent 前後のクラッシュ耐性）
  - Reconciler による起動時の注文/ポジション同期
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス監視、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件を満たしたら flag ファイルを書き ExecutionEngine 停止シグナルを送る
  - AlertManager：LINE Push による通知（クールダウン管理）
  - MonitoringEngine：上記モニタのポーリング統合
  - Streamlit ダッシュボード（監視 DB の可視化）
- Portfolio
  - 候補選定 / 重み計算（等金額・スコア加重）
  - セクターキャップ適用 / レジーム乗数
  - 株数決定（リスクベース・重量ベース）、単元株丸め、aggregate cap 適用
- Research
  - ファクター計算（Momentum / Value / Volatility など）
  - 将来リターン計算・IC（情報係数）・統計サマリ
- AI
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、銘柄ごとのスコアを ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）の MA200 差分とマクロニュースの LLM 結果を合成して市場レジーム判定

---

## 事前準備（セットアップ）

1. リポジトリをクローン／取得し、作業環境に移動

2. Python 仮想環境の作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール（プロジェクトに requirements.txt がない場合、最低限以下が必要）
   - duckdb
   - psutil
   - requests
   - streamlit
   - openai
   例:
   ```
   pip install duckdb psutil requests streamlit openai
   ```

4. 環境変数の設定
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV: 実行環境（`development` | `paper_trading` | `live`、デフォルト `development`）
   - LOG_LEVEL: ログレベル（`DEBUG` / `INFO` / ...）
   - SQLITE_PATH: 監視 DB パス（デフォルト `data/monitoring.db`）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（`paper_trading` 環境で使用、デフォルト `data/paper_trading.db`）
   - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト `data/execution.pid`）
   - KILL_FLAG_PATH: kill.flag のパス（デフォルト `data/kill.flag`）
   - PAPER_FILL_MODE: paper_trading の Fill 動作（`instant` | `partial` | `never` | `reject`、デフォルト `instant`）

---

## 起動 / 使い方

以下は主要スクリプトの実行例です。パッケージとしてインストールされていない場合は、リポジトリのルートから `python` を使ってスクリプトを直接実行できます。

注意：実行前に .env を準備し、必須の環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD など）を設定してください。

1. Monitoring（監視ポーリング）を起動
   - スクリプト: `src/kabusys/run_monitoring.py`
   - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒単位に上書き可能（デフォルト 60 秒）
   - 実行:
     ```
     python src/kabusys/run_monitoring.py
     ```
   - 特徴:
     - Monitoring は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用します（監視は実 DB に対して行う想定）。
     - 起動時にプロセス優先度を "high" に設定します（可能な範囲で）。

2. Execution（発注エンジン）を起動
   - スクリプト: `src/kabusys/run_execution.py`
   - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（`data/paper_trading.db`）に記録します。本番 DB とは分離されます。
   - 実行:
     ```
     python src/kabusys/run_execution.py
     ```
   - 起動時に PID ファイル（デフォルト `data/execution.pid`）を書きます。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に `kill.flag` をクリアします。

3. Streamlit ダッシュボード（監視データ可視化）
   - ファイル: `src/kabusys/monitoring/streamlit_dashboard.py`
   - 起動例:
     ```
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     ```
   - ダッシュボードは監視 DB を読み取り専用で開きます（URI に `?mode=ro` が付与されます）。

4. AI 関連（ニューススコア / レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡して実行すると、ai_scores テーブルへ書き込みます。
     - OpenAI API キーは引数か環境変数 `OPENAI_API_KEY` を使用します。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - DuckDB 接続を渡して市場レジームを計算・保存します。
   - これらはモジュール関数なのでスクリプトは別途作成して呼び出すか、REPL/スクリプトでインポートして利用してください。
   - 例（簡易）:
     ```py
     import duckdb
     from datetime import date
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect('data/kabusys.duckdb')
     score_news(conn, date(2026, 3, 20), api_key='sk-...')
     ```

5. 環境変数による微調整
   - `MONITOR_POLL_INTERVAL`：監視ループのポーリング間隔（秒）
   - `KABUSYS_ENV`：`development` / `paper_trading` / `live`
     - `paper_trading` → MockBroker + separate SQLite（PAPER_TRADING_SQLITE_PATH）
     - `live` → 本番向け挙動（実ブローカーなど）
   - `KILL_FLAG_PATH`：KillSwitch が書き込むファイル。ExecutionEngine はこれを検出して安全停止します。

---

## 重要な実行時の挙動メモ

- Monitoring は常に（KABUSYS_ENV にかかわらず）本番の `sqlite_path` を使って監視データを記録します。監視 DB は `init_monitoring_db()` でテーブルを冪等に作成します。
- ExecutionEngine は PID ファイル（デフォルト `data/execution.pid`）を用いてプロセスの生存を示します。SystemMonitor は PID ファイルを見てプロセスが存在しない場合に stale PID を検出して削除します。
- KillSwitch は条件（ドローダウン超過やポジション上限超過）を満たすと `kill.flag` を書き、ExecutionEngine の起動・ループ中に検出されると安全停止を試みます。
- OpenAI 呼び出しは外部 API を使うため、失敗時はフォールバック（スコア 0.0 など）してフェイルセーフに動作する設計です。ただし API キーの管理には注意してください。

---

## 簡単な .env 例（最低限）

ルートに `.env` を置く例:
```
KABUSYS_ENV=development
LOG_LEVEL=INFO
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
```

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定読み込み（.env 自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 用分離対応）
  - execution/
    - execution_engine.py — ExecutionEngine（シグナル処理 + push ドレイン）
    - order_manager.py — 発注の高レベル制御（Order State Machine の外向き API）
    - order_repository.py —（存在する想定）SQLite の注文永続化層
    - reconciler.py — 起動時の注文/ポジション整合性回復
    - risk_manager.py — 実行時の Gate チェックなど（RiskConfig）
    - broker_factory.py / broker_api.py — ブローカークライアント生成・API 抽象
  - monitoring/
    - monitoring_db.py — SQLite スキーマ定義と読み書きラッパー（MonitoringDB）
    - system_monitor.py — システム状態 / データ鮮度のチェック
    - trade_monitor.py — 注文滞留・約定異常の検出
    - risk_monitor.py — ドローダウン・ポジション上限の監視
    - kill_switch.py — kill.flag の書き込み/管理
    - alert_manager.py — LINE Push による通知（クールダウン管理）
    - monitoring_engine.py — 各 Monitor を統合して定期実行
    - streamlit_dashboard.py — 監視データ可視化用 Streamlit アプリ
  - portfolio/
    - portfolio_builder.py — 候補選定 / スコア順ソート
    - risk_adjustment.py — セクターキャップ / レジーム乗数
    - position_sizing.py — 株数決定ロジック（リスクベース等）
  - research/
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリなど
  - ai/
    - news_nlp.py — raw_news を集約して OpenAI へ投げ、ai_scores テーブルへ書き込み
    - regime_detector.py — MA200 とマクロニュースを合成して market_regime を算出
  - data/ (想定されるデータフォルダ, デフォルト)
    - kabusys.duckdb (DuckDB)
    - monitoring.db (SQLite)
    - paper_trading.db (paper_trading 用 SQLite)
    - execution.pid / kill.flag（PID と停止フラグ）

（注）一部ファイルはここに掲載されているモジュールに依存する外部実装（例: order_repository.py の完全版、broker 実装など）が存在する想定です。

---

## テスト・デバッグのヒント

- 設定の自動読み込みを止めたいときは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してテスト環境で明示的に環境をセットアップしてください。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くので、MonitoringEngine を先に起動してデータを投入してから確認してください。
- OpenAI の呼び出し部分は関数単位でラップされており、テスト時には該当関数（news_nlp._call_openai_api / regime_detector._call_openai_api）をモックすることを想定しています。
- `MONITOR_POLL_INTERVAL` は整数秒を期待します。不正な値や 0 以下は警告されデフォルト（60秒）にフォールバックします。

---

## ライセンス / 貢献

本 README はコードベースの理解を目的とした要約です。実運用へ移す際はブローカー API 認証・取引リスク・法的要件・セキュリティ（API キー管理）などを十分に確認してください。

貢献や不具合報告はリポジトリの issue / PR を通じて行ってください。

---

必要であれば、README に含めるコマンド例（systemd サービス定義、Dockerfile、requirements.txt のサンプル）や各モジュールの詳細な API ドキュメントを追記します。どの部分を詳しく出力しましょうか？