README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視フレームワークです。  
主要コンポーネントは以下の通りです。

- ExecutionEngine：発注ロジック（本番 / ペーパートレード対応）
- Monitoring：システム状態・注文状態・リスク監視と Kill Switch
- Research：DuckDB を使ったファクター計算・特徴量解析
- AI モジュール：ニュースの LLM（OpenAI）によるセンチメント評価・市場レジーム判定
- ユーティリティ：環境設定ウィザード・設定検証・ペーパートレード検証レポート等

主な設計方針
- 本番 DB（monitoring）とペーパートレード DB を明確に分離
- ルックアヘッドバイアスを避ける日時処理
- API 呼び出しは失敗時にフォールバック（フェイルセーフ）
- テスト容易性を考慮した API 呼び出し差し替えポイント

機能一覧
---------
- 環境管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 対話式ウィザードで .env を生成（kabusys.config_setup）
  - 起動前に設定を検証（kabusys.validate_config）

- 実行エンジン
  - run_execution.py：ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、data/paper_trading.db に記録

- 監視
  - run_monitoring.py：SystemMonitor のポーリング起動
  - MonitoringDB（SQLite）に system_status/trade_logs/positions/risk_logs/dashboard を保持
  - TradeMonitor：滞留注文や約定異常を検出、RiskMonitor：ドローダウン・ポジション上限を監視
  - KillSwitch：条件を満たすと data/kill.flag を書き ExecutionEngine を停止
  - AlertManager 経由での通知（LINE 等の連携は設定で有効化）

- ポートフォリオ構築
  - 候補選定・重み付け（等金額・スコア加重）
  - セクター上限制御、レジーム乗数
  - ポジションサイズ算出（単元株丸め、リスクベース配分、集約キャップ）

- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Spearman）計算、統計サマリ

- AI（OpenAI）
  - ニュースセンチメント（news_nlp.score_news）: raw_news を集約して LLM に送信、ai_scores に格納
  - 市場レジーム判定（regime_detector.score_regime）: ma200 とマクロニュースを合成

- ツール
  - paper_verification_report：ペーパートレード DB を解析し PASS/FAIL レポートを作成

セットアップ手順
----------------
前提
- Python 3.10 以上（型ヒントに | を使用）
- SQLite（組み込み）およびファイル I/O が使える環境

1. リポジトリをクローン
   - git clone ... （リポジトリ URL）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   必須（最低限）
   - duckdb
   - psutil
   - openai
   - 例）pip install duckdb psutil openai

   便利/検証用
   - PyYAML（validate_config が YAML を検証する場合に必要）
   - pip install pyyaml

   （プロジェクトに requirements.txt があればそれを使用してください）

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、kabu API パスワード、DB パス、環境（KABUSYS_ENV）などを入力

5. 設定検証
   - python -m kabusys.validate_config
   - 問題が出たら指摘に従って .env を修正

重要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 選択/設定
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（default: data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI を使う場合に必要
  - PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（default: 60）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0|1、本番は 0 推奨）

使い方
------
起動スクリプト（簡易）

- 監視ループ開始（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
  - 監視は本番 sqlite_path を常に使用（環境に依存せず監視 DB を参照）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、ペーパートレード専用 DB に記録
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
  - 実行中に stop flag を作成すると安全に停止する（stop_requested.flag）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証（起動前に実行推奨）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

停止・Kill Switch
- 手動停止（ExecutionEngine）:
  - data/stop_requested.flag を作成すると run_execution が検知して停止します（run_monitoring も同様に停止を検知）
- 自動停止（リスク条件に基づく）:
  - Monitoring の KillSwitch が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止信号を送ります
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では推奨されません

注意点 / トラブルシューティング
- 必須環境変数が未設定だと Settings プロパティや validate_config がエラーを出します
- OpenAI を使う機能は OPENAI_API_KEY の設定が必須です。API 呼び出しはリトライ実装あり
- psutil を用いてプロセス優先度や CPU affinity を変更します。アクセス権がない場合は警告を出してスキップします
- DuckDB / SQLite のパスの親ディレクトリが存在しない場合は警告（実行時に自動生成されることがあります）
- ペーパートレードは production DB と分離されます（デフォルト: data/paper_trading.db）

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 自動読み込みと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - execution/               — 発注関連（実装詳細は省略）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
    - order_record.py
    ...

  - monitoring/
    - monitoring_db.py        — SQLite 永続層（table 定義・CRUD）
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py        — 注文滞留・約定異常検出
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - kill_switch.py          — Kill Switch 書き込みロジック
    - monitoring_engine.py    — 各 Monitor を束ねる
    - alert_manager.py        — 通知管理（LINE 等）（実装部は別途）

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 発注株数計算
    - risk_adjustment.py      — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py      — Momentum/Volatility/Value 計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC・統計サマリ

  - ai/
    - news_nlp.py             — ニュースセンチメント LLM 呼び出しと書き込み
    - regime_detector.py      — 市場レジーム判定（ma200 + マクロニュース + LLM）

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

開発者向けメモ
----------------
- DuckDB 接続を渡して純粋関数でファクター計算を行う設計になっているため、テストが容易です
- OpenAI 呼び出しはモジュール内でラップしているため、ユニットテスト時は該当関数をパッチして外部依存を遮断してください（各モジュールにテスト差し替えポイントあり）
- monitoring_db.init_monitoring_db は冪等でマイグレーション処理（カラム追加）を行います
- Logging は標準 logging を使用。LOG_LEVEL で制御可能

最終的な流れ（起動例）
--------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. 必要ならデータベース／DuckDB を準備
4. 監視を起動（python -m kabusys.run_monitoring）
5. 実行エンジンを起動（python -m kabusys.run_execution）

以上。必要があれば README に含めるコマンド例や .env サンプル、依存関係の requirements.txt を追記しますので、ご希望を教えてください。