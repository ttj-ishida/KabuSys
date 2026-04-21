# KabuSys — README (日本語)

バージョン: 0.1.0

概要
---
KabuSys は日本株向けの自動売買システムのライブラリ群および起動スクリプト群です。本プロジェクトは以下の用途を想定しています。
- 発注エンジン（ExecutionEngine）の起動と管理（本番 / ペーパートレード対応）
- システム監視（SystemMonitor / MonitoringEngine）
- 取引・リスクの監視と Kill Switch
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ決定）
- リサーチ用ファクター計算・特徴量探索（DuckDB ベース）
- ニュース NLP（OpenAI を使用したセンチメント評価）
- ペーパートレード検証レポート生成ツール

主な機能
---
- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV によりペーパートレード用の MockBroker を使用）
  - run_monitoring: SystemMonitor のポーリングループを起動
- 設定管理
  - config_setup: 対話式ウィザードで .env を生成/更新
  - validate_config: .env と config/*.yaml の事前検証（--strict オプションあり）
- モニタリング
  - system_monitor / trade_monitor / risk_monitor を束ねる MonitoringEngine
  - monitoring_db: SQLite に監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）を永続化
  - KillSwitch: 条件に応じて data/kill.flag を作成し ExecutionEngine を停止
- ポートフォリオ構築
  - 候補選定、等重／スコア加重、セクター制約、リスクベースポジションサイズ計算
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターンや IC、統計サマリの算出（DuckDB 接続で SQL 処理）
- AI（OpenAI）
  - news_nlp: ニュース記事を LLM でスコアリングし ai_scores に保存
  - regime_detector: ETF とマクロニュースから市場レジーム判定を実行
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート出力

セットアップ
---
前提
- Python 3.9+ を推奨（コードは typing 機能を利用）
- システムに duckdb, psutil, openai 等がインストールされる必要があります。

推奨手順（簡易）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （validate_config の YAML 検証を使う場合）pip install PyYAML

   ※プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用してください。

3. 環境変数（.env）設定
   - 対話式で作成: python -m kabusys.config_setup
   - もしくは .env ファイルを手動で作成（以下に最小例）

.env の最小例
```
# 実行環境
KABUSYS_ENV=development

# 必須（実運用では実トークン/パスワードを設定）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here

# データベース（デフォルト）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# ログ
LOG_LEVEL=INFO

# Kill Switch 自動クリア（開発時のみ 1）
KILL_FLAG_CLEAR_ON_START=0
```

重要環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- OPENAI_API_KEY: news_nlp / regime_detector が必要とする場合
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用の SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH / SQLITE_PATH: データベースパス
- LOG_LEVEL: ログレベル
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env ロード
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env/.env.local を自動ロードします。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設定検証
- python -m kabusys.validate_config
- 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

使い方
---
起動スクリプト（プロセス管理の想定）
- ExecutionEngine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録して本番 DB と完全分離されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動しません。
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止します（stop フラグ）。
  - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は KillSwitch により作成され、ExecutionEngine に停止要求を送ります。

- Monitoring（システム監視）起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用します。

ログ
- デフォルトログディレクトリ: logs/
- setup_logging() により stdout と日次ローテートファイル（logs/<app_name>.log）へ出力されます。
- LOG_DIR 環境変数で変更可能

ペーパートレード検証レポート
- sqlite（ペーパートレード DB）を解析してレポートを作成:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 短い要点: 稼働率、注文成功率、送信率、レイテンシ（P95）などを判定し PASS/FAIL を出力

AI / OpenAI 関連
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（duckdb.connect(... ) の返り値）を渡して実行
  - OPENAI_API_KEY が必要（引数 api_key で上書き可）
  - ai_scores テーブルへスコアを保存
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA とマクロニュースの LLM 評価を合成して market_regime に保存
- API 呼び出しはリトライおよびフェイルセーフロジックを含みます（エラー時はゼロフォールバック等）

データベース
- DuckDB: 分析用（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）
- SQLite: 監視ログ・トレードログ（monitoring.db / paper_trading.db）
- init_monitoring_db(conn) によってテーブル作成・簡易マイグレーションを自動実行します

停止・Kill Switch
- 実行停止フラグ: data/stop_requested.flag（run_execution/run_monitoring が監視）
- Kill Switch: data/kill.flag を書き込み ExecutionEngine に停止シグナル
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）

ディレクトリ構成（抜粋）
---
プロジェクトの主要ファイル／モジュール構成（src/kabusys 以下を中心に）

- src/kabusys/
  - __init__.py                     パッケージ定義（__version__ 等）
  - config.py                        環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py                  .env 対話式ウィザード
  - validate_config.py               起動前の設定検証ツール
  - run_execution.py                 ExecutionEngine 起動スクリプト
  - run_monitoring.py                SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py    ペーパートレード検証レポート生成
  - monitoring/
    - monitoring_db.py               SQLite 永続化層（テーブル作成 / CRUD）
    - system_monitor.py              システム状態 / データ鮮度監視
    - trade_monitor.py               (取引監視ロジック)
    - risk_monitor.py                ドローダウン・ポジション上限監視
    - monitoring_engine.py           各モニタを束ねたエンジン
    - kill_switch.py                 Kill Switch 実装
    - alert_manager.py               (通知管理)
  - execution/                       （発注エンジン関連）
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py           候補選定・重み算出
    - position_sizing.py             株数計算・制約適用
    - risk_adjustment.py             セクターキャップ・レジーム乗数
  - research/
    - factor_research.py             ファクター計算（momentum/value/vol）
    - feature_exploration.py         将来リターン / IC / summary
  - ai/
    - news_nlp.py                    ニュース NLP スコアリング（OpenAI）
    - regime_detector.py             市場レジーム判定（OpenAI）
  - utils/
    - logging_setup.py               ログ設定ユーティリティ
    - process_priority.py            プロセス優先度 / CPU affinity
  - data/                            デフォルトデータフォルダ（logs, db, flag 等を保持）

注意事項 / 運用メモ
---
- 本番運用時は KABUSYS_ENV=live を明示し、LINE 通知や kill flag の設定を必ず確認してください。
- .env は機密情報を含むため絶対に Git にコミットしないこと。
- run_monitoring は監視 DB（SQLite）を使用します。Monitoring は本番 sqlite_path を参照する点に注意してください（設定上の分離に依存するコードがあるため）。
- run_execution は KABUSYS_ENV=paper_trading の場合にペーパートレード用 DB を使用して本番 DB と分離します。
- OpenAI を利用する機能は API 料金とレート制限を考慮してください。リトライ・クリップ・フェイルセーフ処理を実装していますが、コストは発生します。
- DuckDB のスキーマやテーブル（prices_daily / raw_financials / raw_news 等）は別途データ投入パイプライン/ETL が必要です（本リポジトリにはデータ取り込みスクリプトは含まれません）。

貢献 / 開発
---
- コードはモジュール単位で分離され、ユニットテストが書きやすい設計です（外部 API 呼び出しは抽象化されている箇所が多い）。
- テスト時は環境変数自動読み込みを無効にする（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）ことを推奨します。
- OpenAI 呼び出しや外部依存はモック化してテストしてください（コード内で _call_openai_api などを patch 可能）。

ライセンス
---
（該当リポジトリに記載されているライセンスに従ってください）

お問い合わせ
---
実装・運用に関する質問があれば、プロジェクトのイシューや担当チームに問い合わせてください。

以上。