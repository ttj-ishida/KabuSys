# KabuSys

日本株向け自動売買システム（ライブラリ/ツール群）のリポジトリ用 README。  
この README は提供されたコードベースに基づき、プロジェクトの概要・機能・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネント群を含むシステムです。主要な機能は以下の通りです。

- 実行エンジン（ExecutionEngine）による発注ロジック（paper_trading / live をサポート）
- 監視システム（Monitoring）：プロセス状態、データ鮮度、注文滞留、ドローダウン等の監視とログ永続化
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- リサーチ / ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定） — OpenAI を利用
- ツール群（.env ウィザード、設定検証、Paper Trading 検証レポート など）
- SQLite / DuckDB を用いたデータ永続化と分析

設計方針の一部:
- DuckDB を使った分析・ファクター計算（prices_daily / raw_financials 等）
- SQLite を使った監視・発注ログ（monitoring.db / paper_trading.db）
- 本番とペーパートレードは DB を分離
- OpenAI 呼び出しはフェイルセーフ（API失敗時にスキップやデフォルトにフォールバック）

---

## 主な機能一覧

- 実行（run_execution）
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db など）に記録
  - プロセス優先度調整、PID ファイル管理、停止フラグ検出（data/stop_requested.flag）をサポート

- 監視（run_monitoring / MonitoringEngine）
  - CPU / メモリ / ディスク利用率、Execution プロセス存在チェック、データ鮮度チェック
  - 注文滞留チェック、約定異常チェック、ドローダウン・ポジション上限監視
  - Kill Switch（条件を満たした場合に data/kill.flag を書き込み Execution を停止させる）
  - LINE によるアラート送信（AlertManager、クールダウン管理）

- ポートフォリオ構築
  - 候補選定、等配分/スコア配分、リスクベースのポジションサイズ計算
  - セクター別キャップ適用、レジーム乗数（bull/neutral/bear）

- リサーチ / ファクター
  - モメンタム、ボラティリティ、バリューファクターなどの計算（DuckDB）
  - 将来リターン計算、IC 計算、統計サマリー

- AI（OpenAI）
  - ニュース記事の銘柄別センチメントスコアリング（ai_scores テーブルへ書込）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（market_regime テーブルへ書込）
  - OpenAI API のリトライ/バックオフや JSON 検証を実装

- ツール
  - .env 対話ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

以下はローカルで開発/実行するための一般的な手順です（環境に応じて調整してください）。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 必要な主なパッケージ（参考）
     - psutil, duckdb, openai, requests, PyYAML（設定検証で YAML を検証したい場合）

4. .env を作成・編集
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作り、必須値を設定する。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトでは `data/` 下に DB 等を作成します。必要に応じてディレクトリ作成やパス変更を .env で行ってください。

注意:
- AI 機能を使う場合、OpenAI API キーが必要です: 環境変数 OPENAI_API_KEY を設定してください。
- system/process priority の設定に psutil による権限が必要な場合があります（特に高優先度設定）。

---

## 必須 / 主要な環境変数

必須（validate_config でチェックされる主な項目）
- JQUANTS_REFRESH_TOKEN （J-Quants API）
- KABU_API_PASSWORD （kabuステーション API）

主要な任意設定（デフォルト値は .env のウィザードや Settings クラス参照）
- KABUSYS_ENV: execution 環境。候補: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）（デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知（任意）
- OPENAI_API_KEY: OpenAI を使う AI 機能で必須
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で使用）

その他監視・リスク関連のしきい値は .env（または config/*.yaml）で調整できます。

---

## 使い方（代表的なコマンド）

基本的な CLI 実行はモジュールを直接実行します（プロジェクトルートで実行する前提）。

- .env の対話式生成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - 本番/開発/ペーパーを切替えて起動（KABUSYS_ENV による）
  - 例（ペーパートレード）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 例（開発）:
    - KABUSYS_ENV=development python -m kabusys.run_execution
  - 実行中は data/stop_requested.flag を作成することで安全に停止できます（スクリプトは起動時に既に停止フラグがあれば起動を行いません）。

- 監視ループ起動（SystemMonitor をポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で間隔を秒数で上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラム呼び出し）
  - news_nlp.score_news / regime_detector.score_regime 等をプログラムから呼ぶ際は OPENAI_API_KEY を設定してください。
  - 例（スクリプト内で）:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")

プロセス管理 / フラグ
- data/stop_requested.flag: run_monitoring / run_execution がこのフラグを見て停止します（存在検知で安全停止）。
- data/kill.flag: KillSwitch が書き込む flag。ExecutionEngine が kill.flag を監視することで強制停止できます。
- data/execution.pid: 実行エンジンの PID を書き込むファイル（run_execution 側で扱われます）。

---

## 設計上の注意点・運用メモ

- 監視（Monitoring）は Settings.env にかかわらず常に本番 sqlite_path を使用する設計があるため、運用時は監視 DB のパスに注意してください。
- KABUSYS_ENV=paper_trading の場合は MockBroker を使って発注を分離し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。実際の発注は行われません（本番 DB と完全分離）。
- OpenAI を利用する処理はネットワーク/課金が発生し得るため、API キーは慎重に管理してください。API エラーやレートリミットはリトライロジックとバックオフで扱われますが、失敗時は安全側のフォールバックを行う設計です。
- psutil によるプロセス優先度設定や CPU affinity 設定は権限や OS に依存します。権限不足時は警告でスキップされます。
- DuckDB のバージョンや SQLite の構造変更により executemany の挙動や型バインドが制約される場合があります（コード中で互換性対策あり）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイルとサブパッケージの抜粋です（提供ソースに基づく）。

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数/.env 管理
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py?
    - monitoring_db.py     — SQLite スキーマ初期化 / 永続化 API
    - system_monitor.py    — システム状態・データ鮮度監視
    - trade_monitor.py     — 注文滞留・約定異常監視
    - risk_monitor.py      — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py     — LINE 通知
    - kill_switch.py       — Kill Switch 書き込みユーティリティ
  - execution/              — 発注関連（OrderManager, ExecutionEngine 等） ※一部ファイル参照あり
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
    - news_nlp.py          — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py   — 市場レジーム判定（OpenAI + MA200）
  - tools/
    - __init__.py
    - paper_verification_report.py

※リポジトリ全体のファイル一覧は実際のソースツリーでご確認ください。ここでは主要部分を抜粋しています。

---

## 参考 / 追加情報

- デフォルトの DB パスや各種閾値は `kabusys.config.Settings` クラスで確認できます。
- YAML ベースの config ファイル（config/*.yaml）が扱われる部分もあります（validate_config で存在とパースをチェック）。PyYAML 未インストール時はパース検証をスキップします。
- Paper Trading レポートの閾値（稼働率/成功率/レイテンシ等）は tools/paper_verification_report.py 内で定義されています。運用に応じて調整してください。

---

もし README の追加項目（導入図、CI/CD・デプロイ手順、詳細な API リファレンス、config/*.yaml の仕様など）を望まれる場合は、どの部分を拡張したいか教えてください。