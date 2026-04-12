# KabuSys

日本株向け自動売買システムのコンポーネント群（ライブラリ / 実行スクリプト /監視ツール群）。

このリポジトリは取引実行、監視、ポートフォリオ構築、リサーチ、AI（ニュースNLP／レジーム判定）等の機能を含むモジュール群で構成されています。

---

## プロジェクト概要

- Python 製の自動売買システムライブラリ群。
- Execution（発注エンジン）、Monitoring（稼働・注文・リスク監視）、Portfolio（銘柄選定・配分・株数決定）、Research（ファクター・統計）、AI（ニュースセンチメント／レジーム判定）、および運用ツール類を含みます。
- DuckDB をファクタ計算・リサーチ用途で使用し、SQLite を監視ログ・注文履歴等の永続化に利用します。
- 環境毎（development / paper_trading / live）の挙動差分を設定により制御します。paper_trading モードではモックブローカーと専用 SQLite DB を使い、本番 DB と完全に分離します。

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - ブローカークライアントを BrokerClientFactory 経由で切り替え（paper_trading 時は MockBrokerClient）
  - OrderManager / Reconciler による注文状態管理と再同期（リコンシリエーション）
  - RiskManager によるリスク制約適用（ポジション上限、利用率など）

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor：滞留注文・約定価格異常チェック
  - RiskMonitor：ドローダウンやポジション上限の監視、ダッシュボード更新
  - KillSwitch：旗ファイル（data/kill.flag）による ExecutionEngine 強制停止シグナル
  - AlertManager：LINE Push API 経由の通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）

- Portfolio
  - 候補選定（スコア順）、等配分/スコア配分、リスク調整（セクター上限／レジーム乗数）、株数決定（単元丸め、aggregate cap）

- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）など統計処理

- AI
  - news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores テーブルへ保存）
  - regime_detector: MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定（market_regime テーブルへ保存）
  - API 呼び出しは再試行・バックオフ実装、レスポンスバリデーション有り

- 運用ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - 環境変数管理モジュール（自動で .env/.env.local ロード。ただし無効化可能）
  - プロセス優先度／CPU affinity のユーティリティ

---

## セットアップ手順（ローカル実行向け）

推奨: 仮想環境（venv / pyenv-virtualenv 等）を使って依存を分離してください。

1. リポジトリをクローン・移動
   - git clone ... && cd <repo>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合はそれを利用してください。）

4. 環境変数（.env）を準備
   - プロジェクトルートに .env / .env.local を配置すると自動的にロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development|paper_trading|live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60  # 監視ポーリング間隔（秒）

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要コマンド）

- 監視ループ起動（Monitoring）
  - 簡易実行:
    - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）。

- 発注エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合:
    - MockBrokerClient を使用し、Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録され、本番データとは分離されます。
  - 実行開始時にプロセス優先度を High にセットします（可能な環境で）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で SQLite DB を開きます。Monitoring を先に起動して DB が作成されていることを確認してください。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で変更可能）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI モジュール実行（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY を引数または環境変数で指定する必要があります。

---

## 主要設定・挙動メモ

- Settings（kabusys.config.Settings）
  - .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可。
  - KABUSYS_ENV の有効値: development, paper_trading, live
  - Paper trading の挙動:
    - settings.is_paper True のとき、run_execution は paper_sqlite_path を使用して DB を分離します。
    - PAPER_FILL_MODE によって MockBrokerClient の約定挙動を制御（instant / partial / never / reject）
  - デフォルト DB パス:
    - SQLITE_PATH: data/monitoring.db
    - DUCKDB_PATH: data/kabusys.duckdb
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

- Kill flag / PID
  - PID ファイル: data/execution.pid（ExecutionEngine 側が書き込み）
  - Kill flag: data/kill.flag（KillSwitch が書き込み、ExecutionEngine に停止を指示）
  - Settings.kill_flag_clear_on_start を有効にすると起動時に kill.flag を自動クリアできます（設定は環境変数で切替）。

- MONITOR_POLL_INTERVAL
  - run_monitoring.py のポーリング間隔を上書きできます（秒）。0 または負値は無効でデフォルトにフォールバックします。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等で必要テーブルとインデックスを作成します。既存スキーマに "peak_value" や "latency_ms" がない場合は ALTER TABLE による追加を行います。

---

## 典型的な運用例

1. 本番（ライブ）での監視と実行はそれぞれ別プロセス（または別ホスト）で run_monitoring / run_execution を起動する構成を想定しています。
2. 監視が異常を検出（ドローダウン大、ポジション上限超過等）すると data/kill.flag を書き、ExecutionEngine を停止させる運用ができます。
3. Paper trading では実運用と完全分離して検証を行い、検証レポート（paper_verification_report）で稼働率・注文成功率・レイテンシ等を確認します。

---

## ディレクトリ構成（主要ファイル）

（このリポジトリの src/kabusys 以下の主なファイルとモジュール）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（OpenAI）処理
    - regime_detector.py            — 市場レジーム判定（LLM + MA200）
  - monitoring/
    - __init__.py
    - monitoring_db.py              — monitoring 用 SQLite 永続化層
    - system_monitor.py             — システム・データ鮮度監視
    - trade_monitor.py              — 注文滞留 / 約定異常監視
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - kill_switch.py                — kill.flag 管理
    - alert_manager.py              — LINE 通知（クールダウン）
    - monitoring_engine.py          — 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py        — Streamlit ダッシュボード（起動スクリプト）
  - execution/
    - order_manager.py
    - reconciler.py
    - ...（ブローカー周り・リスク管理等のモジュールが存在）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - data/ (参照される想定のディレクトリ)
    - kabusys.duckdb (デフォルトの DuckDB ファイル)
    - monitoring.db (SQLite 監視 DB)
    - paper_trading.db (Paper Trading 用 SQLite DB)

---

## 注意点・運用上の留意事項

- Python バージョン:
  - 本コードベースでは型注釈に | を用いているため Python 3.10 以降を想定しています。
- OpenAI / 外部 API:
  - OPENAI_API_KEY が必須の機能（news_nlp / regime_detector）があります。API エラー時はフェイルセーフ（デフォルト値・スキップ）で動作するよう設計されていますが、キーが無いと処理は行われません。
- LINE 通知:
  - LINE用の token / user id が空の場合は送信せずログのみ出力します。
- プロセス優先度設定:
  - 起動スクリプトは set_process_priority("high") を最初に呼びます。OS により変更できない場合は警告ログが出力されスキップされます。
- DB 操作:
  - monitoring_db にはいくつかのマイグレーションロジック（カラム追加）があります。直接スキーマを手動変更する場合は注意してください。
- テスト・CI:
  - Settings の自動 .env 読み込みを無効にしたいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。

---

何か特定のモジュール（例: ExecutionEngine の設定項目、AI のプロンプト調整、ポートフォリオ最適化のパラメータ等）について README に追記したい点があれば教えてください。必要に応じてサンプル .env.example も作成します。