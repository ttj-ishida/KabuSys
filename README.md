# KabuSys

日本株向け自動売買システムのコアライブラリ。  
このリポジトリは戦略リサーチ、ポートフォリオ構築、発注実行（ExecutionEngine）、および監視（Monitoring）機能を含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群で構成されています。

- 戦略リサーチ（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定・重み計算・株数算出・リスク調整）
- 発注実行（Broker クライアント抽象化、リスク管理、注文管理、リコンサイル）
- 監視（システム稼働状況、注文ログ、リスク監視、Kill Switch）
- AI 支援（ニュース NLP によるセンチメント、レジーム判定）
- ユーティリティ（設定ウィザード、設定検証、ログ設定等）
- 開発用ツール（Paper Trading 検証レポート生成 等）

設計方針のポイント:
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV により切替）
- DuckDB を分析用に利用、SQLite を監視・履歴保存に利用
- OpenAI 呼び出しは失敗に強い（リトライ・フォールバック）
- ルックアヘッドバイアス対策のため日付参照を固定化している箇所あり

---

## 主な機能一覧

- config_setup: 対話式で `.env` を生成・更新するウィザード（python -m kabusys.config_setup）
- validate_config: 起動前の環境変数・YAML 設定ファイル検証（python -m kabusys.validate_config）
- run_execution: ExecutionEngine を起動（本番/ペーパー切替）
- run_monitoring: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
- monitoring: System / Trade / Risk の監視、Kill Switch 判定、アラート送信
- ai.news_nlp: ニュースを LLM（OpenAI）で評価し ai_scores に書き込み
- ai.regime_detector: 市場レジーム判定（ETF MA + マクロ NLP 合成）
- research: ファクター計算・特徴量解析ユーティリティ
- portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター上限適用

---

## 必要条件（推奨）

- Python 3.10+
- SQLite（標準ライブラリ）
- pip install で必要パッケージを導入
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証を行う場合）
- OS: Linux / macOS / Windows（プロセス優先度・CPU affinity の一部挙動は OS 依存）

例（最低限のインストール例）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（requirements.txt はプロジェクトに含まれていないため、実際の運用では適切なバージョン管理を行ってください）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient を使用し `data/paper_trading.db` に記録
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB のパス、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR（ログ出力ディレクトリ、デフォルト: logs/）
- OPENAI_API_KEY（AI モジュールで必要）
- PAPER_FILL_MODE（ペーパートレードの約定モード）: instant | partial | never | reject
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか: "1" で有効）

自動 .env ロード:
- プロジェクトルートに `.env` / `.env.local` がある場合、自動で読み込みます（OS 環境変数を上書きしない設定）。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境と依存ライブラリのインストール
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install duckdb psutil openai PyYAML
   ```

3. `.env` の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   あるいは `.env` を手動作成（.env.example を参考に）。`.env` は Git にコミットしないでください。

4. 設定検証
   ```
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いになります
   python -m kabusys.validate_config --strict
   ```

5. 必要ならデータディレクトリを作成
   ```
   mkdir -p data logs
   ```

---

## 実行方法（代表例）

- ExecutionEngine（発注エンジン）を起動
  - 本番（KABUSYS_ENV=live）または development: 実際のブローカークライアントを使用
  - ペーパートレード:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実行時はプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid） に書き込みます。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - paper_trading の場合は設定に従い MockBrokerClient が paper DB に記録します。

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトで 60 秒ごとにポーリング。環境変数で上書き:
    ```
    export MONITOR_POLL_INTERVAL=30
    ```
  - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path（SQLITE_PATH）を参照して監視ログを記録します。
  - 停止は `data/stop_requested.flag` を作成することで次のループで終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI 関連（ニューススコアリング / レジーム判定）
  - OpenAI API キーを設定（OPENAI_API_KEY 環境変数）
  - 例（モジュールを直接呼ぶスクリプトから）:
    - kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

- 停止・Kill Switch
  - システムの監視により kill 条件が満たされると `data/kill.flag` が作成されます（ExecutionEngine は起動時や監視によりこのフラグをチェックします）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると ExecutionEngine 起動時に kill.flag を自動クリアします（本番では推奨しません）。

---

## ログ

- ログは `kabusys.utils.logging_setup.setup_logging` を通じて統一的に設定されます。
- デフォルト:
  - コンソール stdout 出力（StreamHandler）
  - ファイル：日次ローテーション（logs/<app_name>.log）、30 日保持
- アプリケーション例:
  - run_execution は logs/execution.log
  - run_monitoring は logs/monitoring.log

ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみになります。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード/パース、Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数計算・集約キャップ処理
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite の永続化層（テーブル作成・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文の滞留/約定異常など監視（省略ファイルは同ディレクトリに存在）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — フラグファイルによる Execution 停止判定
    - monitoring_engine.py — 複数 Monitor を束ねるエンジン
    - alert_manager.py — 通知（LINE 等）を管理するモジュール（実装参照）
  - execution/ (発注関連コンポーネント: BrokerFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager, OrderRepository 等)
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/ (実行時に作成される想定フォルダ: SQLite / PID / flag ファイル等)
  - config/ (yaml テンプレート等: system_config.yaml, data_config.yaml, strategy_config.yaml, ...)

注: ここでは主要ファイルのみ抜粋しています。実際のリポジトリではさらに多くのモジュール（order_manager, broker implementations, execution engine internals など）が存在します。

---

## 開発上の注意・補足

- Settings クラスはプロジェクトルート（.git または pyproject.toml を基準）を自動検出して `.env` を読み込みます。CI/テスト等で自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Monitoring の DB 初期化（init_monitoring_db）は冪等でテーブルを作成・既存 DB に対して必要なマイグレーションを行います（例えば `peak_value` / `latency_ms` 列の追加など）。
- process_priority.set_process_priority は psutil を使用し OS に依存した挙動をします。権限が不足すると設定に失敗して警告が出ますが処理は継続します。
- OpenAI 呼び出しは network エラー / 429 / 5xx に対して指数バックオフでリトライします。API キーは env `OPENAI_API_KEY` で設定してください。
- Paper Trading は本番 DB と完全分離されるよう設計されています（`paper_sqlite_path` を使用）。

---

## よく使うコマンドまとめ

- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```
- Paper 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

何か特定の機能の使い方（例えば ExecutionEngine の詳細設定、Broker 実装、monitoring のカスタマイズ、AI モジュールのテスト方法など）をREADMEに追記したい場合は、その箇所を指定してください。必要に応じて具体的なコマンド例や設定テンプレートを追加します。