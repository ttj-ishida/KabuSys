# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ / 実行スクリプト / ツール群）。  
この README はコードベースに含まれる主要コンポーネントの概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の戦略生成・ポートフォリオ構築・発注・監視・研究用ユーティリティを含む自動売買システムです。  
主な役割:

- 戦略・ファクター計算（research）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- 発注エンジン（execution） — 本番 / ペーパートレード分離
- 監視（monitoring） — システム状態や注文の監視、Kill Switch
- AI を使ったニュースセンチメント / レジーム検出（ai）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話式作成
- 起動前設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine（発注エンジン）
  - KABUSYS_ENV に応じて本番 / ペーパートレードを切替
  - リスク管理（RiskManager）、オーダー管理、再整合（Reconciler）等を備える
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor）による定期チェック
  - kill.flag を書き込む KillSwitch による外部停止トリガー
- Paper Trading 検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）
- Portfolio 構築ユーティリティ（候補選定・重み計算・ポジションサイズ計算・セクター制約等）
- Research モジュール（ファクター計算、forward returns、IC 計算、統計サマリー）
- AI モジュール
  - ニュースのセンチメントを OpenAI でスコア化（ai.news_nlp）
  - マクロ + ETF MA を合成した市場レジーム判定（ai.regime_detector）
- ロギングとプロセス優先度ユーティリティ（utils）

---

## 必要条件 / 依存パッケージ

主に以下が必要です（プロジェクトで使われている外部ライブラリの抜粋）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定検証で YAML ファイルチェックを行う場合に推奨）
- その他（標準ライブラリのみで動作する部分も多い）

インストール例（仮）:
pip install duckdb psutil openai pyyaml

※ 実際の requirements.txt がある場合はそちらを使ってください。

---

## セットアップ手順（推奨フロー）

1. リポジトリをクローン・チェックアウト
2. 仮想環境を作成して依存関係をインストール
3. .env の作成
   - 対話式ウィザードを推奨:
     python -m kabusys.config_setup
   - ウィザードで作成した .env はリポジトリにコミットしないでください。
   - 自動ロード: デフォルトで .env / .env.local は自動読み込みされます（OS 環境変数が優先）。
   - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
4. 設定検証:
   python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い（exit(1)）
5. 必要なディレクトリがなければ作成（通常は起動時に自動作成されるが明示的に作ると安心）
   - data/
   - logs/

重要な環境変数（主なもの・デフォルト）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- OPENAI_API_KEY: OpenAI 利用時に必要
- LOG_LEVEL: INFO（または DEBUG など）
- LOG_DIR: logs/
- KILL_FLAG_CLEAR_ON_START: 0/1（本番では 0 推奨）

特記事項:
- モニタリング関連の DB（monitoring.db）は Monitoring が参照するため、Monitoring は KABUSYS_ENV に関係なく sqlite_path を参照して書き込みます。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。

---

## 使い方（主要スクリプト / コマンド）

パッケージはモジュール実行で利用します（プロジェクトのルートで実行）。

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き可能: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 停止はプロジェクトルート/data/stop_requested.flag ファイルを作成することで検知して終了します

- 発注エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - ExecutionEngine は実行中に data/execution.pid を使用します
  - 停止は同じく data/stop_requested.flag を監視して停止を試みます
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して paper_trading DB に記録

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（デフォルト data/paper_trading.db）

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要（関数引数で明示的に与えることも可能）

- ログ設定
  - すべての起動スクリプトは共通の setup_logging を呼び出します。ログディレクトリは LOG_DIR 環境変数 / デフォルト logs/ に作成され、日次ローテーションでファイル出力されます。

---

## 重要な運用ルール / 動作ポイント

- .env の自動ロード順: OS 環境変数 > .env.local > .env（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- run_monitoring 側は MONITOR_POLL_INTERVAL 環境変数でループ間隔を変更可能（秒、1 未満や非数値はデフォルト 60 秒へフォールバック）
- Kill Switch:
  - RiskMonitor 等の判定により KillSwitch が Settings.kill_flag_path（デフォルト data/kill.flag）に理由文字列を書き込みます。
  - ExecutionEngine 側は kill.flag の存在を確認して安全停止する仕組みを持ちます。
  - Kill flag を自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）がありますが、本番では危険なため 0 を推奨します。
- MonitoringDB（SQLite）
  - init_monitoring_db が必要なテーブル・インデックスを冪等に作成します。
  - monitoring 用 sqlite（SQLITE_PATH）は Monitoring が利用。ExecutionEngine の paper_trading モードは別 DB を使用。
- OpenAI 呼び出し
  - レートリミットや 5xx などはエクスポネンシャルバックオフでリトライする設計です。
  - API キーは OPENAI_API_KEY 環境変数か関数引数で指定してください。
- プロセス優先度 / CPU affinity
  - 起動スクリプトは set_process_priority("high") を呼び出して優先度を上げようとします（プラットフォーム依存で可能な範囲で実行）。

---

## ディレクトリ構成（主要ファイル）

下記はソース内の主要モジュール（src/kabusys）を抜粋した構成です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層（テーブル作成 / CRUD）
    - system_monitor.py      — システム状態・データ鮮度チェック
    - trade_monitor.py       — 注文ログ等の監視（省略ファイルは実コード参照）
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag 書込みロジック
    - monitoring_engine.py   — 各監視を束ねる
    - alert_manager.py       — アラート送信（実装参照）
  - execution/
    - execution_engine.py    — ExecutionEngine（セッションループ）
    - order_manager.py       — オーダー実行管理
    - order_repository.py    — DB 永続化（orders）
    - broker_factory.py      — BrokerClient の生成（本番 / Mock 切替）
    - reconciler.py          — オーダー再整合
    - risk_manager.py        — 発注前リスク判定
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・スケーリング
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Value / Volatility 等の計算（DuckDB 使用）
    - feature_exploration.py — forward returns, IC, summary 等
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - data/                    — 実行時に使用される既定ディレクトリ（DB・pid・flags 等）

（注）一部ファイルは上で抜粋していない実装が存在します。詳細は各モジュールの docstring を参照してください。

---

## 開発上のヒント

- ローカル開発では KABUSYS_ENV=development を使い、発注ブロック等の安全策を有効にしておくと良いです。
- ペーパートレードは KABUSYS_ENV=paper_trading を設定すると本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を使う機能は API コストが発生するため使用の際は注意してください。テストでは API 呼び出し関数をパッチしてモックする設計になっています（テストしやすさを考慮）。
- logs/ 以下に起動ごとのログファイルが出力されます。デフォルトで日次ローテーション・30 日保持です。

---

## 参考コマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視開始: python -m kabusys.run_monitoring
- エンジン開始: python -m kabusys.run_execution
- ペーパートレード検証: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

この README はリポジトリ内コードの docstring / コメントを基にまとめています。各モジュールの詳細な使用方法やパラメータは該当ファイル内の docstring を参照してください。もし README に追加したい具体的なコマンド例や環境変数のテンプレート（.env.example）を用意したい場合は指示ください。