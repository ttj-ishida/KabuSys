# KabuSys

日本株向けの自動売買システム（プロトタイプ）。シグナル生成・ポートフォリオ構築・発注エンジン・監視・研究ツール・AI ニュース解析などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群で構成された自動売買フレームワークです（主要点のみ抜粋）:

- 発注実行エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
  - KABUSYS_ENV による挙動切替（paper_trading モードでは MockBroker を使用しデータを分離）
- 監視（Monitoring）
  - SystemMonitor：プロセス・CPU/メモリ/ディスク・データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション数上限の監視と Kill Switch 発動
  - MonitoringEngine：監視を定期実行してアラート・kill.flag 管理
- ポートフォリオ構築（pure functions）
  - 候補選定、等金額／スコア加重重み、ポジションサイズ算出、セクター制限、レジーム乗数など
- リサーチ（DuckDB ベース）
  - ファクター計算（モメンタム／ボラティリティ／バリュー）や IC 計算、将来リターン計算
- AI 支援
  - ニュースの自然言語処理（OpenAI）による銘柄別センチメントスコア（ai_scores）
  - マクロニュース + ETF ma200 を使った市場レジーム判定
- ユーティリティ
  - .env 対話式ウィザード、設定検証 CLI、paper trading の検証レポート生成 など

設計方針の一例：
- DuckDB / SQLite を用いたローカル DB 中心の設計（分析用と監視用を分離）
- 重要操作は冪等（同一書き込みの上書きやマイグレーションを配慮）
- ルックアヘッドバイアスを避ける（日時参照や DB クエリ条件に注意）
- AI 呼び出しは再試行やフェイルセーフを実装

---

## 主な機能一覧

