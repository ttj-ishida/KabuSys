# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ / 実行スクリプト / モニタリング / 研究用ユーティリティ）。  
このリポジトリは戦略の研究、ポートフォリオ構築、発注エンジン、監視・アラート、AI を用いたニュース解析などのコンポーネントを含みます。

---

## 概要

- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム調整）
- ExecutionEngine（ブローカークライアントを介した発注、リスク管理、リコンシリエーション）
- Monitoring（システム状態、注文滞留、ドローダウン等の監視、LINEによるプッシュ通知、kill flag）
- AI モジュール（ニュースのセンチメント解析、マクロニュースに基づく市場レジーム判定。OpenAI API を利用）
- Research（ファクター計算、将来リターン・IC 計測、特徴量探索）
- ツール（Paper Trading 検証レポートの生成、Streamlit ベースの監視ダッシュボード）

---

## 主な機能一覧

- portfolio:
  - 候補選定（select_candidates）
  - 等重・スコア重みの計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限フィルタ（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）

- execution:
  - OrderManager / OrderRepository による注文ライフサイクル管理
  - ブローカー抽象化（BrokerClientFactory）
  - リコンシリエーション（Reconciler）

- monitoring:
  - SystemMonitor（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文・約定異常監視）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（kill.flag による停止シグナル）
  - AlertManager（LINE Push）
  - MonitoringEngine（複数モニタのポーリング統合）
  - Streamlit ダッシュボード

- ai:
  - ニュースセンチメントスコアリング（news_nlp.score_news）
  - マクロニュース + ETF MA 指標による市場レジーム判定（regime_detector.score_regime）

- research:
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算 / IC 計算 / 統計サマリー

- tools:
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 必要条件（推奨）

- Python 3.9+
- SQLite（標準ライブラリ）
- 主要 Python パッケージ（例）:
  - duckdb
  - psutil
  - openai (OpenAI SDK)
  - requests
  - streamlit

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```
（requirements.txt がある場合は `pip install -r requirements.txt` を推奨）

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. Python 仮想環境を作成して依存パッケージをインストール
3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（既存 OS 環境変数は保護）。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
4. 必須環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
   - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE アラートを使用する場合
5. DB のデフォルトパス（変更可）
   - DuckDB: data/kabusys.duckdb (環境変数: DUCKDB_PATH)
   - Monitoring SQLite: data/monitoring.db (環境変数: SQLITE_PATH)
   - Paper trading SQLite: data/paper_trading.db (環境変数: PAPER_TRADING_SQLITE_PATH)

注意:
- `.env` のパースは独自実装（コメント、クォート、export プレフィックス等に対応）されています。
- Settings モデルにより `KABUSYS_ENV`（development / paper_trading / live）やログレベル等が検証されます。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、発注は MockBrokerClient を使用し、別 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離されます。
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で利用）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabu API 用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のモック約定モード（instant / partial / never / reject、デフォルト "instant"）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag パス（デフォルト data/kill.flag）

---

## 起動・使い方

各スクリプトはパッケージとしてモジュールを実行できます。

- ExecutionEngine 起動（本番 / paper_trading 自動選択）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH の DB に記録します。
  - 起動直後にプロセス優先度を "high" に設定します（プラットフォームの制約で失敗する場合は警告ログ）。

- Monitoring の単体ポーリングループ起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - 監視ログは常に本番用 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。

- Streamlit ダッシュボード（ローカルで監視 DB を読み取り専用で表示）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成ツール
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（プログラム呼び出し例）
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。未設定時は例外。

- Research API（プログラム内で）
  - モメンタム等: kabusys.research.calc_momentum(duckdb_conn, target_date)
  - 将来リターン: kabusys.research.calc_forward_returns(duckdb_conn, target_date)

---

## 注意事項 / 実装上の挙動

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）が探索され、.env → .env.local の順で読み込まれます（OS 環境変数は保護される）。
  - 無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

- Monitoring DB 初期化:
  - init_monitoring_db(conn) は冪等でテーブル・インデックスを作成します。既存 DB に対する軽微なマイグレーション（列追加）も含まれます。

- Execution と Monitoring の DB 分離:
  - paper_trading 環境では execution は paper_trading DB を使用することで本番データと分離します。monitoring は常に sqlite_path（本番 DB）を使う設計に注意してください。

- OpenAI API 呼び出し:
  - Rate limit / ネットワークエラー / 5xx に対して指数バックオフで再試行する実装になっていますが、API キー未設定時は呼び出し側で例外になります。
  - レスポンスのバリデーションや JSON 抽出を行い、失敗時はフェイルセーフ（デフォルト値やスキップ）で動作します。

- プロセス優先度・CPU affinity:
  - set_process_priority / set_cpu_affinity は psutil を利用して OS 毎の差分を吸収します。権限不足などで設定できない場合は警告ログになります。

---

## ディレクトリ構成

以下は src/kabusys 以下のおおまかな構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定読み込み / Settings
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト

  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - risk_adjustment.py          — セクター上限・レジーム乗数
    - position_sizing.py          — 株数算出（丸め・スケーリング）

  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - ...                         — ブローカー API 抽象等（実装有り）

  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（テーブル定義・MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py

  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py          — マクロ + ETF MA によるレジーム判定

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - process_priority.py         — process 限界設定ユーティリティ

（ファイルは抜粋で示しています。実際のツリーにはさらにモジュールが含まれます）

---

## 開発メモ / テスト時のヒント

- DB をローカルで初期化したい場合は、Settings のデフォルトパスに空のファイルを作成するだけで起動時にテーブルが作られます（init_monitoring_db を通す設計）。
- Paper Trading（検証）では PAPER_FILL_MODE の変更により約定挙動を切り替えられます（instant / partial / never / reject）。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くため、MonitoringEngine を別プロセスで実行中でも安全に参照できます（URI モードで read-only を指定）。
- OpenAI 呼び出し部分はテストしやすいように内部の API 呼び出し関数を差し替え可能（モック化可能）に実装されています。

---

これで README の主要項目は網羅しています。必要であれば「環境変数の完全一覧」「CLI の詳細なオプション」「実際の依存パッケージバージョン」「動作フロー図」などを追加できます。どの情報を優先して追加しますか？