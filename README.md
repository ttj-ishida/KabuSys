# KabuSys

日本株自動売買システム（ライブラリ + 起動スクリプト群）

このリポジトリは、戦略実行（ExecutionEngine）、監視（Monitoring）、研究用ファクター計算、AI を用いたニュースセンチメント / レジーム判定、ポートフォリオ構築ユーティリティなどを含む自動売買基盤の一部です。

---

## 概要

- モジュール構造は「実行」「監視」「研究」「AI」「ポートフォリオ」「ユーティリティ」などに分割されています。
- 設定は `.env` ファイルまたは環境変数から読み込まれます。対話式ウィザードで `.env` を生成できます。
- 本番/ペーパートレードの切り替えをサポート（`KABUSYS_ENV`）。
- 監視（System / Trade / Risk）コンポーネントによりシステム稼働性や注文の異常を検出し、必要に応じて Kill Switch（`data/kill.flag`）で ExecutionEngine を停止できます。
- DuckDB/SQLite をデータ層として利用。監視ログは SQLite（デフォルト `data/monitoring.db`）、分析用 DB は DuckDB（デフォルト `data/kabusys.duckdb`）、ペーパートレードは専用 SQLite（`data/paper_trading.db`）に分離されます。
- OpenAI API（例: `gpt-4o-mini`）を使ったニュース NLP とレジーム検出を実装済み（API キー必須）。

---

## 機能一覧

- 設定管理
  - 自動的な `.env` 読み込み（`.env`, `.env.local`）
  - `kabusys.config.Settings` による型付き設定参照
  - 対話式設定ウィザード: `python -m kabusys.config_setup`
  - 設定検証 CLI: `python -m kabusys.validate_config`

- 実行 / 発注
  - ExecutionEngine の起動 / 停止用スクリプト: `python -m kabusys.run_execution`
  - ペーパートレードモード (`KABUSYS_ENV=paper_trading`) は MockBroker を使用し DB を分離
  - リスク管理（RiskManager）・オーダー管理・再整合（Reconciler）を統合

- 監視
  - System / Trade / Risk の監視ロジック
  - 監視ループ起動スクリプト: `python -m kabusys.run_monitoring`
  - 監視ログ永続化（SQLite）とダッシュボード集計
  - Kill Switch による ExecutionEngine 停止（`data/kill.flag`）

- ポートフォリオ構築
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数などの純粋関数群

- リサーチ
  - DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC（Information Coefficient）・特徴量サマリー

- AI
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメントを ai_scores に保存
  - レジーム判定（MA200 + マクロセンチメント合成）を market_regime に保存
  - API 呼び出しはリトライやフェイルセーフを備える

- ツール
  - ペーパートレード検証レポート生成: `python -m kabusys.tools.paper_verification_report`

- ユーティリティ
  - ロギング設定ユーティリティ（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要条件（例）

- Python 3.10+
- 主要依存パッケージ（プロジェクトに requirements.txt がない場合の例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定 YAML の内容検証を行う場合）
- （任意）SQLite は標準ライブラリに含まれます

インストール例:
```bash
python -m pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 展開

2. Python 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # (Unix)
   .venv\Scripts\activate     # (Windows)
   ```

3. 必要パッケージをインストール（上記参照）

4. `.env` の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   このウィザードは `.env`（デフォルト）を生成します。主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   重要な環境変数（一部）:
   - KABUSYS_ENV: development | paper_trading | live
   - DUCKDB_PATH: data/kabusys.duckdb (デフォルト)
   - SQLITE_PATH: data/monitoring.db (デフォルト)
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時）
   - LOG_LEVEL: DEBUG|INFO|...
   - OPENAI_API_KEY: OpenAI を使う場合に必須

5. 設定の検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いになります
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの準備（自動生成されますが、手動でも可）
   - data/
   - logs/

---

## 使い方（起動・運用）

