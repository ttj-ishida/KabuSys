# KabuSys

日本株向け自動売買システムのコアライブラリ群および起動スクリプト群です。本リポジトリはシグナル生成・ポートフォリオ構築・発注エンジン・監視・AI を用いたニュース解析・リサーチユーティリティなどを含みます。

以下は本コードベースの概要・機能・セットアップ・使い方・ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。主な責務は次のとおりです。

- ファクター計算・リサーチ（DuckDB を用いた時系列処理）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- ExecutionEngine（発注ロジック）と Broker クライアントの抽象化（ペーパートレード用のモック含む）
- 監視（System / Trade / Risk の定期チェック）と Kill Switch による安全停止
- AI を用いたニュースセンチメント評価・市場レジーム判定（OpenAI API を利用）
- 各種ツール（.env ウィザード、設定検証、Paper Trading 検証レポート等）

設計方針として、可能な限り純粋関数・副作用の限定、冪等性（データベース初期化や書き込み）を重視しています。

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み（.env, .env.local）
  - interactive ウィザードで .env を生成/更新（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - 発注履歴・取引ログの永続化（SQLite / duckdb）
- Monitoring
  - System / Trade / Risk の定期チェック
  - Kill Switch（閾値超過で data/kill.flag を書き込み、Engine を停止）
  - 監視ループ起動スクリプト（run_monitoring.py）
  - Monitoring DB スキーマ管理（monitoring_db.init_monitoring_db）
- Portfolio
  - 候補選定（スコア順）、等配分・スコア加重配分
  - セクター上限適用、レジーム乗数計算
  - 株数決定（リスクベース / 等分 / スコアベース）、単元株丸め、投下資金スケーリング
- Research
  - モメンタム / ボラティリティ / バリューファクター計算（DuckDB）
  - 将来リターン・IC（情報係数）計算、特徴量サマリ
- AI（OpenAI）
  - ニュース記事を集約して銘柄ごとにセンチメントを算出（news_nlp）
  - マクロニュース＋ETF MA を用いた市場レジーム判定（regime_detector）
- ツール
  - Paper Trading の検証レポート生成（tools.paper_verification_report）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型表記に PEP 604 の `|` を使用）
- 推奨パッケージ（利用する機能に応じてインストール）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (validate_config の YAML 検証を使用する場合)
- SQLite は標準ライブラリに含まれます

インストール例（仮に requirements.txt がある場合）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
もしくは個別インストール:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順（初期）

1. リポジトリをクローン／展開する
2. Python 仮想環境を作成して依存パッケージをインストールする
3. .env の作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードで J-Quants や kabuAPI のパスワード、KABUSYS_ENV 等を設定できます。
   - 手動で .env を作る場合は .env.example を参考にしてください（本コードは .env.example を期待しています）。
4. 設定検証（起動前に実行推奨）:
   ```
   python -m kabusys.validate_config
   ```
   警告も失敗にしたい場合:
   ```
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（起動・実行）

- ExecutionEngine を起動する（本番 / paper_trading は KABUSYS_ENV で切替）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、デフォルトで data/paper_trading.db にペーパートレードログを記録します。
  - 実行中の停止は monitoring の kill.flag（data/kill.flag）によって行われます。監視プロセスからの停止や手動での flag ファイル作成が可能です。
  - 実行時に PID は data/execution.pid に書き出されます。

- Monitoring（監視ループ）を起動する
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒です。環境変数 `MONITOR_POLL_INTERVAL` で上書きできます（秒単位、1 以上）。
    例: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`
  - monitoring は KABUSYS_ENV に関係なく本番用の sqlite_path（デフォルト: data/monitoring.db）を使用して監視データを記録します。
  - 監視停止にはプロジェクトルートの `data/stop_requested.flag` を作成します（run_monitoring/run_execution の両方で停止フラグとしてチェックされます）。

