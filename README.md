# KabuSys — 日本株自動売買システム（README）

このドキュメントは、提供されているコードベースの概要、主要機能、セットアップ手順、起動方法、ディレクトリ構成を日本語でまとめた README です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。以下の主要領域を備えます。

- 発注実行エンジン（ExecutionEngine）
- 監視コンポーネント（System / Trade / Risk Monitor）
- ポートフォリオ構築（シグナル選定、重み付け、ポジションサイズ計算）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI 補助モジュール（ニュースの NLP スコアリング、レジーム検出）
- 運用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、運用用（本番）とペーパートレードを分離しており、設定は環境変数 / `.env` で管理します。DuckDB / SQLite をデータ層に利用します。

---

## 主な機能一覧

- 環境設定
  - 対話式ウィザードで `.env` を生成・更新（kabusys.config_setup）
  - 実行前の設定検証ツール（kabusys.validate_config）
- 実行・監視
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db` に記録（本番 DB とは分離）
    - 停止はフラグファイル（`data/stop_requested.flag` / `data/kill.flag`）で制御
  - Monitoring 起動スクリプト（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視用 SQLite は環境に関係なく本番 sqlite_path を使用
- 監視 DB（SQLite）
  - `system_status`, `trade_logs`, `positions`, `risk_logs`, `dashboard` などのテーブル定義と永続化 API
- Risk / Kill Switch
  - ドローダウンやポジション上限の監視 → 必要なら `data/kill.flag` を書き込んで ExecutionEngine 停止を促す
- ポートフォリオ構築（pure functions）
  - 候補選定、スコア加重 / 等配分、セクター上限適用、ポジションサイズ計算（単元株丸めや aggregate cap 調整）
- 研究（Research）
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン、IC 計算、統計サマリー
- AI（OpenAI）
  - ニュース NLP による銘柄別センチメントスコア生成（gpt-4o-mini を想定）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定
- ツール
  - ペーパートレードの検証レポート生成（kabusys.tools.paper_verification_report）

---

## 必須 / 推奨依存パッケージ

（実行環境に応じて必要なパッケージをインストールしてください）

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイル YAML の検証を行う場合、任意）

例（仮想環境内で）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ requirements.txt が無い場合は上記のように個別インストールしてください。

---

## セットアップ手順（基本）

1. リポジトリをクローンしてソースツリーへ移動
2. 仮想環境を作成・有効化
3. 依存ライブラリをインストール（上記参照）
4. 環境変数を準備
   - 対話式ウィザードで `.env` を作成することが可能:
     ```
     python -m kabusys.config_setup
     ```
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他（例）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒）
     - PAPER_FILL_MODE（paper_trading 時の約定挙動: instant|partial|never|reject）

5. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（起動例・主要コマンド）

各モジュールはパッケージ内のモジュールとして起動できます（プロジェクトルートで実行）。

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine（実際の発注エンジン / ペーパートレード切替あり）
  - ペーパートレード（環境変数で KABUSYS_ENV=paper_trading を指定）
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 本番想定（注意: 本当に発注されます）
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```

  実行時の挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録して本番 DB と分離します。
  - 起動時に `data/stop_requested.flag` が既に存在する場合は起動を中断します。
  - 実行中は `data/execution.pid` が PID ファイルとして利用されます。

- Monitoring（監視ループ）
  ```
  # デフォルト間隔 60 秒
  python -m kabusys.run_monitoring

  # 間隔を変更する例（30 秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  注意:
  - Monitoring は環境変数 KABUSYS_ENV に関係なく、本番 sqlite_path（設定の sqlite_path）を使用します。
  - 停止は `data/stop_requested.flag` を作成すると監視ループが検出して終了します。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / リサーチ機能（プログラムからの呼び出し）
  - ニュース NLP（銘柄別スコア書き込み）
    ```py
    from kabusys.ai.news_nlp import score_news
    # conn: duckdb connection, target_date: datetime.date, api_key: str|None
    score_news(conn, target_date, api_key="...")
    ```
    OPENAI_API_KEY が設定されていないと ValueError を発生します（api_key を明示的に渡すか環境変数を設定してください）。

  - レジーム判定
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")
    ```

---

## 停止・キルフラグについて

