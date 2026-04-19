# KabuSys

日本株自動売買システムのサンプル実装（ライブラリ / 実行スクリプト群）。  
このリポジトリは戦略のリサーチ・ポートフォリオ構築・実行エンジン・監視・AI ベースのニュース解析などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次の関心事を分離して実装した自動売買フレームワークです。

- データ解析 / リサーチ（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- 実行エンジン（発注、リスク管理、注文管理、ペーパートレード対応）
- 監視（システム稼働、注文監視、リスク監視、Kill Switch）
- AI 支援（ニュースの NLP によるセンチメント評価、レジーム判定）
- ユーティリティ（設定ウィザード、検証、ログ設定）

設計方針として「DB を直接叩く」「純粋関数で計算」「本番・ペーパートレードの分離」「ルックアヘッド回避」を重視しています。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード（config_setup）
  - 起動前チェック（validate_config）

- 実行 / 発注
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し、data/paper_trading.db に記録

- 監視
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、プロセス生存監視）
  - TradeMonitor（滞留注文、約定異常など）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - MonitoringEngine（各 Monitor のポーリング統括）
  - Kill Switch（条件に合致すると data/kill.flag を書き込み Execution を停止）

- リサーチ / ファクター計算
  - momentum / volatility / value ファクター計算（DuckDB を使用）
  - 特徴量探索・IC 計算・統計サマリー

- AI（OpenAI）
  - ニュース記事のセンチメント評価（news_nlp）
  - マクロ + ETF MA200 に基づく市場レジーム判定（regime_detector）

- ツール
  - Paper Trading の検証レポート生成（tools.paper_verification_report）

---

## 前提 / 必要ソフトウェア

- Python 3.10+
  - Union 型（X | Y）などの構文を使用しているため Python 3.10 以上を推奨します。
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - pyyaml（設定ファイルの検証時に利用。必須ではない）
- SQLite（標準ライブラリ sqlite3 を使用）
- （任意）kabuステーション等のブローカ API（本番実行時）

依存パッケージはリポジトリに requirements.txt がある場合はそれを使ってください:
```
python -m pip install -r requirements.txt
```
requirements.txt がない場合は上記ライブラリを個別にインストールしてください:
```
python -m pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン / チェックアウト
2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .\.venv\Scripts\activate   # Windows
   ```
3. 依存ライブラリをインストール
   ```
   python -m pip install --upgrade pip
   python -m pip install duckdb psutil openai pyyaml
   ```
4. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザード終了後は `.env` ファイルが生成されます。必須の環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

5. 設定検証（起動前）
   ```
   python -m kabusys.validate_config
   ```
   警告も厳格に扱いたい場合は `--strict` を付けます。

6. 必要なディレクトリを作成（.env のデフォルトでは data/ と logs/ が使われます）
   ```
   mkdir -p data logs
   ```

---

## 重要な環境変数（抜粋・例）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（KABUSYS_ENV=paper_trading）
- LOG_LEVEL — "DEBUG" / "INFO" / ...
- OPENAI_API_KEY — news_nlp / regime_detector を使う場合に必要
- MONITOR_POLL_INTERVAL — monitoring ポーリング間隔（秒、run_monitoring はこの env を参照）

.env の一部例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 実行方法（代表的なコマンド）

パッケージとしてモジュールを実行します（プロジェクトルートで実行してください）。

- 実行エンジン（ExecutionEngine）起動
  - 本番 / ペーパートレードともに ExecutionEngine を開始します。Paper Trading は KABUSYS_ENV=paper_trading を指定。
  ```
  # 例: デフォルト環境（.env で設定済み）
  python -m kabusys.run_execution

  # ペーパートレードを環境変数で直接指定して起動
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

  実行中は data/execution.pid に PID ファイルが書き出され、停止指示は data/stop_requested.flag や data/kill.flag によって行われます。

- 監視プロセス起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト: 60）。
  - 監視は本番 sqlite_path（SQLITE_PATH）を常に参照します（環境に関係なく）。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（任意の期間）
  ```
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 系（プログラム的に呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - 両方とも OPENAI_API_KEY の設定が必要です。テストでは API 呼び出し箇所をモックできます。

---

## ログ / データファイル

- ログ
  - デフォルトログディレクトリ: logs/
  - 各アプリケーションごとに日次ローテートされたファイルを出力（例: logs/execution.log, logs/monitoring.log）
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一

- データファイル
  - DuckDB: data/kabusys.duckdb（データ分析用）
  - SQLite (monitoring): data/monitoring.db
  - SQLite (paper trading): data/paper_trading.db
  - PID / フラグ:
    - data/execution.pid など
    - data/stop_requested.flag（外部からプロセスを安全に停止するための停止フラグ）
    - data/kill.flag（Kill Switch による強制停止を表すフラグ）

---

## 注意点 / 実装メモ

- Paper Trading と本番データは DB を分離しています（paper_sqlite_path）。
- 設定自動ロード:
  - プロジェクトルートに `.env` / `.env.local` がある場合、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- OpenAI 呼び出し:
  - レート制限・5xx 等に対しては指数バックオフでリトライする実装が含まれます。
  - レスポンスは JSON モードを期待してパース・検証しますが、フォールバックを実装している箇所があります。
- プロセス優先度設定:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。psutil による操作のため権限不足で失敗する場合があります（警告のみ）。
- DuckDB 接続は多数のリサーチ / AI モジュールで共有して利用する想定です。
- 一部のユーティリティは依存ライブラリ（PyYAML 等）がない場合、機能をスキップして警告を出します（例: validate_config の YAML 検証）。

---

## ディレクトリ構成

（src/kabusys 以下の主なファイル/パッケージの説明）

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - execution/ — 実行エンジン関連（broker, engine, order_manager, risk_manager 等）
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文系監視（ファイルに含まれていないが存在想定）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py — アラート送信（LINE 等）想定
  - portfolio/
    - portfolio_builder.py — 候補選定・スコア順ソート
    - position_sizing.py — 株数算出・投下上限・lot 単位丸め
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — momentum, volatility, value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュース記事センチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロ NLP）
  - data/ — 実行時生成・使用するファイル（data/*.db, pid, flags）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py — ルートロガー設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 開発 / テストのヒント

- モジュールは明確に分離されているため、単体テスト時は DB 接続や OpenAI 呼び出しをモックすることでテスト可能です。（score_news などは _call_openai_api をパッチしてテストできます）
- DuckDB 接続を渡すだけでリサーチ関数を呼べるため、テスト用の小さな DuckDB ファイルを作って検証が可能です。
- validate_config は .env の基本チェックと config/*.yaml の存在/パースを支援します。CI に組み込むと便利です。

---

## ライセンス / 貢献

この README はコードベースの要約ドキュメントです。ライセンス・貢献ガイドラインはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

必要であれば README に以下を追加で追記できます:
- 具体的な API シーケンス図（ExecutionEngine のフロー）
- 各設定ファイル（config/*.yaml）のサンプル
- よくあるトラブルシュート（ログの読み方、権限エラー対処）
どれを追加希望か教えてください。