# KabuSys

日本株向け自動売買 / 研究フレームワーク（README 日本語版）

---

## プロジェクト概要

KabuSys は日本株の自動売買エンジンとそれに付随する監視・リスク管理・研究ツール群を提供する Python パッケージです。  
主に以下の領域をカバーします。

- 発注実行エンジン（ExecutionEngine） — 本番 / ペーパートレード対応
- 監視（Monitoring） — システム稼働、注文状態、リスク指標監視
- ポートフォリオ構築（候補選定・重み・株数算出）
- 研究（ファクター計算・特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 運用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計方針は「本番コードと研究・外部 API 呼び出しを明確に分離」「ルックアヘッドバイアス排除」「フェイルセーフ（API失敗時は安全側で継続）」です。

---

## 主な機能一覧

- Execution
  - Live / Paper trading 切替（環境変数 `KABUSYS_ENV`）
  - Broker クライアント抽象化（MockBrokerClient を用いたペーパートレード）
  - リスク管理（ポジション上限、ドローダウン等）
- Monitoring
  - システムリソース監視（CPU/メモリ/ディスク）
  - Execution プロセス監視（PID ファイル・停止検出）
  - 注文ログ / リスクログ / ダッシュボードの永続化（SQLite）
  - Kill Switch（条件を満たすと `data/kill.flag` を書き込み Execution を停止）
- Portfolio construction
  - 候補選定（スコア順、上位 N 件）
  - 重み付け（等分・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - 株数算出（リスクベース / 等配分 / スコア配分、単元丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB に対する SQL）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュース記事の LLM による銘柄センチメント得点化（OpenAI）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- ユーティリティ
  - 対話式 .env 作成ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）
  - Paper Trading 検証レポート生成ツール（`kabusys.tools.paper_verification_report`）
  - 統一的なログ設定、プロセス優先度設定ユーティリティ

---

## 必要条件（主な依存ライブラリ）

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（設定 YAML の検証を行う場合に任意）
- （その他、ローカル環境で必要に応じたライブラリ）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
# または requirements.txt がある場合:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・依存インストール（上記参照）

3. 環境変数の準備
   - 対話式ウィザードで `.env` を作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは手動で `.env` を作成（リポジトリ直下）。主なキー例:
     ```
     KABUSYS_ENV=development            # development | paper_trading | live
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_password
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     OPENAI_API_KEY=sk-...
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     ```
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 設定検証（起動前に推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告を厳格に扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. DB / ディレクトリの初期化
   - 多くのスクリプトは起動時に `data/` や `logs/` を自動生成します。必要に応じて手動で作成してください。
   - DuckDB / SQLite の初期化は起動スクリプト内で行われます（冪等）。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（通常はサービス・systemd 等で実行）
  ```bash
  python -m kabusys.run_execution
  ```
  - 注意:
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が使用され `data/paper_trading.db` に記録されます（本番 DB と分離）。
    - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
    - Execution は `data/execution.pid`（デフォルト）を PID ファイルとして扱います。

- Monitoring を起動（ポーリングループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の `SQLITE_PATH` を使用（環境に依らず監視 DB を集約）。
  - 停止: `data/stop_requested.flag` を作成するとループを抜けます。

- .env 設定ウィザード
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
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / 研究用モジュールはライブラリとしてインポートして利用できます。例:
  ```python
  from kabusys.ai.news_nlp import score_news
  from kabusys.ai.regime_detector import score_regime
  # DuckDB 接続を渡して利用
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=my_date, api_key="sk-...")
  ```

---

## 停止・Kill Switch・フラグ

- run_* スクリプトはプロジェクト直下の `data/stop_requested.flag` を監視しています。ファイルが存在すると実行ループを終了します（安全なシャットダウン）。
- KillSwitch（監視側）:
  - 監視が特定条件（例: ドローダウン超過、ポジション上限超過）を検出した場合、`data/kill.flag` を書き込み ExecutionEngine に停止シグナルを送ります。
  - Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると自動クリアされますが、本番では `0` を推奨します。

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default=60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロード無効化（1 で無効）

---

## ログ / PID / データファイル

- ログ: デフォルト `logs/` ディレクトリに日次ローテートで保存（`kabusys.utils.logging_setup`）
- PID: デフォルト `data/execution.pid`
- 停止フラグ: `data/stop_requested.flag`
- Kill フラグ: `data/kill.flag`
- DB:
  - DuckDB: `data/kabusys.duckdb`
  - 監視 SQLite: `data/monitoring.db`
  - ペーパートレード SQLite: `data/paper_trading.db`（`KABUSYS_ENV=paper_trading` 時に使用）

---

## ディレクトリ構成（抜粋）

リポジトリ内の主なファイル・ディレクトリは以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/                 — 発注関連（Engine, OrderManager 等）
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
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のファイル構成はリポジトリのツリーを参照してください）

---

## 運用上の注意 / ベストプラクティス

- 本番（`KABUSYS_ENV=live`）では設定やトークンの管理を厳重に行い、`.env` をリポジトリに含めないでください。
- `KILL_FLAG_CLEAR_ON_START` を本番で `1` にするのは危険です（Kill Switch が誤ってクリアされるため）。デフォルト `0` を推奨。
- OpenAI API（AI モジュール）を利用する際は API キーの料金とレート制限に注意してください。リトライ・バックオフの実装は行われていますがコストがかかります。
- DuckDB / SQLite はファイルベース DB のためバックアップと適切なファイル保護を行ってください。
- `psutil` を使ったプロセス優先度変更は権限依存です。権限が不足すると警告が出ますが処理は継続します。

---

## 開発者向け情報

- 主要な「ビジネスロジック」は純粋関数（ポートフォリオ計算等）として実装されており、ユニットテストしやすい設計です。
- DuckDB を用いた研究モジュールは SQL ベースの処理を主体としており、大量データ処理に適します。
- AI モジュールや外部 API 呼び出し部分は注入可能（API 呼び出し関数をパッチすることでテスト容易化）。

---

問題や改善提案があればリポジトリの Issue に詳細を記載してください。README に書ききれない実装や設計の細かい点は各モジュールの docstring を参照してください。