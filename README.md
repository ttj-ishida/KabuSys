# KabuSys

日本株自動売買システムのコードベース（README）

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。  
主な機能は「戦略に基づくポートフォリオ構築・発注（Execution）」「実行状況・システム監視（Monitoring）」「リサーチ／ファクター計算」「ニュースの NLP によるセンチメント評価」「ペーパートレード検証」などを含みます。  
設計方針としては、DB（DuckDB / SQLite）をデータ層に使い、外部 API 呼び出し（kabuステーション, J-Quants, OpenAI）は必要に応じて切り替え可能／モック化可能になっています。

対象 Python バージョン: 3.10+（型記法や union 演算子 `|` を使用）

---

## 機能一覧

- 環境設定
  - .env を対話式に生成・更新する CLI（kabusys.config_setup）
  - 起動前の設定検証ツール（kabusys.validate_config）

- 実行エンジン（Execution）
  - 実際の発注処理を行う `ExecutionEngine` を起動するスクリプト（kabusys.run_execution）
  - 本番 / ペーパートレードを分離（KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し専用 SQLite DB に記録）
  - オーダー管理、リスク管理、訂正（reconciler）などのコンポーネントを組み合わせ

- 監視（Monitoring）
  - System / Trade / Risk モニタ類の実装
  - 監視データを SQLite に永続化（monitoring_db）
  - Kill Switch（閾値超過時に data/kill.flag を書き込んで ExecutionEngine を停止）
  - 監視ループ起動スクリプト（kabusys.run_monitoring）

- ポートフォリオ構築（Portfolio）
  - 候補選定、重み計算（等金額 / スコア加重）
  - ポジションサイズ計算（リスクベース等）
  - セクターキャップ・レジーム乗数調整

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリューなどの定量ファクター（DuckDB を使った計算）
  - 将来リターン計算、IC 計算、特徴量サマリー

- AI（OpenAI）連携
  - ニュース記事を LLM（gpt-4o-mini 等）でスコアリングし ai_scores に保存（kabusys.ai.news_nlp）
  - マクロ+ETF MA を用いた市場レジーム判定（kabusys.ai.regime_detector）

- ツール
  - ペーパートレードの検証レポート生成（kabusys.tools.paper_verification_report）

- ユーティリティ
  - 統一的ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU アフィニティ設定（kabusys.utils.process_priority）

---

## セットアップ手順

1. リポジトリをクローン（src 配下が含まれている想定）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール  
   （requirements.txt が無い場合は以下の主要パッケージをインストール）
   ```
   pip install duckdb psutil openai
   # オプション: YAML 検証用
   pip install pyyaml
   ```

4. .env の作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードに従って以下などを設定します（必須）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告もエラー化したい場合（--strict）
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリを作成（必要に応じて）
   - デフォルト DB / ログのパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
   これらは .env で上書き可能。

補足:
- OpenAI を利用する機能を使う場合は環境変数 `OPENAI_API_KEY` を設定してください。
- デフォルトの環境（KABUSYS_ENV）は `development`。ペーパートレードや本番は `paper_trading` / `live` を使用。

---

## 使い方（主要コマンド）

- 実行エンジンの起動（エンジンはデーモン/スレッドでセッションを実行）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper 用 DB に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止します。
  - 実行時に data/execution.pid が作成されます（PID 管理）。

- 監視ループの起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず本番 DB を参照）。
  - 停止: プロセスに KeyboardInterrupt、またはリポジトリルートの `data/stop_requested.flag` を作る。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` / `--db` で上書き可能）

- AI 関連（ライブラリ関数として利用）
  - ニューススコアを生成:
    ```python
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="OPENAI_KEY")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="OPENAI_KEY")
    ```

- ログ設定ユーティリティ（アプリ内で自動的に呼ばれる）
  - ルートロガーに StreamHandler と 日次ローテーションファイルハンドラを設定します。

---

## 主要環境変数（抜粋）

- 必須（validate_config によりチェック）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用関連
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）

- Paper トレード
  - PAPER_FILL_MODE: instant | partial | never | reject
  - PAPER_TRADING_SQLITE_PATH

詳しくは `kabusys.config.Settings` を参照してください。

---

## 停止 / Kill Switch の挙動

- デーモン的なプロセス（監視 / 実行）はプロジェクトルートの `data/stop_requested.flag` の存在を監視しています。存在すると起動/ループを中断します。
- Kill Switch（リスク閾値超過時）: `data/kill.flag` に理由を書き込み、ExecutionEngine に停止シグナルを送ります。Kill Switch は冪等的に動作します。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に Kill Flag を自動クリアします（本番では 0 推奨）。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定読み込み
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングスクリプト
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (実装がある場合)
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
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
    - data/ (スクリプトや DB 用の配置場所、デフォルト)
  - その他 config/*.yaml や docs/、scripts/ 等がある想定

（注）上記は主要ファイルを抜粋した構成です。実際のリポジトリでは追加ファイルやサブモジュールが存在する場合があります。

---

## 開発上の注意 / 既知の動作

- Settings は .env / .env.local を自動で読み込みます（環境変数優先）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を解析・リサーチ用途に使い、SQLite は監視・トレードログ用途に使う設計です（用途を分離）。
- AI（OpenAI）呼び出しは堅牢化のためリトライ処理とレスポンスバリデーションを行いますが、API キーや利用制限の管理は運用側で行ってください。
- `run_monitoring` は実行環境（KABUSYS_ENV）にかかわらず監視用 SQLite を使用します（監視は本番データを参照する前提）。

---

## よくあるコマンド（まとめ）

- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視ループ起動:
  ```
  python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に記載されていない詳細（各モジュールの内部動作や API）は、該当ソースファイルの docstring とコメントを参照してください。追加で README に追記したい項目（例: デプロイ手順、systemd ユニットサンプル、Dockerfile など）があれば指示してください。