KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）の主要コンポーネント群を含みます。
主な役割は以下のとおりです。

- ExecutionEngine：発注・約定管理・リスク管理を担うエンジン
- Monitoring：システム状態・注文状況・リスクを定期監視しアラート/Kill Switch を管理
- Portfolio / Research：銘柄選定、重み付け、特徴量計算などのアルゴリズム群
- AI モジュール：ニュースを LLM（OpenAI）でスコアリングしてレジーム判定やシグナルに利用
- Tools：ペーパートレード検証レポートなどのユーティリティ

以下、本プロジェクトの README（日本語）です。

概要
----
KabuSys は、ローカル環境で実行可能な日本株自動売買システムの骨格を提供します。
設計方針として「本番 DB とペーパートレーディング DB の分離」「外部 API 呼び出しを明示的に制御」「監視と Kill Switch による安全停止」が盛り込まれています。

主な機能
--------
- ExecutionEngine 起動 / 発注ロジック（paper_trading モードは MockBroker を使用して DB に記録）
- Monitoring：CPU/メモリ/ディスク、Execution プロセス稼働確認、データ鮮度チェック、注文滞留/約定異常監視
- Kill Switch：条件により data/kill.flag を書き込み ExecutionEngine を停止させる仕組み
- Risk 管理：ドローダウン検出やポジション上限監視とログ記録
- Portfolio 構築：候補選定、等配分/スコア加重、ポジションサイズ計算（単元丸め含む）
- Research：DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー）や特徴量探索
- AI：OpenAI を利用したニュースセンチメント（ai_scores）・レジーム判定（market_regime）
- ユーティリティ：.env 設定ウィザード、設定検証 CLI、Paper Trading 検証レポート作成スクリプト
- ロギング：標準化された logging セットアップ（コンソール + 日次ローテートファイル）

セットアップ手順（ローカル）
--------------------------
前提
- Python 3.10 以上（型注釈の | を利用しているため）
- SQLite（標準ライブラリに含まれます）
- 推奨パッケージ：duckdb, psutil, openai, PyYAML（YAML 検証は任意）

例:
1. リポジトリをクローンし仮想環境を作成
   - git clone <repo>
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （実行環境によっては追加の依存やバージョン固定が必要。requirements.txt があればそれを利用してください。）

3. .env を作成
   - 対話式ウィザードで作る（推奨）:
     - python -m kabusys.config_setup
   - ウィザードで生成した .env を編集して必要な値を確認する

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります: python -m kabusys.validate_config --strict

5. データ・ログ用ディレクトリ（通常は自動作成されますが事前に用意しておくと権限系トラブルを避けられます）
   - mkdir -p data logs

重要な環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 選択 / デフォルトあり:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
  - PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）。デフォルト: instant
  - OPENAI_API_KEY — AI モジュールを使う場合に必要
  - LOG_LEVEL, LOG_DIR
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)。本番では 0 推奨

自動 .env 読み込み
- プロジェクトルートにある .env / .env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（よく使うコマンド）
-----------------------

1) 設定ウィザード
   - python -m kabusys.config_setup

2) 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

3) ExecutionEngine を起動
   - 通常（開発 / 本番）:
     - python -m kabusys.run_execution
     - KABUSYS_ENV を切り替えて本番/ペーパーを指定（例: KABUSYS_ENV=paper_trading python -m kabusys.run_execution）
   - ペーパートレード時は MockBrokerClient を使用し、ペーパートレード用 DB (data/paper_trading.db または PAPER_TRADING_SQLITE_PATH) に記録されます。

4) Monitoring を起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔を上書きするには環境変数 MONITOR_POLL_INTERVAL（秒）を設定します（デフォルト 60）。
     例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

5) Paper Trading 検証レポート生成ツール
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を直接指定:
     - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

停止・Kill
- run_monitoring.py / run_execution.py はプロセスを停止させるためのフラグファイルを監視します。
  - data/stop_requested.flag — run_*.py のポーリングループを終了させるための外部制御フラグ（存在を検出するとループを抜ける）。
  - data/kill.flag — KillSwitch の発動で ExecutionEngine を停止させるために作成されるフラグ。手動で作成することで強制停止させることも可能（例: echo "reason" > data/kill.flag）。
  - フラグの削除は rm data/kill.flag（または KillSwitch.clear() を呼ぶ実装）で行います。