- 環境設定ウィザード（.env を対話的に作成 / 更新）
- 設定検証 CLI（.env と config/*.yaml のチェック）
- ExecutionEngine 起動スクリプト（本番 / ペーパーの切替）
- Monitoring 起動スクリプト（SystemMonitor のポーリング）
- MonitoringDB（SQLite）による監視ログ保存・リスクログ・ダッシュボード
- Trade / Risk / System の監視ロジックと Kill Switch
- Portfolio モジュール（候補選定・重み計算・ポジションサイズ算出・リスク調整）
- Research モジュール（DuckDB を用いたファクター計算・IC・統計）
- AI モジュール（ニュース NLP / レジーム検出） — OpenAI API 必須
- ツール：Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順

前提: Python 3.9+ を推奨（ソースは typing | 現代的構文を使用）

1. リポジトリをクローンし、仮想環境を用意
   - 例:
     ```bash
     git clone <repo-url>
     cd <repo-root>
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     ```

2. 必要パッケージをインストール
   - 主に以下が必要（プロジェクトで使用しているライブラリ）:
     - duckdb
     - psutil
     - openai （AI 機能を使う場合）
     - pyyaml（config YAML のパース検証を行う場合）
   - 例:
     ```bash
     pip install duckdb psutil openai pyyaml
     ```
   - （プロジェクトに requirements.txt があればそれを使ってください）

3. .env の作成
   - 対話式ウィザードを利用:
     ```bash
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使うオプション:
     - KABUSYS_ENV = development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（ペーパートレードの約定モード: instant|partial|never|reject）

   - .env は絶対にリポジトリにコミットしないでください。

4. 設定の検証（任意だが推奨）
   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告もエラー扱いにできます
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの作成（必要に応じて）
   - デフォルトでは `data/` 以下に DB ファイルや PID / flag が生成されます。

---

## 実行方法（使い方）

- ExecutionEngine を起動する
  - 本番 / ペーパートレードは KABUSYS_ENV に依存
  - ペーパーの場合、専用 SQLite (PAPER_TRADING_SQLITE_PATH) を使用して本番 DB と分離されます
  ```bash
  python -m kabusys.run_execution
  ```

  動作上の注意:
  - 起動時にプロセス優先度を "high" に設定しようとします（権限により失敗可）
  - 起動前に data/stop_requested.flag が存在する場合は起動せず終了します
  - 実行中は PID ファイル（data/execution.pid 相当）を使ってプロセス存在を監視します
  - Kill Switch（data/kill.flag）が書かれた場合、ExecutionEngine に停止指示を送ります

- Monitoring（監視）を起動する
  - 起動スクリプトは SystemMonitor のポーリングループを開始します
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数でポーリング間隔を変更可能:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）
    - 0 以下や不正値はデフォルトにフォールバックされます
  - run_monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して監視を行います（監視は本番 DB を参照する想定）

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- .env 対話式ウィザード（再掲）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証 CLI（再掲）
  ```bash
  python -m kabusys.validate_config
  ```

---

## 主要な環境変数（抜粋・デフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START: "1" にすると起動時に kill.flag を自動クリア（本番では推奨しない）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- 自動で .env を読み込む仕組みがあり、プロジェクトルート（.git か pyproject.toml）の存在を基準に .env / .env.local を読み込みます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 監視・停止フラグ

- stop_requested.flag
  - run_execution / run_monitoring の起動／実行ループで参照する停止フラグ（data/stop_requested.flag 相当）
  - 存在を検知するとループを終了します（run_monitoring は検知で終了、run_execution は検知で engine.stop() 実行）

- kill.flag (Settings.kill_flag_path、デフォルト data/kill.flag)
  - KillSwitch により書き込まれるファイル。ExecutionEngine に対する停止シグナル用途
  - KillSwitch.evaluate() がトリガー条件を満たすと書き込みます（冪等処理あり）
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START を使って自動クリアするオプションあり（本番では注意）

---

## 開発者向けメモ / 実装上のポイント

- run_monitoring は MONITOR_POLL_INTERVAL (秒) で check_once を繰り返します（デフォルト 60 秒）
- run_execution は KABUSYS_ENV=paper_trading の場合専用 DB を使い、本番 DB と完全分離されます
- 設定の読み込み・パースは `kabusys.config` が担当。.env のパースはシェル風（export / quotes / コメント）に対応
- MonitoringDB（SQLite）は schema の初期化と簡単なマイグレーションを行います（例: dashboard.peak_value, trade_logs.latency_ms の追加）
- AI 機能（news_nlp, regime_detector）は OpenAI API を利用。API 呼び出しはリトライや JSON バリデーション、部分失敗時の保護ロジックが組み込まれています
- process priority / CPU affinity: `kabusys.utils.process_priority` が psutil を使ってプラットフォーム無関係に設定を試みます（権限不足時は警告でスキップ）

---

## ディレクトリ構成

（src 以下を想定した主要ファイル・モジュール構成の抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数 / .env 読み込みロジック、Settings クラス
    - config_setup.py           # .env 対話ウィザード
    - validate_config.py        # 設定検証 CLI
    - run_execution.py          # ExecutionEngine 起動スクリプト
    - run_monitoring.py         # SystemMonitor ポーリング起動スクリプト
    - utils/
      - __init__.py
      - process_priority.py     # プロセス優先度 / CPU affinity ユーティリティ
    - portfolio/
      - __init__.py
      - portfolio_builder.py    # 候補選定・重み計算
      - risk_adjustment.py      # セクターキャップ・レジーム乗数
      - position_sizing.py      # 株数計算・集計上限処理
    - monitoring/
      - monitoring_db.py        # SQLite schema / 永続化 API
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py        # （ファイル末尾の未表示部分に実装あり）
    - execution/                 # 発注関連コンポーネント（参照あり）
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
      - order_record.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py

- data/
  - monitoring / paper_trading DB ファイル（デフォルトの保存先）
  - execution.pid, stop_requested.flag, kill.flag などのフラグ / PID ファイル

（実際のリポジトリでは上記以外にも追加のモジュールやスクリプトがある場合があります）

---

## よくある質問 / トラブルシューティング

- .env を更新したのに環境変数が反映されない
  - プロセス起動時に .env は読み込まれますが、既にエクスポート済みの OS 環境変数が優先されます。.env の自動読み込みを無効にしている場合（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）や、プロジェクトルートが検出できない場合は手動で export してください。

- OpenAI を使った処理が失敗する
  - OPENAI_API_KEY を設定しているか確認してください。API 呼び出しはリトライを行いますが、キーが無い・不正な場合は機能しません。

- run_monitoring が DB を参照しない / 期待したテーブルがない
  - monitoring 用テーブルは起動時に作成されます（init_monitoring_db）。ただし DuckDB と SQLite のパス設定が正しいか、ファイルが存在するかを確認してください。

---

## ライセンス / 注意事項

- この README はコードベースの概要説明であり、実運用は自己責任で行ってください。
- 実際の発注機能を本番 (KABUSYS_ENV=live) で動かす場合は、十分なテスト・ガード（LINE 通知設定、kill flag の運用、監視設定）を確立してください。

---

README 以上。必要なら各セクションの詳細（設定項目の完全な一覧、DB スキーマ、実行ログ例、ユニットテストの実行方法など）を追記します。どの項目を拡張しますか？