# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ概要ドキュメントです。  
この README はコードベース（src/kabusys 以下）の主要コンポーネント、セットアップ手順、起動方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買（Execution）と、その監視・リスク管理・研究機能を備えたシステムです。主な機能は以下の通りです。

- 自動発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- 研究モジュール（ファクター計算、特徴量探索、IC計算）
- AI モジュール（OpenAI を使ったニュースセンチメント評価、レジーム判定）
- Paper Trading（ペーパートレード）用の分離環境と検証ツール
- ロギング・プロセス優先度設定など運用ユーティリティ

設計上のポイント：
- 環境変数 / .env で設定を管理（config, config_setup, validate_config）
- Paper Trading は本番 DB とは完全分離（デフォルト data/paper_trading.db）
- LLM（OpenAI）呼び出しはフェイルセーフ設計（リトライ・フォールバック）
- DuckDB を研究/分析に使用、SQLite を監視・注文ログに使用

---

## 主な機能一覧

- Execution（発注）:
  - 実口座・ペーパートレードに対応（KABUSYS_ENV により切替）
  - BrokerClientFactory によるブローカークライアント抽象化
  - RiskManager / Reconciler による発注前チェックと整合性確認

- Monitoring（監視）:
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度チェック
  - TradeMonitor: 注文滞留、約定異常などの検出（実装参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 重大アラートで data/kill.flag を書き込み Execution を停止

- Portfolio（ポートフォリオ構築）:
  - 候補選定、等金額/スコア重み、リスクベースの株数計算
  - セクター集中制限、レジーム乗数

- Research（研究）:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン・IC（Information Coefficient）・統計サマリ

- AI（LLM）:
  - ニュース記事を集約して銘柄ごとにセンチメントを算出（OpenAI）
  - マクロニュースを用いた市場レジーム判定（ma200 + LLM）

- ツール:
  - .env 対話ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 必要要件（依存パッケージ）

最低限必要なパッケージ（抜粋）:
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証に必要。任意）
- （その他、実装部分に応じた依存がある可能性があります）

インストール例:
- 仮想環境を作成して pip でインストールしてください（requirements.txt は本リポジトリに含まれない想定）
  - pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン / ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードに従って J-Quants トークンや kabu API パスワード等を入力してください。
     - デフォルトは .env（プロジェクトルート）に保存されます。
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 問題がなければ exit(0) で完了。--strict を付けると警告も失敗扱いになります。

5. DB ディレクトリの作成（必要に応じて）
   - デフォルトの SQLite / DuckDB は data/ 下を使用します。ディレクトリが自動作成されますが、権限などで失敗する場合は手動で作成してください。

6. OpenAI を使用する場合
   - 環境変数 OPENAI_API_KEY を .env に設定してください。
   - news_nlp や regime_detector は環境変数または関数引数で API キーを受け取ります。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: モックブローカーを使用し、paper_trading 用 SQLite に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必須）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- PID_FILE_PATH / KILL_FLAG_PATH: PID・Kill flag のパス（Settings で参照）

注意:
- monitoring は起動時に KABUSYS_ENV にかかわらず Settings.sqlite_path（本番用 path）を使用して監視 DB を開きます（run_monitoring.py の動作）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。

---

## 使い方（起動例）

- 設定チェック（必須項目が揃っているか）
  - python -m kabusys.validate_config

- .env を対話的に作る / 更新
  - python -m kabusys.config_setup

- Execution エンジン起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用、PAPER_TRADING_SQLITE_PATH に記録
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は PID ファイル（data/execution.pid）を書き、停止フラグ / kill.flag を監視して停止可能

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。
  - 動作:
    - SystemMonitor、TradeMonitor、RiskMonitor 等のポーリングを行い、MonitoringDB（SQLite）へ書き込む
    - KillSwitch 評価で必要なら data/kill.flag を書き、Execution 停止トリガーを発動
    - data/stop_requested.flag があると監視ループが終了する

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH または --db で DB パスを指定可能

---

## ロギング／プロセス優先度

- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一管理されます。
  - コンソール（stdout）出力と日次ローテートファイル（logs/<app_name>.log）を設定。
  - LOG_LEVEL / LOG_DIR により挙動を変更可能。

- プロセス優先度／CPU affinity:
  - run_execution / run_monitoring は起動直後に set_process_priority("high") を呼びます。
  - psutil を用いて Windows / POSIX の差分を吸収します。権限不足や未対応 OS の場合は警告出力でスキップします。

---

## 運用上のファイル（フラグ・PID 等）

- data/execution.pid: Execution が書き込む PID ファイル（Settings.pid_file_path デフォルト）
- data/stop_requested.flag: run_execution/run_monitoring の外部停止フラグ（存在するとループを終了）
- data/kill.flag: KillSwitch が書き込む停止理由（存在すると Execution は停止トリガー）
- logs/: アプリケーション別ログファイル（例: logs/execution.log, logs/monitoring.log）

起動時の注意:
- KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

---

## 開発者向け注意点

- DuckDB 接続は research / ai モジュールで利用されます。prices_daily / raw_financials / raw_news などのテーブル構造に依存します。
- AI モジュール（news_nlp, regime_detector）は OpenAI API を利用するため API キーが必須です。API 呼び出しはリトライ・フォールバック設計になっていますが、キー未設定だと ValueError が上がります。
- monitoring.monitoring_db.init_monitoring_db はテーブル作成と簡易マイグレーション処理を行います。既存 DB との互換性に注意してください。

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイル）:

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — Execution エンジン起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py         — ログ初期化ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - execution/                  — 発注関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（補足）
- 実際の execution パッケージ（broker クライアント等）は別ファイルに実装されています。run_execution.py 内でこれらを組み立てて起動します。

---

## よくある質問 / トラブルシューティング

- Monitoring が本番用 SQLite を使用してしまうのはなぜ？
  - 監視は常に実運用系の状態をチェックする必要があるため、Settings.sqlite_path（本番 path）を使う設計です。環境分離が必要なら path を変更してください。

- Paper Trading のデータは本番 DB に混ざりますか？
  - いいえ。KABUSYS_ENV=paper_trading のとき run_execution は PAPER_TRADING_SQLITE_PATH を使用し、別ファイルに記録します。

- OpenAI 呼び出しでエラーが出る
  - OPENAI_API_KEY が設定されているか確認。API のレートやネットワークはリトライ実装がありますが、キーやネットワーク環境を確認してください。

- logs ディレクトリが作れない / ログファイルが作成されない
  - 権限やパスを確認してください。logging_setup は作成失敗時にコンソールのみの出力にフォールバックします。

---

## 最後に

この README はコード内コメントと実装に基づく概要です。  
各モジュールの詳細な挙動は該当ソースファイル（src/kabusys/...）の docstring / コメントを参照してください。開発や運用で不明点があれば、該当モジュールの実装箇所をご確認のうえお問い合わせください。