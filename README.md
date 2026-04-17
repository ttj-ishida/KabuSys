# KabuSys

日本株向け自動売買システムの軽量実装（ライブラリ / 実行スクリプト群）。

この README はコードベース（src/kabusys 以下）をもとに作成しています。動作には外部ライブラリや環境変数の設定が必要です。

## 概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 注文実行（ExecutionEngine）とブローカ抽象化（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk の各モニタ）と Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算、将来リターン、IC 計算など）
- ニュース NLP を用いた銘柄スコアリング & 市場レジーム判定（OpenAI を利用）
- 開発支援ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

設計方針のポイント:
- 実行環境（KABUSYS_ENV）による本番/ペーパートレードの分離
- DB（DuckDB / SQLite）を使った分析・監視ログ永続化
- LLM 呼び出しは冪等・フェイルセーフ（リトライ・部分書込み・フォールバック）で実装

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading DB に記録。
  - 起動時にプロセス優先度を設定し、PID ファイルを扱う。停止フラグ（data/stop_requested.flag）で停止可能。

- run_monitoring.py
  - SystemMonitor をポーリング。MONITOR_POLL_INTERVAL（秒）で間隔を指定可（デフォルト 60 秒）。
  - 監視は本番用 sqlite_path を常に使用して監視ログを記録。

- monitoring/*
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution PID の監視とログ化
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクログ化
  - KillSwitch: リスク条件で data/kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringDB: SQLite による監視テーブル群の初期化 / 読み書き

- portfolio/*
  - 候補選定（スコア順）、等分/スコア加重の重み計算
  - セクター上限適用、レジーム乗数、ポジションサイズ計算（lot 単位丸め・aggregate cap）

- research/*
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC（Spearman）計算、統計サマリー

- ai/*
  - news_nlp: OpenAI を使ったニュースベースの銘柄センチメント計算（ai_scores 書込）
  - regime_detector: ETF (1321) の MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
  - LLM 呼び出しはリトライ・JSON 検証・部分書き込みを行いフェイルセーフ化

- tools/paper_verification_report.py
  - Paper Trading の DB から稼働率・注文成功率・レイテンシなどを集計し PASS/FAIL 判定付きレポート出力

- config_setup.py / validate_config.py
  - .env の対話式生成ウィザード
  - 起動前の設定検証 CLI（必須環境変数・YAMLファイル・DBパス等をチェック）

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10+（型ヒントの | を使うため）
- SQLite は標準ライブラリに同梱
- OS により psutil の一部機能が制限される場合あり

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必要パッケージの一例:
     - duckdb
     - psutil
     - openai
     - pyyaml (validate_config の YAML 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合はそれを使用してください:
    pip install -r requirements.txt）

3. 環境変数の設定
   - 推奨: 対話式ウィザードで .env を作成
     - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

4. DB 初期化
   - 実行スクリプト（run_execution / run_monitoring）が内部で必要なテーブルの初期化を行います（monitoring DB は init_monitoring_db を起動時に呼ぶ）。
   - DuckDB 用の分析用 DB は指定したパス（デフォルト data/kabusys.duckdb）に作成されます。

5. OpenAI を使う機能を使う場合
   - OPENAI_API_KEY を .env に設定（news_nlp / regime_detector で参照）
   - API の利用量に注意してください（バッチ処理・リトライ設計あり）

## 使い方（よく使うコマンド）

- .env の作成（対話式ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番／ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - ペーパートレードにするには .env に KABUSYS_ENV=paper_trading を設定
  - 実行中は data/execution.pid（デフォルト）を作成
  - 停止: data/stop_requested.flag を作成すると起動中のスクリプトが検知して停止します

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（例: export MONITOR_POLL_INTERVAL=30）
  - 停止フラグ: data/stop_requested.flag を作成すると監視ループを終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラム経由）
  - kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime を呼び出し可能
  - 両関数は api_key 引数を受け取るか、環境変数 OPENAI_API_KEY を参照

## 主要な環境変数（抜粋・デフォルト）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV (development, paper_trading, live) — デフォルト: development

- DB パス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用)

- ロギング / 制御
  - LOG_LEVEL: INFO
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 0/1

- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring）

- OpenAI
  - OPENAI_API_KEY

- Paper trading 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject  （デフォルト: instant）

（詳しくは src/kabusys/config.py を参照してください）

## 停止・制御ファイル

- data/stop_requested.flag
  - run_execution / run_monitoring が定期的にチェック。存在するとループを停止します。

- data/kill.flag
  - KillSwitch により書き込まれる。ExecutionEngine の外部停止スイッチとして使う想定。

- PID ファイル
  - data/execution.pid（デフォルト）に起動中プロセス PID を書きます。SystemMonitor はこの PID を監視してプロセス停止を検知します。

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定読み込み・検証ロジック
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

- ai/
  - news_nlp.py            — ニュースを LLM で評価して ai_scores に書込
  - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）

- monitoring/
  - monitoring_db.py       — SQLite テーブル作成 / 永続化 API
  - system_monitor.py      — CPU/MEM/DISK / データ鮮度 / PID チェック
  - trade_monitor.py       — 注文滞留 / 約定異常検出
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — Kill Switch 制御
  - monitoring_engine.py   — 各モニタをまとめてポーリング
  - alert_manager.py       — （実装ファイルあり：アラート送信管理。未表示部分あり）

- portfolio/
  - portfolio_builder.py   — 候補選定 / 重み計算
  - position_sizing.py     — 株数決定・投下資金スケール・lot 丸め
  - risk_adjustment.py     — セクターキャップ / レジーム乗数

- research/
  - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力

- utils/
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

- execution/, data/, strategy/ など（実際の注文ロジックや DB リポジトリ等は別ファイルに実装）

※上記はリポジトリ内の主要ファイルとサブパッケージの抜粋です。詳細は各モジュールの docstring を参照してください。

## 注意事項 / 運用上のポイント

- KABUSYS_ENV による DB 分離
  - paper_trading モードでは paper_trading 用 SQLite を使い、本番 DB と完全分離します（安全対策）。
- OpenAI 利用
  - API キーと利用量に注意。LLM 呼び出しは冪等性や部分書き込みで失敗耐性を持たせていますが、API の課金・遅延に注意してください。
- Kill Switch / Kill Flag の扱い
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0（デフォルト）にし、自動クリアを避けるのが安全です。
- 権限・優先度設定
  - set_process_priority は OS により失敗する可能性があり、その場合はログに警告が出ます（アクセス権限が必要）。
- データの鮮度
  - SystemMonitor は DuckDB の prices_daily からデータ鮮度をチェックします。データ供給パイプラインが必要です。

---

さらに詳しい利用やカスタマイズを行う場合は、各モジュールの docstring（ソースの先頭コメント）を参照してください。必要であれば README を英語版にしたり、運用手順（systemd ユニットや Docker 化）を追加で作成することを推奨します。