- 停止フラグ（監視ループ / エンジン停止制御）
  - data/stop_requested.flag — ローカル管理用（run_monitoring / run_execution はこれを見て起動/停止を判断）
  - data/kill.flag — Kill Switch（KillSwitch が書き込む）。ExecutionEngine 起動時の KILL_FLAG_CLEAR_ON_START 設定により自動クリア可（ただし本番では 0 推奨）

- PID ファイル
  - data/execution.pid — ExecutionEngine が起動時に使用（run_execution が渡します）

---

## 主要設定項目（抜粋）

- KABUSYS_ENV: development|paper_trading|live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使うとき）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/..）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定動作（instant|partial|never|reject）

`.env` はプロジェクトルートに置き、自動読み込みされます（.env.local で上書き可）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## 典型的な運用フロー（例）

1. `.env` を作成（`python -m kabusys.config_setup`）
2. `python -m kabusys.validate_config` で問題がないか確認
3. データベース（DuckDB / SQLite）の初期ファイルを作成・配置（必要に応じて）
4. 監視プロセスを起動（通常は監視を常駐させる）
   ```
   MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
   ```
5. ExecutionEngine を起動（ペーパートレードで確認）
   ```
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   ```
6. 運用中に KillSwitch が作動すると `data/kill.flag` が書かれ、ExecutionEngine 側で停止する仕組み

---

## トラブルシューティング

- OpenAI 関連で "api_key 未設定" のエラーが出る場合は `OPENAI_API_KEY` を `.env` に追加するか、関数呼び出しに `api_key` を直接渡してください。
- `python -m kabusys.validate_config` で YAML 検証をスキップするメッセージが出る場合は PyYAML が未インストールです（任意）。
- `MONITOR_POLL_INTERVAL` に 0 や負の値を設定すると無効値としてデフォルト（60 秒）にフォールバックします。
- ログ出力は `logs/` に日次ローテーションで保存（`kabusys.utils.logging_setup.setup_logging` により設定）。ログディレクトリ作成に失敗した場合はコンソール出力のみにフォールバックします。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールのツリー（`src/kabusys` 以下を抜粋）です。

```
src/kabusys/
├─ __init__.py
├─ config.py                # 環境変数・設定管理
├─ config_setup.py          # .env 対話式ウィザード
├─ validate_config.py       # 設定検証 CLI
├─ run_execution.py         # ExecutionEngine 起動スクリプト
├─ run_monitoring.py        # Monitoring 起動スクリプト
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py           # ニュース NLP スコアリング
│  └─ regime_detector.py    # レジーム判定（MA + マクロセンチメント）
├─ monitoring/
│  ├─ monitoring_db.py      # SQLite 永続化レイヤ
│  ├─ system_monitor.py
│  ├─ trade_monitor.py      # (ファイル内の実装参照)
│  ├─ risk_monitor.py
│  ├─ monitoring_engine.py
│  ├─ kill_switch.py
│  └─ alert_manager.py
├─ execution/                # 発注周り（Engine, OrderManager, BrokerFactory 等）
├─ portfolio/
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ factor_research.py
│  ├─ feature_exploration.py
│  └─ __init__.py
├─ tools/
│  └─ paper_verification_report.py
└─ utils/
   ├─ logging_setup.py
   └─ process_priority.py
```

（`execution` や `monitoring` 以下にはさらに多くの補助モジュールがあります。実装を参照してください。）

---

## 追加メモ / 実装上の注意点

- Monitoring の DB 初期化（`init_monitoring_db`）は冪等処理であり、必要なテーブル・列が存在しない場合は追加マイグレーションを行います。
- `run_execution` は起動時に process priority を high に設定しようと試みます（プラットフォーム依存、失敗時は警告）。
- AI 呼び出しはリトライとエラー処理を含み、部分失敗時のデータ保護（書き込みを対象コードに限定）を考慮しています。
- 研究・ファクター計算は DuckDB 接続を受け取り、基本的に prices_daily / raw_financials 等のテーブルのみを参照します。外部 API を直接叩きません。

---

この README はコードベースの主要点をまとめたドキュメントです。実際の運用・デプロイ時には `.env` の取り扱い（決して Git にコミットしない）、本番 API キーの管理、監視・ログの永続化設計を十分に検討してください。追加で README に追記したい項目（例: デプロイ手順、CI/CD、より詳細な設定例など）があれば教えてください。