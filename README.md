# KabuSys

日本株自動売買システムの一部をまとめたリポジトリ（ライブラリ＋起動スクリプト群）です。  
この README はコードベースから読み取れる主要機能、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するコンポーネント群を提供します。主な機能は以下の通りです。

- 戦略・ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- Market Regime とニュース NLP を用いたマクロ評価（OpenAI API 統合）
- ExecutionEngine（発注エンジン）の起動スクリプト（paper_trading と live を分離）
- Monitoring（システム・注文・リスク監視）および Kill Switch の実装
- Paper Trading 検証レポート生成ツール
- 環境変数ウィザード / 設定検証ツール

設計上の特徴：
- DB は DuckDB（分析）と SQLite（監視・発注履歴）を併用
- Paper Trading は本番 DB と分離（専用 SQLite）
- OpenAI と連携する NLP モジュールは API 呼び出しの失敗に対してフェイルセーフを持つ
- .env ファイルをサポートし、プロジェクトルートから自動読み込みされる（必要に応じて無効化可能）

---

## 機能一覧

- 環境設定関連
  - 対話式 .env 作成/更新: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 起動スクリプト（エントリ）
  - ExecutionEngine 起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、data/paper_trading.db を使用
    - 起動時に PID ファイルを書き、 data/stop_requested.flag を監視して停止
  - Monitoring 起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
    - 監視ログは sqlite（Settings.sqlite_path）に永続化（monitoring モジュールが管理）

- 監視（monitoring）
  - SystemMonitor: システム資源（CPU/メモリ/ディスク）、データ鮮度、Execution プロセス状態を監視
  - TradeMonitor: 発注・約定の異常検出（stale orders / price anomalies 等）
  - RiskMonitor: ドローダウン／ポジション上限の監視、必要に応じて risk_logs に記録
  - KillSwitch: しきい値トリガで data/kill.flag を書き込み、ExecutionEngine を停止させる仕組み
  - MonitoringDB: monitoring 用 SQLite のスキーマ作成・読み書きユーティリティ

- Portfolio（銘柄選定・配分）
  - 候補選定: select_candidates
  - 等配分 / スコア配分: calc_equal_weights / calc_score_weights
  - セクター上限適用: apply_sector_cap
  - レジーム乗数: calc_regime_multiplier
  - ポジションサイズ計算（単元丸め・aggregate cap 処理）: calc_position_sizes

- Research（分析）
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン計算 / IC / 統計サマリ: calc_forward_returns, calc_ic, factor_summary, rank

- AI（OpenAI 連携）
  - ニュース NLP による銘柄ごとのセンチメント算出: kabusys.ai.news_nlp.score_news
  - マクロセンチメント＋ETF MA による市場レジーム判定: kabusys.ai.regime_detector.score_regime

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

前提
- Python >= 3.10（コード中で型ヒントに `|` を使用）
- 標準的なビルド環境（virtualenv 推奨）

1. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（最小）
   - pip install duckdb psutil openai
   - PyYAML は `python -m kabusys.validate_config` の YAML 検証を有効にするために推奨:
     - pip install pyyaml

   （将来的に requirements.txt を用意する場合はそちらを使用してください）

3. ディレクトリ作成（ログ・DB 用）
   - mkdir -p data logs

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（リポジトリにコミットしないこと）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - run_execution / run_monitoring 起動時に monitoring DB スキーマは自動作成されます。
   - 必要に応じて DuckDB ファイルも自動作成されます。

注意:
- OpenAI を使う機能を利用する場合は環境変数 `OPENAI_API_KEY` を設定するか、該当 API 呼び出しに明示的な api_key を渡してください。
- 自動 .env ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方

主要スクリプト／コマンド例を示します。

1. 環境ウィザード
   - python -m kabusys.config_setup
     - .env を対話式で生成・更新します。

2. 設定検証
   - python -m kabusys.validate_config
   - エラーや警告が表示されます。

3. ExecutionEngine を起動する（実行エンジン）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient を使って発注をシミュレートします。
     - 起動時に data/execution.pid などの PID ファイルを用いる可能性があります。
     - data/stop_requested.flag が作成されると安全に停止します。

4. Monitoring を起動する（監視プロセス）
   - python -m kabusys.run_monitoring
   - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
   - 監視ログは SQLite（settings.sqlite_path）に永続化されます。

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

6. AI / リサーチ機能（ライブラリ的に使用）
   - Python から直接呼び出し例:
     - from kabusys.ai.news_nlp import score_news
     - from kabusys.ai.regime_detector import score_regime
     - score_news(conn, target_date, api_key="sk-...")
     - score_regime(duckdb_conn, target_date, api_key="sk-...")
   - OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。

ログ:
- 既定では `logs/<app_name>.log` に日次ローテーションで出力されます（logs ディレクトリを作成しておくことを推奨）。

停止フラグ／Kill Switch:
- ExecutionEngine の外部停止:
  - `data/stop_requested.flag` を作成すると run_execution 側で検知してプロセスを停止します（run_monitoring もこれを見ます）。
- KillSwitch（リスクトリガでの自動停止）:
  - `data/kill.flag` が書き込まれると ExecutionEngine に停止シグナルを送る用途で使います。KillSwitch は監視結果に応じてこのファイルを作成します。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須） — kabuステーション API 接続パスワード
- KABUSYS_ENV（development | paper_trading | live） — 実行環境
- OPENAI_API_KEY — OpenAI API を使用する機能で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを抑止（1 に設定すると無効）

（詳しくは kabusys.config.Settings のプロパティを参照してください）

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュールのツリー（src/kabusys 配下を中心に抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (参照あり：実装は別ファイル)
      - monitoring_engine.py
    - execution/
      - execution_engine.py (参照)
      - order_manager.py (参照)
      - order_repository.py (参照)
      - reconciler.py (参照)
      - broker_factory.py (参照)
      - risk_manager.py (参照)
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
    - data/ (実行時に使うファイルや DB を置く想定)
      - paper_trading.db (paper_trading 用 SQLite, 実行時生成)
      - monitoring.db (監視用 SQLite, 実行時生成)
      - stop_requested.flag / kill.flag / execution.pid など
    - tools/
      - __init__.py
      - paper_verification_report.py

（実際のリポジトリでは他にもファイル・ディレクトリが存在する可能性があります）

---

## 開発上の注意点・設計メモ

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を起点）から行われます。テストや特殊な実行環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- Paper Trading は本番データベースと分離しているため、ローカルでの検証が比較的安全です（ただし設定ミスには注意）。
- OpenAI 呼び出しはネットワーク・API エラーに対して多段リトライやフォールバック（スコア=0 等）を行う設計です。ただし API キーの管理は開発者で適切に実施してください。
- プロセス優先度や CPU affinity の設定は psutil を利用しています。権限不足により設定が失敗することがあるため、ログで警告が出ることがあります（例: 非 root ユーザーでの nice の制御）。

---

もし README に追記して欲しい箇所（例: 実際の ExecutionEngine の設定項目説明、broker の設定例、CI / テストの実行方法など）があれば教えてください。必要に応じてセクションを追加して詳細化します。