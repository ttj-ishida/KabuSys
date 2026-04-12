# KabuSys

KabuSys は日本株向けの自動売買・監視フレームワークです。戦略のファクター計算、ポートフォリオ構築、発注実行（本番 / ペーパートレード）、監視・アラート、LLM を使ったニュース評価などをモジュール化して提供します。

以下はこのリポジトリの要点と使い方のまとめ README です。

---

## プロジェクト概要

主な責務：

- 発注実行（ExecutionEngine） — ブローカー抽象化、注文管理、リコンシリエーション
- 監視（MonitoringEngine） — システム状態、注文滞留、リスク（ドローダウン・ポジション数）監視、LINE 通知、kill flag 発行
- 研究・リサーチ（research） — ファクター計算、将来リターン、IC 計算、統計要約
- ポートフォリオ構築（portfolio） — 候補選定、重み付け、セクター制約・レジーム補正、株数決定
- AI（ai） — ニュース NLP（OpenAI）による銘柄センチメント、マクロニュースによるレジーム判定
- ツール（tools） — Paper Trading 検証レポート等
- DB 層 — DuckDB（時系列・ファクターデータ等）と SQLite（監視ログ / ペーパートレードログ）

設計上のポイント：

- DuckDB を使って大量の時系列データやファクター計算を高速に行う
- 監視 DB（SQLite）には monitoring 用テーブルを保持し、init_monitoring_db によるマイグレーションをサポート
- KABUSYS_ENV により動作モード（development / paper_trading / live）を切替可能
- OpenAI API を用いた外部 LLM 呼び出しはフェイルセーフ（失敗時はフォールバック）で設計
- process priority や CPU affinity を設定するユーティリティあり（psutil ベース）

---

## 機能一覧

- Execution
  - ブローカー抽象化（実ブローカー / モックの切替）
  - OrderManager による注文生成・送信・同期
  - Reconciler による起動時の自動復旧（OrderSent の照合、ポジション差分検出）
  - RiskManager（風変りなパラメータ群）による注文レート制御等（実装箇所あり）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス監視、データ鮮度チェック
  - TradeMonitor：滞留注文、約定価格異常の検出
  - RiskMonitor：ドローダウン監視、ポジション上限監視（kill flag の発行も）
  - AlertManager：LINE Push による通知（クールダウンあり）
  - Streamlit ベースの監視ダッシュボード
- Research / Data
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI
  - news_nlp.score_news: ニュースを集約して OpenAI API に投げ、銘柄ごとのスコアを ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF MA とマクロニュースを組合せて市場レジーム判定、market_regime に書込
- Tools
  - paper_verification_report: Paper Trading DB を解析して稼働率 / 注文成功率 / レイテンシ等のレポートを出力

---

## セットアップ手順（ローカル開発向け）

前提：Python 3.10 以上を推奨（コード中で | 型注釈を使用）

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 代表的な依存：
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例：
     - pip install duckdb psutil openai requests streamlit

   （このリポジトリに requirements.txt があれば `pip install -r requirements.txt` を使ってください）

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置することが可能（自動読み込み）
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
   - 重要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN: （必須）
     - KABU_API_PASSWORD: （必須）
     - OPENAI_API_KEY: OpenAI 利用時に必要
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を使う場合
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用、デフォルト: data/monitoring.db) — run_monitoring は常に本番 sqlite_path を使用します
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — KABUSYS_ENV=paper_trading 時に run_execution が使用
     - PAPER_FILL_MODE: instant | partial | never | reject
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

   - .env の書式は shell の `KEY=val` 形式。コメント行、引用符付き値、`export KEY=val` に対応。

5. DB 初期化
   - 監視テーブルは各起動スクリプト内で init_monitoring_db() を呼んで作成されるため、手動で初期化する必要は通常ありません。

---

## 使い方（主要スクリプト）

