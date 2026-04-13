# KabuSys

日本株自動売買システムの一部（ライブラリ + 実行/監視ツール群）。  
このリポジトリには、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースNLP／レジーム判定）などの主要コンポーネントが含まれます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能をモジュール化したコードベースです。

- 発注ライフサイクル管理（OrderManager、OrderRepository、Reconciler 等）
- 実行エンジン起動スクリプト（run_execution.py）
- 監視（System / Trade / Risk）とアラート（LINE）機構
- 監視ポーリングループ起動スクリプト（run_monitoring.py）
- 監視用 SQLite DB 層（monitoring_db）
- ポートフォリオ構築／ポジションサイズ計算（portfolio パッケージ）
- リサーチ／ファクター計算（research パッケージ、DuckDB 経由）
- ニュースを LLM（OpenAI）でスコアリングするモジュール（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）
- 開発用ツール（paper_trading 検証レポート生成など）
- Streamlit による監視ダッシュボード

設計観点としては「DB 操作と純粋関数の分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時は処理継続）」などが取り入れられています。

---

## 主な機能一覧

- Execution
  - 発注作成 / 送信 / 同期（OrderManager）
  - ブローカー抽象化（BrokerClientFactory 等）により paper_trading モードで MockBroker を利用可能
  - 再起動時の自動リコンシリエーション（Reconciler）
- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク / プロセス / データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常の検知）
  - RiskMonitor（ドローダウン、ポジション上限の監視）
  - KillSwitch（条件に応じてファイルに停止フラグを書き込み ExecutionEngine に停止シグナル）
  - LINE へのプッシュ通知（AlertManager）
  - Streamlit ダッシュボード（positions / orders / system / overview）
- Portfolio
  - 候補選定、等金額・スコア加重の重み計算
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap 等）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等
- AI
  - raw_news を LLM（OpenAI）で銘柄別にスコア化して ai_scores テーブルに書き込み
  - マクロニュース + ETF MA200 を用いたレジーム判定を行い market_regime に保存
- Tools
  - paper_trading の検証レポート生成ツール（paper_verification_report.py）

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに | None 等を利用）
- DuckDB（Python パッケージ）、psutil、requests、openai、streamlit など

推奨手順（例）:

1. リポジトリをクローンして Python 仮想環境を作成・有効化
   ```
   git clone <this-repo>
   cd <this-repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール（requirements.txt がない場合は下記をインストール）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   （必要に応じて pandas 等を追加）

3. .env を用意（任意）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. SQLite / DuckDB 用のデータディレクトリを用意
   ```
   mkdir -p data
   # デフォルトファイルパス:
   #  - monitoring sqlite: data/monitoring.db
   #  - paper trading sqlite: data/paper_trading.db
   #  - duckdb: data/kabusys.duckdb
   ```

5. 必要な環境変数の設定（下記参照）

---

## 環境変数（主なもの）

Settings クラス（kabusys.config）で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（既定: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite パス（既定: data/monitoring.db） ※ monitoring は本番 DB を使用
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（既定: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject、既定: instant）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（既定: data/execution.pid）
- KILL_FLAG_PATH — kill flag パス（既定: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag をクリアするか（"1" で有効）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値（パーセンテージ）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（既定: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（既定: INFO）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、既定: 60）

※ .env の自動読み込みはプロジェクトルート（.git or pyproject.toml）を基準に行われます。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（通常はプロダクション／paper_trading により挙動が変わる）
  ```
  # モジュールとして実行
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録され本番 DB と分離されます。
  - 起動時に PID ファイルを書き、終了時に削除します。

- Monitoring ポーリングループを開始
  ```
  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に（KABUSYS_ENV にかかわらず）Settings.sqlite_path（本番の monitoring.db）を使用します。
  - プロセス優先度を高く設定し、System/Trade/Risk のチェックを周期的に実行します。

- Streamlit ダッシュボード（監視用）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # or 指定 DB
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュールをプログラムから呼ぶ例（ニューススコア付け）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect('data/kabusys.duckdb')
  n_written = score_news(conn, target_date=date(2026,4,1), api_key='YOUR_OPENAI_KEY')
  print('written:', n_written)
  ```

---

## 監視・停止関連

- KillSwitch は条件（ドローダウン超過やポジション上限超過）に合致すると `KILL_FLAG_PATH`（既定: data/kill.flag）に理由文字列を書き込みます。ExecutionEngine はこのファイルの存在を検出して安全に停止する設計です。
- ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアできます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / Settings
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
    - utils/
      - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - execution_engine.py
      - broker_factory.py
      - broker_api.py
      - ...                          — 発注周りの実装
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/
      - pipeline.py (参照される想定)
    - tools/
      - paper_verification_report.py
    - ... その他テスト・ユーティリティ

---

## 注意点 / 実運用でのポイント

- Python バージョンは 3.10 以上を推奨（型注釈の | 演算子を使用）。
- monitoring は本番 DB（Settings.sqlite_path）を使うため、起動前に適切なバックアップ・権限を確認してください。
- paper_trading モードは本番 DB と明確に分離される設計（PAPER_TRADING_SQLITE_PATH に書き込む）です。テスト時は必ず paper_trading 環境にすることを推奨します。
- OpenAI API を使用する機能（ai.news_nlp, ai.regime_detector）は API キーが必須です。API 呼び出しの失敗時はフェイルセーフ（スコアを無効値にする等）で処理を継続しますが、費用やレート制限に注意してください。
- .env の自動読み込みはプロジェクトルート検出 (.git または pyproject.toml) に依存します。CI やテスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して明示的に環境を注入することを推奨します。

---

必要であれば、README に含める「requirements.txt の推奨内容」や、各コンポーネント（ExecutionEngine/MonitoringEngine）の詳細起動例、API モックの説明、スキーマ（DB テーブル）ドキュメントなどを追加で作成します。どの情報を優先して追加しますか？