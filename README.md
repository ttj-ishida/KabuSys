# KabuSys README

KabuSys は日本株向けの自動売買・リサーチ基盤のミニマル実装です。本リポジトリには以下の主要コンポーネントが含まれます：ExecutionEngine（注文実行）、Monitoring（監視・アラート・Kill Switch）、ポートフォリオ構築ユーティリティ、リサーチ／ファクター計算、AI を使ったニュースセンチメント／レジーム判定ツール、各種 CLI ツール。

バージョン: 0.1.0

---

## プロジェクト概要

- 目的：日本株の自動売買フロー（シグナル → ポジション構築 → 発注 → 監視）をサポートするライブラリと運用用スクリプト群。
- 設計方針：
  - 本番（live）/ ペーパートレード（paper_trading）/ 開発（development）を環境変数で切替可能。
  - DB は DuckDB（分析）と SQLite（監視・発注ログ）を併用。ペーパートレードは本番 DB と分離可能。
  - OpenAI を利用したニュース NLP / レジーム検出を備え、API 失敗時はフェイルセーフで継続する設計。
  - モジュールはできるだけ純粋関数・副作用最小化で実装（研究/ポートフォリオ/計算部分）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（paper_trading 時は Mock を使用）
  - 注文管理・リスク管理・照合（reconciler）を含む実行パイプライン

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態 / データ鮮度監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン監視・ポジション上限監視
  - KillSwitch：閾値到達時に data/kill.flag を書いて Execution を停止
  - MonitoringEngine：上記モニターを束ねたポーリングループ（run_monitoring.py）

- Portfolio（純粋関数）
  - 候補選定（スコア順）、等金額／スコア重み配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（リスクベース・配分ベース）

- Research
  - ファクター計算（Momentum / Volatility / Value など）
  - 将来リターン計算、IC（Information Coefficient）、特徴量サマリ

- AI（OpenAI）
  - news_nlp: raw_news を集約して LLM へ送信、銘柄ごとの sentiment（ai_scores）を書き込み
  - regime_detector: ma200 とマクロニュースの LLM 評価を合成して日次レジーム判定

- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限:
     - pip install duckdb psutil openai
   - validate_config の YAML パース（任意）:
     - pip install pyyaml
   - 例えば:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があればそれを使用してください。）

3. プロジェクトルートで .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）
   - 自動ロードはデフォルトで有効（プロジェクトルートの .env が自動で読み込まれます）。
     - テスト等で無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を指定すると警告も失敗扱いになります

5. 必要ディレクトリ作成（.env デフォルトに基づく）
   - data/（SQLite / PID / フラグファイル保存）
   - 例:
     - mkdir -p data

注意:
- OpenAI API を使う機能を利用する場合、OPENAI_API_KEY を設定してください。
- 本番運用時は KABUSYS_ENV=live を慎重に設定し、LINE 通知などの設定を確認してください。

---

## 使い方

主な実行コマンド（プロジェクトルートで実行）:

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に記録
    - プロセス優先度を "high" に変更（psutil が許可する場合）
    - data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中は data/execution.pid に PID を書く

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings に基づき monitoring 用 DB を初期化
    - SystemMonitor.check_once() を周期実行（デフォルト 60 秒）
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（例: MONITOR_POLL_INTERVAL=30）
    - 停止: data/stop_requested.flag が存在するとループを終了する（外部から停止させるためのフラグ）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を直接受け取り、処理結果をテーブルへ書き込みます。
  - API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用

- 停止・Kill Switch
  - Monitoring の KillSwitch は閾値を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を促します
  - 外部から確実に監視ループを停止したい場合は data/stop_requested.flag を作成してください（run_* スクリプトはこれを監視します）
  - KILL_FLAG_CLEAR_ON_START=1 を本番で使うのは危険（デフォルト 0 推奨）

主要な環境変数（抜粋とデフォルト）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API トークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL: INFO など
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、run_monitoring 用。デフォルト 60）

---

## ディレクトリ構成（主要ファイル）

以下は src/ 以下の主要モジュール構成の抜粋です。実際のリポジトリはこの構成に沿っています。

- src/
  - kabusys/
    - __init__.py
    - config.py               # 環境変数 / .env の自動読み込みと Settings
    - config_setup.py         # .env 対話式ウィザード
    - validate_config.py      # 起動前設定検証 CLI
    - run_execution.py        # ExecutionEngine 起動スクリプト
    - run_monitoring.py       # Monitoring ポーリング起動スクリプト
    - utils/
      - __init__.py
      - process_priority.py   # プロセス優先度 / CPU affinity ユーティリティ
    - execution/              # 発注パイプライン関連（OrderManager 等）
      - ...                  # 実装ファイル群（OrderManager, ExecutionEngine, BrokerFactory 等）
    - monitoring/
      - monitoring_db.py      # SQLite テーブル定義 + MonitoringDB クラス
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py      # ※ファイル先頭までの実装あり（アラート送信ロジック）
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/                    # データ作成用スクリプト / パイプライン（prices_daily 等の取得）
      - pipeline.py (参照実装)
    - tools/
      - __init__.py
      - paper_verification_report.py

その他:
- config/                   # YAML 設定テンプレート（system_config.yaml 等）
- data/                     # 実行時生成ファイル（DB, PID, flag）

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では外部 API（kabuステーション）へ実際に発注が行われます。設定やシークレットの管理に十分注意してください。
- Kill Switch と停止フラグの挙動:
  - Monitoring の KillSwitch は条件を満たすと data/kill.flag を書き込みます（実行中の ExecutionEngine はこのフラグを検知して停止する設計）。
  - 手動停止や CI 用停止には data/stop_requested.flag を利用してください（run_* スクリプトはこれを監視します）。
- OpenAI API を用いる機能はコストが発生します。API キーの漏洩や誤用に注意して運用してください。
- validate_config は YAML の存在や簡易パスチェックを行いますが、実際の API 認証やブローカー接続の動作確認も事前に行ってください。

---

もし README に追加してほしい具体的な例（.env のサンプル、コマンド例、図解など）があれば教えてください。必要に応じて追記します。