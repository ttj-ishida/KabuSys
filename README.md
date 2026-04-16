# KabuSys

日本株向け自動売買システムのサンプル実装（バージョン 0.1.0）。  
ポートフォリオ構築・ポジションサイズ計算・監視・実行エンジン・AI を用いたニューススコアリング等のコンポーネント群を含みます。

---

## 概要

KabuSys は以下のような機能ブロックで構成された自動売買プラットフォームのコードベースです。

- Execution エンジン：ブローカーとの発注・状態管理・再同期（リコンシリエーション）
- Monitoring：システム稼働監視、注文監視、リスク監視、Kill Switch（停止フラグ）
- Portfolio construction：候補選定・重み付け・ポジションサイズ計算・セクター制約
- Research：ファクター計算（モメンタム・バリュー・ボラティリティ等）、特徴量解析
- AI：ニュースを LLM（OpenAI）でスコアリングしてシグナル補助、レジーム判定
- Tools：Paper Trading 検証レポート等のユーティリティ
- Streamlit ダッシュボード：監視データの可視化

設計方針として「外部 API への直接アクセスを最小化」「ルックアヘッドバイアス防止」「フェイルセーフ（API失敗時は安全側でフォールバック）」等が考慮されています。

---

## 主な機能一覧

- system monitor（CPU/メモリ/Disk/プロセス/データ鮮度監視）
- trade monitor（滞留注文・約定価格異常検出）
- risk monitor（ドローダウン・ポジション上限監視、リスクログ記録）
- Kill Switch（条件を満たしたら外部ファイルを書いて ExecutionEngine を停止）
- AlertManager（LINE による通知、クールダウン機構付き）
- ExecutionEngine 起動スクリプト（本番 / Paper Trading 分離）
- Paper Trading 用検証レポート生成ツール
- AI モジュール（ニュース NLP によるセンチメントスコア、レジーム判定）
- Portfolio 構築ユーティリティ（候補選出、重み計算、ポジションサイズ最適化）
- Streamlit ベースの監視ダッシュボード

---

## 要求環境

- Python 3.10 以上（typing の | 演算子などを使用）
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（Python 標準ライブラリで利用）
- ネットワーク接続（LINE / OpenAI 使用時）

requirements.txt を別途用意している場合はそれを使ってください。例:

```
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン / 配置
2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存関係をインストール
   ```
   pip install -r requirements.txt
   ```
   もしくは個別に:
   ```
   pip install duckdb psutil requests openai streamlit
   ```
4. 環境変数を用意する
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし OS 環境変数が優先され、読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABU_API_BASE_URL (任意)
     - OPENAI_API_KEY (AI モジュール使用時必須)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知を使う場合）
     - KABUSYS_ENV = development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE = instant | partial | never | reject（Paper Trading 時の約定挙動）
     - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
     - DUCKDB_PATH (分析用 DuckDB、デフォルト: data/kabusys.duckdb)
     - PID_FILE_PATH / KILL_FLAG_PATH 等

   .env のパース・ロードは `kabusys.config` モジュールが自動で行います。

5. データディレクトリの準備（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 実行方法（代表的なコマンド）

プロジェクトはモジュールとして実行できます（src 配下が PYTHONPATH に含まれていることを前提とする）。ルートで実行する場合は `python -m kabusys.<module>` を利用します。

- Monitoring の起動（ポーリングループ）
  ```
  # デフォルトポーリング間隔 60 秒。環境変数で上書き可能:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  備考:
  - 監視は monitor データベース（Settings.sqlite_path）に書き込みます。Monitoring は環境にかかわらず本番 sqlite_path を使用します。
  - 停止はプロジェクトルート `data/stop_requested.flag` を作成することで検知してループを抜けます。

- ExecutionEngine（注文実行エンジン）の起動
  ```
  # Paper Trading を使う場合:
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution

  # 本番/開発:
  export KABUSYS_ENV=live
  python -m kabusys.run_execution
  ```
  備考:
  - `paper_trading` の場合は MockBrokerClient を利用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離します。
  - Engine は `data/execution.pid` を利用します。停止は `data/stop_requested.flag` を作成することで検知されます。