- 監視ループの起動:
  - デフォルトは 60 秒ポーリング間隔。環境変数で上書き可能:
    - MONITOR_POLL_INTERVAL（秒、1 以上）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 監視は常に本番の sqlite_path（`Settings.sqlite_path`）を使用します（環境にかかわらず）。

- ExecutionEngine の起動:
  ```bash
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を利用します（本番 DB と完全分離）。
  - 起動時に `data/stop_requested.flag` が存在すると起動を中止します。
  - 実行中は `data/execution.pid` に PID が書かれます。

- 停止方法 / Kill Switch:
  - 監視が異常を検出した場合、`data/kill.flag` を書き込んで ExecutionEngine に停止命令を送ります（KillSwitch）。
  - 手動で停止したい場合は `data/stop_requested.flag` を作成すると起動中のループ / エンジンが検知して停止します。
  - `Settings.kill_flag_clear_on_start` が `1` の場合、起動時に kill.flag を自動クリアします（本番では `0` 推奨）。

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプション `--db` で DB パスを指定可能（環境変数より優先）。

- AI 機能（プログラム的利用例）
  - ニューススコアリング（DuckDB 接続を渡す）
    from kabusys.ai import score_news
    score_news(conn, target_date, api_key="...")

  - レジーム判定
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

- ライブラリ関数の利用（例）
  - 設定参照:
    from kabusys.config import settings
    settings.env, settings.sqlite_path, ...
  - ポートフォリオ関数:
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

---

## 注意点 / 運用に関するメモ

- 環境変数の優先順位: OS 環境変数 > .env.local > .env。自動読込は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- `PAPER_FILL_MODE`（ペーパートレードの約定挙動）: "instant" | "partial" | "never" | "reject"。無効値は例外。
- ログ:
  - デフォルトは `logs/` ディレクトリにアプリ別ログが日次ローテートで保存されます。
  - `kabusys.utils.logging_setup.setup_logging(app_name="execution")` が起動スクリプトから呼ばれます。
- プロセス優先度は起動時に High に設定されますが、権限やプラットフォームによっては設定に失敗する場合があります（警告ログ）。
- DuckDB / SQLite のパスは設定で上書き可能。ペーパートレードは本番 DB と分離することが強く推奨されます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — 優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 / 永続化層
    - system_monitor.py
    - trade_monitor.py       — （トレード監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラートの抽象化）
  - execution/
    - execution_engine.py    — 実行エンジン本体
    - order_manager.py
    - order_repository.py
    - broker_factory.py
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
  - monitoring/               — 監視関連（上記）
  - tools/
    - paper_verification_report.py

その他: `data/`（DB/フラグファイル等）、`logs/`（ログ）を想定する。

---

## FAQ（よくある質問）

- Q: ペーパートレードで本番データベースに影響しますか？
  - A: いいえ。`KABUSYS_ENV=paper_trading` のときは `PAPER_TRADING_SQLITE_PATH` を使用し、本番 DB と分離されます。

- Q: 監視と実行は同一マシンで走らせるべきですか？
  - A: 運用設計次第です。監視は ExecutionEngine を外部から監督し Kill Switch を書き込む役割を果たします。常時別プロセス／別インスタンスでの運用を想定しています。

- Q: OpenAI の呼び出しに失敗したらどうなりますか？
  - A: 各 AI モジュールはリトライやフェイルセーフ（例: macro_sentiment=0.0）を持ち、失敗してもシステム全体が停止しないよう設計されています。ただし AI 出力を前提にする判定は結果に影響します。

---

README でカバーしきれない詳細（ExecutionEngine の内部仕様、OrderRepository の DB スキーマ詳細、AlertManager の実装など）は各モジュールの docstring およびソースコードを参照してください。必要であれば、起動手順のサービス化（systemd / supervisor / docker-compose）や運用 runbook のテンプレートも作成できます。必要であれば教えてください。