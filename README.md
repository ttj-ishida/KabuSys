# KabuSys — README

日本株自動売買システム（KabuSys）の簡易 README です。  
この README はコードベースの主要なモジュール・使い方・設定方法・ディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境設定ウィザード
  - 設定検証
  - 実行（ExecutionEngine）
  - 監視（Monitoring）
  - Paper Trading 検証レポート
  - AI 関連（ニュース NLP / レジーム判定）
- 主要環境変数（抜粋）
- 停止・Kill Switch の操作
- ディレクトリ構成（主なファイル説明）

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを想定した Python パッケージ群です。  
主要コンポーネントは戦略/ポートフォリオ構築、ポジションサイズ計算、発注エンジン（ExecutionEngine）、監視（Monitoring）、および研究用のファクター計算・特徴量探索です。  
監視ログや発注ログは SQLite（監視用）・DuckDB（分析用）に永続化されます。Paper Trading モードを用いて本番 DB と完全に分離したシミュレーションが可能です。

---

## 機能一覧

- 環境設定ウィザード（.env を対話式で作成）
- 設定検証 CLI（.env と config/*.yaml の基本チェック）
- ExecutionEngine（発注エンジン、paper_trading モード対応）
- Monitoring（システム状態 / 注文状態 / リスク監視、Kill Switch）
- Portfolio construction（候補選定、重み計算、ポジションサイジング）
- Research（ファクター計算、forward returns、IC 計算、統計サマリー）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定） — OpenAI API 使用
- Paper Trading 検証レポート出力ツール

---

## セットアップ手順（開発環境向け）

1. Python 仮想環境を作成して有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - requirements ファイルがある場合:
     - pip install -r requirements.txt
   - 主要依存（最小）:
     - pip install duckdb openai psutil
   - 解析用に PyYAML があると config/*.yaml の検証が有効になります:
     - pip install pyyaml

3. リポジトリルートに移動（.env 自動ロードや data/ パス解決に必要）

---

## 使い方

### 環境設定ウィザード（.env の作成）
対話式ウィザードで .env を生成できます。

コマンド:
- python -m kabusys.config_setup

作成される .env の例（抜粋）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

注意:
- .env は絶対に Git 等へコミットしないでください。

### 設定検証
作成した環境変数や config/*.yaml の整合性チェックを行います。

コマンド:
- python -m kabusys.validate_config
- 厳格モード（警告もエラー扱い）:
  - python -m kabusys.validate_config --strict

### 実行（ExecutionEngine）
発注エンジンを起動します。起動時にプロセス優先度を上げます。

コマンド:
- python -m kabusys.run_execution

挙動:
- 環境変数 KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して paper_trading 専用の SQLite（デフォルト data/paper_trading.db）に記録し、本番 DB と完全に分離します。
- 起動前に data/stop_requested.flag が存在する場合はエンジンを起動しません。
- 実行中は data/stop_requested.flag の存在をチェックし、見つかればエンジンを停止します。
- 実行中には data/execution.pid（デフォルト）に PID を書く仕組みがあります（pid ファイルパスは Settings で変更可能）。

### 監視（Monitoring）
SystemMonitor をポーリングして監視データを記録し、Kill Switch の評価やアラート発行を行います。

コマンド:
- python -m kabusys.run_monitoring

挙動・設定:
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。1 未満の値は無効化されデフォルトにフォールバックします。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視 DB を開きます。
- 停止はプロジェクトルート/data/stop_requested.flag を作成するか、Execution 側で Kill Switch（data/kill.flag）を検知させて行います。

### Paper Trading 検証レポート
Paper Trading データベースから検証レポートを生成します。

コマンド:
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db PATH を使うか、環境変数 PAPER_TRADING_SQLITE_PATH を設定

レポート指標（例）:
- 稼働率（uptime）
- 注文成功率（fill rate）
- 送信率（send rate）
- レイテンシ（avg / max / P95）
- リスク却下数

検証基準（デフォルト）:
- 稼働率 >= 99.0%
- 注文成功率 >= 90.0%
- 送信率 >= 95.0%
- P95 レイテンシ <= 200 ms

### AI 関連（ニュース NLP / レジーム判定）
- kabusys.ai.news_nlp.score_news: raw_news を OpenAI API（gpt-4o-mini）で評価し ai_scores テーブルへ書き込む。
- kabusys.ai.regime_detector.score_regime: ETF(1321) の MA200 乖離 + マクロニュースの LLM センチメントを組み合わせて市場レジームを判定し、market_regime テーブルへ書き込み。

注意:
- OpenAI を使う機能は環境変数 OPENAI_API_KEY を必要とします（または関数引数で指定）。
- API 呼び出しにはリトライ・フェイルセーフ（失敗時は中立値やスキップ）を備えています。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- KABUSYS_ENV — 実行環境。allowed: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（本番）デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の Fill 動作（instant | partial | never | reject）、デフォルト "instant"
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring のみ）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1、本番では 0 推奨）
- KILL_FLAG_PATH / PID_FILE_PATH — Settings で参照されるパス

Settings モジュールの自動読み込み:
- リポジトリルートに .env / .env.local があれば自動で読み込みます（OS 環境変数が優先）。自動読み込み無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 停止・Kill Switch の操作

- ExecutionEngine 側の緊急停止信号:
  - KillSwitch が条件を満たすと data/kill.flag を書き込みます（理由テキストを含む）。
  - ExecutionEngine は kill.flag を検知して適切に停止動作を行います。
- 手動で停止フラグを立てる（全プロセスの停止に使用）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution で検知して停止します。
- kill.flag の自動クリア:
  - 本番での自動クリアは危険です。KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。

注意:
- kill.flag と stop_requested.flag は挙動が異なります（kill.flag は主に KillSwitch による ExecutionEngine 停止理由の伝達、stop_requested.flag は manual stop 要請など）。

---

## ロギング

- setup_logging を通じて以下を設定:
  - StreamHandler → stdout（コンソール）
  - TimedRotatingFileHandler → logs/<app_name>.log（daily, 30 日保持）
- デフォルトログディレクトリ: logs/
- app 名:
  - run_execution では app_name="execution"
  - run_monitoring では app_name="monitoring"

---

## ディレクトリ構成（主要ファイルと説明）

以下は src/kabusys 以下の主なファイルと役割です（抜粋）。

- __init__.py
  - パッケージメタ情報（__version__ 等）

- config.py
  - Settings クラス: 環境変数 / .env 自動ロード、各種設定（パス・閾値など）をラップ

- config_setup.py
  - .env を対話式で作成・更新するウィザード

- validate_config.py
  - 環境変数と config/*.yaml の基本検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、起動/停止監視）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）

- utils/
  - logging_setup.py — 統一的なログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化と永続化 API（MonitoringDB クラス）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — （注文監視、コードベースに含まれる）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — Kill Switch のロジック（flag 書き込み）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — （アラート送信の抽象化）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
  - 発注フロー・発注ログ管理・ブローカラッパー等（発注ロジック）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定 / aggregate cap 等のロジック
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — momentum/value/volatility ファクター計算（DuckDB 利用）
  - feature_exploration.py — forward returns / IC /統計サマリ
  - 利用関数は DuckDB 接続を受け取り SQL を実行する設計

- ai/
  - news_nlp.py — raw_news を LLM でセンチメント解析して ai_scores へ書き込み
  - regime_detector.py — MA200 + マクロニュースを LLM で合成して market_regime を決定

- tools/
  - paper_verification_report.py — Paper Trading DB から検証レポート生成

---

## 補足・運用上の注意

- 本番運用（KABUSYS_ENV=live）時は特に以下を確認してください:
  - LINE 通知が設定されているか（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）
  - KILL_FLAG_CLEAR_ON_START は 0（自動クリアを無効化）
  - 本番 DB のバックアップ / アクセス権限
- Paper Trading は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI API を利用する機能はコストとレート制限に注意してください。失敗時は多くの関数がフェイルセーフ（中立値やスキップ）で動作しますが、結果の解釈には注意が必要です。

---

この README はコードの概要と運用に必要な最低限の情報をまとめたものです。詳細な運用手順や設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）がリポジトリ内にあればそちらを参照してください。何か追加で README に含めたい項目があれば教えてください。