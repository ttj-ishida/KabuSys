# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ・起動スクリプト群）。  
本リポジトリには取引エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・リサーチ・AIによるニュース解析などの主要コンポーネントが含まれます。

※ 本 README はソースコード（src/kabusys 以下）を元に日本語でまとめた利用案内です。

---

## 概要

KabuSys は次のような目的をもつモジュール群を提供します：

- Execution：注文送信、注文管理、リスク管理（本番 / ペーパートレード切替対応）
- Monitoring：システム状態、注文ログ、リスク指標の定期監視とアラート／Kill Switch
- Portfolio：銘柄選定・重み計算・ポジションサイズ決定（純粋関数）
- Research：DuckDB を使ったファクター計算・特徴量探索
- AI：OpenAI を利用したニュースセンチメント（ai.news_nlp）や市場レジーム判定（ai.regime_detector）
- Tools：ペーパートレード検証レポートなどのユーティリティスクリプト
- Utils：ログ設定、プロセス優先度設定、.env 読み込み補助 など

設計方針の特徴：
- 環境設定は .env（.env.local）および環境変数で管理。自動読み込みはソースルート検出に基づく
- DuckDB / SQLite をデータ層に使用（本番/ペーパーを分離）
- AI モジュールは OpenAI API を使用（APIキーが必要）
- 多くの処理はフェイルセーフ（API失敗時はフォールバック or スキップ）で実装

---

## 主な機能一覧

- run_execution.py：ExecutionEngine 起動スクリプト（KABUSYS_ENV により paper_trading 用 DB と MockBroker を利用）
- run_monitoring.py：SystemMonitor のポーリング起動（MONITOR_POLL_INTERVAL で間隔指定可）
- config_setup.py：.env の対話式作成ウィザード
- validate_config.py：.env および config/*.yaml の事前検証 CLI
- tools/paper_verification_report.py：Paper Trading 検証レポート生成（稼働率、成功率、レイテンシ等）
- ai/news_nlp.py：ニュース記事を LLM でスコアリングし ai_scores に書き込む
- ai/regime_detector.py：ETF（1321）MA とマクロニュースを合成して market_regime を判定、書き込み
- monitoring/*：MonitoringDB（SQLite永続化）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine
- portfolio/*：候補選定・重み付け・ポジションサイズ計算・セクター制約の適用
- research/*：ファクター計算（モメンタム・ボラティリティ・バリュー）、IC 計算、特徴量探索

---

## セットアップ手順（開発 / 実行環境）

1. リポジトリをクローン
   - git clone <repo>

2. Python 環境（推奨: venv）を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 主な依存（コード参照）:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. .env を作成
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（下記「環境変数」の例を参照）

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も厳密にチェックする場合:
     - python -m kabusys.validate_config --strict

6. 実行
   - 実運用スクリプトは以下を参照（後述）

---

## 環境変数（主要）

自動ロード: OS 環境変数 > .env.local > .env（プロジェクトルートが特定できない場合は自動ロードをスキップ）
自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な変数（重要順）:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: mock broker を使い data/paper_trading.db に記録（本番 DB と完全分離）
  - live: 本番
  - development: 開発
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: Execution/kill flag 管理

簡単な .env 例（実際は秘密値を入れること）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
OPENAI_API_KEY=sk-xxxx...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（主要コマンド / スクリプト）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告があると終了コード 1）
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading DB に記録
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 実行中は data/execution.pid に PID を書き、停止フラグで停止可能

- 監視起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔指定（秒、デフォルト 60）
  - 停止は data/stop_requested.flag を作成すると次回ループで検知して終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング / レジーム判定（プログラム的に呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: Optional[str])
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: Optional[str])
  - 注意: 両関数は OpenAI API キーを要求します（引数または環境変数 OPENAI_API_KEY）

- ロギング
  - すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を使用して統一的にログを出力します
  - デフォルト: stdout + 日次ローテートファイル（logs/<app_name>.log）

---

## 監視・停止（Kill Switch / Flag ファイル）

- Kill Switch:
  - KillSwitch.evaluate が条件（ドローダウン、ポジション上限 等）を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る設計
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を自動クリアします（本番では 0 推奨）
- 手動停止:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了する設計

---

## ディレクトリ構成（抜粋）

以下は src/kabusys の主要ファイル・モジュールのツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py         (コード内参照。監視ロジック)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         (アラート送信ロジック)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/*.py, execution/*.py, data/*.py 等（多数の補助モジュール）

注意: ここに示したファイルはリポジトリ内の主要ファイルを抜粋したものです。実際の全ファイルはツリーを参照してください。

---

## 開発上の注意 / FAQ

- 環境変数の優先順位:
  - OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- paper_trading モード:
  - KABUSYS_ENV=paper_trading のとき、実際のブローカー呼び出しは MockBroker に置き換えられ、データは PAPER_TRADING_SQLITE_PATH に記録されます。本番 DB と分離されます。
- OpenAI 呼び出し:
  - API 失敗時は部分的にフォールバック（0.0 等）する設計のため、スコア処理は堅牢ですが、適切な API キーとレート制限管理が必要です。
- ログディレクトリが作成できない環境（権限不足等）ではファイルハンドラ設定をスキップして stdout のみで動作します。
- process_priority.set_process_priority() は OS によって挙動が異なります。権限不足で設定できない場合は警告が出ますが処理は継続します。

---

## 参考コマンドまとめ

- 仮想環境の作成・依存インストール（例）
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai PyYAML

- .env 作成
  - python -m kabusys.config_setup

- 構成チェック
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視起動
  - python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ライセンス・セキュリティ

- .env（機密情報）は絶対に Git にコミットしないでください（config_setup.py も同旨のヘッダを出力します）。
- 実運用（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にする等の安全策を有効にしてください。
- 実稼働での資金を扱う際は必ずリスク設定を慎重に確認してください（validate_config の警告を活用）。

---

必要であれば以下を追加で作成します：
- 例の .env.example ファイル
- 起動 / systemd / docker 用のデプロイ手順テンプレート
- 全 API の引数仕様一覧（ai.score_news, ai.score_regime など）