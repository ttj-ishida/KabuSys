# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主に以下を目的としています。

- 発注エンジン（ExecutionEngine）による売買ロジックの実行（実口座／ペーパートレード対応）
- 監視（Monitoring） — システム状態、注文状況、リスク監視、Kill Switch（停止フラグ）
- ポートフォリオ構築（銘柄選定・重み算出・ポジションサイズ決定）
- リサーチ（ファクター計算、特徴量探索）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 解析用 DB：DuckDB（分析用）／SQLite（監視・発注ログ）

コードベースは純粋関数的なモジュールと、起動用スクリプト / CLI ツール群で構成されています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（本番／ペーパートレード対応）
  - BrokerClientFactory により環境に合わせたブローカークライアントを生成
  - リスク管理（RiskManager / Reconciler / OrderManager 等）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor: 注文の滞留・約定異常など監視（コード内に実装あり）
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringEngine: 各 Monitor を統合してポーリング
  - MonitoringDB: SQLite を用いた監視ログの永続化
- Portfolio
  - 銘柄選定 / 等重・スコア重み計算（portfolio_builder）
  - セクター上限、レジーム乗数（risk_adjustment）
  - 単元株丸め・リスクベース等の株数計算（position_sizing）
- Research
  - ファクター計算（Momentum/Value/Volatility など）
  - 将来リターン計算、IC 計測、ファクター統計サマリ
- AI
  - news_nlp: raw_news を集約し OpenAI（gpt-4o-mini）でセンチメントを算出、ai_scores に格納
  - regime_detector: ETF MA 乖離とマクロニュースセンチメントを合成して市場レジーム判定
- ユーティリティ
  - 設定ウィザード（config_setup）で .env を対話式生成
  - 設定検証ツール（validate_config）で環境変数・config/*.yaml のチェック
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report）
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils.process_priority）

---

## 要件（主な依存）

- Python 3.10+ （typing 記法、| union を多用）
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - openai
- 任意 / 機能依存
  - PyYAML（config/*.yaml を検証する場合に必要）
- 標準で SQLite3 を使用（組み込み）

※ 実行環境に合わせて requirements.txt を用意して pip install することを推奨します。
例:
```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil openai PyYAML
   ```
4. .env の初期作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   - J-Quants トークン、kabu API パスワード等の必須値を入力してください。
   - 生成される .env は絶対に Git にコミットしないでください。

5. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにしたいとき:
   python -m kabusys.validate_config --strict
   ```

6. OpenAI を使う機能（news_nlp / regime_detector）を使う場合、
   環境変数 OPENAI_API_KEY を設定するか、各関数呼び出し時に api_key を渡す。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB, デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading 用, instant|partial|never|reject; デフォルト: instant)
- LOG_LEVEL (DEBUG/INFO/...)
- OPENAI_API_KEY （AI 機能で必要）
- MONITOR_POLL_INTERVAL （run_monitoring のポーリング秒数、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動消去するか、開発用）

自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（起動 / CLI）

- 設定ウィザード（.env 生成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動（本番または paper_trading は KABUSYS_ENV に依存）
  ```bash
  # 本番 / paper_trading / development は .env の KABUSYS_ENV を設定
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、データは paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録され本番 DB と分離されます。
  - 実行中に停止シグナルを送るには `data/kill.flag` を作成してください（Kill Switch が検出すると Engine を停止します）。
  - run_execution は実行中に `data/stop_requested.flag` の存在をチェックしてスレッドを終了します（プロジェクトルートの data ディレクトリ内）。

- Monitoring 起動（ポーリング監視ループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は実行環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化します。
  - 停止フラグファイル `data/stop_requested.flag` が存在するとループを終了します。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # データベース指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（スクリプト的に利用）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キーを環境変数または引数で渡す必要があります。

---

## 停止・Kill Switch・フラグファイル

- data/kill.flag
  - KillSwitch が発動した理由を文字列で書き込むファイルです。ExecutionEngine はこのフラグを見て停止します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時にこのフラグを自動クリアします（本番環境では 0 推奨）。

- data/stop_requested.flag
  - run_monitoring / run_execution の起動スクリプトがループ終了やスレッド終了判定に使用する「停止リクエスト」フラグです。

- PID ファイル
  - 実行スクリプトは PID ファイル（デフォルト data/execution.pid 等）を使用します。

---

## ログと DB

- デフォルトログディレクトリ: logs/
  - ログは stdout とファイル（<log_dir>/<app_name>.log）に出力され、日次ローテーション（30 日保管）が設定されています。
  - LOG_DIR 環境変数で変更できます。

- デフォルト DB パス
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - SQLite (paper_trading): data/paper_trading.db

---

## 注意事項 / 運用上のポイント

- KABUSYS_ENV が `live` の場合は本番扱いになります。validate_config は本番向けのチェックと警告を行います。LINE 通知が未設定であれば警告が出ます。
- OpenAI を利用するモジュールは API エラー時に適切にフォールバックする実装になっていますが、API キーの管理（レート制限・料金）に注意してください。
- process_priority.setup は起動時にプロセス優先度を "high" に設定します。OS の権限により設定できない場合は警告でスキップされます。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- DuckDB の SQL 実行や executemany の振る舞いはバージョン差に影響されるため、運用環境で動作確認を行ってください。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` をルートに見た抜粋構成です（実際のファイル数はさらに存在します）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                  — ニュース NLP / OpenAI スコアリング
    - regime_detector.py           — 市場レジーム判定
  - monitoring/
    - monitoring_db.py             — SQLite テーブル初期化 / DB ラッパ
    - system_monitor.py            — システム監視
    - trade_monitor.py             — 注文監視（ファイルに実装あり）
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — Kill Switch 管理
    - monitoring_engine.py         — モニタリング統合エンジン
    - alert_manager.py             — 通知管理（LINE 等）
  - execution/
    - execution_engine.py          — 発注エンジン実装
    - broker_factory.py            — Broker クライアント生成
    - order_manager.py             — 注文管理
    - order_repository.py          — 注文永続化（SQLite）
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数計算・資金配分
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - factor_research.py           — ファクター計算
    - feature_exploration.py       — 将来リターン・IC 等
  - data/
    - pipeline.py                  — 価格データ取り込みユーティリティ（参照される）
    - stats.py                     — Z-score 等（参照される）
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — 優先度 / CPU affinity ユーティリティ

※ 上記は主要なファイル群の抜粋です。実際はさらに細かなモジュール / テストが含まれる可能性があります。

---

## よく使うコマンドまとめ

- .env の対話生成:
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
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、この README をベースに「デプロイ手順」「Dockerfile / systemd ユニット例」「運用 Runbook（Kill Switch の運用、バックアップ、ログローテーション）」「テスト手順」などの追加ドキュメントも作成できます。どの内容を優先して追加しますか？