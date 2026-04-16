# KabuSys

日本株向け自動売買システムのコアライブラリ群と運用ツール群のサンプル実装です。  
このリポジトリは以下の主要要素を含みます：実行エンジン（ExecutionEngine）・発注管理、監視（Monitoring）・アラート、ポートフォリオ構築モジュール、リサーチ（ファクター計算）、AI を使ったニュース NLP / レジーム判定、運用ツール（レポート生成・Streamlit ダッシュボード）など。

---

## 主な特徴（機能一覧）

- Execution（発注）周り
  - OrderManager / OrderRepository を用いた注文ライフサイクル管理
  - ブローカークライアントの抽象化（実運用 / Paper Trading 切替）
  - Reconciler による起動時の注文・ポジション自動リコンシリエーション
  - リスク管理（RiskManager・ポジション・ドローダウン制御）

- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウンやポジション上限の監視
  - KillSwitch：閾値超過時に停止フラグ（data/kill.flag）を出力
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード

- Portfolio（ポートフォリオ構築）
  - 候補選定（スコア順ソート）
  - 等分配・スコア加重配分
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元丸め・aggregate cap）

- Research（リサーチ）
  - Momentum / Volatility / Value ファクター計算（DuckDB を利用した SQL 実装）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ

- AI（OpenAI 統合）
  - ニュース記事のセンチメント（ai_scores）生成（gpt-4o-mini を想定）
  - マクロニュース + ETF ma200 による市場レジーム判定（bull / neutral / bear）
  - API 呼び出しは再試行・バックオフ・レスポンス検証を実施

- 運用ツール
  - run_monitoring.py：SystemMonitor のポーリングループ起動
  - run_execution.py：ExecutionEngine（発注エンジン）起動（paper_trading 切替対応）
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成
  - monitoring/streamlit_dashboard.py：Streamlit でダッシュボード起動

---

## 前提（Prerequisites）

- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリの sqlite3 を使用）
- （任意）LINE Messaging API の channel access token / user id（アラート送信）

インストール例（venv を使う想定）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt がない場合:
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに移動
2. Python 仮想環境の作成と依存ライブラリのインストール
3. 環境変数を設定（.env または OS 環境変数）
   - 自動で .env / .env.local を読み込む仕組みがあります（Settings モジュール）。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
4. data ディレクトリの作成
```
mkdir -p data
```

推奨の最低環境変数（.env 例）:
```
# API / 認証
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...

# OpenAI（AI モジュールを使う場合）
OPENAI_API_KEY=...

# 環境指定
KABUSYS_ENV=development   # development | paper_trading | live

# DB パス（必要に応じて変更）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

主要な設定（Settings クラス）:
- KABUSYS_ENV: 開発 / paper_trading / live を切替。Execution 起動時に paper_trading のときは専用 DB と MockBrokerClient を使用。
- PAPER_FILL_MODE: paper_trading 時の約定動作（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- OPENAI_API_KEY: AI モジュールで必須

---

## 使い方（起動例）

- 監視ループ（SystemMonitor）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を変更可能（デフォルト 60 秒）。
  - 実行（パッケージとして）:
    ```
    python -m kabusys.run_monitoring
    ```
  - 監視は Settings.sqlite_path に対して常に「本番」SQLite を使用します（環境に依存しない）。

- 実行エンジン（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に隔離されたモードで動作します。
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid に PID を書きます（PID ファイルの stale 判定は SystemMonitor で検出・除去されることがあります）。

- Paper Trading 検証レポート
  - usage:
    ```
    python -m kabusys.tools.paper_verification_report
    ```
  - 期間指定:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB 指定:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- Streamlit ダッシュボード
  - 実行:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータを生成してください。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）。
  - 関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 優先度 / CPU affinity 設定
  - 起動スクリプト内で set_process_priority("high") が呼ばれます（Linux / Windows をサポート、失敗時は警告でスキップ）。

- 停止 / 強制停止
  - 実行エンジンを停止させるには data/kill.flag ではなく、KillSwitch を経由する設計です（ただし管理者操作で data/kill.flag を作成して停止する運用も可能）。
  - run_monitoring / run_execution は data/stop_requested.flag を検出して終了します。

---

## 実装上の注意点・挙動

- Monitoring の DB スキーマは init_monitoring_db() で冪等に作成・マイグレーションされます。既存テーブルにカラムがなければ ALTER TABLE で追加します。
- Execution は paper_trading 環境では MockBrokerClient を使用し、本番 DB と完全に分離された PAPER_TRADING_SQLITE_PATH を使います。
- AI 呼び出しは再試行・バックオフ・レスポンス検証を実装しており、失敗時はフェイルセーフ（スコア 0.0 やスキップ）で継続します。
- Settings モジュールはリポジトリルートから .env / .env.local を自動読み込みします（CWD に依存しないプロジェクトルート検出ロジック）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルのツリー（src/kabusys 配下中心）です。実際のリポジトリでは追加ファイルやテスト等が存在する可能性があります。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / Settings
    - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 用検証レポート
    - monitoring/
      - __init__.py
      - monitoring_db.py           — SQLite 永続化層（監視ログ）
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
      - order_repository.py         — （Order 関連 DB 操作）
      - execution_engine.py        — （Engine 実装: run_session 等）
      - broker_factory.py
      - broker_api.py
      - order_record.py
      - ...                         — Broker クライアント実装など
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
      - news_nlp.py                 — ニュースセンチメント取得
      - regime_detector.py          — レジーム判定
    - utils/
      - __init__.py
      - process_priority.py

---

## よく使う環境変数一覧（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用

---

## トラブルシューティング

- DB に接続できない / ファイルが見つからない:
  - パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を確認してください。
  - Streamlit の場合、読み取り専用 URI を使っているためファイルの存在とアクセス許可を確認してください。

- OpenAI 呼び出しエラー:
  - OPENAI_API_KEY が正しく設定されているか確認してください。
  - レート制限や一時的な障害はリトライ処理が入りますが、永続的に失敗する場合はログを参照してください。

- PID / stale PID 関連:
  - 実行中のエンジンは data/execution.pid に PID を書きます。プロセスが存在しない stale PID ファイルは SystemMonitor により削除・アラートされます。

---

README は以上です。必要であれば、運用手順（systemd ユニット例、Docker 化、CI/CD 構成）や各モジュールの API ドキュメント（関数詳細・戻り値・例）を追加で作成できます。どの情報を優先して追加しますか？