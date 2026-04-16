# KabuSys

日本株向け自動売買システムのリファレンス実装です。  
ポートフォリオ構築、発注エンジン、監視・アラート、リサーチ用ファクター計算、AI（ニュースセンチメント・レジーム判定）などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群で構成されています。

- 発注（Execution）エンジンとオーダー管理
- Paper Trading（モックブローカー）による検証環境
- 監視（Monitoring）：プロセス・データ鮮度・注文異常・リスク検出、LINE 通知、ダッシュボード
- ポートフォリオ構築（候補選定・重み・ポジションサイズ計算・セクター制限）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI モジュール：ニュースセンチメント（OpenAI）・市場レジーム判定
- ツール：Paper Trading 用検証レポート、Streamlit ダッシュボード 等

設計上のポイント:
- 環境変数 / .env による設定管理（自動読み込み）
- Paper Trading と本番 DB を分離（KABUSYS_ENV により挙動変更）
- フェイルセーフ：API失敗時のフォールバックや部分失敗時に既存データを保護
- DuckDB を使った時系列データ処理、SQLite を監視・トレードログ永続化に使用

---

## 機能一覧

主要な機能（抜粋）:

- Execution
  - ExecutionEngine（ブローカー抽象化、OrderManager、Reconciler）
  - Paper Trading モード（MockBrokerClient、paper_trading DB）
- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク / プロセス PID / データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じた停止フラグ書き込み）
  - AlertManager（LINE へのプッシュ通知）
  - MonitoringEngine（これらの統合ポーリングループ）
  - Streamlit ダッシュボード（監視 DB の可視化）
- Portfolio
  - 候補選定・等配分／スコア配分
  - ポジションサイズ計算（リスクベース等）
  - セクターキャップ・レジーム乗数
- Research
  - ファクター（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC（スピアマン）、統計サマリ
- AI
  - news_nlp: ニュース記事の LLM によるセンチメントスコア化（ai_scores へ書込み）
  - regime_detector: ma200 とマクロニュースの LLM 出力を合成して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB から検証レポートを出力
  - streamlit_dashboard: 監視 DB を読み取りダッシュボードを表示

---

## 必要要件

- Python 3.9+
- 主要依存ライブラリ（抜粋）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（OpenAI や外部 API を使う場合）

（プロジェクトに requirements.txt がない場合は上記パッケージをインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主なもの）

Settings クラスにより環境変数から設定を読み込みます。自動でプロジェクトルートの`.env` / `.env.local` を読み込みます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

主要な環境変数（抜粋）:

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

簡単な .env 例:
```
KABUSYS_ENV=paper_trading
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb psutil requests openai streamlit
   ```

3. `.env`（または `.env.local`）を作成して必要な環境変数を設定

4. データフォルダ作成（任意）
   ```
   mkdir -p data
   ```

5. DB 初期化は各コンポーネント起動時に必要なテーブルを作成します（init_monitoring_db が実行されるため、手動初期化不要）

---

## 使い方

### 監視ループを起動（Monitoring）
監視は本番用 sqlite_path（Settings.sqlite_path）を参照します。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）。

```
python -m kabusys.run_monitoring
```

オプション:
- MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

停止:
- プロセスに SIGINT（Ctrl+C）を送るか、プロジェクトルートの data/stop_requested.flag ファイルを作成するとループが検出して安全に終了します。

補足:
- Monitoring は KABUSYS_ENV に依らず Settings.sqlite_path（本番）を使用します。

---

### ExecutionEngine を起動（注文エンジン）
KABUSYS_ENV により挙動が変わります。paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。

```
python -m kabusys.run_execution
```

- Paper Trading モードで起動する場合:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
- 起動時に data/stop_requested.flag が存在すると起動せず終了します。
- 実行中に data/stop_requested.flag を作成するとエンジンを停止します。
- プロセスは data/execution.pid に PID を書きます（Settings.pid_file_path でパス変更可）。

---

### Paper Trading 検証レポート
Paper Trading の SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成します。

```
python -m kabusys.tools.paper_verification_report
```

期間指定:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```

データベース指定:
```
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

出力される指標例:
- 稼働率 (uptime)
- 注文成功率 / 送信率
- P95 レイテンシ
- リスク却下数

---

### Streamlit ダッシュボード（監視）
監視 DB を参照するダッシュボードを起動します。

```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

注意: DB は読み取り専用モードで開きます（起動中の MonitoringEngine が DB を書き込んでいる想定）。

---

### AI 機能
- ニュースセンチメント: kabusys.ai.news_nlp.score_news(conn, target_date, api_key)
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)

両方とも OPENAI_API_KEY（または api_key 引数）が必要です。API 呼び出しはリトライ・バックオフや部分失敗保護が組み込まれています。

---

## 停止・キルフラグ関連

- data/stop_requested.flag: run_monitoring / run_execution の主ループで監視され、存在すると安全に停止します。
- data/kill.flag: KillSwitch が書き込むフラグ（ExecutionEngine に対する停止シグナル）。Settings.kill_flag_path でパス変更可。KillSwitch はドローダウンやポジション上限超過で書き込みます。
- PID ファイル: data/execution.pid（Settings.pid_file_path）に ExecutionEngine の PID が書かれます。SystemMonitor は stale PID を検出してログ／アラートします。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（.env 自動ロード）
  - run_monitoring.py            — SystemMonitor のポーリング起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite テーブル定義 / CRUD（MonitoringDB）
    - system_monitor.py           — システム状態・データ鮮度監視
    - trade_monitor.py            — 注文滞留・約定異常検知
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 書込みユーティリティ
    - alert_manager.py            — LINE 通知（クールダウン管理）
    - monitoring_engine.py        — 各モニター統合ポーリング
    - streamlit_dashboard.py      — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - (その他ブローカー関連)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                 — ニュースセンチメント（OpenAI）
    - regime_detector.py          — 市場レジーム判定（ma200 + macro sentiment）
  - data/                         — 実行時データ（例: monitoring.db, paper_trading.db, kabusys.duckdb）
  - utils/
    - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要コンポーネントのみ。実際のリポジトリにはさらに補助モジュールが含まれます）

---

## 注意点 / 運用上のメモ

- Settings は自動で .env / .env.local をロードします。OS 環境変数を優先します。
- Monitoring は常に Settings.sqlite_path（本番監視 DB）を使用します。paper_trading でも監視は本番 DB を見る設計です（運用上の注意）。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite に記録し本番 DB と完全分離します。
- OpenAI を使う処理は API 呼び出し失敗に対してフェイルセーフなフォールバック（ゼロスコアやスキップ）を行いますが、API キーを設定しておくことを推奨します。
- process_priority.set_process_priority("high") を実行してプロセス優先度を上げます。権限不足で失敗した場合はログに警告が出ますが処理は継続します。
- DB スキーマのマイグレーション処理（monitoring_db.init_monitoring_db）は冪等性を考慮しています。既存スキーマがあれば必要に応じてカラム追加を行います。

---

必要に応じて README に更に詳細（API ドキュメント、クラス/関数仕様、開発手順、テスト手順）を追加できます。どの項目を追記したいか教えてください。