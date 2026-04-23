# KabuSys

日本株自動売買 / 研究プラットフォーム（KabuSys）のリポジトリ。  
この README はコードベース（src/kabusys 以下）を前提に、概要・機能・セットアップ・起動方法・ディレクトリ構成を日本語でまとめたものです。

> 前提: Python 3.10 以上を想定（型ヒントに `|` を使用）。実行環境や依存パッケージはプロジェクトに合わせて適宜調整してください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムとそれを支える研究/監視ツール群を含むモジュール群です。主な目的は以下：

- シグナル生成 → ポートフォリオ構築 → 発注までの Execution Engine
- 実行時の監視（System / Trade / Risk）と Kill Switch による安全停止
- Paper Trading（模擬発注）を本番 DB と分離して検証可能
- DuckDB を使ったファクター計算 / リサーチ機能
- OpenAI を利用したニュース NLP / レジーム判定機能
- CLI ツール（環境設定ウィザード・設定検証・ペーパートレード検証レポート 等）

設計方針としては「本番（発注）ロジックと分析ロジックの分離」「DB（SQLite / DuckDB）を中心にした永続化」「外部 API 呼び出しは明示的に扱う（OpenAI, kabu API 等）」です。

---

## 機能一覧（主要コンポーネント）

- execution
  - ExecutionEngine: 発注セッションの起動・制御
  - BrokerClientFactory: 本番 or Mock ブローカーの切替（KABUSYS_ENV）
  - RiskManager / OrderManager / Reconciler / OrderRepository：注文フロー管理
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution の生存確認
  - TradeMonitor: 注文ログの健全性チェック（滞留注文、約定異常など）
  - RiskMonitor: ドローダウン・ポジション上限の監視と Dashboard 更新
  - KillSwitch: 異常時に data/kill.flag を書いて Execution を停止
  - MonitoringEngine: 上記監視を束ねたポーリングループ
  - monitoring_db: SQLite を使った監視ログの永続化層
- portfolio（ポートフォリオ構築）
  - 候補選定、重み計算、セクター制約、ポジションサイズ算出（純粋関数でテスト容易）
- research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 特徴量探索・IC 計算・統計サマリ
- ai
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング（ai_scores に保存）
  - regime_detector: ETF とマクロニュースを合成した市場レジーム判定
- utils
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテート）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- tools
  - paper_verification_report: Paper Trading の実行結果を元に検証レポートを生成
- CLI
  - config_setup: .env を対話式で生成・更新するウィザード
  - validate_config: .env / config/*.yaml の事前チェックツール

---

## 前提・依存関係（例）

最低限必要な外部パッケージ（抜粋）：

- duckdb
- psutil
- openai
- PyYAML（config yaml 検証時のみ必要）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実プロジェクトでは requirements.txt を用意して pip install -r でインストールしてください）

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン / コードを配置
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. .env を作成
   - 対話式ウィザードを使うのが簡単:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - (本番で OpenAI を使う場合) OPENAI_API_KEY
   - 設定例（簡易）
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```
4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   必要であれば `--strict` を付けると警告も FAIL 扱いになります。

5. データディレクトリ / ログディレクトリの確認
   - デフォルト DB パス: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db
   - ログ: logs/<app_name>.log（logs ディレクトリは logging_setup が自動作成）

---

## 使い方（起動・コマンド例）

- Execution Engine（トレード実行）
  - 本番/開発切替は KABUSYS_ENV による:
    - Paper Trading（MockBroker を使用）:
      ```
      KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      ```
      Paper Trading はデフォルトで data/paper_trading.db に記録し、本番 SQLite と分離されます。
    - 本番実行:
      ```
      KABUSYS_ENV=live python -m kabusys.run_execution
      ```
  - 実行中停止のためのフラグ:
    - data/stop_requested.flag を作成すると起動済みプロセスが順次停止します（run_execution / run_monitoring が参照）。
    - Kill Switch は監視モジュールから data/kill.flag を書き込み、Execution に停止指示を出します。

- Monitoring（監視ループ）
  - 監視プロセス起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を環境変数で上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    デフォルトは 60 秒。
  - Monitoring は Settings に関係なく本番 sqlite_path を使用して監視テーブルを初期化します。

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB を指定:
  ```
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- 研究 / AI モジュール（プログラムから利用）
  - 例: DuckDB 接続を渡してファクター計算
    from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI スコアリング:
    from kabusys.ai import score_news

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

---

## 安全機構・運用注意点

- Paper Trading は SQLite を別ファイルに分けて本番 DB と完全分離する設計です（PAPER_TRADING_SQLITE_PATH）。
- Kill Switch（data/kill.flag）により Execution を確実に停止させる仕組みがあります。起動時に KILL_FLAG_CLEAR_ON_START=1 にすると自動クリアされますが、本番では 0 を推奨します。
- Logging は stdout と日次ローテートのファイル出力（logs/<app_name>.log）を使用します。ログディレクトリが作れない場合はファイル出力がスキップされコンソールのみとなります。
- プロセス優先度を High に上げる処理が実行されます（set_process_priority）。権限不足で失敗する場合は警告が出ます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys の主要ファイル・ディレクトリの抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - execution/               — Execution 実行ロジック（Engine / OrderManager 等）
  - monitoring/
    - monitoring_db.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                    — 実行時に使用する DB / フラグファイル など（例: data/*.db, data/kill.flag）

（上記はソースの一部抜粋です。詳細は各モジュールの docstring を参照してください）

---

## 開発者向けメモ

- DuckDB 接続を渡す設計になっているため、研究関数は副作用が少なくテスト容易です。
- AI 部分（news_nlp, regime_detector）は OpenAI SDK を利用。テスト時は内部の API 呼び出し関数をモックすることが想定されています（例: unittest.mock.patch）。
- monitoring_db.init_monitoring_db は冪等でスキーママイグレーション（列追加）を試みます。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 参考コマンドまとめ

- .env 作成（対話式）
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  ```
- 実行（Paper）
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- 監視起動
  ```
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば README に以下を追加できます：
- 具体的な .env.example（テンプレート）
- requirements.txt の内容
- CI / テストの実行方法
- 各モジュールの詳細な API 使い方（関数説明・サンプルコード）

どの情報を追加したいか教えてください。