- 監視ループを起動（Monitoring）
  - 実行：
    - python -m kabusys.run_monitoring
  - 補足：
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60）
    - run_monitoring は KABUSYS_ENV にかかわらず本番の SQLITE_PATH を使用します（監視は本番 DB を参照すべきため）
    - プロセス優先度を high に設定します（psutil により実行可なら変更）

- 実行エンジン起動（Execution）
  - 実行（本番/開発/ペーパー共通）：
    - python -m kabusys.run_execution
  - ペーパートレードで起動する例：
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と完全分離）
  - 補足：
    - 起動時に ExecutionEngine が Reconciler 等を用いて自動復旧を試みます
    - 実行時にプロセス優先度を high に設定します

- Streamlit ダッシュボード（監視 UI）
  - 起動例：
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 補足：
    - ダッシュボードは monitoring DB を read-only で開きます（存在しない場合はエラー表示）

- Paper Trading 検証レポート
  - コマンド：
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで別 DB を指定可能（デフォルトは env または data/paper_trading.db）

- AI 関連（プログラムから）
  - ニューススコアリング（例）:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  — DuckDB 接続を渡して実行
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

---

## 重要な挙動・注意点

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を探索）を自動検出して `.env` / `.env.local` をロードします（OS 環境変数が優先されます）。
  - テストで自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- 監視 DB のマイグレーション
  - init_monitoring_db() は冪等でテーブルを作成し、必要に応じて既存テーブルへのカラム追加（例：peak_value, latency_ms）を行います。
- run_monitoring は監視用に本番 sqlite_path を使います
  - 監視は本番データを監視する想定のため、KABUSYS_ENV に依存せず settings.sqlite_path を使います。
- run_execution の DB 切替
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path を用い、本番 DB と分離します。
- OpenAI / LINE
  - OpenAI を使う機能は OPENAI_API_KEY が必要です。失敗時は多くの機能がフェイルセーフ（スコア = 0 等）で継続しますが、API キーは設定してください。
  - LINE 通知は channel token と user id が設定されていないと送信をスキップします。
- kill.flag
  - RiskMonitor 等で条件を満たすと data/kill.flag に理由を書き込み、ExecutionEngine 停止のシグナルとして扱います。KillSwitch クラスにて生成・判定・クリアが可能です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定の読み込みと Settings クラス
  - utils/
    - process_priority.py — psutil を用いたプロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite テーブル定義 / DB 操作クラス（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - alert_manager.py — LINE 通知送信
    - kill_switch.py — kill.flag の生成/判定
    - monitoring_engine.py — 監視コンポーネントを束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — OrderManager（注文状態遷移の外向け API）
    - reconciler.py — 起動時の同期・差分検出
    - ...（broker_factory 等、ブローカー関連）
  - portfolio/
    - portfolio_builder.py — 候補選定、等重・スコア重み
    - position_sizing.py — 発注株数計算、aggregate cap 処理
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value の計算（DuckDB ベース）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースの LLM スコアリング（OpenAI）
    - regime_detector.py — マクロニュース + MA200 でレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - run_monitoring.py — Monitoring のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

（上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 簡単な実行例

- 監視をデフォルト DB で起動
  - export KABUSYS_ENV=development
  - python -m kabusys.run_monitoring

- ペーパートレードでエンジン起動
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Streamlit ダッシュボード（ローカル）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 開発上のヒント

- unit test では .env の自動ロードを無効化するため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると安定します。
- OpenAI など外部 API を含む箇所はテスト時にモック化（patch）して呼び出しを切ることを推奨します（ソース中にその旨の注記あり）。
- DuckDB を使う関数は接続を受け取る純粋関数設計が多く、解析や検証がしやすくなっています。

---

必要であれば .env のサンプル（.env.example）や requirements.txt のテンプレート、より詳しい各モジュールの使用例（API 呼び出し例や ExecutionEngine の設定例）を追加で作成できます。どの内容を優先して補足しましょうか？