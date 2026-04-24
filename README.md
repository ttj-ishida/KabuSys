# KabuSys

日本株の自動売買 / 研究基盤用ライブラリ（部分実装）。本リポジトリは以下の主要コンポーネントを含みます：Execution エンジン（発注）、Monitoring（監視・Kill Switch）、Portfolio 建設ロジック、Research（ファクター計算・特徴量探索）、AI 補助モジュール（ニュース NLP / レジーム判定）、および各種ユーティリティとツール群。

---

## 主な特徴

- ExecutionEngine（発注エンジン）
  - live / paper_trading / development 環境に応じた動作
  - paper_trading 環境では MockBrokerClient を使い、data/paper_trading.db に完全分離して記録
  - OrderManager / RiskManager / Reconciler 等の構成要素を含む

- Monitoring（常時監視）
  - System / Trade / Risk の複数モニタを組み合わせた MonitoringEngine
  - Kill Switch（data/kill.flag）による強制停止
  - 監視ログは SQLite（監視 DB）へ永続化

- Portfolio（銘柄選定・配分・サイズ決定）
  - 候補選定、等重・スコア重み、ポジションサイズ計算（単元丸め・集約キャップ等）
  - セクターキャップ、レジーム乗数などのリスク調整

- Research（DuckDB を用いたファクター計算）
  - Momentum / Volatility / Value などのファクター計算モジュール
  - 将来リターン計算、IC（Spearman）や統計サマリー

- AI モジュール（OpenAI）
  - ニュース記事を LLM（gpt-4o-mini 想定）でスコアリングして ai_scores に書き込み
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定

- ユーティリティ
  - ロギング初期化（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - `.env` 対話ウィザードと設定検証 CLI
  - ペーパートレードの検証レポート生成ツール

---

## 必要条件（開発環境）

- Python 3.10 以上（| 型や標準型ヒントを使用しているため）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に YAML ファイルの内容検証を行う場合）
- SQLite は標準ライブラリの sqlite3 を使用

インストール例（仮の requirements がない場合）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ 実際の requirements.txt があれば `pip install -r requirements.txt` を使用してください。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 仮想環境を作成・有効化、依存パッケージをインストール

3. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 実行環境: KABUSYS_ENV は `development` / `paper_trading` / `live`
   - paper_trading を使う場合、DB は data/paper_trading.db に分離して記録されます

4. 設定の検証
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗として exit(1) になります
   - PyYAML がない場合は一部の YAML 検証がスキップされます（警告）

5. 必要なディレクトリの作成（ログ / data）
   - ログ: `logs/`（デフォルト。環境変数 LOG_DIR で変更可）
   - DB格納先: `data/`（デフォルト）
   - これらは起動時に自動生成されることが多いですが、権限などに注意してください

---

## 使い方（実行コマンド）

主要なエントリポイントはモジュールとして起動します。プロジェクトルートで実行してください。

- ExecutionEngine を起動（バックグラウンドで発注処理を実行）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し data/paper_trading.db に記録
  - 起動前に data/stop_requested.flag があると起動しません
  - エンジン稼働中に同ファイルが作成されると安全に停止を試みます
  - ExecutionEngine の PID ファイル: data/execution.pid（Settings で変更可能）

- Monitoring（ポーリング監視）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き: `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視ログは本番 DB 想定）
  - 監視は system/trade/risk のチェックを行い、必要なら kill.flag（デフォルト data/kill.flag）を書き込む

- 設定検証（CLI）
  ```
  python -m kabusys.validate_config
  ```

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート生成ツール
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH`、`--db` オプションで変更可）

- ライブラリとしての利用（例）
  - AI スコアリングを呼ぶ:
    ```python
    from kabusys.ai.news_nlp import score_news
    # conn は duckdb.connect(...) のコネクション
    score_news(conn, target_date, api_key="sk-...")
    ```

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒、デフォルト 60）
- OPENAI_API_KEY（AI モジュール使用時）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動的にクリアするフラグ、"1" で有効 — 本番では注意）

詳細は `kabusys.config.Settings` を参照してください。

---

## 停止・制御ファイル

- data/stop_requested.flag
  - run_execution / run_monitoring が監視している「停止要求」フラグ（生成すると実行プロセスに停止を促す）
- data/kill.flag
  - Kill Switch が書き込むファイル。ExecutionEngine 側で存在確認を行い、発注を停止します
- data/execution.pid
  - ExecutionEngine の PID ファイル（Settings の pid_file_path で指定可能）

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル / ディレクトリ構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB
    - monitoring_engine.py   — モニタの統括ポーリング
    - system_monitor.py
    - trade_monitor.py       — （TradeMonitor 実装が別ファイルにある想定）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信処理: LINE 等）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - (ほか関連モジュール)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                   — 実行時に生成される想定（monitoring / duckdb / pid / flag 等）
  - logs/                   — ログ出力先（デフォルト）

---

## 開発メモ / 注意点

- 自動で .env をロードする仕組みがあり、プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Monitoring は監視 DB（SQLite）へログを常に書きます。run_monitoring は `MONITOR_POLL_INTERVAL` で間隔を変更可能です。
- ExecutionEngine は paper_trading 環境時に本番 DB と完全に分離してペーパートレード DB を使います。実運用時は KABUSYS_ENV と DB パスの設定を特に注意してください。
- AI モジュールは OpenAI API を利用します。API の失敗やレートリミットは内部でリトライ処理やフェイルセーフ（スコア 0.0 等）で扱いますが、費用・API キー管理に注意してください。
- ロギングはルートロガーをクリアして再設定します。既存のハンドラがある場合は上書きされる点に留意してください。

---

必要に応じて、この README をプロジェクトの実際の README.md にコピーし、依存関係や実行手順（systemd / supervisor / Docker など）を環境に合わせて追記してください。質問や追加したいセクションがあれば教えてください。