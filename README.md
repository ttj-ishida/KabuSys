# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ。  
この README はコードベースを元に各コンポーネントの概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したコンポーネント群です。主な機能は以下の通り：

- 実際の発注ロジック（ExecutionEngine、OrderManager、BrokerClientFactory 等）
- モニタリング（SystemMonitor / TradeMonitor / RiskMonitor、監視 DB）
- ポートフォリオ構築／ポジションサイジング（等金額・スコア加重・リスクベース）
- 研究用ファクター計算・特徴量解析（DuckDB を用いたファクター計算）
- AI 補助（ニュースセンチメント解析／レジーム判定：OpenAI を利用）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- プロセス優先度 / CPU affinity ユーティリティ

設計方針として、DB（DuckDB / SQLite）を用いたデータ処理、テスト可能な純粋関数群、API 呼び出しのフェイルセーフハンドリング、ルックアヘッドバイアス対策などが組み込まれています。

---

## 機能一覧

- Execution
  - 発注作成 / 送信 / 状態同期（Reconciler による再起動後の復旧）
  - Paper Trading モード（実ブローカーと分離して data/paper_trading.db に記録）
- Monitoring
  - システム状態監視（CPU / メモリ / ディスク / プロセス生存）
  - 注文監視（滞留注文、約定異常価格）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（フラグファイル書込で ExecutionEngine 停止指示）
  - LINE による通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定、等重・スコア重み、リスク調整、ポジション算出（単元丸め含む）
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリー
- AI
  - ニュースのセンチメント解析（OpenAI 使用、gpt-4o-mini 想定）
  - 市場レジーム判定（MA + マクロニュースの LLM 解析）
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

---

## 前提条件 / 依存関係（推奨）

Python 3.9+ を想定。主なパッケージ（抜粋）:

- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード使用時)
- (必要に応じて) その他の一般的パッケージ

準備例:
- 仮想環境作成: python -m venv .venv && source .venv/bin/activate
- インストール例:
  - pip install duckdb psutil requests openai streamlit

（実際の requirements.txt はプロジェクトに応じて作成してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。
2. Python 仮想環境を作成して有効化。
3. 依存ライブラリをインストール（上の例参照）。
4. データディレクトリを作成（必要に応じて）:
   - デフォルトの DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - PID ファイル: data/execution.pid
     - Kill フラグ: data/kill.flag
5. 環境変数を設定（.env/.env.local をプロジェクトルートに配置可）。自動ロード機能が有効（既定）で、OS 環境変数優先で .env/.env.local を読み込みます。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（主なもの）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時の挙動: instant / partial / never / reject、デフォルト: instant）
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（監視ループ間隔秒、デフォルト 60。0以下や不正値はデフォルトへフォールバック）

---

## 使い方

以下は主な実行例です。モジュールはパッケージモードで起動できます。

1. ExecutionEngine を起動（本番/ペーパーの切替）
   - 本番 / デフォルト:
     - python -m kabusys.run_execution
   - Paper Trading（MockBroker を使用、DB を data/paper_trading.db に分離）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 補足:
     - Execution 起動時にプロセス優先度を "high" に設定します（set_process_priority）。
     - Paper Trading 時は settings.paper_sqlite_path を使用して完全に分離された DB に記録されます。

2. Monitoring を起動（監視ポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数で間隔を変更:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 補足:
     - run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（settings.sqlite_path）を使用します（監視は常に本番 DB を見る設計）。
     - 起動時にプロセス優先度を "high" に設定します。

3. Streamlit ダッシュボード（監視 UI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ブラウザ上でポートフォリオ、ポジション、注文履歴、システムステータス、最近のリスクログを確認できます。

4. Paper Trading 検証レポート（ツール）
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - レポートは期間内の稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL 判定を出力します。

5. AI 関連（ニューススコア / レジーム判定）
   - ニュースセンチメントやレジーム判定は OpenAI API を使用します。実行時に OPENAI_API_KEY が必要です。
   - 関数呼び出し例（Python API）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key="...")

   - 注意:
     - API キーが未設定の場合は例外を投げます。
     - レートリミット・一時エラー時はリトライ/フォールバックの実装があります。

---

## 主要設定の挙動・注意点

- .env の自動ロード:
  - プロジェクトルートを .git または pyproject.toml で検知し、.env（上書き不可）→ .env.local（上書き可）を読み込みます。
  - OS 環境変数は保護され、.env.local の override でも上書きされません（protected）。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔。環境変数で上書き可。デフォルト 60 秒。1未満や不正値はデフォルトへフォールバック。

- PID / Kill Flag:
  - ExecutionEngine は PID を data/execution.pid に書きます（Settings.pid_file_path）。
  - KillSwitch は data/kill.flag の作成で ExecutionEngine に停止シグナルを送ります（Settings.kill_flag_path）。
  - kill.flag は既存の場合は上書きしない（冪等）。Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag を削除できます。

- DB マイグレーション（簡易）:
  - monitoring_db.init_monitoring_db は存在しないテーブルやカラムを作成する冪等処理を含みます（例: dashboard.peak_value, trade_logs.latency_ms の追加）。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
  - パッケージ定義（__version__ 等）
- config.py
  - Settings クラス。環境変数読み込み・検証・デフォルト管理。
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて paper_trading を分離）。
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト。
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ（psutil）
- monitoring/
  - monitoring_db.py — SQLite テーブル定義と MonitoringDB ラッパー
  - system_monitor.py — システム状態 / データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag を管理するユーティリティ
  - alert_manager.py — LINE Push 通知用クライアント
  - monitoring_engine.py — 複数モニタを束ねるループ管理
  - streamlit_dashboard.py — Streamlit 監視ダッシュボード
- execution/
  - order_manager.py — 注文ライフサイクル管理
  - reconciler.py — 起動時の注文・ポジション突合せ
  - （ブローカーファクトリ / Broker API） ※省略されている実装ファイルもある想定
- portfolio/
  - portfolio_builder.py — 候補選定、重み付け
  - position_sizing.py — 株数算出、利用資金キャップ処理
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ
- ai/
  - news_nlp.py — ニュースを OpenAI で解析して ai_scores に書き込む処理
  - regime_detector.py — MA と LLM によるレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール

（上記は主要ファイルの抜粋・説明です。実際のリポジトリにはさらに細分化されたモジュールが存在します。）

---

## 開発者向けメモ / その他

- DuckDB は分析処理向けの高速列指向 DB として prices_daily / raw_financials 等の集計に用います。接続オブジェクトを各関数に渡す設計です。
- OpenAI を利用するモジュールでは、レスポンス検証・リトライ・スコアクリッピング等の安全策を設けています。API キー管理に注意してください。
- monitoring の一部は本番監視 DB（settings.sqlite_path）を参照する設計のため、Paper Trading とモニタを混同しないよう運用時は設定に注意してください。
- エラーハンドリングはフェイルセーフを重視しており、API 失敗時はスキップ・フォールバックする実装が多く含まれます。

---

この README はコードをベースにした概要ドキュメントです。実際の運用やデプロイ前には環境固有の設定 (.env)・ブローカークレデンシャル・API キーの取り扱いを必ず確認してください。必要であれば、requirements.txt や運用マニュアルを別途作成することを推奨します。