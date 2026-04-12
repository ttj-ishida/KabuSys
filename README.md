# KabuSys — README

本プロジェクトは日本株の自動売買／研究・監視を目的とした軽量フレームワークです。  
この README ではプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の主要機能を備えるモジュール群です。

- 注文発行・状態管理（Execution Engine）
- 発注ログ・監視（Monitoring、SQLite ベース）
- ポートフォリオ構築、ポジションサイズ計算（Portfolio）
- ファクター計算・リサーチ（Research、DuckDB を利用）
- ニュース NLP による銘柄センチメント評価（AI モジュール：OpenAI 連携）
- 起動時のリコンサイル（Reconciler）、キルスイッチ／アラート送信（LINE）
- Streamlit を用いた監視ダッシュボード、検証レポート出力ツール

設計方針の一部：
- DB 保存は SQLite（監視等）と DuckDB（時系列ファクター/価格データ）を使用
- 本番 / ペーパー取引を環境変数で切替可能（DB ファイルを分離）
- OpenAI API 呼び出しは冗長性（リトライ・フェイルセーフ）を考慮
- ルックアヘッドバイアス対策のため、日付参照は明示的に引数で渡す設計

---

## 機能一覧（抜粋）

- 実行関連
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper DB に記録。
  - execution パッケージ: OrderManager、OrderRepository、Reconciler、RiskManager など。

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）。
  - monitoring パッケージ: SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine、AlertManager、KillSwitch、MonitoringDB（永続化層）、Streamlit ダッシュボード。

- ポートフォリオ構築
  - portfolio パッケージ: 候補選定、重み付け、セクター制限、ポジションサイジング（lot 単位丸め、aggregate cap のスケールダウン等）

- リサーチ／特徴量
  - research パッケージ: モメンタム・ボラティリティ・バリューなどのファクター計算、将来リターン、IC 計算、統計サマリー

- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事を集約して LLM に送信し、銘柄ごとのセンチメントスコアを ai_scores に保存
  - ai/regime_detector.py: ETF の MA とマクロニュースのセンチメントを合成して市場レジームを判定・永続化

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）
  - monitoring/streamlit_dashboard.py: Streamlit で監視ダッシュボードを表示

---

## セットアップ手順

以下はローカル開発用の簡易手順例です。環境に合わせて調整してください。

1. Python 環境
   - 推奨: Python 3.10+（ソース内の型注釈に対応するバージョンを想定）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール
   - 代表的な依存パッケージ:
     - duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

3. データディレクトリ作成
   - デフォルトで使用する DB / ファイル:
     - data/kabusys.duckdb (DuckDB、価格・財務等の時系列)
     - data/monitoring.db (監視ログ、SQLite)
     - data/paper_trading.db (ペーパートレード用 SQLite)
     - data/execution.pid (ExecutionEngine の PID ファイル)
     - data/kill.flag (KillSwitch 用フラグ)
   - 例:
     - mkdir -p data

4. 環境変数の設定
   - .env / .env.local をプロジェクトルートに置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - LOG_LEVEL=INFO
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - MONITOR_POLL_INTERVAL=60

   - .env のロード順:
     - OS 環境変数 > .env.local > .env（自動読み込み。プロジェクトルートは .git または pyproject.toml を基準に探索）

5. DB 初期化
   - monitoring 用テーブルは run_monitoring や run_execution の起動時に自動で生成（init_monitoring_db）されます。

---

## 使い方（主要コマンド例）

- 実行エンジン（ExecutionEngine）を起動
  - 本番想定:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（MockBroker を使用、DB を data/paper_trading.db に分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視ループを起動
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 注意: run_monitoring は KABUSYS_ENV にかかわらず monitoring 用に settings.sqlite_path（production 想定の sqlite_path）を使用します（ソースコード内の設計）。

- Streamlit ダッシュボード（監視ビュー）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

- AI / リサーチ系（プログラムから呼び出す例）
  - AI ニューススコアを計算して書き込む:
    - from datetime import date
      from kabusys.ai.news_nlp import score_news
      score_news(conn=duckdb_conn, target_date=date(2026, 4, 10), api_key="...")

  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn=duckdb_conn, target_date=date(2026, 4, 10), api_key="...")

- 設定確認 / デバッグ
  - Settings クラス（kabusys.config.Settings）で環境変数のバリデーションや既定値を管理しています。
  - 自動 .env ロードを無効化したい場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 重要な挙動メモ

- ペーパートレード分離
  - KABUSYS_ENV=paper_trading のとき、run_execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 sqlite_path と完全に分離します。

- monitoring DB の初期化
  - init_monitoring_db() は冪等でテーブルと必要なマイグレーション（列追加）を行います。run_monitoring / run_execution 起動時に呼ばれます。

- kill.flag（KillSwitch）
  - RiskMonitor の判定や KillSwitch の評価により data/kill.flag が書き込まれると、ExecutionEngine 側で監視して停止シグナルとして扱う想定です。

- OpenAI 呼び出しのフェイルセーフ
  - rate limit / network error / 5xx は指数バックオフでリトライ。最終的に失敗しても例外を投げずにフォールバック動作（例: macro_sentiment=0.0）で継続する箇所が多くあります。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル・パッケージ構成を示します（src 配下）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 execution 関連モジュール: broker_factory, execution_engine, order_repository, order_record, risk_manager など)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/ (DuckDB 用スキーマ/パイプラインは別に実装)
      - (prices_daily 等のデータを保持する kabusys.data パッケージ想定)

（実際のリポジトリにはさらに細かなモジュール・ファイルが含まれます。上は主要な位置づけの抜粋です）

---

## 開発・運用上の注意点

- シークレット（API キー等）は .env / 環境変数で管理してください。.env.example を参考に作成する運用が推奨されます。
- PAPER_FILL_MODE（instant/partial/never/reject）はペーパートレードの約定挙動を制御します（無効な値は Settings が弾きます）。
- CPU/メモリ/ディスク閾値は Settings から環境変数で指定可能（CPU_THRESHOLD_PCT 等）。
- Process priority / CPU affinity の設定は psutil を利用します。権限不足の場合は警告となり処理は継続します。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）はリサーチ・AI モジュールで参照されます。データ投入は別パイプラインで行ってください。
- ランタイムでの例外は基本的にログに記録して継続する方針の箇所が多いです（監視や AI 周りの外部依存故障に対するフェイルセーフ）。

---

## ライセンス・貢献

- 本 README はコードベースのドキュメント生成用です。実際のライセンス、貢献規約はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

必要であれば以下を追加で作成します：
- .env.example（推奨環境変数テンプレート）
- requirements.txt（推奨パッケージの固定バージョン）
- データベース初期ダミーデータ挿入スクリプト
- 運用手順書（systemd / supervisor 用のサービス定義例）

どれが必要か教えてください。