- ExecutionEngine 側では起動時に KILL_FLAG_CLEAR_ON_START 設定を参照して自動クリアするかどうかを決められます（本番では自動クリアを無効化することを推奨）。

AI（OpenAI）機能
- news_nlp や regime_detector は OpenAI API（gpt-4o-mini 等）を用います。使用には OPENAI_API_KEY が必要です。
- API 呼び出しは冪等性やリトライ（指数バックオフ）を考慮した実装になっていますが、API 利用料やレート制限には注意してください。

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30 日保持）。コンソール出力は stdout に出ます。
- LOG_DIR / LOG_LEVEL で挙動を変更できます。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下の主要ファイルと簡単な説明）

- src/kabusys/__init__.py
  - パッケージ定義、バージョン情報

- 起動スクリプト
  - src/kabusys/run_execution.py — ExecutionEngine 起動スクリプト
  - src/kabusys/run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- 設定関連
  - src/kabusys/config.py — Settings クラス（環境変数・.env ロード）
  - src/kabusys/config_setup.py — .env 対話式ウィザード
  - src/kabusys/validate_config.py — 設定検証 CLI

- Execution / 発注関連（ディレクトリ）
  - src/kabusys/execution/（OrderManager, RiskManager, ExecutionEngine 等 — 実装ファイル群）

- Monitoring（監視）
  - src/kabusys/monitoring/monitoring_db.py — SQLite DB 初期化 & 永続化層
  - src/kabusys/monitoring/system_monitor.py — CPU/メモリ/データ鮮度チェック
  - src/kabusys/monitoring/trade_monitor.py — 注文関連監視（滞留・異常）
  - src/kabusys/monitoring/risk_monitor.py — ドローダウン・ポジション上限
  - src/kabusys/monitoring/kill_switch.py — Kill Switch 実装
  - src/kabusys/monitoring/monitoring_engine.py — 各モニタを束ねる

- Portfolio（銘柄選定・サイズ計算）
  - src/kabusys/portfolio/portfolio_builder.py
  - src/kabusys/portfolio/position_sizing.py
  - src/kabusys/portfolio/risk_adjustment.py

- Research（DuckDB を用いたファクター計算）
  - src/kabusys/research/factor_research.py
  - src/kabusys/research/feature_exploration.py

- AI（OpenAI 連携）
  - src/kabusys/ai/news_nlp.py — ニュース NLP スコアリング（ai_scores）
  - src/kabusys/ai/regime_detector.py — レジーム判定（market_regime）

- Utils
  - src/kabusys/utils/logging_setup.py — 統一的なログ設定
  - src/kabusys/utils/process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- Tools
  - src/kabusys/tools/paper_verification_report.py — ペーパートレード検証レポート

サンプル .env（最小）
--------------------
以下は .env に最低限入れておくべき項目の例（.env.example を参考にしてください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx...   # AI 機能を使う場合

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では必須設定と通知設定（LINE 等）を必ず確認してください。validate_config によるチェックを実行してください。
- kill.flag や stop_requested.flag を不用意に操作すると発注プロセスが停止します。運用手順を運用担当で明確にしてください。
- OpenAI 等の外部 API を用いる機能はコスト・レイテンシの観点で管理が必要です。
- データベースパス（DuckDB/SQLite）は適切なバックアップ・権限設定を行ってください。

開発・拡張
----------
- research モジュールは DuckDB 接続を受け取りデータを読みます。分析用データを DuckDB にロードすればローカルで即座に計算可能です。
- AI モジュールは API 呼び出し箇所をモック化しやすい設計です（テストでは _call_openai_api を差し替え可能）。
- ロギングや DB スキーマはマイグレーション対応済みの箇所があります（monitoring_db.py の init_monitoring_db を参照）。

ライセンス / 貢献
----------------
（リポジトリに LICENSE があれば記載してください）

問題報告 / 使い方の質問は issue を立ててください。

付記
----
README に書かれていない細かい挙動（内部のパラメータや閾値など）はソース内の docstring / コメントに詳細が書かれています。実運用前に該当箇所をよく確認してください。