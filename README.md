# KabuSys — 日本株自動売買システム

簡易説明  
KabuSys は日本株の自動売買を想定したモジュール型システムです。注文実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの機能を持ち、ローカル開発・ペーパートレード・本番（live）を切り替えて運用できます。

主な設計方針
- モジュール化（Execution / Monitoring / Portfolio / Research / AI / Utils）
- DBは DuckDB（分析）と SQLite（監視・履歴保存）を併用
- 本番とペーパートレードで DB を分離
- OpenAI を使った NLP 機能は外部 API キーを利用（故障時はフェイルセーフ）
- ログは統一的に設定（stdout と日次ローテーションファイル）

---

## 機能一覧
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレードを切替可能（KABUSYS_ENV）
  - ブローカークライアントの抽象化（MockBroker を含む）
  - オーダー管理・リスク管理・リコンサイル機能を含む
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働・データ鮮度監視
  - TradeMonitor: 注文の滞留・約定異常などの検出（trade_logs 参照）
  - RiskMonitor: ドローダウンやポジション上限監視、kill switch 連動
  - MonitoringEngine: 各モニタの集約・ポーリング・アラート発行
- Portfolio（銘柄選定・配分・ポジションサイズ計算）
  - 候補選択・等分 / スコア重み・リスクベースの株数決定
  - セクターキャップ・レジーム乗数
- Research（ファクター計算・特徴量探索）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 上の prices_daily 等を利用）
  - 将来リターン、IC、統計サマリー
- AI（OpenAI 利用の機能）
  - news_nlp: ニュース記事を集約して LLM でセンチメント評価 → ai_scores に保存
  - regime_detector: ETF 等の MA とマクロニュースを LLM で評価して日次の市場レジーム判定
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前設定検証 CLI（YAML の簡易検査は PyYAML 必須）
  - paper_verification_report: ペーパートレード履歴から検証レポート生成

---

## 必要要件（例）
- Python 3.9+
- 主要パッケージ（例、環境に応じて pip 等でインストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config の YAML 検証を利用する場合）
- SQLite は標準ライブラリで利用可能

（requirements.txt は本リポジトリに含まれていないため、上記パッケージを手動でインストールしてください）

---

## セットアップ手順（基本）
1. リポジトリをクローン / 展開
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - python -m kabusys.config_setup
   - または手動で作成（下記「環境変数例」参照）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）
6. データディレクトリの準備（デフォルト）
   - data/ （SQLite・PID・flag 等が配置されます）
   - logs/ （ログファイルが出力されます）

---

## 環境変数（主なもの）
必須（基本起動に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
- KABU_API_PASSWORD: kabuステーション API パスワード

必須（AI 機能を使う場合）
- OPENAI_API_KEY: OpenAI API キー

その他（推奨）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading: ブローカーは MockBroker を使用し DB は data/paper_trading.db を使用
  - live: 本番
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知（任意）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）

簡単な .env の例
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

※ .env は決してリポジトリにコミットしないでください。

---

## 使い方（コマンド・起動例）
全てパッケージモジュールとして実行します（プロジェクトルートで実行）。

1. 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

3. Execution エンジン起動（本番 / ペーパー）
   - python -m kabusys.run_execution
   - 動作:
     - プロセス優先度を High に設定し、SQLite / DuckDB に接続
     - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用し MockBrokerClient が利用される
     - 停止: data/stop_requested.flag の検出で停止。PID を data/execution.pid に書きます

4. Monitoring 起動（監視ループ）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔秒数を上書き可能（デフォルト 60）
   - 監視は Settings.sqlite_path を常に使用（KABUSYS_ENV にかかわらず本番の monitoring DB を参照）
   - 停止: data/stop_requested.flag を作成すると監視ループが終了します

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可能

6. AI 機能（コード呼び出し）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続と target_date（date オブジェクト）を渡す
     - api_key を None にすると環境変数 OPENAI_API_KEY を使用
   - regime_detector.score_regime(conn, target_date, api_key=None)

ログ:
- ログは logs/<app_name>.log に日次ローテーションで出力されます（app_name は run 実行時に "execution" / "monitoring" 等が設定されます）
- コンソール出力は stdout に書かれます

停止・Kill スイッチ:
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（監視側が条件を検出して書き込む）
- run_monitoring / run_execution は data/stop_requested.flag の存在を見て安全にシャットダウンします
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を起動時にクリアします（本番では推奨されません）

---

## 開発上の注意点
- validate_config は config/*.yaml の存在をチェックします。YAML の中身検証には PyYAML が必要です。
- DuckDB クエリは prices_daily / raw_financials / raw_news 等のテーブル構造に依存します。DB スキーマの準備が必要です（分析データはプロジェクト外で準備する想定）。
- AI 機能は OpenAI の呼び出しを行うため、API キーの管理とコストに注意してください。API 呼び出しはリトライ・バックオフ実装済みでフェイルセーフ設計です。
- process_priority でプロセス優先度を上げますが、権限不足で設定できない場合はログ警告が出て処理は継続します。

---

## ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py — 環境変数読み込み / Settings
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI 使用）
  - regime_detector.py — 市場レジーム判定（OpenAI 使用）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定ロジック
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 将来リターン・IC・統計
- monitoring/
  - monitoring_db.py — SQLite テーブル定義・永続化 API
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （滞留注文等の検出、コード内に実装）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の読み書き
  - monitoring_engine.py — 監視を束ねるエンジン
  - alert_manager.py — アラート送信（LINE 等、コード参照）
- execution/
  - execution_engine.py — 実行エンジン本体（run_session 等）
  - broker_factory.py — ブローカークライアント生成
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注周りコンポーネント
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/monitoring_db.py — SQLite スキーマと MonitoringDB クラス
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成ツール

（上記は主要ファイルの抜粋です。詳しくはソースコードを参照してください）

---

必要に応じて README に追記します。起動方法や .env のテンプレート、データベーススキーマやサンプルデータの作成手順を補足しますか？