# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システムのコア部分を実装した Python パッケージです。  
主に発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（DuckDB ベースのファクター計算）、および AI を用いたニュース分析を含みます。

---

## プロジェクト概要

- 発注ロジックと注文管理を行う ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働状況・注文状況・リスク指標の監視コンポーネント
- DuckDB を用いたファクター計算・研究モジュール（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini）を用いたニュース NLP（センチメント評価）・レジーム検出
- ペーパートレード検証用レポート生成ツール
- 環境設定ウィザードと設定検証 CLI

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注、リスク管理、リコンシリエーション）
  - Paper trading（KABUSYS_ENV=paper_trading）では MockBrokerClient を利用し、DB は分離（data/paper_trading.db）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス存在、データ鮮度の監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、Kill Switch（flag ファイル）対応
  - AlertManager: LINE Push による通知（設定がある場合）
- Portfolio
  - 候補選定、重み付け（等金額・スコア加重）、ポジションサイズ計算
  - セクターキャップ、レジーム乗数などリスク調整ロジック
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン・IC 計算・ファクター統計サマリ
- AI
  - news_nlp.score_news: ニュース記事から銘柄別センチメントを生成して ai_scores に格納
  - regime_detector.score_regime: ETF の MA200 とマクロニュースを組み合わせた市場レジーム判定
- ツール
  - config_setup: .env の対話式生成・更新
  - validate_config: 環境変数 / config/*.yaml の検証
  - paper_verification_report: ペーパートレード DB の検証レポート生成

---

## セットアップ手順

前提：
- Python 3.10+（PEP 604 の union 型記法を使用）
- 仮想環境の作成を推奨

1. リポジトリをクローンして仮想環境を作成・有効化します。
   ```
   git clone <this-repo>
   cd <this-repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストールします（requirements.txt がある場合はそれを使用してください）。主な依存ライブラリ：
   - duckdb
   - psutil
   - openai
   - requests
   - PyYAML（設定検証で YAML のパースを行う場合に必要）
   ```
   pip install duckdb psutil openai requests pyyaml
   ```

3. 環境変数の設定
   - 推奨: 対話式ウィザードで .env を作成
     ```
     python -m kabusys.config_setup
     ```
   - 手動で .env を作成する場合はルートに `.env` を置きます（例は次節を参照）。

4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ（デフォルト: data/）の作成は自動で行われますが、必要に応じて作成してください。

---

## 主要な環境変数（例）

最低限設定が必要なもの：
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live
- OPENAI_API_KEY — OpenAI を使う場合に必要

DB 関連（デフォルト値を変更可能）：
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 default: data/paper_trading.db)

監視関連：
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH — ExecutionEngine の pid ファイル（default: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch の flag ファイル path（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアする (開発用。0/1)

ログ：
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL

例 (.env)
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（起動コマンド例）

- 環境設定ウィザード（.env の対話式生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループの起動（SystemMonitor をポーリングして monitoring DB に記録）
  ```
  python -m kabusys.run_monitoring
  # ポーリング間隔を上書きする例（30秒ごと）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  補足:
  - run_monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使用します。
  - 停止は data/stop_requested.flag を作成するか、Ctrl+C。

- ExecutionEngine の起動（実際の発注を行うエンジン）
  ```
  python -m kabusys.run_execution
  ```
  補足:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH の DB に記録して本番 DB と分離します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID が書かれます。停止は data/stop_requested.flag を作成するか kill でプロセスにシグナルを送る等。

- Paper Trading 検証レポート出力
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  これらは OpenAI API キー（OPENAI_API_KEY）を必要とします。CLI ラッパーは本リポジトリに付属していないため、スクリプトやスケジューラから呼び出してください。

---

## 監視 / Kill Switch の動作概要

- RiskMonitor がドローダウンやポジション上限を検出すると risk_logs に記録し、KillSwitch が条件に応じて data/kill.flag を書き込みます。
- KillSwitch が作成した kill.flag を ExecutionEngine 起動時に検出すると、起動をブロックするか、稼働中のエンジンを停止します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動クリアします（本番環境では設定しないことを推奨）。

---

## ディレクトリ構成

（src/kabusys をルートにした主要ファイル・ディレクトリ）

- kabusys/
  - __init__.py — パッケージ情報（__version__ 等）
  - config.py — 設定読み込み・Settings クラス（.env 自動ロード等）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite による監視 DB スキーマ + 永続化 API
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成 / 管理
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - alert_manager.py — LINE Push 通知
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金割当
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - execution/    （発注エンジン関連のサブパッケージ: broker_factory, execution_engine など）
  - data/         （データ・DB のデフォルト置き場: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, flag/pid ファイル等）

---

## DB（主要テーブル）

監視用 SQLite（monitoring_db.init_monitoring_db により作成）主なテーブル:
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (単一行で集計保存: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

分析用 DuckDB: prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等を想定。

---

## トラブルシューティング / 注意点

- 設定値不足・誤りはまず `python -m kabusys.validate_config` で検出してください。
- OPENAI API を利用する機能はレート制限・一時エラーに対してリトライ処理が入っていますが、APIキーが未設定だと例外になります。
- run_monitoring は MONITOR_POLL_INTERVAL の値が 1 以上の整数であることを想定します（不正値はデフォルト 60 秒にフォールバック）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0、.env の管理・安全性に注意してください。
- psutil を使ったプロセス優先度設定は権限に依存します（AccessDenied などが発生しても警告ログでスキップされます）。

---

## 開発者向けメモ

- Settings クラスは .env の自動読み込みを行います（プロジェクトルート検出: .git または pyproject.toml を基準）。
- .env の自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- テスト時は多くの外部依存（OpenAI 呼び出し、psutil の一部など）をモックできます（ソース内に差し替えの想定ポイントあり）。
- DuckDB を使ったリサーチコードは外部 API に依存せず、prices_daily / raw_financials の内容に依存します。

---

必要に応じて README の補足（運用手順、デプロイ手順、cron / systemd ユニット例、CI テスト方法など）を追加できます。追加して欲しい情報があれば教えてください。