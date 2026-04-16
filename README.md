# KabuSys

日本株向け自動売買・調査フレームワークのコードベース（抜粋）用 README。

概要、主要機能、セットアップと起動方法、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買エンジン、監視（Monitoring）、リサーチ（ファクター計算 / 特徴量解析）、および AI（ニュースセンチメント／レジーム判定）周りのユーティリティを含むモジュール群です。  
本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine（発注・注文管理・リコンシリエーション）
- Monitoring（システム / 注文 / リスク監視、LINE 通知、ダッシュボード）
- Research（ファクター計算・将来リターン・IC 等）
- AI（ニュース NLP による銘柄センチメント、レジーム検出）
- Portfolio（銘柄選定・重み付け・株数決定）

設計方針として、可能な限り副作用を排し DuckDB / SQLite をデータ永続化に使用、外部 API 呼び出し（OpenAI 等）は明示的な API キーで制御します。

---

## 主な機能

- 監視（Monitoring）
  - CPU / メモリ / ディスク / プロセス生存の定期ポーリング（system_monitor）
  - 注文滞留・約定価格異常の検出（trade_monitor）
  - ドローダウン・ポジション上限の監視と kill flag 発行（risk_monitor / kill_switch）
  - LINE によるアラート送信（alert_manager）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- 実行（Execution）
  - ブローカークライアント抽象化（実運用 / モック）
  - OrderManager, Reconciler による注文状態同期・自動復旧
  - Paper Trading と Live の DB 分離（paper_trading 用 DB をサポート）
- リサーチ（research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を想定）
  - 将来リターン・IC・統計サマリの計算
- AI（ai）
  - raw_news を OpenAI（gpt-4o-mini 等）でセンチメント評価して ai_scores へ保存
  - ETF（1321）MA200 乖離とマクロニュースの LLM 評価を組合せたレジーム判定
- ツール
  - Paper Trading 用検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## 要件

- Python 3.10 以上（PEP 604 の union 型（A | B）などを使用）
- 必要な主要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（標準で Python に同梱）
- （任意）LINE Messaging API トークン、OpenAI API キーなどの外部サービスキー

依存関係はプロジェクトの requirements.txt がある場合はそちらを使用してください。なければ上記パッケージを pip でインストールしてください。

例:
pip install duckdb psutil openai requests streamlit

---

## セットアップ手順

1. リポジトリをクローン、プロジェクトルートへ移動
   - git clone ...
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - または個別: pip install duckdb psutil openai requests streamlit

4. data ディレクトリを作成（必要に応じて）
   - mkdir -p data

5. 環境変数設定（.env をプロジェクトルートに置くことで自動読み込みされます）
   - 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（例）
     - KABUSYS_ENV=development | paper_trading | live (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - LOG_LEVEL=INFO

   例 .env（最小）:
   JQUANTS_REFRESH_TOKEN=xxx
   KABU_API_PASSWORD=yyy
   OPENAI_API_KEY=zzz
   KABUSYS_ENV=paper_trading

注意: config.py はプロジェクトルートを基準に .env / .env.local を自動読み込みします（CWD に依存しない設計）。テスト等で自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方

以下は代表的な起動例です。プロジェクトルート（src を含むルート）で実行するか、PYTHONPATH に src を含めて実行してください。

1. 監視ループを起動（Monitoring）
   - 簡単起動:
     - PYTHONPATH=src python -m kabusys.run_monitoring
   - ポーリング間隔を変更:
     - MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
   - 動作:
     - 監視は Settings に従い SQLite（monitoring.db）に永続化します。MONITOR は環境に関わらず本番 sqlite_path を使用します（設計上の注記）。

2. 実行エンジンを起動（Execution）
   - Live / Paper の切替は KABUSYS_ENV により制御:
     - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
     - KABUSYS_ENV=live PYTHONPATH=src python -m kabusys.run_execution
   - paper_trading では MockBrokerClient を使用し、paper 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます（本番 DB と分離）。

3. Streamlit ダッシュボード（監視情報確認）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 既存の monitoring.db を読み込み（read-only）して表示します。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス変更:
     - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

5. AI 関連（プログラム的に呼ぶ）
   - News NLP スコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="...")
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="...")

   注意: 上記は DuckDB の接続（duckdb.connect(...)）を呼び出し元で用意して渡す必要があります。OpenAI API キーは引数で渡すか、環境変数 OPENAI_API_KEY を利用します。API 呼び出し失敗時はフェイルセーフ（0.0 フォールバックなど）で継続する設計です。

6. Kill / Stop 制御
   - data/kill.flag を書き込むと ExecutionEngine に停止シグナルを送ります（KillSwitch）。flag の自動削除は行いません。
   - run_monitoring/run_execution は data/stop_requested.flag の存在を検知して終了します（手動で作成/削除して制御可能）。

---

## 重要な設定項目（抜粋）

- KABUSYS_ENV: 開発 / ペーパー / 本番を切替（development | paper_trading | live）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default 60）
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 専用 SQLite ファイルパス（分離）
- OPENAI_API_KEY: OpenAI 呼び出しに必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE push）用
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロードと Settings クラス
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 時はモック）
  - monitoring/
    - monitoring_db.py — SQLite のテーブル初期化 / MonitoringDB ラッパ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 複数モニタを束ねる
    - streamlit_dashboard.py — Streamlit 監視 UI
  - execution/
    - order_manager.py — 発注ワークフローの外向き API
    - reconciler.py — 起動時リコンシリエーション（同期）
    - (その他 ExecutionEngine 関連コンポーネント／ブローカ抽象)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・集計上限処理
    - risk_adjustment.py — セクター上限 / レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — raw_news を LLM でスコア化して ai_scores に書込
    - regime_detector.py — ma200 とマクロニュースを合成したレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 備考 / 運用上の注意

- process_priority: run_monitoring.py / run_execution.py は起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限不足や未対応 OS ではスキップされます。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に必要カラムが無ければ ALTER TABLE で追加します。
- セーフティ: AI API 呼び出しや外部 API はリトライ / フェイルセーフを備え、失敗してもシステム全体を停止させない設計です。
- Paper Trading: paper_trading モードは本番 DB と分離されるように設計されています（PAPER_TRADING_SQLITE_PATH を利用）。
- Auto .env ロード: config.py はプロジェクトルート（.git または pyproject.toml を探索）を見つけると自動で .env / .env.local を読み込みます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制できます。

---

本 README はコードベースの主要点をまとめたものです。詳細な動作確認・デプロイ手順は運用ポリシーやインフラ環境に応じて補足してください。質問や追加で欲しい項目があれば教えてください。