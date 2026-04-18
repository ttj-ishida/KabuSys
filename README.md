# KabuSys

日本株自動売買システムのコードベース（抜粋）。  
この README はプロジェクトの概要、機能、セットアップ、使い方、主要ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。  
主なコンポーネントとして以下を含みます。

- Execution Engine（発注 / 注文管理 / リスク管理）
- Monitoring（システム状態・注文状態・リスク監視）
- Portfolio construction（銘柄選定・重み付け・ポジションサイズ計算）
- Research（ファクター計算・特徴量探索）
- AI 関連（ニュース NLP によるセンチメント、レジーム判定）
- ユーティリティ（設定管理、ログ設定、プロセス優先度設定 等）
- 各種 CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

設計上の特徴：
- 設定は .env または環境変数から読み込み（プロジェクトルート自動検出）
- Paper Trading（ペーパートレード）では本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用に、SQLite を監視やトレードログ用に使用
- OpenAI（GPT 系）を使ったニュースセンチメントやマクロ判定をサポート
- ログは stdout と日次ローテーションファイル（logs/<app>.log）に出力

---

## 機能一覧（抜粋）

- 環境・設定管理
  - .env 自動読み込み（プロジェクトルートが見つかれば .env/.env.local を読み込む）
  - 設定ウィザード（対話式）および検証 CLI
- 実行エンジン
  - Broker クライアント抽象化（実取引 / モック切替）
  - 注文管理、リスク管理、再整合処理
- 監視
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、プロセス PID チェック
  - TradeMonitor: 注文滞留、約定異常などの検出（コードの一部）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: しきい値超過で data/kill.flag を書き込み ExecutionEngine に停止指示
  - MonitoringEngine: 各モニタを束ねて定期実行、アラート発行
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、セクター制限、ポジションサイジング（単元丸め・集計上限考慮）
- リサーチ
  - Momentum/Volatility/Value ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン、IC（スピアマン）計算、統計サマリー
- AI（OpenAI）統合
  - ニュースを LLM に投げて銘柄別センチメントを ai_scores に保存
  - マクロニュースと ETF MA を合成して市場レジーム（bull/neutral/bear）を判定
- ツール
  - Paper Trading 検証レポート生成スクリプト

---

## 依存 (最低限)

このリポジトリの機能をすべて使う場合の代表的なパッケージ例：

- Python 3.10+
- duckdb
- psutil
- openai

インストール例（仮）:
```bash
python -m pip install duckdb psutil openai
```

（実際には requirements.txt があればそれを利用してください）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb psutil openai
   ```
4. 環境変数の設定
   - 対話式ウィザードで .env を生成:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env` を作成してキーを設定します（`.env.example` を参考に）。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
5. 設定検証（起動前に必ず実行推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```
6. 必要なディレクトリ（data, logs 等）が自動で作成されることを確認。起動時に作成されます。

---

## 主な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant/partial/never/reject）
- KABUSYS_ENV: execution モード (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル保存先（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

（設定ウィザードで主要項目は対話的に作成できます）

---

## 使い方 — 起動・実行例

- 監視ループ (Monitoring)
  - 簡易起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を環境変数で上書き（秒単位、デフォルト 60秒）:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

  - 実行のポイント:
    - run_monitoring はデフォルトで本番 sqlite_path（Settings.sqlite_path）を使用して監視テーブルを初期化します。
    - data/stop_requested.flag が存在するとループを終了します。

- 実行エンジン (ExecutionEngine)
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - Paper trading（モックブローカーと別 DB を利用）:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 実行のポイント:
    - Paper trading モードでは settings.paper_sqlite_path を利用して注文を data/paper_trading.db に記録（本番 DB と完全分離）。
    - プロセスは data/execution.pid に PID を書きます。data/stop_requested.flag により停止がトリガーされます。

- .env の作成（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示的に指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコア / レジーム判定（プログラムから呼び出す例）
  - ニュース NLP（ai_scores に書き込む）:
    from kabusys.ai.news_nlp import score_news
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
  - どちらも DuckDB 接続オブジェクトと target_date を受け取ります。OpenAI キーは OPENAI_API_KEY 環境変数か引数で指定。

---

## ロギング

- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
- 出力:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log（日次ローテーション、30日保持）
- ログディレクトリは環境変数 LOG_DIR で上書き可能

---

## 注意点 / 運用上のヒント

- KABUSYS_ENV が `live` の場合は設定を慎重に確認してください。LINE 通知など本番向けの警告を出す仕組みがあります。
- Kill Switch（data/kill.flag）を用いた緊急停止機構があります。実行前に kill flag を自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1（ただし本番では 0 推奨）。
- process priority の設定に psutil を使用します。権限や OS によって設定が失敗することがあります（警告のみ）。
- DuckDB / SQLite のファイルパスの親ディレクトリがない場合は起動時に自動作成することが多いですが、権限やパスに注意してください。
- OpenAI API を使う機能は API の利用料が発生します。API キーとレート制限に注意してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要モジュール・ファイルの例（提供コードベースに基づく抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_monitoring.py
  - run_execution.py
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
    - trade_monitor.py (一部参照あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照あり)
  - execution/
    - execution_engine.py (参照あり)
    - order_manager.py (参照あり)
    - order_repository.py (参照あり)
    - reconciler.py (参照あり)
    - broker_factory.py (参照あり)
    - risk_manager.py (参照あり)
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
  - data/ (実行時に使用される既定の格納先)
    - monitoring.db (デフォルト SQLite)
    - paper_trading.db (Paper Trading 用)
    - kill.flag, stop_requested.flag, execution.pid などのフラグ / PID ファイル

（実際の完全なツリーはリポジトリ内容に依存します）

---

## 開発・テスト

- モジュールは可能な限り副作用を避ける設計（設定の自動読み込みは無効化可能）。
- AI 呼び出し部分は外部 API を用いるため、ユニットテスト時は API 呼び出しを差し替える（mock）ことを推奨します（コード中にもそのためのエントリポイントが用意されています）。
- DuckDB / SQLite を使った関数は DB スキーマやテーブルが想定どおり存在することを前提にしています。テスト用 DB を用意して実行してください。

---

もし特定のスクリプトの起動方法（例: SystemMonitor の詳細な引数、ExecutionEngine の拡張設定）や、.env の具体的なサンプル、開発用の Dockerfile / systemd ユニット例などが必要であれば教えてください。必要に応じて追記します。