- Streamlit ダッシュボード（監視画面）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート（コマンドライン）
  ```
  # 全期間（デフォルト DB path が使用される）
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パスを明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（プログラム経由で呼び出す）
  - ニューススコア: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - これらは DuckDB 接続を受け取り DB を読み書きします。OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` を使用します。

---

## 主要な環境変数（まとめ）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- PAPER_FILL_MODE: instant | partial | never | reject
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

注意: `kabusys.config` が .env / .env.local を自動読み込みします。自動読込を無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

概観（src/kabusys 以下）:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/run_monitoring.py          — 監視ループ起動スクリプト
- src/kabusys/run_execution.py           — ExecutionEngine 起動スクリプト
- src/kabusys/tools/
  - paper_verification_report.py         — Paper Trading 検証レポート CLI
- src/kabusys/monitoring/
  - monitoring_db.py                     — SQLite テーブル作成・永続化層
  - system_monitor.py                    — システム状態 / データ鮮度監視
  - trade_monitor.py                     — 注文滞留・約定異常検出
  - risk_monitor.py                      — ドローダウン / ポジション上限監視
  - kill_switch.py                       — kill.flag 書き込みロジック
  - alert_manager.py                     — LINE 通知送信ロジック
  - monitoring_engine.py                 — 各 Monitor を束ねるループ/テスト実行
  - streamlit_dashboard.py               — Streamlit 監視ダッシュボード
- src/kabusys/execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py (エンジン本体: 起動・セッション管理など)
  - broker_factory.py / broker_api.py    (ブローカーインターフェース)
- src/kabusys/portfolio/
  - portfolio_builder.py                 — 候補選出・重み計算
  - position_sizing.py                   — 株数決定・スケーリング
  - risk_adjustment.py                   — セクターキャップ・レジーム乗数
- src/kabusys/research/
  - factor_research.py                   — ファクター計算（momentum, volatility, value）
  - feature_exploration.py               — 将来リターン・IC・統計サマリ
- src/kabusys/ai/
  - news_nlp.py                          — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py                   — 市場レジーム判定（MA + マクロセンチメント）
- src/kabusys/utils/
  - process_priority.py                  — プロセス優先度 / CPU affinity 設定ユーティリティ

データディレクトリ（プロジェクトルート）:
- data/
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (デフォルト DUCKDB_PATH)
  - stop_requested.flag (run scripts で停止を検知)
  - kill.flag (KillSwitch が書き込む停止フラグ)
  - execution.pid (ExecutionEngine が書き込む PID ファイル)

---

## 運用上の注意点 / ヒント

- Monitoring は設定にかかわらず Settings.sqlite_path（監視 DB）を使用します。Paper Trading と監視 DB の分離に注意してください。
- ExecutionEngine を Paper Trading モードで動かすと、ブローカーはモック・DB は paper_trading.db を使い本番 DB と分離されます。
- OpenAI を利用するモジュールは API のエラーに対してリトライ（指数バックオフ）やフォールバック実装がされていますが、API キーが未設定だと例外を投げる箇所があります。CI やテスト時は呼び出し側でキーの有無を制御してください。
- kill.flag / stop_requested.flag / execution.pid の取り扱いに注意してください。手動で削除して起動・停止を制御できます。
- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml で検出して行われます（テストで自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

## 開発・テスト

- ユニットテストやモックを利用して外部 API（OpenAI / Broker）呼び出しを差し替えてください。ソース内では API 呼び出し関数を差し替え可能に設計している箇所が複数あります（テスト用に _call_openai_api を patch する等）。
- DuckDB / SQLite の接続は引数で渡す設計になっているため、テスト時は一時データベースを用意して状態検証が可能です。
- MonitoringEngine は `run_once()` を提供するため、ループを回さず単発実行でのテストが容易です。

---

必要に応じて README に追記します。特に欲しい情報（例: サービス化 / systemd ユニット化の例、CI 設定、詳細な環境変数サンプルなど）があれば教えてください。