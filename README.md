# KabuSys — README (日本語)

## プロジェクト概要
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースのシステムです。  
主な機能は戦略による銘柄選定・配分、発注管理、リコンシリエーション、監視・アラート、Paper Trading 検証、LLM を使ったニュースセンチメントや市場レジーム判定などを含みます。

設計方針の要点:
- DuckDB / SQLite をデータ層に使い、ロジックはできるだけ純粋関数化（テスト容易性重視）
- 実行環境に依存しない設定ロード（.env 自動読み込み機能）
- Paper Trading と本番 DB は分離可能
- OpenAI（gpt-4o-mini 等）を使った NLP 機能を統合（APIキーは環境変数で管理）
- 監視（MonitoringEngine）により稼働状況・注文状態・リスク監視 → 必要時に kill.flag を書き込み停止指示

---

## 機能一覧
- ポートフォリオ構成
  - シグナルから候補選定（score / rank ベース）
  - 等金額／スコア重み配分
  - リスク調整（セクター上限・市場レジーム乗数）
  - 発注株数決定（単元株丸め・aggregate cap）
- 実行（ExecutionEngine）
  - ブローカークライアント抽象化（paper_trading では Mock を使用可能）
  - OrderManager によるクラッシュ耐性のある状態遷移と発注
  - Reconciler による起動時の自動復旧・ポジション差分チェック
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - システム資源・プロセス・データ鮮度監視
  - 注文滞留・約定異常価格検出
  - ドローダウン・ポジション上限に基づく kill.flag 発行
  - LINE 通知（AlertManager）
  - Streamlit ダッシュボード（読み取り専用）
- AI（LLM）連携
  - ニュースのセンチメントスコアリング（ai.news_nlp）
  - マクロニュース + ETF MA200 による市場レジーム判定（ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ
  - process priority / CPU affinity 設定ユーティリティ
  - 環境設定ロード（.env の自動読み込みと Settings クラス）

---

## セットアップ手順（ローカル開発向け）
1. Python を用意
   - 推奨: Python 3.10+（コードベースの型注釈等を考慮）
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必要パッケージの一例:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合はそれを使用してください）
4. .env の準備
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置けます。
   - 自動ロードはデフォルトで有効。無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 主要な環境変数（後述）を `.env` に設定してください。
5. データディレクトリ
   - デフォルトの DB・ファイルパス:
     - SQLite (監視): data/monitoring.db
     - DuckDB: data/kabusys.duckdb
     - Paper trading SQLite: data/paper_trading.db
     - PID / kill flag: data/execution.pid / data/kill.flag
   - 必要に応じてディレクトリを作成（コード側で自動作成する箇所もあります）。
6. 初回起動
   - 監視用 SQLite は接続時にテーブル作成（init_monitoring_db）されます。特別な初期化は不要です。

---

## 環境変数（主なもの）
- KABUSYS_ENV
  - 値: development | paper_trading | live
  - default: development
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能使用時に必要)
- PAPER_FILL_MODE (paper_trading 用)
  - allowed: instant | partial | never | reject
  - default: instant
- PAPER_TRADING_SQLITE_PATH
  - default: data/paper_trading.db
- SQLITE_PATH
  - default: data/monitoring.db
- DUCKDB_PATH
  - default: data/kabusys.duckdb
- PID_FILE_PATH / KILL_FLAG_PATH
  - default: data/execution.pid / data/kill.flag
- MONITOR_POLL_INTERVAL
  - 監視ループのポーリング間隔（秒）。デフォルト 60。1 以上の整数で指定。無効値は 60 にフォールバック。
- LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（Settings クラス参照）

注意: Settings クラスは自動で .env を読み込みます（OS 環境変数が優先）。.env の書式はシェルライクなものに対応（コメントやクォート処理を考慮）。

---

## 使い方（主要コマンド例）

- ExecutionEngine を起動（本番/ペーパートレードに応じて KABUSYS_ENV を設定）
  - 本番 (live) / development:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合、MockBrokerClient が使用され、デフォルトで data/paper_trading.db に記録されます。

