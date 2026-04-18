# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリを含みます。市場データの集計・ファクター計算、ポートフォリオ建成、発注エンジン、監視（Monitoring）、および AI を用いたニュースセンチメント/レジーム判定などの機能を備えます。

---

## プロジェクト概要

KabuSys は以下の目的で設計されたモジュール群です。

- DuckDB / SQLite を用いたデータ処理と永続化
- ファクター計算（モメンタム、バリュー、ボラティリティ等）
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター制限）
- ExecutionEngine による発注ロジック（paper / live 切替対応）
- 監視サブシステム（システム稼働、注文モニタ、リスク監視、Kill Switch）
- AI モジュール（OpenAI を用いたニュースセンチメント/レジーム判定）
- ユーティリティツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計方針の一部：
- 本番 DB（monitoring.db）と paper_trading DB を明確に分離
- ルックアヘッドバイアス対策（日時参照の取り扱いに注意）
- フェイルセーフ（外部 API 失敗時は安全側のフォールバック）

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話生成）
  - `kabusys.config_setup.run_wizard` / `python -m kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の事前チェック）
  - `python -m kabusys.validate_config`
- Execution 起動スクリプト（本番 / ペーパートレード切替）
  - `python -m kabusys.run_execution`
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用、DB は `data/paper_trading.db`
- Monitoring 起動スクリプト（ポーリングで各監視を実行）
  - `python -m kabusys.run_monitoring`
  - MONITOR_POLL_INTERVAL 環境変数で間隔指定（デフォルト 60 秒）
- 監視モジュール
  - SystemMonitor（プロセス死活、CPU/メモリ/Disk、データ鮮度検査）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン、ポジション上限）
  - KillSwitch（条件一致で `data/kill.flag` を書き込み、Execution を停止）
  - MonitoringDB（SQLite を使った永続化 API）
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算）
  - 等配分 / スコア加重 / リスクベース配分
  - セクター制限・レジーム乗数
- リサーチ（DuckDB を用いたファクター計算・将来リターン・IC 等）
  - `kabusys.research.calc_*`
- AI モジュール（OpenAI）
  - ニュースセンチメント：`kabusys.ai.news_nlp.score_news`
  - レジーム判定：`kabusys.ai.regime_detector.score_regime`
- ツール
  - Paper Trading 検証レポート生成：`python -m kabusys.tools.paper_verification_report`

---

## セットアップ手順

前提:
- Python 3.9+（typing の仕様に合わせてください）
- 必要な外部パッケージ（例: duckdb, psutil, openai, PyYAML（任意））をインストールしてください。

推奨手順（例: 仮想環境）:

1. リポジトリをクローンして移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb psutil openai
   # 設定検証で YAML 検証を有効にする場合:
   pip install PyYAML
   ```

4. .env の作成（対話ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   必須環境変数（最低限設定が必要）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

5. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も fail にしたい場合:
   python -m kabusys.validate_config --strict
   ```

重要な環境変数の説明（主なもの）:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパー発注時の約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

---

## 使い方

### 1) 環境を生成・編集
対話式ウィザードで .env を作成:
```
python -m kabusys.config_setup
```

ウィザードで作成した .env を編集したら、設定検証を実行:
```
python -m kabusys.validate_config
```

### 2) Execution（発注エンジン）を起動
通常起動:
```
python -m kabusys.run_execution
```
挙動:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し DB は `data/paper_trading.db` に記録（本番 DB と分離）
- 起動時に `data/stop_requested.flag` が存在すると起動を行いません
- 実行中に `data/stop_requested.flag` が作成されるとエンジンは停止します
- プロセスは起動直後にプロセス優先度を "high" に設定しようとします（権限や OS に依存）

停止方法（安全）:
- Execution を止めたい場合、監視側が kill.flag を書く（KillSwitch）か、手動で `data/stop_requested.flag` を作成してください。

### 3) Monitoring（監視）を起動
```
python -m kabusys.run_monitoring
```
オプション・環境変数:
- MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。
- Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視ログを記録します（`SQLITE_PATH` またはデフォルト `data/monitoring.db`）。

停止:
- `data/stop_requested.flag` を作成すると監視ループは次回ポーリングで終了します。

### 4) Paper Trading 検証レポート
指定期間の paper_trading DB を集計してレポートを標準出力に出します。
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを直接指定する場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
デフォルト DB: `data/paper_trading.db`（または環境変数 `PAPER_TRADING_SQLITE_PATH`）

### 5) AI 機能（ニュース NLP / レジーム判定）
- ニュースセンチメントのバッチ処理:
  - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - OpenAI API キーが無いと ValueError が発生します（api_key 引数または環境変数 `OPENAI_API_KEY`）
- レジーム判定:
  - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
- 注意:
  - 両方とも外部 API 呼出しに依存するため、実行前に `OPENAI_API_KEY` を設定してください
  - API はリトライやフェイルセーフを備えていますが、レート制限や API 料金に注意してください

---

## 停止 / Kill Switch の仕組み

- `KillSwitch` は監視ロジックの一部で、一定条件（例: ドローダウン超過、保有銘柄数上限超過）で `data/kill.flag` を書き込みます。
- ExecutionEngine は起動時や稼働中に kill.flag を検出すると安全に停止するよう設計されています（monitoring と連携）。
- また、起動/停止の外部操作用に `data/stop_requested.flag` を置くことで run scripts（run_monitoring/run_execution）を終了させることができます。

設定によっては起動時に kill.flag を自動でクリアする (`KILL_FLAG_CLEAR_ON_START=1`) こともできますが、本番では 0 を推奨します。

---

## ディレクトリ構成（主なファイル/モジュール）

以下はソースツリー（src/kabusys）内の主な構成です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — Execution 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 発注エンジン関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 & 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信のためのマネージャ）
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
  - data/                    — データファイル（デフォルトパス: data/*.db / .flag / .pid）
  - tools/
    - paper_verification_report.py

（実際のファイル群は src/kabusys 以下を参照してください）

---

## 依存関係・注意点・トラブルシューティング

- 必須パッケージ: duckdb, psutil, openai（AI 機能を使う場合）
- PyYAML がない場合、`validate_config` は YAML の中身検証をスキップします（存在チェックは行います）。
- OpenAI を用いる機能は `OPENAI_API_KEY` が必要。API のレート制限やコストに注意してください。
- `set_process_priority` は OS 権限やプラットフォーム依存のため、失敗する場合は警告ログを出してスキップします（AccessDenied 等）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、内部で空チェックが入っています。
- データ鮮度チェックは DuckDB の `prices_daily` を参照します。初期データ投入を忘れないでください。

---

## 開発メモ / 既知の設計ポイント

- Paper Trading は本番データベースから分離されています（`PAPER_TRADING_SQLITE_PATH`）。
- AI モジュールは過度に統合せず、エラーハンドリング（リトライ、フォールバック）を重視しています。
- Monitoring は `MONITOR_POLL_INTERVAL` で調整可能。0 以下の指定は無効でデフォルトへフォールバックします。
- ファイルフラグ（`data/stop_requested.flag`, `data/kill.flag`）を利用してプロセス間の単純なシグナルを実現しています。

---

必要があれば、README をプロジェクト固有のセットアップ手順（systemd ユニット、Dockerfile、CI/CD 設定など）に合わせて追記します。追加で記載したい内容（例: 実行例のログ出力例、API レート制限のベストプラクティス、DB スキーマ詳細など）があれば教えてください。