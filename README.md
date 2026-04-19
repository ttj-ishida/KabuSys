# KabuSys

日本株自動売買システムの一部をまとめたリポジトリ（モジュール群）の README です。  
このドキュメントはリポジトリ内の主要スクリプト / モジュールの概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な責務は以下のとおりです。

- 売買システムの ExecutionEngine（発注管理・リスク管理）
- 監視（System / Trade / Risk）と Kill Switch（致命的な状態で発注の停止）
- ポートフォリオ構築（候補選定、配分、ポジションサイズ算出）
- リサーチ（ファクター計算、前向きリターン、IC 等）
- ニュース NLP によるセンチメント評価（OpenAI API を使用）
- ペーパートレード環境の分離（実運用 DB と分離して検証可能）

主要なランナー:
- `run_execution.py` — ExecutionEngine 起動スクリプト
- `run_monitoring.py` — 監視ポーリングループ起動スクリプト
- `config_setup.py` — .env 作成ウィザード（対話式）
- `validate_config.py` — 起動前の設定検証 CLI
- `tools/paper_verification_report.py` — ペーパートレード検証レポート生成

---

## 機能一覧（抜粋）

- 環境設定管理（.env 自動ロード、Settings クラス）
- .env 対話式ウィザード（`kabusys.config_setup`）
- 設定検証（必須環境変数・パス・YAML 構文チェック、`kabusys.validate_config`）
- ロギング統一設定（コンソール + 日次ローテートファイル、`kabusys.utils.logging_setup`）
- プロセス優先度 / CPU affinity 設定（`kabusys.utils.process_priority`）
- ExecutionEngine 実行（本番 / ペーパートレード切替）
- 監視エンジン（System / Trade / Risk 各モニタ + KillSwitch）
- ポートフォリオ構築（候補選定、等重・スコア重み、リスク調整、ポジションサイズ計算）
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算）
- AI モジュール（ニュース NLP による銘柄別スコア、レジーム判定） — OpenAI API を利用
- ペーパートレードの検証レポート生成

---

## 必要条件（推奨）

- Python 3.10 以上（型ヒントの記法などに依存）
- 必要なパッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証時に必要）
- その他: SQLite（標準ライブラリで利用可）

インストール例（仮想環境内で）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（リポジトリに requirements.txt がない場合は、上記を参考に必要なパッケージをインストールしてください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化して依存パッケージをインストール
3. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   対話式で J-Quants、kabuAPI の認証情報や DB パス等を入力できます。`.env` を生成するときは絶対にコミットしないでください。
4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も厳格に FAIL とする場合:
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリやログディレクトリが自動作成されますが、必要に応じて手動で `data/` `logs/` を作成してください。

---

## 環境変数（主要）

（`.env` に設定する主なキーと意味）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring) ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 専用、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant, partial, never, reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、`run_monitoring` で上書き可）

注意:
- 監視プロセス (run_monitoring) はコメントどおり「監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」します（監視ログは本番用 monitoring DB に保存されます）。
- ペーパートレードは `KABUSYS_ENV=paper_trading` を設定すると、ExecutionEngine は MockBrokerClient を使用して `PAPER_TRADING_SQLITE_PATH` に記録します（本番 DB と分離）。

---

## 使い方（コマンド例）

各スクリプトはパッケージモジュールとして実行できます。

- .env を作成（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（通常モード: development / live）
  ```bash
  python -m kabusys.run_execution
  ```
  - ペーパートレードで起動する場合:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    この場合、専用の paper_trading SQLite DB（デフォルト: data/paper_trading.db）を使用します。

- Monitoring を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔を上書きする場合:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート作成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI / リサーチ系はライブラリとして呼び出して使用します（例: Python REPL から）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026, 4, 10), api_key="sk-...")
  ```

---

## ロギング / ファイル

- ログ: デフォルトで `logs/` に出力。ファイルはアプリ名ごとに日次ローテーション（例: logs/execution.log, logs/monitoring.log）。
- データ / 制御ファイル:
  - data/monitoring.db — 監視（SQLite、デフォルト）
  - data/kabusys.duckdb — DuckDB 分析 DB（デフォルト）
  - data/paper_trading.db — ペーパートレード（分離用）
  - data/kill.flag — Kill Switch のフラグファイル
  - data/stop_requested.flag — プロセス停止要求フラグ（run_* スクリプトで利用）
  - data/execution.pid — ExecutionEngine の PID ファイル（設定によりパス変更可）

注意: `.env` は機密情報を含むため絶対に VCS にコミットしないでください。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主要モジュールと役割の簡略一覧です。

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定管理（Settings）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — 監視ポーリング起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/  （発注関連コンポーネント）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py — 監視ログの永続化層（SQLite）
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 発注・約定の監視（ログ参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 複数モニタを束ねる
    - alert_manager.py — （アラート送信、LINE など）（省略）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数、資金配分、丸め処理
    - risk_adjustment.py — セクター規制・レジーム乗数
  - research/
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングし ai_scores へ書き込む
    - regime_detector.py — マーケットレジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（上記は主要ファイルの抜粋です。詳細は各ソースファイルの docstring を参照してください）

---

## 運用上の注意 / ヒント

- 本番環境では `KABUSYS_ENV=live` を設定します。`validate_config` は live の場合に追加注意を表示します（LINE 通知未設定など）。
- Kill Switch（`data/kill.flag`）は起動時に残っていると ExecutionEngine の起動を阻止します。必要に応じてクリーンアップしてください。
- 監視は `run_monitoring` による定期ポーリングで動作します。`MONITOR_POLL_INTERVAL` で秒数を上書きできます（デフォルト 60 秒）。
- ペーパートレード環境は本番 DB と分離する設計です。検証や実験は必ず paper_trading モードを使ってください。
- OpenAI API を利用する機能は API コストが発生します。APIキーと利用方法は慎重に管理してください。

---

## よくあるコマンドまとめ

- .env 作成
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```
- 実行エンジン起動（ペーパー）
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- 監視起動（ポーリング間隔 30 秒）
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に更に詳しい設定例（.env のサンプル）、データベーススキーマや起動フロー図、各コンポーネントのより詳細な API ドキュメントを追加できます。どの部分を拡張したいか教えてください。