- Monitoring（SystemMonitor の単体スクリプト）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  # ポーリング間隔を 30 秒に変更

- Streamlit ダッシュボード（監視データの閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを明示可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- AI 機能（コード呼び出し例）
  - ニューススコア（ai.news_nlp.score_news）やレジーム判定（ai.regime_detector.score_regime）は DuckDB 接続と target_date を与えて呼び出します。OPENAI_API_KEY（または api_key 引数）が必要です。
  - 例:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="sk-...")

- ユーティリティ
  - プロセス優先度は run_* スクリプト内で自動的に set_process_priority("high") が呼ばれます。

---

## ディレクトリ構成（主要ファイルの説明）
（src/kabusys 以下）

- __init__.py
  - パッケージ定義、__version__、公開モジュール一覧

- config.py
  - .env / 環境変数の自動ロード、Settings クラス（全設定プロパティ）

- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading で Mock を使用）

- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL で間隔調整）

- tools/
  - paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI

- utils/
  - process_priority.py
    - プロセス優先度 / CPU affinity 設定ユーティリティ

- portfolio/
  - portfolio_builder.py
    - 候補選定・基礎配分アルゴリズム（select_candidates, calc_equal_weights, calc_score_weights）
  - position_sizing.py
    - 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py
    - セクターキャップ・レジーム乗数

- monitoring/
  - monitoring_db.py
    - SQLite による監視テーブル定義・CRUD（init_monitoring_db, MonitoringDB）
  - system_monitor.py
    - システム資源・プロセス・データ鮮度監視
  - trade_monitor.py
    - 注文滞留・約定異常の検出
  - risk_monitor.py
    - ドローダウン・ポジション数監視（ダッシュボード更新、リスクログ）
  - kill_switch.py
    - kill.flag 管理（作成・削除・判定）
  - alert_manager.py
    - LINE Push 通知
  - monitoring_engine.py
    - 上記モニタを束ねるポーリングエンジン
  - streamlit_dashboard.py
    - Streamlit を用いる監視ダッシュボード（読み取り専用）

- execution/
  - order_manager.py
    - 発注ワークフロー（状態遷移、送信、クラッシュ耐性）
  - reconciler.py
    - 起動時の OrderSent 照合・ポジションリコンシリエーション
  - （その他ブローカー抽象・リポジトリ等の実装ファイル）

- research/
  - factor_research.py
    - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受ける）
  - feature_exploration.py
    - 将来リターン計算、IC（Information Coefficient）、統計要約

- ai/
  - news_nlp.py
    - raw_news を用いた銘柄別センチメントスコア付与（OpenAI 呼び出し、バッチ・リトライ処理）
  - regime_detector.py
    - ETF MA200 とマクロニュースを合成した市場レジーム判定（LLM 呼び出し）

- monitoring_db / execution_db / data ファイルは実行時に生成されることが多いです（data/ 配下の DB 等）。

---

## 運用上の注意
- KABUSYS_ENV=paper_trading を使うと本番 DB と分離された paper_trading DB に記録されます。Paper と本番を明確に分けて運用してください。
- MONITOR_POLL_INTERVAL の値が 1 未満または不正の場合、デフォルト 60 秒にフォールバックします。
- OpenAI を使う機能は API コストが発生します。呼び出し頻度やバッチサイズを運用ルールに合わせて調整してください。
- kill.flag により ExecutionEngine 停止のシグナルを送る設計です。kill.flag の存在はプロセス間の停止合図になるため、運用時は取り扱いに注意してください。
- psutil を使ってプロセス優先度や CPU affinity を設定します。権限不足により設定が失敗する場合があります（警告ログのみ）。

---

もし README に追加したい具体的な情報（requirements.txt、CI/CD、開発フロー、テストコマンド、サンプル .env の雛形 など）があれば教えてください。必要に応じて README を拡張します。