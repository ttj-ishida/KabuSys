# KabuSys

日本株向け自動売買システムのライブラリ/ランタイム周り。  
このリポジトリは実運用・ペーパートレード・リサーチ用途の共通コンポーネント群（実行エンジン、監視、ポートフォリオ構築、ファクター計算、ニュースNLP連携など）を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のような機能を分離して提供する設計です。

- ExecutionEngine（発注エンジン）: 本番 or ペーパートレードで発注処理を行うランタイム
- Monitoring（監視）: システム稼働状況、データ鮮度、注文挙動、リスク（ドローダウン・保有上限）を定期チェックしてログ / アラート / Kill Switch を管理
- Portfolio construction（銘柄選定・配分・ポジションサイズ）: 純粋関数群で重み・株数を計算
- Research（ファクター計算・特徴量探索）: DuckDB を使ったファクター計算・IC 等の分析ツール
- AI（ニュース NLP / レジーム判定）: OpenAI を用いてニュースのセンチメントや市場レジームを算出し DB へ書き込む
- CLI ツール: .env 設定ウィザード、設定検証、Paper Trading レポート生成 など
- 共通ユーティリティ: ロギング設定、プロセス優先度制御等

設計方針として、ランタイムとリサーチ/分析コードは原則データベースを介して分離され、ペーパートレードは本番 DB と分離して安全に実行できるようになっています。

---

## 主な機能一覧

- 環境設定管理 (.env 自動読み込み / Settings クラス)
- 対話式 .env ウィザード (kabusys.config_setup)
- 起動前設定検証 CLI (kabusys.validate_config)
- ExecutionEngine 起動スクリプト (kabusys.run_execution)
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し data/paper_trading.db に保存
- Monitoring 起動スクリプト (kabusys.run_monitoring)
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
- 監視用 DB 層（SQLite）および MonitoringEngine（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- Portfolio コンポーネント（候補選定、重み計算、セクター制約、ポジションサイズ計算）
- Research（ファクター計算: momentum / volatility / value、特徴量探索、IC 計算）
- AI モジュール
  - kabusys.ai.news_nlp.score_news: ニュースを OpenAI で評価 → ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime: ETF MA とマクロ記事からレジーム判定
- ツール: paper_verification_report（ペーパートレードの検証レポート生成）
- ユーティリティ: ロギングの統一設定、プロセス優先度設定、CPU affinity 設定

---

## 前提 / 必要環境

- Python 3.10+
- 必須パッケージ（実行機能を使う場合）:
  - duckdb
  - psutil
  - openai
- 任意/補助:
  - PyYAML（config/*.yaml のパース検証に使用）
- ビルトイン: sqlite3 は標準ライブラリを使用

インストール例（仮の requirements）:
```bash
python -m pip install duckdb psutil openai PyYAML
```

（実際のプロジェクトでは requirements.txt / poetry 等で管理してください）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに移動
2. Python 仮想環境を作成・有効化
3. 必要なパッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードを推奨:
     ```bash
     python -m kabusys.config_setup
     ```
   - 手動で作成する場合は最低限以下を設定してください:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - OPENAI_API_KEY（AI 機能を使う場合）

5. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. 必要に応じてデータディレクトリを作成（デフォルト）
   - SQLite / DuckDB のデフォルトパス:
     - data/monitoring.db
     - data/kabusys.duckdb
     - data/paper_trading.db（ペーパートレード用）
   - ログディレクトリ: logs/

注意:
- 自動的に .env をプロジェクトルートの .env/.env.local から読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主なコマンド）

- ExecutionEngine を起動
  - 本番 / 開発 / ペーパーは KABUSYS_ENV で切り替え
  ```bash
  python -m kabusys.run_execution
  ```
  - ペーパートレード:
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - ペーパートレードでは MockBrokerClient が使用され、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に保存され、本番 DB と分離されます。

- Monitoring を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには環境変数 `MONITOR_POLL_INTERVAL`（秒）を指定:
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- .env 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB または環境変数 PAPER_TRADING_SQLITE_PATH を使用
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- プログラムからの呼び出し例（AI スコア）
  ```python
  import duckdb
  from kabusys.ai import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026, 4, 20), api_key="sk-...")
  ```

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知（任意）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- LOG_DIR: ログ出力先（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（1）

---

## ログ・PID・Kill Switch

- ログ: デフォルトは `logs/<app_name>.log`（日次ローテーション、30 日保持）。`setup_logging()` で統一的に設定。
- PID ファイル: ExecutionEngine は起動時に PID ファイル（デフォルト `data/execution.pid`）を使用します。
- Kill Switch: `data/kill.flag`（`Settings.kill_flag_path` で上書き可能）を作成することで ExecutionEngine を停止させる仕組み。Monitoring の KillSwitch が条件を満たすと自動的に flag を書き込みます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env ウィザード CLI
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — 優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py       — （省略箇所あり、取引監視）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — アラート送信管理（LINE など）
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig 等）
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
    - news_nlp.py             — ニュース NLP（OpenAI 連携）
    - regime_detector.py      — レジーム判定
  - tools/
    - paper_verification_report.py

（上記は主要ファイルのみ抜粋。詳細はソースツリーを参照してください）

---

## 注意事項 / 運用メモ

- ペーパートレードは本番 DB と完全分離する設計です。KABUSYS_ENV=paper_trading を利用してください。
- OpenAI API を使う機能は API キー（OPENAI_API_KEY）が必要です。API 利用はコストとレート制限に注意してください。
- monitor はデフォルトで本番 sqlite_path を参照します（監視は実稼働 DB を見る想定）。
- Settings による .env 自動ロードはプロジェクトルート（.git or pyproject.toml）を検出して行います。CI / テストで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- データベーススキーマの簡単なマイグレーション（カラム追加など）処理を init_monitoring_db が行いますが、本格的なマイグレーションを行う場合は別途 migrate ツールを用意してください。

---

## 貢献 / 開発

- 開発者向け: ソースは `src/kabusys` 配下にあり、各モジュールは単体テストしやすい純粋関数や小さなクラスに分かれています。ユニットテスト、モック（OpenAI 等）の導入を推奨します。
- 実運用ではログ、アラート、Kill Switch の動作確認を必ず行ってください（特に KABUSYS_ENV=live の場合）。

---

必要であれば、README に実際の .env のテンプレート、より詳細な起動例、systemd / supervisor / cron のユニット例、CI ワークフロー、あるいは内部設計ドキュメント（API、DB スキーマ、メッセージフロー）を追加します。どの情報を優先して追加しますか？