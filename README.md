# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。  
監視（Monitoring）・実行エンジン（ExecutionEngine）・ポートフォリオ構築・リサーチ・AI（ニュースNLP / レジーム判定）などの機能をモジュール化して提供します。

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール化された自動売買フレームワークです。

- 株価データを用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 実行エンジン（発注管理・リスク管理・再突合）
- 監視モジュール（システム稼働・注文滞留・リスク監視）と Kill Switch
- Paper Trading（模擬発注）サポートと検証レポート生成
- OpenAI を利用したニュースセンチメント / マクロセンチメント評価

設計方針の一部:
- 多くの機能は純粋関数または DB 接続を受け取る形で実装され、本番 API への不要なアクセスを避ける
- 環境変数と .env による設定管理（対話式ウィザード・検証 CLI あり）
- DuckDB（分析用）と SQLite（監視・発注ログ用）を併用

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 対話式ウィザード: `kabusys.config_setup`
  - 設定検証: `kabusys.validate_config`
- 実行（Execution）
  - 実注文/模擬発注（KABUSYS_ENV に応じて MockBroker）
  - リスク管理（position cap / drawdown 等）
  - 発注履歴・トレードログの永続化（SQLite）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・実行プロセス検出
  - TradeMonitor: 発注滞留 / 約定異常の検出
  - RiskMonitor: ドローダウン・ポジション数監視とログ記録
  - KillSwitch: 条件到達で data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各モニタの定期実行とアラート送出
- ポートフォリオ構築
  - 候補選定（スコア降順）
  - 等金額・スコア加重の重み計算
  - リスク調整（セクター制限、レジーム乗数）
  - 株数算出（リスクベース / 等分配 / スコアベース）、単元丸め・aggregate cap
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 使用）
  - 将来リターン・IC 計算・統計サマリ
- AI（OpenAI 連携）
  - ニュースをまとめて LLM に投げ、銘柄ごとの sentiment を ai_scores に書き込み
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）

---

## セットアップ手順（基本）

前提: Python 3.10 以上を推奨（PEP 604 の型記法などを使用）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 以下は最低限の推奨パッケージ（プロジェクトに requirements.txt がある場合はそちらを使用）
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - PyYAML（config 検証時に YAML のパースを行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成（対話式推奨）
   - 対話ウィザードを実行:
     - python -m kabusys.config_setup
   - または手動で `.env` をプロジェクトルートに配置（例は下記）

5. 設定検証（起動前の確認）
   - python -m kabusys.validate_config
   - 問題がある場合は出力に従って修正。厳密モード:
     - python -m kabusys.validate_config --strict

注意:
- .env は決して Git にコミットしないでください（機密情報を含みます）。
- 環境変数で上書き可能です。

### 最低限必要な環境変数（例）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を利用する場合）
- KABUSYS_ENV（development / paper_trading / live） — デフォルト: development
- その他: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL など（多くはデフォルトあり）

例（.env の最小例）:
JQUANTS_REFRESH_TOKEN="your_jquants_token"
KABU_API_PASSWORD="your_kabu_password"
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方（起動・主要スクリプト）

主にモジュールはモジュールパス指定で実行します。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH, デフォルト: data/paper_trading.db）に記録されます
    - 起動時に data/stop_requested.flag が存在すると起動を停止
    - 実行中、data/stop_requested.flag を置くと安全に停止します

- 監視プロセス（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用（監視 DB: settings.sqlite_path）
    - data/stop_requested.flag を検知するとループを終了

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit code 1）

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: env PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

運用に関する重要なファイル・フラグ:
- data/kill.flag
  - KillSwitch が発動した際に作成されるフラグ。ExecutionEngine に停止を促すために使用します。
- data/stop_requested.flag
  - run_* スクリプトの外部停止要求に使われる短期停止フラグ。
- data/execution.pid
  - ExecutionEngine が PID を保存するファイル（Settings.pid_file_path を参照）。

ログ:
- デフォルトで `logs/` にアプリ別のログファイルを日次ローテーションで出力します（kabusys.utils.logging_setup）。
- 環境変数 LOG_DIR または引数で変更可能。
- ログ出力レベルは LOG_LEVEL（デフォルト INFO）。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys）内の主要ファイル／モジュールの一覧（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py        — ログ設定ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py        — SQLite テーブル定義 + MonitoringDB
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py        — （実装ファイルがある想定）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py        — （実装ファイルがある想定）
    - execution/
      - execution_engine.py     — ExecutionEngine（起動ロジックは run_execution 参照）
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - data/                      — （実行時に生成されることが想定）
      - monitoring.db（デフォルト SQLite）
      - paper_trading.db（paper_trading 用 DB）
      - kabusys.duckdb（DuckDB ファイル）

注: 上記のうち一部ファイルは別途実装や設定（外部サービスの接続など）が必要です。

---

## 運用上の注意 / トラブルシューティング

- Python バージョン:
  - 3.10 以上を推奨（Type union 演算子 | を使用）
- 依存パッケージ不足:
  - duckdb, psutil, openai, PyYAML などが無いと一部機能が動作しません。インストールしてください。
- ログディレクトリ作成に失敗する場合:
  - 書き込み権限のあるパスを LOG_DIR に指定するか、実行ユーザの権限を確認してください。
- Kill Switch / kill.flag:
  - 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアを無効にする）。
- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔を秒単位で調整できます。0 以下や非整数は無効でデフォルト 60 秒にフォールバックします。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル作成 / カラム追加を行います。古い DB からのアップグレード時に必要なカラムが自動で追加される場合があります。

---

## 開発・拡張のヒント

- DuckDB を使った分析 / ファクター計算関数は DB 接続を引数で受け取るため、テスト時に in-memory DB を用意して単体テストが行いやすい設計です。
- OpenAI 呼び出しは `_call_openai_api` を通す形になっているため、unittest.mock.patch により簡単にモック可能です（テストに便利）。
- ログ設定はアプリ名ごとに分かれているので、複数プロセスを同時に起動してもログファイルが分離されます。

---

必要であれば README に
- 依存関係の固定（requirements.txt の提案）
- systemd / supervisor / cron の起動スクリプト例
- CI 用のテスト実行手順
なども追加できます。どの情報を優先して追記しますか？