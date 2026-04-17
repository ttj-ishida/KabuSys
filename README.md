# KabuSys

日本株向けの自動売買 / 監視 / リサーチ用ライブラリ群および実行スクリプト群。

本リポジトリは、発注エンジン・監視（Monitoring）・ポートフォリオ構築・ファクター計算・ニュース NLP（OpenAI）など、実運用を想定したコンポーネントを集めたモノリポジトリ構成になっています。

---

## プロジェクト概要

- 名前: KabuSys
- 目的: 日本株の自動売買システムのコアロジック（発注、リスク制御、監視、バックテスト/リサーチ補助、AI によるニュースセンチメント評価）を提供する。
- 言語: Python（型ヒントあり、Python 3.10+ を想定）
- 永続化:
  - SQLite（監視ログ・発注ログなど）
  - DuckDB（時系列データ・リサーチ向け）
- 設計方針:
  - モジュールは可能な限り純粋関数または I/O を明確化したクラスに分離
  - Paper Trading（検証用）と Live（本番）を環境変数で切替
  - OpenAI を用いる機能は API キー必須。失敗時はフェイルセーフで継続する実装が多い

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine、OrderManager、Reconciler を備え、発注・状態同期・再起動時のリコンシリエーションを行う
  - paper_trading 環境では MockBroker を利用し、本番 DB と分離して data/paper_trading.db に記録

- Monitoring（監視）
  - SystemMonitor: CPU/MEM/DISK・プロセス生存・データ鮮度の監視
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン／ポジション上限の監視とリスクログ記録
  - MonitoringEngine: 各モニタを束ねて周期ポーリング
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウン付き）
  - KillSwitch: 条件に応じて data/kill.flag を書いて ExecutionEngine を停止させる

- Portfolio（ポートフォリオ構築）
  - 候補選定、重み付け（等金額・スコア重み）、セクター上限適用、ポジションサイズ計算（単元株丸め・リスクベース等）

- Research（リサーチ）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI 統合）
  - news_nlp: ニュース記事を LLM に送り銘柄ごとのセンチメントを算出して ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（監視ダッシュボード）

- ユーティリティ
  - process_priority（プロセス優先度 / CPU affinity 設定）
  - 環境設定 loader（.env 自動ロード、Settings クラス）

---

## 動作環境 / 依存ライブラリ（例）

- Python 3.10+
- 必要な外部パッケージ（主なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite は標準ライブラリで利用

インストール例（仮、プロジェクトの requirements.txt を用意していない場合）:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit

4. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動読み込みされます（既存 OS 環境を上書きしない挙動）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: 必須（Settings.jquants_refresh_token）
     - KABU_API_PASSWORD: 必須（kabuステーション API）
     - OPENAI_API_KEY: OpenAI を使う機能で必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

5. ディレクトリ data の作成
   - data フォルダを作成しておくと PID / flag ファイルが利用しやすい:
     - mkdir -p data

注: Settings は起動時に .env / .env.local をプロジェクトルートから自動で読み込みます（CWD に依存しない探索）。見つからない場合は自動読み込みをスキップします。

---

## 使い方

### 実行（Execution Engine）
- 実行スクリプト: src/kabusys/run_execution.py
- 使い方（デフォルトで Settings に従い起動します）:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
  - 起動時に data/execution.pid に PID を書き込む（Settings.pid_file_path）
  - data/stop_requested.flag が存在すると起動・実行中に停止します（kill.flag とは別）
  - リスク設定は RiskConfig で初期化（コード内にデフォルト値あり）

### 監視（Monitoring）
- 監視スクリプト: src/kabusys/run_monitoring.py
- 実行:
  - python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- 動作:
  - SystemMonitor / TradeMonitor / RiskMonitor を使い定期チェックし、Monitoring DB（Settings.sqlite_path）へログを残す
  - KillSwitch がトリガー条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）を書き込み、ExecutionEngine の停止を促す
  - AlertManager を組み合わせれば LINE 通知が可能

### Streamlit ダッシュボード（監視可視化）
- ファイル: src/kabusys/monitoring/streamlit_dashboard.py
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 機能:
  - ダッシュボード集計、ポジション一覧、最近の発注ログ、最新のシステムステータス、最近のリスクログを表示

### Paper Trading 検証レポート
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 実行例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- 出力:
  - 期間内の稼働率、注文成功率、送信率、レイテンシ指標を算出し PASS/FAIL を判定する

### AI 機能（ニューススコア / レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡し、指定日向けのニュースを LLM でスコアリングして ai_scores テーブルへ書込
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY
- regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ書込
- 実行例（簡易、Python REPL）:
  - from datetime import date
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, date(2026,4,1), api_key="sk-...")

注意: OpenAI を使う処理は API 呼び出しの失敗に対してフォールバック設計がされていますが、APIキーが未設定だと例外を投げる処理もあります（明示的に api_key を渡すか OPENAI_API_KEY を設定してください）。

---

## 主要ファイル / コマンドまとめ

- 実行:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

## ディレクトリ構成

（主要ファイルを抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード）
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - data/                     — （実行時に使用される想定のディレクトリ）
    - execution.pid
    - kill.flag
    - stop_requested.flag
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py      — （エンジン本体、他ファイルと連携）
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_repository.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

---

## 運用上の注意 / 補足

- KABUSYS_ENV により動作モードが切り替わります。paper_trading を使うと本番データベースを汚さず検証できます。
- run_execution / run_monitoring はデーモン化やプロセスマネージャ（systemd など）と組み合わせて運用してください。PID ファイルや stop/kill フラグが起動制御に使われます。
  - stop flag: data/stop_requested.flag — run_* スクリプトは存在を検出すると終了します
  - kill flag: data/kill.flag — KillSwitch が書き込むことで ExecutionEngine 側で停止判定に使用
- Settings は .env/.env.local の自動ロードを行います。OS 環境を上書きしない工夫がありますが、テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分はレート制限や 5xx に対して指数バックオフでリトライする実装が含まれますが、APIコストや使用制限には注意してください。

---

この README はコードベースの公開 API と運用の概要を示しています。詳細な設計や API の振る舞いは各モジュールの docstring を参照してください。README に含めてほしい追加情報（CI・テスト実行手順・推奨設定など）があれば教えてください。