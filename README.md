# KabuSys — README

日本株自動売買フレームワーク (KabuSys) の簡易 README です。  
このドキュメントはリポジトリ内の実装（src/kabusys 以下）を元に作成しています。

目次
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 環境変数（.env）
- 使い方（起動スクリプト・ツール）
- 運用上の注意点
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースのフレームワークです。  
主なコンポーネントは以下です。

- ExecutionEngine: 発注管理・注文実行（本番 / ペーパートレード対応）
- Monitoring: システム状態・注文状態・リスクを監視しアラートや Kill Switch を制御
- Portfolio: 銘柄選定、重み付け、株数算出（純粋関数群）
- Research: ファクター計算・特徴量探索・IC 計算
- AI モジュール: ニュースの NLP スコアリング、マーケットレジーム判定（OpenAI API を利用）
- Tools: Paper Trading の検証レポート生成など

設計上、DuckDB は分析/研究用、SQLite は監視・発注ログ用に利用します。ペーパートレード時は本番 DB と分離されます。

---

## 主な機能一覧

- 環境ごとの設定管理（.env 自動読み込み / 対話式ウィザード）
- ExecutionEngine（本番 / paper_trading 切替、MockBroker 対応）
- Monitoring: SystemMonitor / TradeMonitor / RiskMonitor を統合する監視エンジン
- Kill Switch: ドローダウンやポジション上限の閾値超過で停止フラグを書き込み Execution を停止
- ログ管理: コンソール + 日次ローテーションファイル（logs/*.log）
- Portfolio コンポーネント: 候補選定・重み付け・リスク調整・株数算出
- Research: Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
- AI: ニュースセンチメントとレジーム判定（OpenAI API 使用、リトライ/バックオフ実装）
- Tools: Paper Trading の検証レポート生成（成功率・レイテンシ・稼働率など）

---

## 必要条件

- Python 3.9+
- 推奨ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証に利用、必須ではない）
- その他: ネットワーク接続（kabuAPI / OpenAI を使う場合）

（実際の requirements はプロジェクトで配布される requirements.txt を参照してください）

---

## セットアップ手順（ローカル開発向けの基本）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants / kabuAPI / DB パス / LOG_LEVEL など主要変数を順に聞きます。
   - 生成された .env は絶対にバージョン管理にコミットしないでください。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います。

6. DB は起動スクリプトが必要に応じて初期化します（monitoring 用のテーブルは init_monitoring_db により作成されます）。

---

## 主要な環境変数（.env）

重要な環境変数（デフォルト・用途を簡潔に示します）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI を使う場合に必須（ai/news_nlp, ai/regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN — 任意（アラート通知）
- LINE_USER_ID — 任意（アラート通知先）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（production 監視用）デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）デフォルト: INFO
- LOG_DIR — ログファイル格納ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0、本番は 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）※ run_monitoring で使用

（.env は config_setup により簡単に生成できます）

---

## 使い方（起動スクリプト・ツール）

各モジュールはパッケージモジュールとして実行できます（python -m ...）。

- 環境ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - 起動時に data/execution.pid に PID を書く（設定により変更）
    - 停止フラグ: data/stop_requested.flag が存在するとエンジンを停止
    - Kill Switch (data/kill.flag) が存在すると起動に影響する設定もあるので注意

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（デフォルト 60 秒）
    - monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path（SQLITE_PATH）を使用してログを残します
    - 停止フラグ: data/stop_requested.flag を検知してループを終了

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数 > デフォルト data/paper_trading.db）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ、最終判定 PASS/FAIL

- AI モジュール（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY 必須（引数 api_key で明示可）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 運用上の注意点

- Kill Switch / stop フラグ
  - Kill Switch は data/kill.flag に理由を書き込みます。ExecutionEngine は kill.flag を検知して停止する設計です。
  - stop_requested.flag（data/stop_requested.flag）は run_monitoring / run_execution が外部から停止するために監視するフラグです。
  - 本番環境で KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアしますが、本番では 0 を推奨します。

- ログ
  - デフォルトは logs/<app_name>.log（タイムローテート、30日分保持）
  - 権限やディレクトリ作成に失敗した場合、コンソール出力のみで継続します

- データベース
  - monitoring の初期化は init_monitoring_db によって行われます（冪等）
  - Paper Trading と本番の SQLite DB は分離するよう設計されています（settings.is_paper 判定）

- OpenAI（AI モジュール）
  - API 呼び出しにはリトライ / バックオフが実装されていますが、API キーと利用料に注意してください
  - レスポンスのバリデーションを行っており、失敗時は部分的にスキップして安全に継続します

---

## ディレクトリ構成（主要ファイルの説明）

リポジトリの主要な構造（src/kabusys を起点）:

- kabusys/
  - __init__.py
  - config.py — 環境変数・Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py — .env の対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — マーケットレジーム判定（MA200 + LLM マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite の監視テーブル初期化・読み書きラッパー
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （該当ファイルあり）注文滞留・約定異常検出（コードベース参照）
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - monitoring_engine.py — 各 Monitor を統合してループするエンジン
    - kill_switch.py — kill.flag の書き込み/判定ユーティリティ
    - alert_manager.py — （アラート送信を担う想定のモジュール）
  - execution/
    - execution_engine.py — ExecutionEngine（メインロジック）
    - broker_factory.py — Broker クライアントの生成（本番/Mock 分岐）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注周りのコンポーネント群
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出・aggregate cap ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB 上）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - data/ (実行時に作成される想定)
    - monitoring.db など
    - paper_trading.db
    - kill.flag / stop_requested.flag / execution.pid
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - utils/
    - logging_setup.py — ルートロガーの初期化（stdout + 日次ファイルローテート）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は実コードの意図を要約したもので、細かなファイルは実際のツリーを参照してください）

---

## よくある運用コマンドまとめ（例）

- .env を生成
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config

- 監視を起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution を起動（paper_trading の例）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - またはパス指定: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

README は以上です。実運用前に必ず:
- .env を正しく設定する
- validate_config で設定チェックを行う
- 本番（KABUSYS_ENV=live）での Kill Switch / LINE 通知設定を再確認する

必要があれば、この README をベースに導入ガイド（デプロイ、systemd / Supervisor 設定例、監視ダッシュボード連携など）を追記できます。必要な項目を教えてください。