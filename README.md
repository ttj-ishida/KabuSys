# KabuSys

日本株自動売買システム（KabuSys）のコードベース README（日本語）

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのサンプル実装です。  
主な目的は、取引実行エンジン（ExecutionEngine）、システム監視（Monitoring）、ファクター研究・ポートフォリオ構築、AI によるニュースセンチメント解析などを統合した運用基盤を提供することです。

主な設計方針：
- 本番・ペーパートレードを切り替え可能（環境変数 `KABUSYS_ENV`）。
- DuckDB を用いたリサーチ／集計、SQLite を用いた監視／発注ログ永続化。
- OpenAI を用いたニュース NLP とレジーム判定（外部 API 呼び出し部はフェイルセーフ実装）。
- ログ・プロセス優先度・Kill Switch（フラグファイル）など運用機能を含む。

---

## 機能一覧

- Execution
  - ExecutionEngine による発注処理（本番・ペーパートレード切替）
  - ブローカークライアント抽象化（MockBroker/実ブローカー切替）
  - 注文管理・リスク管理・レコンシリエーション
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor：発注ログ監視（滞留注文・約定異常など）
  - RiskMonitor：ドローダウン監視、ポジション上限チェック、Kill Switch 発動
  - MonitoringEngine：各モニタのポーリング集約、アラート管理
  - 永続化：SQLite（`monitoring.db`）へのログ保存（`monitoring_db.py`）
- Research / Portfolio
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - フォワードリターン、IC 計算、特徴量要約
  - ポートフォリオ選定・重み付け・ポジションサイズ計算（等配分／スコア加重／リスクベース）
  - セクター上限・レジーム乗数調整
- AI（オプション）
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメント算出 → `ai_scores` に保存
  - regime_detector: MA200 とマクロセンチメントを組み合わせて日次レジーム判定
- ツール
  - `config_setup.py`：.env を対話式で生成/更新するウィザード
  - `validate_config.py`：環境変数／config/*.yaml の事前検証 CLI
  - `tools/paper_verification_report.py`：ペーパートレード検証レポート生成
- ユーティリティ
  - ロギング設定（コンソール + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要条件（推奨）

- Python 3.10 以上（typing の | 演算子等を使用しているため）
- 必須 Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（`validate_config.py` の YAML 検証を利用する場合）
- SQLite（標準ライブラリで利用可）

requirements.txt は本リポジトリに含まれていない場合もあるため、上記パッケージを個別にインストールしてください。

例：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン／配置
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. 環境変数設定（.env）
   - 対話式で作る（推奨）：
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは `.env` を作成／更新します。`.env` は絶対に Git にコミットしないでください。
   - 最低限設定が必要な環境変数
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（`development` / `paper_trading` / `live`、デフォルト `development`）
     - OPENAI_API_KEY（AI を使う場合）
4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   ```
   警告も失敗扱いにする場合は `--strict` を付ける。
5. データディレクトリの準備（自動作成されることが多い）
   - デフォルトの DB / ログパス:
     - DuckDB: `data/kabusys.duckdb`（`DUCKDB_PATH`）
     - SQLite（monitoring）: `data/monitoring.db`（`SQLITE_PATH`）
     - Paper trading SQLite: `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH`）
     - ログディレクトリ: `logs/`（`LOG_DIR` で上書き可能）

---

## 使い方（実行例）

主要な起動スクリプトはモジュールとして実行できます。

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  補足：
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使い `data/paper_trading.db` にトレードを記録します（本番 DB とは分離）。
  - 起動時に `data/stop_requested.flag` があればエンジンは起動せず終了します。
  - 実行中は `data/execution.pid` に PID を書きます。

- Monitoring 起動（ポーリング監視）
  ```
  python -m kabusys.run_monitoring
  ```
  補足：
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の SQLite パス（Settings.sqlite_path）を使用します（環境に関わらず）。
  - 停止は `data/stop_requested.flag` を作成することでループを終了します。

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- .env 対話式設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  もしくは環境変数 `PAPER_TRADING_SQLITE_PATH` を利用：
  ```
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report
  ```

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR（ログ保存ディレクトリ、デフォルト logs/）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト 60）
- PAPER_FILL_MODE（paper_trading の注文約定挙動: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（本番で Kill スイッチ自動クリアするか: 0/1）

設定ファイル `.env` の自動ロードはデフォルトで有効です。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 運用上の注意

- .env を絶対にリポジトリにコミットしないこと（APIキーやパスワードを含む）。
- 本番環境では `KABUSYS_ENV=live` の設定に注意。`validate_config.py` は本番向けの追加警告を出します。
- Kill Switch:
  - `KillSwitch` は `data/kill.flag` を作成して ExecutionEngine に停止シグナルを送ります（`Settings.kill_flag_path` でパス指定可）。
  - `KillSwitch.clear()` は起動時の自動クリアに使われます（`KILL_FLAG_CLEAR_ON_START` で制御）。
- 停止フラグ:
  - `data/stop_requested.flag` を作成すると `run_execution` / `run_monitoring` のループが検知して停止します。
- ログ:
  - ログはコンソール（stdout）と日次ローテートファイル（`logs/<app_name>.log`）に出力されます。
  - ログディレクトリ作成に失敗した場合はファイル出力はスキップされ、コンソールのみになります。

---

## AI 機能（OpenAI）について

- ニュースセンチメント（news_nlp）とレジーム判定（regime_detector）は OpenAI を利用します。`OPENAI_API_KEY` を環境変数化するか、関数引数で渡してください。
- 使用モデルは `gpt-4o-mini`（コード内設定）。API 呼び出しはリトライ・バックオフとレスポンス検証を実装していますが、料金やレート制限に注意してください。
- AI 機能はフェイルセーフ設計で、API 失敗時はデフォルト安全値にフォールバック（例: macro_sentiment=0.0）します。

---

## ディレクトリ構成（主要ファイル）

（ルート: src/kabusys 以下を示します）

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (実装ファイルが存在する想定)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装ファイルが存在する想定)
  - execution/
    - broker_factory.py (実装ファイルが存在する想定)
    - execution_engine.py (実装ファイルが存在する想定)
    - order_manager.py (実装ファイルが存在する想定)
    - order_repository.py (実装ファイルが存在する想定)
    - reconciler.py (実装ファイルが存在する想定)
    - risk_manager.py (実装ファイルが存在する想定)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (実行時に作られることが多い)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb
    - kill.flag / stop_requested.flag / execution.pid など

注: 上記の一部モジュール（trade_monitor、alert_manager、execution/*.py 等）は実行に必要な実装がこのスニペットに含まれていない場合があります。実行前に該当ファイルの存在と実装内容を確認してください。

---

## 開発・拡張ポイント（メモ）

- position_sizing や risk_adjustment は純粋関数群であり単体テストが容易です。
- AI 部分はプロンプトやモデル、バッチ戦略を調整することで性能改善が可能です。
- DuckDB を用いた分析コードは SQL ベースで設計されており、大規模データでも高速に集計できます。
- 運用面では `kill.flag`/`stop_requested.flag` を利用した外部制御の取り扱いに注意してください（特に本番での自動クリアは慎重に）。

---

README に収めた内容はこのコードベースの主要な使い方・運用上の注意をまとめたものです。実際にデプロイ／運用する際は `config/*.yaml`（設定ファイル）、各モジュールの実装、外部サービスのアクセス制御（APIキー管理）を十分に確認してください。必要であれば、各モジュールの詳細なドキュメント（関数仕様や DB スキーマ）を追加で作成します。