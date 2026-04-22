# KabuSys

日本株向け自動売買システムのコアライブラリ群。  
このリポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI 補助（ニュース NLP / レジーム検出）などのモジュールを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような責務を持つモジュール群で構成されています。

- ExecutionEngine: 発注／注文管理／リスク管理（本番とペーパートレードを区別）
- Monitoring: システム状態・注文状態・リスクを定期チェックしアラートや Kill Switch を制御
- Portfolio: 候補選定、ウェイト計算、ポジションサイズ算出などポートフォリオ構築ロジック
- Research: DuckDB 上の時系列データからファクター計算・IC 計算などを提供
- AI: ニュースの NLP スコアリング、マクロニュースを使った市場レジーム判定（OpenAI を利用）
- ユーティリティ: ロギング設定、プロセス優先度設定、設定読み込みウィザード／検証など

設計方針として、データベース（SQLite / DuckDB）や外部 API へのアクセスは明示的に行い、テスト容易性やフェイルセーフを意識した実装になっています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成・更新）: python -m kabusys.config_setup
- 設定検証ツール（.env および config/*.yaml の基本チェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、paper_trading 用 DB に書き込む（本番 DB と分離）
- Monitoring 起動スクリプト（ポーリングループ）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）
  - 停止は data/stop_requested.flag によるフラグ検知で行う
- Paper Trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築関数群（候補選定・等金額/スコア配分・リスク調整・ポジションサイズ算出）
- DuckDB ベースのリサーチ関数（モメンタム / ボラティリティ / バリュー 等）
- ニュース NLP（OpenAI）を用いた銘柄別センチメントスコアリング
- マーケットレジーム判定（ETF MA + マクロニュースの LLM スコアを合成）
- ロギング設定ユーティリティ（stdout + 日次ローテートファイル）
- プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）

---

## セットアップ手順（開発環境）

1. Python（3.9+ 推奨）を準備し、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストールします（プロジェクトに requirements.txt があればそれを利用してください）。主要依存の例:
   - pip install duckdb psutil openai pyyaml

   注: sqlite3 は標準ライブラリに含まれます。

3. プロジェクトルートに移動し、.env を作成します。推奨フロー:
   - python -m kabusys.config_setup
     - 対話形式で .env を作成・更新します（.env は絶対に Git にコミットしないでください）

4. 設定を検証します:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いされ exit(1) になります。

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境指定
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: 発注はモック、別 SQLite に記録
    - live: 実際の実行（注意して設定してください）

- DB / ログ
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - LOG_DIR: ログディレクトリ（デフォルト: logs/）
  - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）

- AI
  - OPENAI_API_KEY: OpenAI を利用する機能（news_nlp / regime_detector）で必要

- 監視・制御
  - PID_FILE_PATH: data/execution.pid（ExecutionEngine の PID ファイル）
  - KILL_FLAG_PATH: data/kill.flag（Kill Switch 用）
  - KILL_FLAG_CLEAR_ON_START: 0/1（起動時に kill.flag を自動クリアするか。production では 0 推奨）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用、デフォルト 60）
  - PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject）

既定値は Settings クラス内に定義されています（kabusys.config）。

---

## 使い方（コマンド例）

- .env の初期化（対話ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV で切り替わります（paper_trading なら専用 DB と MockBroker）

- Monitoring 起動（常駐ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: プロセスに KeyboardInterrupt を送るか プロジェクトルート/data/stop_requested.flag を作成すると監視ループが検知して終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（プログラム的に利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  # api_key が None の場合は OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- Monitoring は run_monitoring.py 内で本番用 sqlite_path を用いる設計です（環境に関わらず）。
- Execution は KABUSYS_ENV=paper_trading のとき paper_trading 用 SQLite を使用して本番 DB とは切り離します。

---

## 停止・Kill フラグ

- data/stop_requested.flag
  - run_execution / run_monitoring のループで存在を検知すると安全終了します（外部からの停止指示用）。

- data/kill.flag
  - KillSwitch が条件を満たすと書き込み、ExecutionEngine に停止を促します（人為的に作る/削除も可能）。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアする挙動になります（本番では 0 推奨）。

---

## ロギング

- setup_logging により stdout（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler）が設定されます。
- デフォルトログディレクトリ: logs/
- アプリ名別のログファイル（例: logs/execution.log, logs/monitoring.log）

---

## 依存関係（主要）

- duckdb
- psutil
- openai（AI 機能利用時）
- pyyaml（validate_config は PyYAML がインストールされていると config/*.yaml のパース検証を行います）
- Python 標準の sqlite3

実際の requirements.txt が存在する場合はそちらを参照してインストールしてください。

---

## ディレクトリ構成（主要ファイル）

例: src/kabusys 以下

- __init__.py
- config.py                — 環境変数と Settings クラス
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 起動前の設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリング起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）によるスコアリング
  - regime_detector.py      — マーケットレジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py        — SQLite テーブル初期化＋永続化 API
  - system_monitor.py       — システム状態・データ鮮度監視
  - trade_monitor.py        —（注文ログ等の監視: 実装参照）
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag 書込ロジック
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - alert_manager.py        —（アラート送信ロジック: 実装参照）
- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 株数算出・集計キャップ
  - risk_adjustment.py      — セクターキャップ・レジーム乗数
- research/
  - factor_research.py      — モメンタム/ボラ/バリュー等の計算（DuckDB）
  - feature_exploration.py  — 将来リターン・IC・統計サマリー
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring.db / paper_trading.db / kabusys.duckdb — デフォルトは data/ 配下（実行で自動作成される）

（注: 上述はこの README に含まれるコードベースの抜粋に基づく構成。実プロジェクトではさらに execution/ や data/ 等のサブモジュールが存在します）

---

## 開発・デバッグのヒント

- 設定関連のデバッグ:
  - .env を編集したら python -m kabusys.validate_config で問題を早期発見
- ロギング:
  - LOG_LEVEL を DEBUG に上げると内部挙動が詳細に出力されます
- モジュール単体テスト:
  - research / portfolio モジュールは副作用が少ない純関数群なので単体テストを作りやすいです
- AI 機能のテスト:
  - OPENAI_API_KEY を用意するか、score_news／score_regime 内の API 呼び出しラッパーをモックしてテストしてください

---

## 注意事項

- .env ファイルには機密情報（API トークン・パスワード等）を含みます。絶対にバージョン管理にコミットしないでください。
- KABUSYS_ENV=live の設定は本番動作になります。Kill Switch 設定や LINE 通知の設定などを十分確認してください。
- OpenAI を使う処理は API コストが発生します。テスト環境ではモック化を推奨します。

---

必要に応じて README に追記します。特に「実際に ExecutionEngine を systemd 等でデーモン化する手順」や「config/*.yaml の各項目の詳細説明」が必要なら教えてください。