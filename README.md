# KabuSys

日本株向け自動売買システムのパッケージ（抜粋）。  
この README はリポジトリ内の主要スクリプト/モジュール（起動スクリプト、設定・検証、監視、ポートフォリオ構築、リサーチ、AI 製品等）を使うための概要・セットアップ・使い方をまとめたものです。

注意: 実運用では .env に機密情報（API トークン等）を保存します。`.env` を Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は以下のような機能を持つ日本株自動売買システムのライブラリ兼ランチャー群です（コードベースの一部を抜粋）:

- 環境設定管理（.env 読み込み / ウィザード）
- 起動前設定検証 CLI
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）
- 監視（Monitoring）コンポーネント（システム状態・取引状態・リスク監視）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量解析）
- AI 製品群（ニュース NLP を用いた銘柄センチメント、レジーム判定）
- ユーティリティ（ロギング設定、プロセス優先度設定 等）

主要な設計方針:
- 本番データベースとペーパートレード DB を分離
- ルックアヘッドバイアスを避ける設計（日時参照の扱いに注意）
- フェイルセーフ: 外部 API エラーはスキップして継続する挙動が多い

---

## 機能一覧（抜粋）

- 環境設定
  - config_setup.py: 対話式ウィザードで .env 作成/更新
  - config.py: .env/.env.local の自動読み込み（無効化可）、Settings クラスで値を参照

- 設定検証
  - validate_config.py: 環境変数、設定ファイル、DB パス等の事前検証 CLI

- 実行系
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBroker を使用し `data/paper_trading.db` を利用
  - run_monitoring.py: SystemMonitor のポーリングループを起動、MONITOR_POLL_INTERVAL で間隔を指定可能

- 監視 / キルスイッチ
  - monitoring/*: system_monitor, trade_monitor, risk_monitor, monitoring_db, monitoring_engine, kill_switch, alert_manager 等
  - kill.flag により ExecutionEngine を停止させる仕組み

- ポートフォリオ構築
  - portfolio/*: 候補選定、重み付け、セクター上限、ポジションサイズ計算（単元株丸めや集計上限の調整を実装）

- リサーチ
  - research/*: ファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン計算、IC 計測等（DuckDB を利用）

- AI（OpenAI）
  - ai/news_nlp.py: ニュースを LLM でセンチメント評価し ai_scores に書き込み
  - ai/regime_detector.py: ETF（1321）MA とマクロニュースの LLM センチメントを合成して市場レジーム判定

- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを出力

- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング（stdout + 日次ローテートファイル）
  - utils/process_priority.py: クロスプラットフォームでの優先度 / CPU affinity 設定

---

## 必要要件（主な依存）

以下は本コードで利用されている主要ライブラリです。実際はプロジェクトに用意された requirements.txt や pyproject.toml を参照してください。

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config が YAML の検証を行う場合、オプション）

例: 仮想環境作成・インストール
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai pyyaml

※ 実際のプロジェクトでは requirements.txt / pyproject.toml に従ってください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成 & 必要パッケージをインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt  （無ければ個別インストール）

3. 環境変数設定
   - 対話式ウィザードを実行して .env を作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（`.env.example` を参照）
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 問題があれば修正。--strict を付けると警告も失敗扱いになります。

5. データディレクトリ
   - デフォルトで使用されるディレクトリ（例: data/, logs/）は起動時に自動作成されることが多いですが、事前に作成しておくと権限トラブルを減らせます。

---

## 使い方（起動・運用）

以下はパッケージモジュールとしての起動例（プロジェクトをパッケージとしてインストールせずソース直下で実行する想定）。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - Settings.KABUSYS_ENV により本番 / ペーパートレードを切替
    - paper_trading モード: MockBrokerClient を使用し DB を data/paper_trading.db に分離
    - 起動時に data/execution.pid に PID を書く等の管理（実装参照）
    - 起動前に data/stop_requested.flag が存在すると起動を中止

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に本番用の sqlite_path を使用（Settings に従う）
  - 停止: data/stop_requested.flag を作成すると監視ループは終了する

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証（CI などで使用）
  - python -m kabusys.validate_config
  - --strict オプションで警告を失敗扱いにする

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

- AI 機能（プログラムから呼び出す）
  - ニュース NLP: from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
    - api_key 未指定時は環境変数 OPENAI_API_KEY を利用
  - レジーム判定: from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境
  - development / paper_trading / live
  - paper_trading: ExecutionEngine が MockBroker を使い DB を分離
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う機能の API キー
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（本番は 0 推奨）

自動 .env 読み込み:
- プロジェクトルートに `.env` / `.env.local` があると自動で読み込まれます（OS 環境変数が優先）。
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ログ / DB / 停止制御

- ログ
  - デフォルト: logs/<app_name>.log（日次ローテーション、30日保持）
  - 標準出力にも同内容が出ます（stdout を使用）
  - 環境変数 LOG_DIR でログ保存先を変更可能

- データベース
  - DuckDB: 分析用（prices_daily, raw_news, raw_financials などを想定）
  - SQLite:
    - 監視用 (monitoring.db)
    - ペーパートレード用 (paper_trading.db)

- 停止制御
  - data/stop_requested.flag: run_monitoring / run_execution の起動・実行ループを停止するためのファイル（存在を検知して終了）
  - data/kill.flag: KillSwitch が作成するファイル。ExecutionEngine に停止シグナルを送るために使用される。KILL_FLAG_CLEAR_ON_START に注意（本番では自動クリアを無効にすることを推奨）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要構成（抜粋）です：

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env ウィザード CLI
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite 操作（テーブル作成・CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - broker_factory.py
    - execution_engine.py
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
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

プロジェクトルートには data/（DB・フラグファイル）、logs/（ログ）などが想定されています。

---

## 開発者向けメモ / 注意事項

- ペーパートレードと本番データは厳密に分離する設計ですが、設定ミスにより接続先が混在する可能性があるため .env と validate_config の出力を必ず確認してください。
- OpenAI 等の外部 API 呼び出しは冪等性・エラー耐性を考慮した実装になっていますが、API コストやレート制限に注意してください。
- ローカルでのテスト時は KABUSYS_ENV=development を利用し、KILL_FLAG_CLEAR_ON_START=1 を設定すると Kill Flag の自動クリアが行われます（本番では推奨されません）。
- logging_setup.setup_logging を各起動スクリプトで最初に呼び出して統一的なログ設定を行っています。
- run_monitoring の MONITOR_POLL_INTERVAL を 0 以下にすると無効値扱いでデフォルト 60 秒にフォールバックします。

---

もし README に追加したい情報（API ドキュメント、起動オプションの詳細、実運用手順、サンプル .env や DB スキーマ図など）があれば教えてください。必要に応じて追記・拡張します。