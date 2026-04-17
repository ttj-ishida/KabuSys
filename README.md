# KabuSys

日本株自動売買システム（軽量リファレンス実装）

このリポジトリは、シグナル生成 → ポートフォリオ構築 → 発注実行 → 監視・アラート のワークフローを含む自動売買基盤のコンポーネント群を提供します。学術的／実務的な設計指針（PortfolioConstruction, StrategyModel 等）に基づき、モジュール化された純粋関数群と I/O 層（SQLite / DuckDB / 外部 API クライアント）で構成されています。

主な用途
- 研究（ファクター計算、特徴量探索）
- ペーパートレード（発注ロジック検証）
- 実運用（kabuステーション などのブローカ連携）
- 運用監視（プロセス生存、データ鮮度、注文滞留・約定異常など）

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートに .env/.env.local）。対話式ウィザードで .env を作成する `kabusys.config_setup`。
  - 起動前チェック `kabusys.validate_config`（必須環境変数・YAML 設定ファイル・パス検証など）。
- 実行エンジン起動スクリプト
  - run_execution: 発注エンジン（ExecutionEngine）を起動。`KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し DB を分離。
- 監視プロセス
  - run_monitoring: SystemMonitor をポーリングして system_status / risk_logs / trade_logs / dashboard を記録。
  - MonitoringEngine: System / Trade / Risk の各 Monitor をまとめて定期実行、Kill Switch 評価、アラート送信。
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重の重み計算、ポジションサイズ計算（リスクベース等）、セクター制限、レジーム乗数。
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）、将来リターン計算、IC（Information Coefficient）など。
- AI モジュール（OpenAI を利用）
  - news_nlp: ニュース記事を LLM でセンチメント採点 → ai_scores テーブルに保存
  - regime_detector: マクロニュース + ETF MA200 を元に日次の市場レジーム判定
- 運用ツール
  - paper_verification_report: ペーパートレード結果の検証レポート生成
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil 利用）
- 永続化層（SQLite）と分析 DB（DuckDB）との併用

---

## 要件（推奨・必須）

- Python 3.10 以上（型ヒントの構文や一部の標準機能に依存）
- 必須 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
- 任意（機能に応じて）
  - PyYAML（config YAML の検証を行う場合）
- SQLite は標準ライブラリで利用
- ネットワーク接続（kabuステーション API、OpenAI API を使う場合）

pip での一例（requirements.txt がない場合）:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. 対話式で .env を作成（推奨）
   ```
   python -m kabusys.config_setup
   ```
   このウィザードは .env を生成・更新します。生成後、`python -m kabusys.validate_config` で検証してください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱い
   ```

6. データディレクトリの確認
   - デフォルトの DuckDB / SQLite ファイルは `data/kabusys.duckdb` / `data/monitoring.db`
   - Paper trading は `data/paper_trading.db`（KABUSYS_ENV=paper_trading 時に使用）

---

## 重要な環境変数（代表例）

- 必須（少なくとも起動前に設定）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OpenAI
  - OPENAI_API_KEY（news_nlp / regime_detector が必要な場合）
- ログ・運用
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
  - PID_FILE_PATH（実行エンジン用 pid ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（Kill Switch フラグ、デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。1=クリア, 0=クリアしない）
- 監視間隔
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）

その他、PAPER_FILL_MODE（paper_trading の約定挙動）など各種設定があります。`.env.example` を参考にしてください。

---

## 使い方

基本的な実行コマンド例。

1. ExecutionEngine を起動（本番 / ペーパーどちらでも settings に依存）
   ```
   python -m kabusys.run_execution
   ```
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録されます（本番 DB とは分離）。
   - 起動前に `data/stop_requested.flag` が存在すると起動しません。
   - 実行中に同フラグが作成されると安全に停止します。
   - 実行開始時にプロセス優先度を "high" に設定する処理が入ります（psutil の権限による）。

2. 監視プロセスを起動
   ```
   python -m kabusys.run_monitoring
   ```
   - Monitoring は KABUSYS_ENV に関係なく `settings.sqlite_path`（デフォルト `data/monitoring.db`）を使用します（監視 DB は本番を想定）。
   - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書きできます（秒）。不正値はデフォルト 60 秒にフォールバックします。
   - `data/stop_requested.flag` があればループを停止します。

3. ペーパートレード検証レポート生成
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - `--db` で DB パスを指定可能（`PAPER_TRADING_SQLITE_PATH` 環境変数、またはデフォルト `data/paper_trading.db`）。
   - 稼働率・注文成功率・送信率・P95 レイテンシなどを集計し PASS/FAIL を判定します。

4. 環境設定ウィザード（再掲）
   ```
   python -m kabusys.config_setup
   ```

5. 設定検証（再掲）
   ```
   python -m kabusys.validate_config --strict
   ```

---

## 停止・Kill Switch

- ExecutionEngine を外部から停止する方法
  - `data/kill.flag` を作成すると Kill Switch が評価されて ExecutionEngine に停止シグナル（ファイルベース）を送ります。KillSwitch は一度フラグが書かれると再度書き込みは行いません（冪等）。
  - 監視側は `KillSwitch.evaluate()` によりドローダウンやポジション上限超過時に `kill.flag` を書きます。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

- プロセス停止フラグ
  - `data/stop_requested.flag` は run_execution/run_monitoring のループを止めるために利用されます（開発用の手動停止など）。

---

## ディレクトリ構成（抜粋）

（プロジェクトルートに `src/kabusys` がパッケージルート）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装の一部があるはずです)
  - tools/
    - paper_verification_report.py
    - __init__.py
  - execution/               — Execution 関連モジュール（Engine, BrokerFactory, OrderManager 等）

データディレクトリ（デフォルト）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/kill.flag
- data/stop_requested.flag

---

## 開発・運用の注意点

- KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれかを使用。`live` は本番扱いのため注意深く設定してください。
- Paper trading では発注先とデータベースを完全に分離しているため、本番 DB を汚す心配はありません。
- OpenAI API を使う機能（news_nlp, regime_detector）は API 呼び出しの失敗に対してフェイルセーフ（0.0 等でフォールバック）する設計です。ただし API キー未設定は明示的にエラーを出します。
- DuckDB / SQLite のパスやその他の設定は .env で管理してください。`.env` は絶対にコミットしないでください。
- 実行プロセスは起動時にプロセス優先度を "high" にしようとします（psutil の権限に依存）。権限不足の場合は警告が出てスキップします。
- システム監視は監視 DB（SQLite）に永続化し、監視指標は後で分析・アラートトリガーに利用します。run_monitoring は監視 DB を常に本番パス（settings.sqlite_path）で開きます。

---

## よく使うコマンド一覧

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- 監視プロセス起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README はコードベースの要点をまとめたものです。詳細は各モジュールの docstring / 関数コメントを参照してください。運用前には必ず `python -m kabusys.validate_config` で設定を検証し、`data` ディレクトリや DB のバックアップ方針を確認してください。