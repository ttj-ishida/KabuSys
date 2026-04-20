# KabuSys

日本株向け自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、マーケットデータ集計・ファクター計算・ポートフォリオ構築・注文実行（本番/ペーパートレード）およびシステム監視機能を含むモジュール群を提供します。OpenAI を使ったニュース NLP、レジーム判定、検証レポート生成ツールも含まれます。

---

## プロジェクト概要

- モジュール設計により、研究（Research）、ポートフォリオ構築（Portfolio）、執行（Execution）、監視（Monitoring）、AI（ニュース NLP / レジーム）などを分離。
- DuckDB を分析 DB、SQLite を監視・注文履歴用 DB として使用。
- 本番実行・ペーパートレードを環境変数 `KABUSYS_ENV` で切り替え（`development` / `paper_trading` / `live`）。
- システム監視（CPU/メモリ/ディスク・データ鮮度・プロセス稼働確認）と、Kill Switch（フラグファイルによる ExecutionEngine 停止）を備える。
- OpenAI を利用したニュースセンチメント評価（ai.news_nlp）、市場レジーム判定（ai.regime_detector）機能を搭載。

---

## 主な機能一覧

- research
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー
- portfolio
  - 候補選定、等配分 / スコア配分、リスク調整（セクター上限、レジーム乗数）
  - 株数決定（単元株丸め、投下資金スケーリング）
- execution
  - ExecutionEngine（注文管理、リスク管理、リコンシリエーション等）
  - Paper trading 用の MockBrokerClient（`KABUSYS_ENV=paper_trading` 時に DB を分離）
- monitoring
  - SystemMonitor（リソース・データ鮮度・プロセス監視）
  - TradeMonitor / RiskMonitor（滞留注文・ドローダウン等の監視）
  - MonitoringEngine（複数 Monitor の統合、アラート・Kill Switch 発動）
  - 永続化層（monitoring DB: system_status / trade_logs / positions / risk_logs / dashboard）
- ai
  - news_nlp: raw_news から LLM（OpenAI）を使って銘柄ごとのセンチメントを算出して保存
  - regime_detector: ETF MA とマクロ記事センチメントを合成して market_regime を算出
- tools
  - Paper Trading 検証レポート生成スクリプト（期間指定でパス/フェイル判定）

---

## 必要条件 / 依存ライブラリ

- Python 3.10+
- 推奨ライブラリ（pip インストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイルの検証を行う場合、任意）
- 標準ライブラリ: sqlite3, threading, datetime, logging, pathlib など

（requirements.txt は本リポジトリに含まれていないため、必要に応じて上記パッケージを手動でインストールしてください）

例:
```
pip install duckdb psutil openai PyYAML
```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development) — 値: development | paper_trading | live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — `paper_trading` 用 DB
- LOG_LEVEL (default: INFO)
- OPENAI_API_KEY (OpenAI を使う機能で必要)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）を上書き、デフォルト 60）
- PAPER_FILL_MODE（ペーパートレードの fill 挙動: instant | partial | never | reject）

注意:
- run_monitoring は「環境にかかわらず」Production の sqlite_path（SQLITE_PATH）を使用します（設計上の制約）。
- run_execution は `KABUSYS_ENV=paper_trading` の場合、`PAPER_TRADING_SQLITE_PATH` を使用して DB を分離します。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. .env の作成（対話ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - 対話で値を入力して `.env` を生成します。
   - 生成後、設定を検証:
     ```
     python -m kabusys.validate_config
     # 警告も fail としたい場合:
     python -m kabusys.validate_config --strict
     ```

5. データディレクトリの作成（必要に応じて）
   - デフォルトでは `data/` と `logs/` が使用されます。スクリプトが自動作成するので手動で作る必要は基本的にありません。

---

## 使い方

### 起動スクリプト

- 監視ループを起動（SystemMonitor をポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 停止方法:
    - Ctrl+C（KeyboardInterrupt）
    - またはプロジェクトルートの `data/stop_requested.flag` を作成するとループ検出で終了します。

- ExecutionEngine を起動（注文執行）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH` に注文履歴等を記録して本番 DB と分離します。
  - 停止フラグ:
    - `data/stop_requested.flag` が存在すると起動しない / 実行中に停止処理が呼ばれます。
  - PID ファイル: `data/execution.pid`（設定によって異なる場合あり）

### 設定ウィザード / 検証

- 対話式で `.env` を生成 / 更新:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（.env と config/*.yaml の存在・基本チェック）:
  ```
  python -m kabusys.validate_config
  ```

### ツール

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` で別 DB を指定可能。

### AI / 研究系関数（ライブラリ呼び出し例）

- ニュース NLP（スコア生成）
  - 呼び出し例（アプリケーションコードから）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")
  - OpenAI API キーが必要（引数 or 環境変数 OPENAI_API_KEY）

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

- ファクター計算等は `kabusys.research` の関数群を直接利用してください。

---

## 動作上の注意 / 実装上のポイント

- run_monitoring は「監視用」プロセスであり、監視 DB（SQLITE_PATH）に対して常に本番パスを使う仕様です。環境による切替は行いません（設計上の意図）。
- run_execution の `paper_trading` モードでは DB を分離します（PAPER_TRADING_SQLITE_PATH）。
- ロギング:
  - 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を使用。
  - ログは stdout と日次ローテートファイル（`logs/<app_name>.log`）に出力されます。`LOG_DIR` 環境変数で変更可能。
- Kill Switch:
  - `data/kill.flag` を書き込むことで ExecutionEngine 停止を要求できます（KillSwitch を通じた評価ロジックに従う）。
  - `KILL_FLAG_CLEAR_ON_START` が `1` の場合、起動時に kill.flag を自動クリアする挙動があるため、本番環境では `0` を推奨します。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成し、簡単なカラム追加（マイグレーション）ロジックを含みます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）処理
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続化レイヤ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
- execution/               — Execution エンジン関連（broker_factory, order_manager 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

プロジェクトルートに利用される補助ディレクトリ:
- data/    — デフォルトで DB・フラグファイル・PID を格納
- logs/    — ログファイル（app_name.log）

---

## よくある運用フロー（例）

1. `.env` を `python -m kabusys.config_setup` で作成
2. `python -m kabusys.validate_config` で設定検証
3. DuckDB にマーケットデータ・raw_news 等を投入（外部スクリプト / ETL）
4. 研究用途に `kabusys.research` の関数を利用してファクターを算出
5. Execution を `python -m kabusys.run_execution` で起動（必要に応じて systemd / supervisor で管理）
6. Monitoring を `python -m kabusys.run_monitoring` で起動し稼働監視・Kill Switch 評価を行う

---

## 参考 / 補足

- OpenAI を利用する機能（news_nlp, regime_detector）は API 呼び出し失敗時にフェイルセーフを設けていますが、API キーの管理・コストに注意してください。
- 本 README はコードベース（src/kabusys/*.py）を元にまとめています。実運用では config/*.yaml や外部 ETL/データ投入処理が必要です。

---

必要であれば、この README をベースに「デプロイ手順」「systemd ユニット例」「テスト手順」「CI 設定」などの追加ドキュメントも作成できます。どの項目を優先しますか？