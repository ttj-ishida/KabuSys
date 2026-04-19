# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。  
この README はソースコード（src/kabusys）に基づき作成しています。セットアップ手順、主要機能、使い方、ディレクトリ構成などを日本語でまとめます。

---

概要
---
KabuSys は日本株向けの自動売買システムです。注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ用ファクター計算、AI（ニュースに基づくセンチメント評価・市場レジーム判定）等のコンポーネントを含みます。設計方針としては「本番データと研究/ペーパートレードを分離」「DB は SQLite / DuckDB を使用」「LLM 呼び出しはフェイルセーフ設計（リトライ・部分失敗保護）」などが採用されています。

主な機能
---
- ExecutionEngine（発注エンジン）
  - 本番およびペーパートレード（KABUSYS_ENV=paper_trading）に対応
  - Broker クライアントを抽象化するファクトリ（MockBroker を利用可能）
  - リスク管理（RiskManager）、OrderManager、Reconciler 等と連携

- Monitoring（監視）
  - システムリソース（CPU/MEM/DISK）・Execution プロセス監視
  - 注文ログ / 約定・滞留注文のチェック
  - ドローダウンやポジション上限の監視と Kill Switch（停止フラグ）出力
  - 監視ログを SQLite に永続化（monitoring.db）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分・スコア加重配分、ポジションサイズ計算
  - セクターキャップ、レジームによる乗数適用などのリスク調整

- Research（リサーチ）
  - DuckDB を用いたファクター計算（Momentum、Value、Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（ai_scores への書込み）
  - マクロニュースと ETF MA を合成した市場レジーム判定（market_regime テーブルに書込み）
  - API 呼び出しはリトライ/バックオフ実装、部分的失敗は他データを保護して継続

- ツール
  - Paper Trading の検証レポート生成ツール（tools/paper_verification_report.py）
  - .env 作成ウィザード（config_setup）と設定検証 CLI（validate_config）

セットアップ手順
---
前提
- Python 3.10 以上を推奨（ソースは型注釈・modern syntax を使用）
- SQLite は標準ライブラリ、DuckDB は外部パッケージ（以下参照）

インストール（例）
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - 任意: PyYAML（config/*.yaml の内容検証を行う場合）: pip install pyyaml

（注）プロジェクトに requirements.txt が無い場合は上記パッケージを個別にインストールしてください。

.env（環境変数）設定
1. 対話式ウィザードで作成:
   - python -m kabusys.config_setup
   - ウィザードは .env を生成します（デフォルト: リポジトリルート/.env）。出力は .env に保存されます。

2. 設定の検証:
   - python -m kabusys.validate_config
   - 必須項目未設定やパスの問題を事前に検出できます。
   - --strict を付けると警告も失敗扱いになります。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合は MockBroker を使い、データは data/paper_trading.db に分離記録されます
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL, LOG_DIR 等

使い方（起動/実行）
---
ログ設定
- 全コンポーネントは共通の logging 設定ユーティリティを使用します。
  - ログディレクトリデフォルト: logs/
  - アプリごとに logs/<app_name>.log に日次ローテーションで出力されます

主要 CLI / モジュール
- ExecutionEngine を起動（本番 / ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録します
  - 実行中は data/execution.pid に PID を書く（設定の pid_file を参照）

- Monitoring を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず）

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告もエラーに昇格（exit 1）

- .env 作成ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止・Kill Switch
- ExecutionEngine の停止はフラグファイルを使います:
  - data/kill.flag を作成するとエンジン側が停止シグナルとして検出します（KillSwitch）
  - monitoring は条件に応じて kill.flag を書き込む設計（drawdown やポジション上限等）
  - デバッグ的な強制停止には data/stop_requested.flag を使うスクリプトも存在します（起動スクリプトが参照）

その他の注意点
- AI 機能（news_nlp, regime_detector）は OPENAI_API_KEY を要求します。未設定の場合は ValueError を投げます（ただし失敗時はフェイルセーフでスコア 0.0 を使用する箇所もあります）。
- DuckDB 接続は分析・リサーチ用途に使用します。prices_daily / raw_financials / raw_news 等のテーブルを参照します。
- SQLite は監視・トレードログ用に使用。init_monitoring_db() でテーブルの初期化・軽いマイグレーションを行います。

ディレクトリ構成（抜粋）
---
src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings 管理、自動 .env ロード機能
- config_setup.py — .env 対話ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ（主なファイル）
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — マクロニュース + ETF MA 合成で市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite に対する永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/MEM/DISK・データ鮮度・プロセス監視
  - trade_monitor.py — （注文ログ / 約定監視）※ファイル参照あり
  - risk_monitor.py — ドローダウン・ポジション上限検知
  - kill_switch.py — kill.flag の生成/確認
  - monitoring_engine.py — 各モニタを束ねる Engine
  - alert_manager.py — （アラート通知管理）※実装参照
- execution/
  - execution_engine.py — ExecutionEngine（発注セッション制御）
  - broker_factory.py — Broker クライアントの生成（実ブローカー / mock）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行に必要なサブコンポーネント
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・資金配分・丸め
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成ツール
- utils/
  - logging_setup.py — 共通ログ設定（コンソール + 日次ローテート）
  - process_priority.py — プロセス優先度 / CPU affinity 設定（psutil 利用）

サンプル .env（主要項目）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- OPENAI_API_KEY=sk-xxxx
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

よくある運用フロー（例）
1. 仮想環境を用意して依存をインストールする
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定を確認
4. データベース（DuckDB/SQLite）に必要なテーブル・データを用意
5. python -m kabusys.run_execution を起動（または systemd / supervisor でデーモン化）
6. python -m kabusys.run_monitoring を別プロセスで起動して監視・Kill Switch を有効化
7. 必要に応じて AI スコアリング（kabusys.ai.score_news）やレジーム判定（kabusys.ai.score_regime）を定期的に実行

補足・開発者向けメモ
- config._find_project_root() は .git / pyproject.toml を探してプロジェクトルートを特定します。これにより .env 自動読み込みが CWD に依存せず動作します。
- .env の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます（テスト時に有用）。
- Logging はアプリ名（例: "execution" / "monitoring"）で logs/<app_name>.log に出力されます。ログディレクトリが作成できない場合はコンソール出力のみになります。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能。0 以下の値は無効扱いでデフォルト 60 秒にフォールバックします。

ライセンス・貢献
---
（このリポジトリにライセンス情報がない場合はプロジェクト固有のライセンスに従ってください）

---

README の内容や起動方法の詳細は、実際の運用環境やデプロイ構成（systemd / container / k8s など）に合わせて適宜調整してください。必要であれば、この README をベースに手順書（systemd unit 例、Dockerfile、CI/CD 設定）も作成できます。