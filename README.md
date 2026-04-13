# KabuSys

日本株自動売買フレームワーク（プロトタイプ）

このリポジトリは日本株アルゴリズム取引のための小規模フレームワークです。戦略生成、ポートフォリオ構築、発注・リスク管理、監視、研究（DuckDB ベースのファクター計算）、およびニュース NLP を用いた補助機能を含みます。

---

## 主な特徴

- Execution（発注）エンジン
  - Broker 抽象化（実口座・Paper trading 切替）
  - OrderManager / OrderRepository によるクラッシュ耐性ある二相永続化・同期
  - 起動時のリコンシリエーション（Reconciler）

- Portfolio construction
  - 候補選定、等配分 / スコア加重配分
  - ポジションサイズ計算（リスクベース、上限・単元丸め、集計キャップ）
  - セクター集中制限、レジーム乗数

- Research（DuckDB を使用）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC（Information Coefficient）、統計サマリ

- AI（OpenAI 統合）
  - ニュース記事のセンチメント解析（gpt-4o-mini を想定）
  - マクロニュースと MA を組み合わせた市場レジーム判定

- Monitoring
  - System / Trade / Risk の監視
  - 監視ログは SQLite に永続化（data/monitoring.db）
  - LINE へプッシュ通知（AlertManager）
  - kill.flag による外部停止シグナル送出
  - Streamlit ベースの監視ダッシュボード

- ツール
  - Paper Trading 検証レポート出力スクリプト

---

## 動作環境（前提）

- Python 3.10+
  - コード内で型注釈に `X | Y` を使用しているため Python 3.10 以降を推奨します。
- SQLite（標準ライブラリで対応）
- 推奨パッケージ（主要依存）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit

requirements.txt がある場合はそちらを使用してください。ない場合は下記コマンド例を参照してください。

---

## セットアップ手順（例）

1. リポジトリを取得
   - git clone ... && cd <repo>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. データディレクトリを作成
   - mkdir -p data

5. 環境変数を用意
   - プロジェクトルートの `.env` / `.env.local` を使えます（自動的に読み込まれる。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用（使用箇所がある場合）
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
   - 選択・推奨:
     - OPENAI_API_KEY — AI 機能を使う場合に必須
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定挙動 ("instant"|"partial"|"never"|"reject")（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / LOG_LEVEL / LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID 等（詳細は config.Settings を参照）

---

## 基本的な使い方

- 監視ループの起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 監視は SQLite（monitoring.db）へ永続化されます。

- 発注エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し data/paper_trading.db に分離して記録します（本番 DB と完全に分離）。
  - 実行時、プロセス優先度を高く設定します（プラットフォーム依存で権限が必要になる場合があります）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きます（起動中の MonitoringEngine による DB 作成/更新が前提）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定可能（デフォルト: data/paper_trading.db）。

- AI 機能（プログラムから呼ぶ例）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")  # DuckDB 接続と日付を渡す
  - regime_detector も同様（OpenAI API キーが必要）

---

## 環境変数（主なもの）

（詳細は src/kabusys/config.py を参照）

- 必須（使用する機能に応じて）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- データベース
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視ログ SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）

- AI / OpenAI
  - OPENAI_API_KEY

- 監視設定など
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - MONITOR_POLL_INTERVAL（run_monitoring 用の上書き、秒）

- LINE 通知
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml）から `.env` と `.env.local` を自動読み込みします。
- OS 環境変数の優先度が高く、`.env.local` は `.env` を上書きします。
- 自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定管理
- run_monitoring.py — SystemMonitor のポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを LLM でスコアリング、ai_scores へ書込
  - regime_detector.py — マクロ＋MA による市場レジーム判定

- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化と DB 操作ラッパー
  - system_monitor.py — CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の生成 / 管理
  - alert_manager.py — LINE 通知ラッパー
  - monitoring_engine.py — 各 Monitor を束ねたポーリングエンジン
  - streamlit_dashboard.py — Streamlit ベースの簡易ダッシュボード

- execution/
  - reconciler.py — 起動時の自動復旧 / 照合
  - order_manager.py — Order State Machine の外向き API
  - order_repository.py, order_record.py, broker_api.py 等（発注ロジック・DB レイヤ）※一部ファイルは抜粋されていません

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出・集計キャップ・単元丸め
  - risk_adjustment.py — セクター上限・レジーム乗数

- research/
  - factor_research.py — Momentum/Volatility/Value ファクター
  - feature_exploration.py — 将来リターン・IC・統計サマリ

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート出力スクリプト

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意・補足

- Paper trading は本番 DB と完全に分離します。KABUSYS_ENV=paper_trading により PAPER_TRADING_SQLITE_PATH を使います。
- プロセス優先度設定（set_process_priority）はプラットフォームに依存し、権限不足で失敗することがあります（ログで警告）。
- kill.flag を使用した強制停止は冪等であり、既に存在する場合は上書きしません。Execution 側は kill.flag の存在を起動時に確認して動作します（設定により起動時クリア可）。
- OpenAI/API 呼び出し関連は外部サービス依存のため、API キーの設定とレート制限などに注意してください。AI モジュールは失敗時にフェイルセーフ（スコア0など）で継続する設計です。
- DuckDB をデータ分析基盤として利用する設計になっています。prices_daily / raw_financials / raw_news 等のテーブル準備は別途 ETL パイプラインが必要です。

---

## 参考コマンド例

- 監視を 30 秒間隔で起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ExecutionEngine を Paper Trading モードで起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

問題や変更提案、ドキュメントへの追記要求があればお知らせください。README のサンプル .env や requirements.txt、起動ユニット（systemd 例）などのテンプレートを追加で作成できます。