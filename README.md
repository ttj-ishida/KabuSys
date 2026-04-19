# KabuSys

日本株向け自動売買フレームワーク（ミニマム実装）

このリポジトリは、監視・発注・ポートフォリオ構築・リサーチ・AI を組み合わせた日本株自動売買システムのコア部分です。  
ドキュメントは日本語で記載しています。

---

## プロジェクト概要

KabuSys は次の役割を持つ複数のコンポーネントで構成されています。

- ExecutionEngine：ブローカークライアントを介して発注を行うエンジン（本番／ペーパートレード対応）
- Monitoring：システム稼働状況・データ鮮度・注文ログ・リスク（ドローダウン等）をポーリング監視し、Kill Switch を作動させる
- Portfolio：候補選定、重み付け、ポジションサイズ計算などのポートフォリオ構築ロジック（純粋関数群）
- Research：DuckDB を使ったファクター計算・将来リターン・特徴量解析
- AI：ニュース記事を LLM（OpenAI）でセンチメント評価してスコアを保存、マーケットレジーム判定等
- ユーティリティ：設定読み込み、ログ設定、プロセス優先度設定など

設計方針の一部：
- 環境変数 / .env による設定管理
- DuckDB / SQLite を用いたデータ保管（分析用 / 監視用）
- 本番（live）とペーパートレード（paper_trading）を明確に分離
- 外部 API (OpenAI 等) は明示的にキーを渡すか環境変数で設定

---

## 主な機能一覧

- システム監視（CPU/メモリ/ディスク、データ鮮度、プロセス生存）
- 取引イベントログ（trade_logs）、ポジション管理、リスクログの永続化（SQLite）
- Kill Switch（条件達成時に data/kill.flag を書き込んで Execution 停止）
- ExecutionEngine：ブローカー抽象化（本番 / Mock 対応）、リスク管理、注文管理、再整合（reconciler）
- ポートフォリオ構築：候補選定、等金額・スコア加重配分、リスクベース・単元調整
- リサーチ：モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
- AI モジュール：ニュースの銘柄別センチメント評価（OpenAI）・市場レジーム判定
- CLI ユーティリティ：
  - config_setup（対話式 .env 作成）
  - validate_config（設定検証）
  - tools.paper_verification_report（ペーパートレード検証レポート生成）

---

## 前提 / 必要ライブラリ

（最小限の例。実際の requirements.txt を用意している場合はそちらを使用してください）

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config 検証で YAML のパースを行う場合）

例（仮のインストールコマンド）:
pip install duckdb psutil openai PyYAML

SQLite は標準ライブラリで利用可能です。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成して data ディレクトリ等を設定

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合は:
     - python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要時）
   - mkdir -p data logs

注意: 自動で .env を読み込む仕組みがあり、プロジェクトルート（.git または pyproject.toml がある場所）から .env / .env.local を読み込みます。テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live）デフォルト: development
  - paper_trading の場合、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）が使用される
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant | partial | never | reject）※ paper_trading 用
- OPENAI_API_KEY（AI モジュール利用時）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- LOG_DIR（デフォルト logs/）
- MONITOR_POLL_INTERVAL（監視ポーリング秒、run_monitoring 用デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（1 で起動時に kill.flag を自動クリア、デフォルト 0。本番は 0 推奨）
- KILL_FLAG_PATH（デフォルト data/kill.flag）
- PID_FILE_PATH（実行エンジン PID ファイル、デフォルト data/execution.pid）

---

## 主要コマンド / 使い方

各モジュールはパッケージモジュールとして起動できます。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にペーパー取引ログを保存して本番 DB と分離します。
    - 起動時に data/stop_requested.flag（または設定された停止フラグ）が存在する場合は起動を中止します。
    - 起動時にプロセス優先度を "high" に設定します。
    - 動作中は PID ファイル（デフォルト data/execution.pid）を書きます。

- Monitoring 起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを永続化します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 系（関数 API）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  - OpenAI API キー（OPENAI_API_KEY）を設定するか、api_key 引数で明示的に渡してください。

停止フラグ / Kill スイッチ:
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止を促します。
- 監視処理や外部オペレーターにより kill.flag が存在すると ExecutionEngine が安全に停止します。

ログ:
- ログは標準出力と日次ローテートされるファイル（logs/<app_name>.log）に出ます。
- ログレベルは LOG_LEVEL / 引数で指定可能。

---

## 典型的なワークフロー（例）

1. .env を作成（config_setup）
2. 設定検証（validate_config）
3. データロード（DuckDB に prices_daily などを準備）
4. ExecutionEngine を起動（本番または paper_trading）
   - python -m kabusys.run_execution
5. 別プロセスで Monitoring を起動
   - python -m kabusys.run_monitoring
6. 定期的に AI スコアやレジーム判定をスケジュールして実行（外部 scheduler, cron 等）

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイル/パッケージを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / .env 自動ロード / Settings クラス
    - config_setup.py               — 対話式 .env ウィザード
    - validate_config.py            — 設定検証 CLI
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — Monitoring ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - utils/
      - __init__.py
      - logging_setup.py            — ログ設定ユーティリティ
      - process_priority.py         — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py            — SQLite 永続化層（system_status, trade_logs 等）
      - system_monitor.py           — システム状態・データ鮮度監視
      - trade_monitor.py            — （取引）監視ロジック（滞留注文・約定異常等）
      - risk_monitor.py             — ドローダウン・ポジション上限監視
      - kill_switch.py              — kill.flag の作成 / 判定
      - monitoring_engine.py        — 各 Monitor の統合実行
      - alert_manager.py            — （通知）アラート送信ロジック（LINE 等）
    - execution/
      - execution_engine.py         — ExecutionEngine 本体
      - broker_factory.py           — BrokerClient 作成（本番 / mock）
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
      - news_nlp.py                 — ニュースを LLM に送って銘柄別スコア化
      - regime_detector.py          — 市場レジーム判定（MA + macro sentiment）
      - __init__.py

- data/                              — 実行時生成（SQLite / PID / flag 等）
- logs/                              — ログ出力先（デフォルト）

---

## 実装上の注意点 / トラブルシューティング

- Monitoring は環境に関係なく Settings.sqlite_path（監視 DB）を使用します。ペーパートレード DB は ExecutionEngine 側で分離されています。
- .env の自動読み込みはプロジェクトルート（.git / pyproject.toml）を基準に行われます。テスト等で自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI 機能（news_nlp、regime_detector）を使う場合は OpenAI API キー（OPENAI_API_KEY）または関数引数でキーを渡してください。API 呼び出しはリトライとフェイルセーフがありますが、キー未設定だと例外になります。
- run_execution/run_monitoring は起動時にプロセス優先度を high に設定しようとします。権限がない場合は警告が出るだけで継続します。
- SQLite / DuckDB のパスに対して親ディレクトリが存在しない場合、validate_config は警告を出しますが起動時に自動作成されることがあります。
- kill.flag（data/kill.flag）を書き込むと ExecutionEngine 側で検出して停止します。起動時に自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。

---

## ライセンス / バージョン

- パッケージバージョンは kabusys.__version__ （現状 "0.1.0"）
- ライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（なければプロジェクトに合わせて追加してください）。

---

この README はコードベースの主要構成と実行手順をまとめたものです。追加の運用手順やデプロイ手順（systemd / docker / k8s など）を導入する場合は本 README に追記してください。