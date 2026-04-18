# KabuSys

日本株向け自動売買システムのコアライブラリ群および起動スクリプト集です。  
このリポジトリはトレーディング実行、監視、リサーチ、ポートフォリオ構築、AIニュース分析などのコンポーネントで構成されています。

Version: 0.1.0

---

## 概要

KabuSys は以下の機能ブロックを持つモジュール化された自動売買基盤です。

- Execution Engine：発注実行・注文管理・リスク管理を行う（paper_trading / live 切替対応）
- Monitoring：システム状態、データ鮮度、注文/約定状態、リスク指標をポーリングしてログ・アラート・Kill Switch を管理
- Research：DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析
- Portfolio：銘柄選定、配分、ポジションサイズ計算、セクターキャップ等の純粋関数群
- AI モジュール：ニュースのセンチメント評価（OpenAI）や市場レジーム判定
- ユーティリティ：設定 (.env) ウィザード、設定検証、ログセットアップ、プロセス優先度調整など

設計方針の一部：
- データベース（DuckDB/SQLite）は読込・書込ポイントを明確に分離
- paper_trading と live は DB を分離して安全性を確保
- OpenAI 呼び出しは冪等性・リトライ・バリデーションを考慮
- ログはコンソール + 日次ローテーションで保存

---

## 機能一覧（抜粋）

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading/ live 切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整）
- 設定管理
  - config_setup.py: .env を対話式で作成/更新
  - validate_config.py: .env と config/*.yaml の事前検証
- 監視
  - monitoring_engine、system_monitor、trade_monitor、risk_monitor、kill_switch、monitoring_db
- ポートフォリオ構築
  - 選定、重み算出（等分/スコア加重）、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ
  - factor_research（モメンタム/ボラティリティ/バリュー）、feature_exploration（IC 等）
- AI
  - news_nlp: raw_news を摘要して OpenAI で銘柄ごとにセンチメント評価、ai_scores へ書込
  - regime_detector: ETF とマクロ記事で市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成（成功率・稼働率・レイテンシ等）

---

## セットアップ手順

前提（代表的な依存）:
- Python 3.9+
- pip

推奨パッケージ（requirements.txt がない場合、少なくとも以下をインストールしてください）:
- duckdb
- psutil
- openai
- PyYAML（設定検証の YAML パース用だが必須ではない）

例:
```bash
python -m pip install duckdb psutil openai PyYAML
```

1. リポジトリルートに移動（.git または pyproject.toml が存在するディレクトリをプロジェクトルートとみなします）。
2. .env を作成:
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - または .env を手動作成（.env.example があれば参照）。`.env` は絶対に git にコミットしないでください。
3. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL としたい場合:
   python -m kabusys.validate_config --strict
   ```
4. データディレクトリ作成（デフォルトパスを使用する場合）:
   - data/ ディレクトリ（SQLite, pid, flag 用）
   - logs/ ディレクトリ（ログ）
   ウィザードか起動時に自動作成されることもありますが、権限に注意してください。

---

## 主要な環境変数（一覧とデフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (デフォルト: development) — 有効値: development / paper_trading / live
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring DB
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用 DB
- PAPER_FILL_MODE (デフォルト: instant) — instant / partial / never / reject
- LOG_LEVEL (デフォルト: INFO)
- LOG_DIR (デフォルト: logs/)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (デフォルト: 0) — 起動時に kill.flag を自動クリアするか
- MONITOR_POLL_INTERVAL (デフォルト: 60) — run_monitoring のポーリング秒数
- OPENAI_API_KEY — AI モジュール使用時に必要（引数でも渡せる）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知に使用（任意）

設定は .env と OS 環境変数から読み込まれます。自動読み込みはプロジェクトルートが特定できる場合に行われ、OS 環境変数が優先されます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 起動 / 使い方

基本的にモジュールは `python -m kabusys.<module>` で実行します。

1. Execution Engine（実行）
   - 起動:
     ```bash
     python -m kabusys.run_execution
     ```
   - 動作:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
     - 実行中は data/execution.pid を作成します。
     - 停止は data/stop_requested.flag を配置すると検知して優雅に停止します。
     - kill.flag（Settings.kill_flag_path）を監視しているため、監視コンポーネントから停止シグナルが送られると停止します。

2. Monitoring（監視ループ）
   - 起動:
     ```bash
     # MONITOR_POLL_INTERVAL を上書きする例（秒）
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     ```
   - 動作:
     - Settings から sqlite_path（監視 DB）へ接続し、SystemMonitor を定期実行して system_status/risk_logs/trade_logs 等を更新します。
     - MONITOR_POLL_INTERVAL でポーリング間隔を指定（デフォルト 60 秒）。
     - data/stop_requested.flag を検出するとループを終了します（停止フラグはプロジェクトルート/data 配下にあります）。
     - 監視は本番 sqlite_path を使用（環境に依らず）。

3. .env ウィザード
   ```bash
   python -m kabusys.config_setup
   ```

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   ```

5. Paper Trading 検証レポート
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB パス指定
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```

6. AI 関連（例）
   - ニューススコアリング:
     - 呼び出し関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
     - コマンドラインエントリは現在提供されていません（スクリプトやバッチから呼び出して使用）。
   - regime_detector.score_regime(conn, target_date, api_key=None)

注: OpenAI を使う機能は OPENAI_API_KEY を環境変数または引数で指定する必要があります。API 呼び出しはリトライとバリデーションが組み込まれており、失敗時はフェールセーフで処理を継続します（多くの場合ゼロスコアやスキップで安全に継続）。

---

## ロギング

- ロギング初期化は `kabusys.utils.logging_setup.setup_logging(app_name="...")` を通じて統一されています。
- デフォルトでは stdout と `logs/<app_name>.log`（日次ローテーション、30日保持）へ出力します。
- `LOG_DIR` や `LOG_LEVEL` で出力先/レベルを変更できます。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。

---

## Kill Switch / 停止フラグ

- Kill Switch（監視モジュール）はリスク条件（ドローダウン超過、ポジション上限超過等）で `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。
- ExecutionEngine と Monitoring は `data/stop_requested.flag`（run scripts 内の停止フラグ）をチェックして起動中の停止を行います。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると ExecutionEngine 起動時に kill.flag を自動クリアします（本番環境では 0 推奨）。

---

## ディレクトリ構成

以下は主なファイル／ディレクトリ構成（src/kabusys 配下）です：

- src/kabusys/
  - __init__.py
  - config.py                — 設定管理（.env 読込、Settings クラス）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 初期化 / CRUD
    - system_monitor.py      — システム / データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - trade_monitor.py       — （trade 関連監視 — 省略している箇所あり）
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — （アラート送信管理 — 省略）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動・セッション管理）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - monitoring/              — 上記監視関連
  - tools/
    - paper_verification_report.py
    - __init__.py

プロジェクトルートには `data/`（DB / pid / flag 等）と `logs/`（ログ）が作られる想定です。

---

## 開発上の注意点 / 運用上の注意

- .env は機密情報を含むため Git 管理しないこと（config_setup が警告を出します）。
- KABUSYS_ENV を `live` にする際は設定検証を十分に行い、LINE 通知設定や Kill Switch の設定値を確認してください。
- paper_trading モードは本番 DB を汚染しないよう専用 SQLite を使用します。実行前に PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI API を利用するコンポーネントはコストとレイテンシが発生します。運用で定期的に実行する場合はレート制限・コスト管理を行ってください。
- データベースマイグレーションは `monitoring_db.init_monitoring_db` などで一部自動化されていますが、スキーマ変更時は注意が必要です。
- プロセス優先度や CPU affinity の設定は環境・権限によって失敗することがあり、その場合は警告を出してスキップします。

---

## よく使うコマンドまとめ

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```bash
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に以下の追加を行います：
- requirements.txt のサンプル
- systemd ユニットや cron/systemd-timer の例
- 実行時のログ出力例やトラブルシュート（よくあるエラー）
- 詳細な API ドキュメント（関数 / クラス一覧と引数）  

どれを追加するか教えてください。