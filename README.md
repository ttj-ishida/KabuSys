# KabuSys

日本株自動売買システムのコードベース（軽量版ドキュメント）。  
本 README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ基盤です。主な要素は以下です。

- Execution（発注エンジン）: 実際の発注処理およびペーパートレード（分離された DB）をサポート。  
- Monitoring（監視）: システム状態・発注状況・リスク指標を収集し、Kill Switch（停止フラグ）やアラート発行を行う。  
- Portfolio construction: 候補選定、重み計算、ポジションサイズ計算、セクター制限等のロジック（純粋関数）。  
- Research: DuckDB を用いたファクター計算、将来リターン・IC 計算、統計サマリ等。  
- AI（OpenAI）連携: ニュース NLP によるセンチメントスコアリングや市場レジーム判定。  
- ユーティリティ: 設定管理、対話式 .env ウィザード、設定検証、ログ設定、プロセス優先度設定等。  
- ツール: ペーパートレード検証レポート生成スクリプト等。

設計方針として、発注ロジックとデータ解析・研究ロジックは分離され、本番 DB や API への不必要なアクセスを避ける実装になっています。

---

## 機能一覧（抜粋）

- 環境設定ウィザード（.env を対話式に生成）
- 設定検証 CLI（.env と config/*.yaml の検査）
- ExecutionEngine（本番・ペーパートレードの両対応、paper_trading は専用 SQLite に記録）
- MonitoringEngine（SystemMonitor / TradeMonitor / RiskMonitor を束ねて定期実行）
- Monitoring DB（SQLite ベースの永続化レイヤ、system_status / trade_logs / risk_logs / positions / dashboard）
- Portfolio モジュール（銘柄選定、重み算出、ポジションサイズ計算、セクターキャップ）
- Research モジュール（モメンタム／ボラティリティ／バリュー等のファクター計算、IC・統計）
- AI モジュール（news_nlp: ニュースを LLM でスコアリング、regime_detector: 市場レジーム判定）
- ツール: Paper Trading 検証レポート生成（期間指定可能）

---

## 必要条件（推奨）

- Python 3.9+
- pip（仮想環境を推奨）
- 主な依存パッケージ（プロジェクトに requirements.txt があればそちらを使用してください）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config YAML の検証を行う場合）
- SQLite（標準で Python に同梱）
- ネットワークアクセス（API を使用する場合）

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし、作業ディレクトリへ移動

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（例）

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（プロジェクトに requirements.txt が無ければ下記を参照）

   ```bash
   pip install duckdb psutil openai pyyaml
   ```

4. データディレクトリ作成（ログ・DB・フラグファイル用）

   ```bash
   mkdir -p data logs
   ```

5. 環境変数 (.env) を作成する  
   対話式ウィザードを使うと便利です:

   ```bash
   python -m kabusys.config_setup
   ```

   必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主要な環境変数の例（.env）
   ```
   KABUSYS_ENV=development            # development | paper_trading | live
   JQUANTS_REFRESH_TOKEN=your_token
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   OPENAI_API_KEY=sk-...
   PAPER_FILL_MODE=instant           # paper_trading 用（instant|partial|never|reject）
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   KILL_FLAG_CLEAR_ON_START=0
   ```

6. （オプション）設定検証

   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いになります
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（実行方法）

### 1) Execution（発注エンジン）の起動

- 本番 / 開発 / ペーパートレードは環境変数 KABUSYS_ENV で切り替えます。
- KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ書き込みます。

起動:

```bash
python -m kabusys.run_execution
```

挙動ポイント:
- 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
- 実行中、停止させたい場合は data/stop_requested.flag を作成するか kill.flag を書き込むなどの仕組みを用います（monitoring 側で kill.flag を作成することが想定されています）。
- 実行中は data/execution.pid が使用されます。

### 2) Monitoring（監視）の起動

起動:

```bash
python -m kabusys.run_monitoring
```

挙動ポイント:
- デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
- Monitoring は KABUSYS_ENV の値にかかわらず `Settings.sqlite_path`（デフォルト: data/monitoring.db）を使用します（監視ログは常に本番 DB を参照）。
- 停止: data/stop_requested.flag を作成するとループが終了します。

### 3) Paper Trading 検証レポート

ペーパートレード用 DB（デフォルト: data/paper_trading.db）を解析して検証レポートを生成します。

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを直接指定する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

出力: 稼働率、注文成功率、送信率、レイテンシ（P95 など）を表示し PASS/FAIL を判定します。

### 4) AI 関連（ニュース NLP / レジーム判定）

OpenAI API キーは環境変数 `OPENAI_API_KEY` または関数引数で指定します。モジュール提供 API:

- ニューススコアリング:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（duckdb.connect(...)）を渡し、target_date を指定して ai_scores テーブルへ書き込みます。

- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意点:
- API 呼び出しに失敗した場合はフェイルセーフ（多くの箇所でゼロフォールバック等）により処理を継続する設計です。
- OpenAI の使用にはクォータ/課金が発生します。

---

## 主要設定（環境変数）

主な環境変数（抜粋）:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 用）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 本番起動時に kill.flag を自動クリアするか（0/1。production では注意）

---

## ログ

- 共通のログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を各起動スクリプトで使用しています。  
- デフォルトでログは stdout と `logs/<app_name>.log`（日次ローテーション、30 日保持）に出力されます。`LOG_DIR` でディレクトリを変更可能です。

---

## 停止 / Kill Switch

- 停止フラグ: data/stop_requested.flag — 起動ループを正常に終了させるためのフラグ（run_execution / run_monitoring がチェック）。
- Kill Switch: monitoring 側の判定で `data/kill.flag` を書き込むと ExecutionEngine 停止を誘発可能。`KillSwitch` クラスが管理します。
- PID ファイル: data/execution.pid（ExecutionEngine 用）

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なモジュールとその役割のツリーです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings の管理、自動 .env ロード
  - config_setup.py        — 対話式 .env ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py     — ログ設定ユーティリティ
    - process_priority.py  — プロセス優先度 / CPU affinity 設定
  - execution/             — 発注エンジン関連（BrokerFactory 等） ※詳細は該当フォルダ
  - monitoring/
    - monitoring_db.py     — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI 連携）
    - regime_detector.py    — 市場レジーム判定（OpenAI 連携）
  - tools/
    - paper_verification_report.py

（注）実際のツリーはこの README に示した以外のファイル / サブモジュールを含む場合があります。

---

## 開発・拡張メモ

- DuckDB を解析用に使用しており、prices_daily / raw_financials / raw_news 等のテーブルを前提とした実装が多数あります。データの投入パイプライン（data pipeline）は別モジュールに実装される想定です（get_last_price_date 等の参照）。
- AI 周りは OpenAI SDK（chat completions）を利用しており、レスポンスの堅牢な検証とリトライ/バックオフを組み込んでいます。API のエラーは多くの箇所でフェイルセーフ（0 にフォールバック・スキップ）されています。
- portfolio / position sizing や risk adjustment の関数群は純粋関数として設計され、モジュール単体でユニットテストしやすくなっています。

---

## よくある質問（FAQ）

- Q: ペーパートレードと本番 DB は分離されていますか？  
  A: はい。KABUSYS_ENV=paper_trading のとき、Execution は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用します。Monitoring は常に `SQLITE_PATH` を参照します。

- Q: Monitoring のポーリング間隔を変えたいです。  
  A: 環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書きできます。無効な値や 0 以下はデフォルト 60 秒にフォールバックします。

- Q: OpenAI を使いたくない／キーがない場合は？  
  A: AI 機能（news_nlp, regime_detector）は OpenAI API キーが必須です。キー未設定時はそれらの関数を呼ぶと例外になります。ただし、その他機能（Execution / Monitoring / Research の SQL ベース計算）は OpenAI なしで動作します。

---

## 連絡・貢献

小さな修正や機能追加は Pull Request をお願いします。ドキュメント改善やテスト追加も歓迎します。

---

README に記載の内容はコードベースの主要ポイントを抜粋したものです。各モジュールの詳細やパラメータについては該当ファイルの docstring / コメントを参照してください。