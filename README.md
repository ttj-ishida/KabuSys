# KabuSys

日本株向け自動売買システムのサブセット実装（ライブラリ + 起動スクリプト）。  
このリポジトリは、注文実行エンジン、監視コンポーネント、ポートフォリオ構築、ファクター計算、AI を用いたニューススコアリング等の主要機能を含みます。

---

## プロジェクト概要

KabuSys は以下の用途を持つモジュール群と CLI スクリプトから構成されています。

- ExecutionEngine: 発注ロジック、注文管理、リスク管理を担う起動可能なエンジン
- Monitoring: システム・注文・リスクをポーリングして監視し、アラートや Kill Switch を発動
- Portfolio: 候補選定、重み計算、ポジションサイズ決定などの純関数群
- Research: DuckDB を用いたファクター計算・特徴量解析
- AI: OpenAI を利用したニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- ユーティリティ: ログ設定、プロセス優先度設定、.env ウィザード、設定検証ツール 等
- Tools: Paper Trading の検証レポート生成スクリプト

設計上の特徴:
- SQLite（監視ログ / ペーパートレード DB）と DuckDB（分析向け）を併用
- 本番 / ペーパートレードの DB 分離（KABUSYS_ENV による）
- .env ベースの環境変数管理（対話式ウィザードでの生成サポート）
- OpenAI API を用いる機能は API キー必須（フェイルセーフでのデフォールト挙動あり）

---

## 主な機能一覧

- 実行関連
  - ExecutionEngine 起動スクリプト: `src/kabusys/run_execution.py`
  - BrokerClientFactory を使ったブローカ接続（paper_trading 時は Mock）
  - リスクマネージャ、OrderManager、Reconciler を統合

- 監視関連
  - SystemMonitor / TradeMonitor / RiskMonitor をまとめてポーリングする MonitoringEngine
  - kill.flag による ExecutionEngine 停止シグナル
  - 監視ログの永続化（SQLite）と簡易 DB マイグレーション

- ポートフォリオ構築
  - 候補選定、スコア加重・等重配分、セクター制約、ポジションサイズ計算（単元株対応）

- リサーチ
  - DuckDB 上でのモメンタム / ボラティリティ / バリュー計算
  - 将来リターン、IC（スピアマン・ランク相関）、統計サマリー

- AI
  - ニュース記事を LLM に投げて銘柄別センチメントを ai_scores テーブルへ書き込み
  - ETF とマクロニュースの組合せによる市場レジーム判定（bull/neutral/bear）

- ツール
  - Paper Trading 検証レポート生成スクリプト（成功率、稼働率、レイテンシ等を集計）

---

## 必要条件（Prerequisites）

- Python 3.9+
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（`validate_config` で YAML 検証を行う場合）
- SQLite は Python 標準ライブラリに含まれます。

例（仮想環境を使ったインストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 実際の requirements.txt が無い場合は必要なパッケージをプロジェクトの使用機能に応じてインストールしてください。

---

## セットアップ手順

1. リポジトリのクローン & 仮想環境（任意）
   - git clone ...
   - python -m venv .venv && source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - PyYAML は設定ファイル検証を行いたい場合に追加

3. データディレクトリ作成
   - デフォルトでは `data/` を使用します。書き込み権限を付与してください。
   - 例: mkdir -p data logs

4. .env を作成（推奨: 対話式ウィザード）
   - 対話式ウィザードで .env を生成:
     ```
     python -m kabusys.config_setup
     ```
   - 必須変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live）
   - 詳細は後述の「環境変数」参照

5. 設定検証（任意）
   - 作成後に検証:
     ```
     python -m kabusys.validate_config
     ```
   - 警告もエラーにしたい場合:
     ```
     python -m kabusys.validate_config --strict
     ```

---

## 環境変数（主なもの）

- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant/partial/never/reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API を利用する場合に必要
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で上書き可能）
- KILL_FLAG_CLEAR_ON_START: 本番で危険なためデフォルト 0（起動時に kill.flag を自動クリアするか）

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 通常起動（環境に応じて本番/ペーパー DB を自動選択）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、ペーパートレード DB（デフォルト: data/paper_trading.db）へ記録されます。

  挙動:
  - data/stop_requested.flag を配置すると起動中のエンジンを順次停止
  - data/execution.pid に PID ファイルを書き出します
  - KILL スイッチは `data/kill.flag` を監視して発動されます（Monitoring が書込む）

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  挙動:
  - SystemMonitor は Docker/ホスト問わず本番 sqlite_path を使用して監視ログを記録
  - data/stop_requested.flag を検知するとループを終了します

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: env か `data/paper_trading.db`。`--db` で指定可能。

- AI 関連（プログラム内 API 呼び出し）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

  いずれも OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）。

---

## 停止・Kill Switch の仕組み

- stop_requested.flag
  - run_monitoring / run_execution が起動ループ中にこれを検出すると安全にシャットダウンします。
  - 位置: プロジェクトの data/stop_requested.flag（run scripts はそれを参照）

- kill.flag（KillSwitch）
  - Monitoring の監視結果（例: ドローダウン閾値超過、ポジション数上限超過）により KillSwitch が判定し、`data/kill.flag` を書き込みます。
  - ExecutionEngine は kill.flag の存在を検知して発注停止（または安全停止）します。
  - 本番での誤動作を避けるため、KILL_FLAG_CLEAR_ON_START を 1 にしない運用を推奨します。

---

## ログ / PID / データファイル

- ログ: デフォルト `logs/<app_name>.log`（日次ローテーション、30日保持）
  - setup_logging() により統一的に設定されます。

- PID: `data/execution.pid`（ExecutionEngine 用）

- DB:
  - DuckDB: デフォルト `data/kabusys.duckdb`
  - 監視 SQLite: デフォルト `data/monitoring.db`
  - ペーパートレード SQLite: デフォルト `data/paper_trading.db`（KABUSYS_ENV=paper_trading 時に使用）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みユーティリティ
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 発注エンジン周り（Engine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層 + Migration
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
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

（実際のファイルツリーはリポジトリを参照してください。上記は代表的なモジュールの一覧です。）

---

## 開発・運用上の注意

- KABUSYS_ENV が `live` の場合は本番設定となり、発注等の操作は慎重に扱ってください。`validate_config` は本番環境での注意点を警告します。
- OpenAI API を使用するモジュールは API 失敗時にフォールバック挙動を持ちますが、API キーの漏洩や課金に注意してください。
- ファイルベースの Kill Switch / stop flag を用いるため、運用時にファイルの監視・誤書込みに気を付けてください。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を無効化し、標準出力のみで継続します。

---

もし README の追加情報（例: 詳細な環境変数一覧、実行フロー図、データベーススキーマ詳細、各モジュールの API 仕様など）を追記したい場合は、どのトピックを優先するか教えてください。