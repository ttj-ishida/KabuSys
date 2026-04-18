# KabuSys

日本株向け自動売買システムのコアライブラリ / 起動スクリプト群です。  
このリポジトリには取引エンジン実行、監視、ポートフォリオ構築、リサーチ、AIベースのニュース解析などの主要コンポーネントが含まれます。

---

## プロジェクト概要

KabuSys は以下のような責務を持つモジュール群で構成された自動売買プラットフォームのコア実装です。

- ExecutionEngine（発注エンジン）
- Monitoring（稼働・データ鮮度・リスク監視）
- Portfolio Construction（候補選定、重み付け、ポジションサイズ）
- Research（ファクター計算、将来リターン・IC 計算）
- AI モジュール（ニュース NLP によるセンチメントおよび市場レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度、設定読み込み）
- CLI ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

設計方針の一部として、DuckDB / SQLite を用いたローカルデータベースアクセスや、OpenAI API（gpt-4o-mini 等）を介した NLP 処理を行うことを想定しています。Paper Trading（ペーパートレード）用 DB は本番 DB と分離されています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使用して専用 DB に記録）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- 設定・検証 CLI
  - config_setup.py: 対話式ウィザードで .env を作成/更新
  - validate_config.py: .env や config/*.yaml の整合性チェック
- 監視
  - monitoring_engine, system_monitor, trade_monitor, risk_monitor, kill_switch：稼働監視、滞留注文・約定異常の検出、ドローダウン監視、Kill Switch の発動
  - monitoring_db: SQLite スキーマの初期化と単純な永続化 API
- ポートフォリオ構築
  - 銘柄選定、等金額／スコア加重、リスクベースのポジションサイズ計算、セクター上限の適用、レジーム乗数
- リサーチ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（スピアマンランク相関）や統計サマリ
- AI (OpenAI)
  - news_nlp: ニュース記事を集約して LLM でセンチメント評価 → ai_scores に書き込み
  - regime_detector: ETF の MA とマクロニュースセンチメントを合成して日次レジームを判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート（稼働率、注文成功率、レイテンシ等）

---

## 必要な依存ライブラリ（例）

主要なランタイム依存例:

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config 検証時に任意）
- （プロジェクトで requirements.txt を用意している場合はそちらを使ってください）

インストール例（最小）:
```bash
pip install duckdb psutil openai PyYAML
```

---

## 環境変数（主要項目とデフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/... (デフォルト: INFO)
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート用（任意）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI モジュール使用時）
- PAPER_FILL_MODE: instant | partial | never | reject （Paper Trading の約定挙動）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視関連の設定

.env はルートに置かれる想定（config_setup で生成可能）。環境変数は OS 環境 > .env.local > .env の順で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## セットアップ手順

1. レポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # Windows の場合は .venv\Scripts\activate
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil openai PyYAML
   ```
4. 環境変数を準備
   - 対話式ウィザードで .env を作成する:
     ```bash
     python -m kabusys.config_setup
     ```
   - または .env を手動作成し、必須 KEY を設定する（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD など）。
5. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告を厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```
6. 必要ディレクトリ（data/, logs/）が自動で作成されますが、権限等で失敗した場合は手動で作成してください。

---

## 使い方（起動 / 実行例）

- ExecutionEngine を起動（本番 / 開発 / Paper Trading は KABUSYS_ENV に従う）
  ```bash
  python -m kabusys.run_execution
  ```
  - Paper Trading（env=paper_trading）の場合は MockBroker が使われ、記録先 DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）になります。
  - 実行時、data/execution.pid に PID を書き込み、data/stop_requested.flag の存在で安全停止します。

- Monitoring を起動（SystemMonitor のポーリング）
  ```bash
  # ポーリング間隔を環境変数で上書き可能
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は KABUSYS_ENV に関係なく本番の sqlite_path を使用します（monitoring は常に本番 DB を見る設計）。
  - 監視ループは data/stop_requested.flag を検出すると終了します。

- .env の対話式セットアップ
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポートの生成
  ```bash
  # デフォルト DB または環境変数で指定された PAPER_TRADING_SQLITE_PATH を使用
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 特定の DB を直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI / リサーチ機能（ライブラリ呼び出し例）
  - ニュース NLP（ai.score_news）
    ```python
    from kabusys.ai import score_news
    import duckdb
    from datetime import date

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    print("書き込み件数:", written)
    ```
  - レジーム判定（ai.regime_detector.score_regime）
    ```python
    from kabusys.ai.regime_detector import score_regime
    import duckdb
    from datetime import date

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

---

## 監視 / 停止フラグ関係

- data/kill.flag: KillSwitch が書き込む「ExecutionEngine を停止する」ためのフラグファイル。存在する場合 Execution は（起動時や稼働中に）停止されます。KillSwitch は drawdown やポジション上限等で発動します。
- data/stop_requested.flag: run_execution / run_monitoring の外部停止用フラグ。起動スクリプトはこのファイルの存在を検出してループを終了します。
- PID ファイル: data/execution.pid に Execution の PID を書き込みます。

注意: KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると起動時に kill.flag を自動クリアするため危険です（本番では 0 推奨）。

---

## ディレクトリ構成

リポジトリの主要なファイルとディレクトリ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py               — .env 対話式ウィザード CLI
  - validate_config.py            — 起動前の設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - ai/
    - news_nlp.py                 — ニュースを LLM で評価して ai_scores に書込む
    - regime_detector.py          — マクロ + ETF MA からレジーム判定
  - monitoring/
    - monitoring_db.py            — SQLite スキーマ初期化 + 永続化 API
    - monitoring_engine.py        — 監視用エンジン（複数 Monitor を束ねる）
    - system_monitor.py           — システム・データ鮮度監視
    - risk_monitor.py             — ドローダウン & ポジション上限監視
    - kill_switch.py              — Kill Switch 実装（kill.flag の書込み）
    - trade_monitor.py            — （発注監視関連。コードベース内に依存）
    - alert_manager.py            — アラート送信管理（LINE 等）
  - execution/                     — ExecutionEngine, OrderManager, BrokerFactory 等（発注ロジック）
  - portfolio/
    - portfolio_builder.py        — 候補選定、等重／スコア重み
    - position_sizing.py          — 株数決定、投下額スケーリング
    - risk_adjustment.py          — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py          — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py      — 将来リターン計算、IC、統計サマリ
  - utils/
    - logging_setup.py            — ログの統一セットアップ（Console + 日次ローテート）
    - process_priority.py         — プラットフォームに応じたプロセス優先度設定
  - data/                          — (実行時に使用される) DB やフラグファイル、PID、ログなどの出力先（デフォルト）

（※上記は抜粋／要約です。実際のリポジトリはさらに細分化されたモジュールを含んでいます。）

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では設定項目や LINE 通知先を必ず確認してください。validate_config は本番向けのガードも出力します。
- monitoring は KABUSYS_ENV に関係なく production sqlite_path を使用する設計になっています（監視は本番 DB を常に監視するため）。
- Paper Trading は本番 DB と完全に分離するため、PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI API を利用する処理は API 呼出しで料金が発生します。rate limit / error に対する retry ロジックやフェイルオープン設計は入っていますが、API キーとコスト管理を行ってください。
- ログは logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリが作成できない場合はコンソール出力のみになります。

---

## 参考コマンドまとめ

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
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

必要であれば、README に含める具体的な .env.example のテンプレートや、各モジュール（ExecutionEngine / BrokerFactory / OrderManager 等）の詳細仕様、API 使用例、または CI/デプロイ手順を追加で作成します。どの内容を優先して追加しますか？