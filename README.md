# KabuSys — 日本株自動売買システム (README)

以下はこのリポジトリに含まれるコードベースの簡易 README です。日本語でプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアライブラリです。戦略（リサーチ・ファクター計算）、ポートフォリオ構築、ポジションサイズ計算、発注・注文管理（ExecutionEngine）、監視（Monitoring）、AI を使ったニュース評価やレジーム判定などのコンポーネントを含みます。設計方針としては、運用時の安全（ペーパートレード分離、Kill Switch、監視ログなど）と再現性（DuckDB/SQLite ベースのデータ、.env 管理）を重視しています。

---

## 主な機能一覧

- 環境設定・管理
  - .env 自動ロード（.env / .env.local）
  - 対話式設定ウィザード（config_setup）
  - 設定検証ツール（validate_config）

- 実行エンジン（Execution）
  - ExecutionEngine 起動スクリプト（run_execution）
  - Paper Trading 用の分離 DB と MockBroker（KABUSYS_ENV=paper_trading）

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - 監視ログ永続化（SQLite）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み、発注エンジンを停止）

- ポートフォリオ構築
  - 候補選定、等加重・スコア加重、リスク調整（セクター制限、レジーム乗数）
  - ポジションサイズ計算（単元丸め、リスクベース、aggregate cap）

- 研究（Research）
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量サマリー

- AI 機能
  - ニュースを LLM で評価して銘柄ごとのスコアを生成（news_nlp）
  - マクロニュース + 指標を使った市場レジーム判定（regime_detector）
  - OpenAI API を利用（モデル: gpt-4o-mini を使用想定）

- ユーティリティ
  - ログ設定ユーティリティ（console + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading の検証レポート生成ツール

---

## 前提 / 必要環境

- Python 3.10+（型アノテーションに `X | Y` を使用）
- 必要な Python パッケージ（主要な例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証時に YAML ファイルを検証する場合）
- SQLite（標準ライブラリ）
- ネットワーク接続（OpenAI API を使う場合）

※ requirements.txt はこのリポジトリに含まれていない場合があるため、上記パッケージを個別にインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン／展開する。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話式に必要な環境変数を入力して `.env` を生成できます。
   - 手動で作成する場合は `.env.example` を参考に、少なくとも必須変数を設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数や config/*.yaml の存在などを確認します。
   - --strict オプションで警告も失敗扱いにできます。

6. データディレクトリの準備
   - デフォルトでは `data/` に SQLite / PID / フラグファイルを置きます。必要に応じて `.env` の `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` を変更してください。
   - ログはデフォルトで `logs/` に出力されます（LOG_DIR 環境変数で変更可能）。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主なオプションとデフォルト:
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- OPENAI_API_KEY: OpenAI API を使う場合に設定
- PAPER_FILL_MODE: paper_trading 時の Mock ブローカーの約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1）

特殊:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

注意: `.env` は機密情報を含むため決してバージョン管理にコミットしないでください。

---

## 使い方（実行例）

各スクリプトはモジュールとして実行できます。プロジェクトルート（src の親）から実行してください。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能。
  - 監視は常に本番用の sqlite_path を使用（環境に関係なく monitoring は本番 DB を参照する仕様）。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動中に `data/stop_requested.flag` が存在すると起動・ループを終了します。
  - 実行時の PID ファイルは `data/execution.pid`（デフォルト）に書き込まれます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプションで --from / --to（YYYY-MM-DD）や --db PATH を指定可能。
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能。

- AI 機能（例: ニューススコア）
  - モジュール API をプログラムから呼び出します（例: kabusys.ai.score_news）。
  - OpenAI API を使用するため `OPENAI_API_KEY` が必要です。

停止 / Kill 操作:
- 監視ループ・実行ループの強制停止用にプロジェクト内の `data/stop_requested.flag` を作成すると、ループ系スクリプトが検知して安全に終了します（run_monitoring / run_execution）。
- Kill Switch（監視が判断して書き込む）: `data/kill.flag`。ExecutionEngine は起動時にこのフラグの有無を確認し、存在する場合は起動を行いません。Kill flag は Settings.kill_flag_path（デフォルト `data/kill.flag`）で指定可能。

ログ:
- ログは標準出力と日次ローテートファイル（logs/<app_name>.log）に出力されます。ログディレクトリは LOG_DIR 環境変数または引数で上書きできます。

---

## 開発・デバッグのヒント

- .env の自動読み込みは、プロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。
- validate_config は PyYAML が無い場合は YAML 内容チェックをスキップします（警告が出ます）。
- OpenAI 呼び出し部分はリトライ実装や JSON パースのサニタイズ処理が入っており、テスト時は該当呼び出しをモックすることを推奨します。
- DuckDB により研究用のクエリが高速に実行できるため、prices_daily / raw_financials 等のテーブルをロードして使います。

---

## ディレクトリ構成（主要ファイル）

リポジトリのルートが project_root としたときの主要な配置（src/kabusys 配下を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュースの LLM スコアリング
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite 監視ログ層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        — （存在する前提）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        — （存在する前提）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体（存在する前提）
    - broker_factory.py       — ブローカークライアント生成（Mock含む）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                     — 実行時ファイル（例: monitoring.db, paper_trading.db, pid, flags）
  - logs/                     — ログ出力先（デフォルト）

（※ 上記はコードベースの主要モジュールと想定存在ファイルをまとめています。実際のファイル一覧はリポジトリの内容を参照してください。）

---

## 注意事項 / 動作上の設計メモ

- run_execution は KABUSYS_ENV が `paper_trading` の場合、発注は MockBrokerClient に置き換わり、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- run_monitoring は監視用 DB（monitoring.db）へ状態を書き込みます。MONITOR_POLL_INTERVAL で間隔を調整可能。
- Kill Switch（監視側）で `data/kill.flag` が書き込まれると ExecutionEngine は起動を抑止する、または実行中は停止されます。
- AI 機能は OpenAI API を前提とするため、API キー・コスト管理に注意してください。API 失敗時はフェイルセーフで処理を継続するよう実装されていますが、信頼性やレイテンシ要件は運用で検証してください。

---

以上がこのコードベースの README.md（日本語）の要約です。追加の詳細（モジュール API、DB スキーマ詳細、運用手順など）が必要であれば、どの項目を深掘りするか指示してください。