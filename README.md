# KabuSys

日本株向けの自動売買 / 研究用ライブラリ群および実行用スクリプト群です。  
本リポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AIを用いたニュース解析などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群から構成されています。

- 発注・実行エンジン（ExecutionEngine）
  - 本番/ペーパートレード切替、リスク管理、注文管理など
- 監視（Monitoring）
  - システム稼働状況、注文ログ、リスク指標の定期チェックとアラート/キルスイッチ
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value 等）、将来リターン、IC計算、特徴量統計
- AI（OpenAI）連携
  - ニュースのセンチメント分析（ai/news_nlp.py）
  - 市場レジーム判定（ai/regime_detector.py）
- ユーティリティ
  - ロギング設定、プロセス優先度設定、設定ウィザード / 検証ツール 等
- ツール
  - ペーパートレード検証レポート生成ツール等

設計方針として、DBアクセスやAPI呼び出しの影響を最小限にしてテスト可能性・安全性を確保することを重視しています（例: ペーパートレードは本番DBと分離）。

---

## 主な機能一覧

- 実行（run_execution.py）
  - KABUSYS_ENV に応じて実DB / mock broker を使い分け
  - 停止フラグ（data/stop_requested.flag）検知で安全停止
  - PID ファイル管理（data/execution.pid）
- 監視（run_monitoring.py）
  - SystemMonitor のポーリングループ（デフォルト間隔 60 秒、環境変数で変更可）
  - 監視ログは SQLite（monitoring.db）へ永続化
  - kill.flag 用いた ExecutionEngine 停止トリガー
- 設定関連
  - 対話式 .env 生成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py） — .env / config/*.yaml のチェック
- 研究用
  - DuckDB を用いたファクター計算（momentum / volatility / value）
  - forward returns / IC / 統計サマリー
- AI
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント集計（ai.news_nlp.score_news）
  - マクロニュース＋ETF MA を合成して市場レジーム判定（ai.regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## セットアップ手順

1. Python 環境（3.10+ 相当）を準備します。仮想環境を推奨します。

   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 必要なパッケージをインストールします（プロジェクトに requirements.txt がない場合は以下を参考にインストールしてください）。

   必須（最低限）:
   - duckdb
   - psutil
   - openai

   任意（YAML の検証を行う場合）:
   - PyYAML

   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. .env を作成します（対話式ウィザード推奨）。

   ```
   python -m kabusys.config_setup
   ```

   ウィザードに従って必須項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）を入力してください。`.env` は絶対にリポジトリにコミットしないでください。

4. 設定を検証します:

   ```
   python -m kabusys.validate_config
   # 警告を厳密に扱いたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリを用意します（デフォルト DB・フラグなど）:

   - data/（デフォルトで logs/ なども作成されます）
   - 環境変数でパスを上書きすることができます（下記参照）。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LOG_LEVEL / LOG_DIR: ログレベル・ログディレクトリ
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（"1" でクリア）

自動で .env を読み込む仕組みがあります（プロジェクトルートの .env, .env.local）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方

以下はよく使うコマンド例です。パッケージ内のスクリプトは module として実行することを想定しています。

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 監視ループ起動（SystemMonitor をポーリングして監視ログを保存）
  ```
  python -m kabusys.run_monitoring
  # ポーリング間隔を 30 秒にしたい場合:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  特徴:
  - MONITOR_POLL_INTERVAL で間隔を変更可能（秒）
  - 監視は常に本番の sqlite_path を参照（環境にかかわらず）

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```

  特徴:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`data/paper_trading.db` に発注ログを保存して本番 DB と分離します
  - 起動時に data/stop_requested.flag が存在すると起動しません
  - 停止は data/stop_requested.flag を作ることで可能（Kill Switch と併用可）

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI ニューススコアリング（プログラムから呼ぶ例）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
  print("書き込み件数:", count)
  ```

- 市場レジーム判定（プログラムから）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 04, 11), api_key="sk-...")
  ```

ログ出力:
- setup_logging により stdout と logs/<appname>.log（日次ローテーション、30 日分保持）に出力されます。

停止・Kill Switch:
- KillSwitch は RiskMonitor 等の判定結果に応じて `data/kill.flag` を書き込み、ExecutionEngine に停止指示を与えます。flag は起動時に自動クリア設定がオンであれば消されます（KILL_FLAG_CLEAR_ON_START）。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src/kabusys 以下）:

- kabusys/__init__.py
- kabusys/config.py
- kabusys/config_setup.py
- kabusys/validate_config.py
- kabusys/run_monitoring.py
- kabusys/run_execution.py

- kabusys/ai/
  - news_nlp.py            # ニュースセンチメントの LLM スコアリング
  - regime_detector.py     # マクロ + ETF MA によるレジーム判定

- kabusys/monitoring/
  - monitoring_db.py       # SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py       # （コードベースに存在、監視用）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py       # （アラート送信ロジック）

- kabusys/execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py

- kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- kabusys/research/
  - factor_research.py
  - feature_exploration.py

- kabusys/tools/
  - paper_verification_report.py

- kabusys/utils/
  - logging_setup.py
  - process_priority.py

- その他:
  - config/                 # 各種 YAML 設定ファイル（例: system_config.yaml 等）
  - data/                   # デフォルトの DB / flag / pid ファイル置き場
  - logs/                   # ログ出力先（デフォルト）

（上記は抜粋です。詳細はソースツリーを参照してください）

---

## 開発・運用時の注意点

- .env の取り扱い:
  - 機密情報を含むため絶対にリポジトリにコミットしないでください。
  - config_setup で .env を作成後、validate_config でチェックすることを推奨します。

- 本番環境（KABUSYS_ENV=live）の注意:
  - LINE 通知の設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を確認してください。未設定だとアラートが届きません。
  - KILL_FLAG_CLEAR_ON_START は本番では "0" を推奨します（自動クリアは危険）。

- DB 切り分け:
  - paper_trading モードでは paper_trading 用の SQLite を使用し、本番監視 DB と分離します。環境変数 PAPER_TRADING_SQLITE_PATH でパスを指定できます。

- OpenAI 利用:
  - API キーは環境変数 OPENAI_API_KEY または関数引数で指定してください。
  - LLM 呼び出し時のエラーはリトライやフォールバックを実装していますが、API制限やコストに注意してください。

- ロギング / 権限:
  - logs ディレクトリ作成に失敗した場合はコンソールのみの出力へフォールバックします。
  - process priority / cpu affinity の設定は権限により失敗する場合があります（警告のみ）。

---

## よくあるコマンドまとめ

- .env を新規作成 / 更新:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- 監視ループ起動:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```

- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README はまずはここまでです。必要であれば以下の追加情報を作成できます：

- 依存パッケージの詳細な requirements.txt
- config/*.yaml のサンプル説明と生成手順
- 各モジュール（ExecutionEngine / MonitoringEngine / AI モジュール等）の詳細な API ドキュメント（関数説明、引数例）
- 運用手順（デプロイ、systemd / cron での起動例）

どれを追加しますか？