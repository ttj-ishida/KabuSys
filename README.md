# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ群・起動スクリプト・ユーティリティ群）。

この README はコードベース（src/kabusys 以下）を元にした概要・セットアップ・使い方・ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関連するコンポーネントをまとめたシステムです。主な責務は次のとおりです。

- データパイプラインや DuckDB ベースのリサーチ（ファクター計算、特徴量探索）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数）
- 実行エンジン（ExecutionEngine）とブローカー抽象（paper_trading 用の MockBroker を含む）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor、Kill Switch、アラート）
- AI 補助（ニュースの NLP スコアリング、レジーム判定に OpenAI を使用）
- 開発支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

設計方針として、ロジックを純粋関数化してテストしやすくし、DB 書き込みは明確に分離しています。OpenAI や外部 API 呼び出しはフェイルセーフ（失敗時は安全にフォールバック）を意識して実装されています。

---

## 主な機能一覧

- 環境設定の対話式ウィザード（config_setup）
- 設定検証 CLI（validate_config）
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBroker を利用し data/paper_trading.db に記録
- 監視用ポーリングループ起動スクリプト（run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は常に本番用の sqlite_path を参照
- 監視 DB 層（monitoring_db）と複数の Monitor（system/trade/risk）
- Kill Switch（data/kill.flag による ExecutionEngine 停止シグナル）
- ポートフォリオ構築ユーティリティ（候補選定 / 等重・スコア重み / 単元丸め / 集約キャップ）
- 研究用モジュール（ファクター計算、IC、将来リターン等）
- AI モジュール
  - news_nlp: ニュース記事を集約して OpenAI に送信し銘柄ごとにスコア化し ai_scores に書込
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントを合成して市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB から成功率やレイテンシ等の検証レポートを生成

---

## 必要な依存関係

（代表的なもの。環境に応じてバージョンを固定してください）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml のパース検証を行う場合）
- その他：標準ライブラリ（sqlite3 等）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ requirements.txt がある場合はそちらを使用してください（本リポジトリでは提供されていません）。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb psutil openai PyYAML
   ```

2. .env ファイル作成（対話式ウィザード推奨）

   ```bash
   python -m kabusys.config_setup
   ```

   ウィザードは `.env`（デフォルト）を生成／更新します。J-Quants や kabuステーションの認証情報は必須です。

3. 設定検証

   ウィザードの後、設定の整合性を検証します。

   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリの確認（デフォルト）

   - SQLite（監視用）: data/monitoring.db（Settings.sqlite_path）
   - Paper Trading DB: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）
   - DuckDB: data/kabusys.duckdb
   - ログ: logs/（デフォルト。権限に注意）

   必要に応じて .env でパスを上書きしてください。

5. OpenAI を使う場合

   環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に api_key を渡します。

---

## 使い方（起動例）

- 実行エンジン（ExecutionEngine）を起動

  - 本番・開発モード（環境変数 KABUSYS_ENV による）

  ```bash
  # 例: development (発注なし)
  export KABUSYS_ENV=development
  python -m kabusys.run_execution

  # 例: paper_trading（MockBroker を使用）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  - 停止シグナルは `data/stop_requested.flag`（run_execution はこれを監視）や `data/kill.flag`（KillSwitch）で制御されます。PID ファイルは `data/execution.pid`（デフォルト）に出力します。

- 監視ループ（Monitoring）を起動

  ```bash
  # MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定可能（デフォルト 60）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  監視は SystemMonitor / TradeMonitor / RiskMonitor を呼び、必要に応じて Kill Switch を発動します。監視の DB 初期化は起動時に行われます（init_monitoring_db）。

- .env の対話式作成（再掲）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（再掲）

  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート

  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB 指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連ユーティリティ（Python から呼び出し）

  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

  いずれも DuckDB 接続（duckdb.connect(...) の返り値）を受け取り、内部で OpenAI クライアントを用いて結果をテーブルへ書き込みます。API キーは引数か環境変数 `OPENAI_API_KEY` を参照します。

---

## 主要な環境変数

- 必須（主に Settings 参照で例示）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 推奨 / オプション
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
  - LOG_LEVEL（DEBUG/INFO/...）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート用）
  - OPENAI_API_KEY（AI 機能使用時）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）
  - PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject）
  - KILL_FLAG_CLEAR_ON_START（本番での自動クリアを抑止するため通常は 0）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env ロードを無効化）

Settings モジュールにほかの getter があり、詳細は `src/kabusys/config.py` を参照してください。

---

## 運用メモ / 注意点

- run_monitoring は Monitoring 用 SQLite DB を初期化します（init_monitoring_db）。monitoring は環境にかかわらず本番 sqlite_path を使用する設計になっています。運用時はパスに注意してください。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使います。本番 DB と分離されます。
- ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソールのみの出力になります。
- OpenAI 等の API 呼び出しはリトライやフォールバックロジックを備えていますが、料金や API 制限には注意してください。
- Kill Switch が発動すると `data/kill.flag` が作成されます。これを手動でクリアすることで再起動できるようになります（設定で自動クリアも可能）。

---

## ディレクトリ構成（抜粋）

```
src/kabusys/
├─ __init__.py
├─ config.py                   # 環境変数・設定管理
├─ config_setup.py             # .env ウィザード（対話式）
├─ validate_config.py          # 設定検証 CLI
├─ run_execution.py            # ExecutionEngine 起動スクリプト
├─ run_monitoring.py           # SystemMonitor ポーリングループ起動スクリプト
├─ tools/
│  └─ paper_verification_report.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py              # ニュース NLP（OpenAI）によるスコアリング
│  └─ regime_detector.py       # 市場レジーム判定（MA200 + マクロニュース）
├─ monitoring/
│  ├─ monitoring_db.py         # SQLite persistence layer（init / CRUD）
│  ├─ system_monitor.py
│  ├─ trade_monitor.py         # （該当ファイルあり。監視ロジック）
│  ├─ risk_monitor.py
│  ├─ kill_switch.py
│  └─ monitoring_engine.py
├─ execution/                   # ExecutionEngine, OrderManager, BrokerFactory 等
│  └─ ...
├─ portfolio/                   # portfolio_builder, position_sizing, risk_adjustment
│  ├─ __init__.py
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/                    # factor_research, feature_exploration
│  └─ ...
├─ utils/
│  ├─ logging_setup.py
│  └─ process_priority.py
└─ data/                        # 実行時に生成される（DB、pid、kill/stop フラグ等）
```

（上記は主要ファイルの抜粋です。詳細は `src/kabusys` 以下のソースをご確認ください。）

---

## 開発・テストのヒント

- モジュールは可能な限り純粋関数（副作用を持たない計算）に分離されています。unit test が書きやすい設計です。
- AI モジュールや外部 API を使う部分は API 呼び出し関数（例: _call_openai_api）をパッチ（mock）しやすい設計になっています。
- .env 自動ロードは Settings モジュールの起動時に行われます。テストで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 参考コマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

この README はコードベースの主要点をまとめたものです。詳細な実装や API の使い方は各モジュール（src/kabusys 以下）の docstring を参照してください。必要であれば README にコマンド例や運用手順の追記、設計ドキュメント（PortfolioConstruction.md 等）の要約を追加します。どの情報を追加希望か教えてください。