- .env ウィザード
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート生成（ツール）
  ```
  python -m kabusys.tools.paper_verification_report
  ```
  オプション:
  - --from YYYY-MM-DD
  - --to YYYY-MM-DD
  - --db PATH (PAPER_TRADING_SQLITE_PATH 環境変数で指定することも可)

- AI 関連（OpenAI API を利用）
  - 環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に `api_key` を渡してください。
  - ニュースセンチメント: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要な環境変数

（.env の設定は `kabusys.config_setup` を使うと便利です）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用）
- LOG_LEVEL — ログレベル (DEBUG/INFO/…)
- OPENAI_API_KEY — OpenAI を使う場合の API キー
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか (0/1)

---

## 停止・リカバリ

- 強制停止・Kill Switch:
  - risk やその他の条件で KillSwitch が発動すると `data/kill.flag` が作成されます。ExecutionEngine は起動中に `kill.flag` を検出すると停止します。
  - kill.flag は `KillSwitch.clear()` を呼ぶか手動で削除することでクリアできます。
  - run_monitoring/run_execution は `data/stop_requested.flag` を検出するとループを抜けて終了します（管理用の別フラグ）。

- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力されます（kabusys.utils.logging_setup.setup_logging により自動設定）。

---

## データベース（Monitoring DB）スキーマ（概要）

monitoring_db.init_monitoring_db により作成される主なテーブル:

- system_status: システム監視ログ（CPU/MEM/DISK、プロセス正常フラグ 等）
- trade_logs: 発注・約定イベントログ（event_type, client_order_id, code, qty, price, latency_ms 等）
- positions: 保有ポジション（code 主キー）
- risk_logs: リスク関連のログ（ドローダウン、ポジション上限 等）
- dashboard: ダッシュボード集計（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

初期化は冪等で、古い DB に対して必要な ALTER を行うマイグレーション処理も含まれます（例: latency_ms, peak_value の追加）。

---

## ディレクトリ構成

（src 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py            — ニュース → センチメント解析（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py       — Monitoring DB 初期化 / ラッパー
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 発注 / 約定の整合性チェック（存在）
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - kill_switch.py         — kill.flag の管理
    - alert_manager.py       — アラート通知（存在）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・投下資金スケーリング
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — momentum / volatility / value の計算
    - feature_exploration.py — forward returns, IC, factor summary
  - monitoring/ (上記)
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - data/ (ランタイムで生成される可能性あり)
    - monitoring.db
    - paper_trading.db
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - config/ (YAML 設定ファイル置き場、generate スクリプト参照)
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml

※ 実際のリポジトリでは execution や trade 関連の詳細ファイル群（broker クライアント、execution_engine、order_manager 等）が存在します。上記は主要モジュールの抜粋です。

---

## 開発者向けメモ / 注意点

- KABUSYS_ENV による挙動差:
  - development: ローカル開発向け（発注などは制限）
  - paper_trading: MockBroker を使用し、専用 DB に記録（本番 DB と分離）
  - live: 本番（実際に発注）
- monitoring プロセスは監視データに対して本番 sqlite_path（設定に依らず）を参照します。設定を適切に確認してください。
- OpenAI を利用する機能は API 呼び出し失敗時にフォールバック（フェイルセーフ）する設計ですが、API キーの管理には注意してください。
- ロガーはデフォルトで stdout とファイル（logs/）に出力します。ログディレクトリの作成に失敗しても stdout には出ます。
- 実運用では `KILL_FLAG_CLEAR_ON_START=0`（デフォルト）を推奨します。production で自動クリアする設定は危険です。

---

## 付録: よく使うコマンドまとめ

- .env 作成ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動（ポーリング間隔30秒にする例）:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading 検証レポート（過去期間指定例）:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に書かれている内容で不明点や補足が必要な箇所があれば教えてください。設定ファイル例（.env.example）や起動スクリプトの具体的な追加オプション説明など、追記できます。