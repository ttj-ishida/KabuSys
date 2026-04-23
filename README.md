# KabuSys

日本株向け自動売買システムのリポジトリ（実験 / 研究 / ペーパートレード対応）。  
この README はコードベース（src/kabusys）を対象に、概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群で構成されています：

- リサーチ（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 実行エンジン（ExecutionEngine）／注文管理（OrderManager）／リスク管理
- 監視（System / Trade / Risk のモニタリング、Kill Switch）
- AI 支援（ニュース NLP によるセンチメント、レジーム判定）
- ペーパートレード用検証・レポート生成ツール

設計方針の主なポイント：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV により切替）
- DuckDB を使った分析用クエリ、SQLite を使った監視・ログ永続化
- OpenAI（gpt-4o-mini）を利用したニュース解析（任意）
- .env による設定管理、対話式ウィザード・検証スクリプトあり

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成/更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: python -m kabusys.validate_config
- 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db を利用
- 監視ループ起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御
- 監視モジュール群: SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch
- データ永続化（監視用）: MonitoringDB （SQLite のテーブル初期化 / 操作）
- ポートフォリオ構築ユーティリティ（等ウェイト・スコア重み・セクター制約・ポジションサイズ）
- リサーチ（ファクター計算、forward returns、IC、統計要約）
- AI モジュール:
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- ツール: ペーパートレード検証レポート generator（python -m kabusys.tools.paper_verification_report）

---

## 前提（Prerequisites）

- Python 3.10 以上（コード内の型ヒントにより Union 表記 `X | Y` を使用）
- 推奨／必要パッケージ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の内容検証を行う場合に任意）
- OS によってはプロセス優先度設定で管理者権限が必要な場合があります。

（プロジェクトには requirements.txt が含まれていない想定のため、必要なパッケージを手動でインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化し依存をインストール（上記参照）

3. .env を作成する（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは .env の生成・更新を手助けします。

4. 設定検証を実行
   ```bash
   python -m kabusys.validate_config
   # 警告を fail として扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. （初回）ログディレクトリ・DB 用ディレクトリの作成
   - デフォルトの DB/ログパスは .env に無ければ `data/` と `logs/`。スクリプトが起動時に自動生成しますが、権限に注意してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / デフォルト:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: INFO（DEBUG 等指定可）
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用
- OPENAI_API_KEY: OpenAI を使う場合は必須（AI 機能用）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 用、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

例 (.env の抜粋)
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
```

---

## 起動と使い方

- 設定ウィザード（.env 作成/更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- 実行エンジン（ExecutionEngine）起動
  - 通常起動（本番 / 開発 / ペーパーは KABUSYS_ENV で切替）
  ```bash
  # ペーパートレードで起動する例
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - ペーパートレード時は専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離します。
  - 起動時、`data/stop_requested.flag` が存在すると起動を行わず終了します。
  - 実行中は `data/execution.pid` に PID を書きます。

- 監視ループ起動
  ```bash
  # ポーリング間隔を環境変数で制御（秒）
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - モニタは常に本番用の sqlite_path を使用（環境にかかわらず）。
  - 停止は `data/stop_requested.flag` の作成で行います（run_execution と同様）。
  - 監視が KillSwitch 条件を満たすと `data/kill.flag` を作成し ExecutionEngine に停止信号を送ります。

- ペーパートレード検証レポート（ツール）
  ```bash
  # デフォルト DB path: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```

- AI 機能（プログラムから呼び出す例）
  - ニューススコアリング
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, date(2026, 4, 15), api_key="sk-...")
    print(f"written scores: {written}")
    ```
  - レジーム判定
    ```python
    from kabusys.ai.regime_detector import score_regime
    written = score_regime(conn, date(2026, 4, 15), api_key="sk-...")
    ```

---

## 停止 / キルスイッチの仕組み

- 停止フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring のポーリングで監視され、存在するとループを終了します。
  - data/kill.flag — KillSwitch が書き込むファイル。ExecutionEngine は起動／実行中にこのファイルを見つけると停止します。
- KillSwitch は次のような条件で発動する設計です：
  - ドローダウンが閾値を超えた場合（デフォルト 10%）
  - 保有銘柄数が上限を超えた場合
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアしますが、本番環境では推奨されません。

---

## ログ

- デフォルトのログディレクトリ: logs/
- setup_logging() が stdout と日次ローテートファイルハンドラ（logs/<app>.log）を設定します。
- 環境変数 LOG_DIR で出力先を変更可能。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御。

---

## ディレクトリ構成（概要）

（src/kabusys 配下の主要ファイル／ディレクトリを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（自動 .env 読み込み）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py            — SQLite のテーブル作成 + DB 操作ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
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
    - news_nlp.py                 — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py          — マーケットレジーム判定（MA + マクロセンチメント）
  - monitoring/ (上記に含む)
  - tools/
    - paper_verification_report.py

- その他（プロジェクトルート）
  - .env.example
  - config/*.yaml                  — 各種テンプレート（system_config.yaml 等）
  - data/                          — データベース・フラグファイル等（自動生成）
  - logs/                          — ログファイル（自動生成）

---

## 開発・運用時の注意点

- KABUSYS_ENV の値は厳格（development / paper_trading / live）。live 設定時は特に注意して運用を行ってください。
- OpenAI API を利用する機能は API キーが必須です。API 失敗時は安全側フォールバック（例: スコア 0.0）する実装ですが、期待どおりの更新が行われない可能性があります。
- process priority / CPU affinity の設定はプラットフォーム依存です。権限不足で設定が失敗する場合は警告を出して継続します。
- DuckDB / SQLite のパスは .env で変更可能。ペーパートレード時は data/paper_trading.db を使用することを確認してください。
- デバッグや CI 用に自動 .env ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 参考コマンド一覧

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- 実行エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要があれば README にサンプル .env、より詳細な実行例（systemd サービス定義、Dockerfile、テストの書き方等）や各モジュールの API 使用例を追加できます。どの情報を優先して追加しましょうか？