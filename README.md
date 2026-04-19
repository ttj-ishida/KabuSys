# KabuSys

日本株向け自動売買システムのリファレンス実装（モジュール群・サンプルツール含む）。

概要、起動スクリプト、監視機構、ポートフォリオ構築、研究用ファクター計算、AIによるニュース分析などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的および機能群を持つ小規模な自動売買プラットフォームの実装例です。

- ExecutionEngine：発注ロジック（本番 / ペーパートレード切替）
- Monitoring：システム状態・注文状態・リスク監視・Kill Switch（自動停止）
- Portfolio Construction：候補選定・配分・リスク調整・サイズ計算
- Research：DuckDB を使ったファクター計算・探索ユーティリティ
- AI モジュール：ニュースの NLP スコアリング、および市場レジーム検出（OpenAI 利用）
- 設定管理 / ウィザード / 検証ツール（.env の対話生成、設定チェック）
- ユーティリティ：ログ設定、プロセス優先度設定、各種ツール（レポート生成等）

設計上の注意点：
- Paper Trading は本番 DB と分離して動作（PAPER_TRADING_SQLITE_PATH を使用）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml が基準）から行われる。
- LLM（OpenAI）を利用する機能は API キーが必要。失敗時はフェイルセーフ（多くはスコア 0 にフォールバック）を採用。

---

## 主な機能一覧

- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading / live を切替）
- run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で調整可）
- monitoring_engine: SystemMonitor / TradeMonitor / RiskMonitor を束ねてアラート・Kill Switch を実行
- monitoring_db: 監視ログ（SQLite）テーブルの初期化・読み書き
- portfolio モジュール: 銘柄選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数
- research モジュール: momentum / volatility / value 等のファクター計算、IC や統計サマリ
- ai.news_nlp: OpenAI を用いたニュースの銘柄別センチメントスコアリング（ai_scores テーブルへ保存）
- ai.regime_detector: MA200 とマクロニュースのセンチメントを合成して市場レジーム判定
- tools.paper_verification_report: Paper Trading の検証レポート生成
- config_setup.py: .env の対話式作成・更新ウィザード
- validate_config.py: 起動前設定検証 CLI（--strict オプションあり）
- utils.logging_setup: 統一ログ設定（コンソール + 日次ローテートファイル）
- utils.process_priority: プラットフォーム差を吸収したプロセス優先度設定

---

## セットアップ手順

推奨 Python バージョン: 3.10 以上（型ヒントに `X | Y` 構文を使用）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   リポジトリに requirements.txt が無い場合は最低限以下を入れてください。
   - duckdb
   - psutil
   - openai
   - PyYAML（設定ファイル検証に任意で必要）

   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. .env の作成
   対話式ウィザードを用意しています：
   ```
   python -m kabusys.config_setup
   ```
   これにより `.env` が生成されます（既存値の再利用可）。手動で作成する場合は README 内の「環境変数一覧」を参照して設定してください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   本番相当の厳密チェックを行う場合:
   ```
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ作成（必要に応じて）
   デフォルトの DB / pid / flag は `data/` 配下になります。自動作成されることもありますが、必要なら手動で作成して権限を確認してください。

---

## 環境変数（代表例）

主要な環境変数とデフォルト値（.env で設定）:

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境。valid: development, paper_trading, live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を利用する機能で必須（ai.*）
- LOG_LEVEL — デフォルト INFO
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 任意（本番での通知用）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）。デフォルト 60
- PAPER_FILL_MODE — paper_trading 時の模擬約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 本番での自動 kill.flag クリア禁止推奨。1=クリアする, 0=しない（デフォルト 0）
- PID_FILE_PATH / KILL_FLAG_PATH — 各種ファイルパス（デフォルト data/*.pid / data/kill.flag）

例（.env の一部）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
```

注意:
- 自動ロードはプロジェクトルートに .env / .env.local がある場合に行われます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env は絶対に Git に含めないでください。

---

## 使い方（主なコマンド）

- 実行エンジン（Execution）を起動
  - 本番（live）:
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - ペーパートレード:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  実行中は `data/execution.pid`（デフォルト）を使用し、停止リクエストは `data/stop_requested.flag` を作成することで受け付けます（monitoring から Kill Switch が作る `data/kill.flag` と別）。

- 監視プロセス起動（SystemMonitor のポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔を変更するには環境変数で:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 設定ウィザード（.env の作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（ニューススコア等）
  ai.news_nlp や ai.regime_detector は DuckDB 接続と日付・APIキーを引数に取る関数として提供されています。OpenAI API キー（OPENAI_API_KEY）が必要です。

---

## 停止 / Kill Switch の挙動

- 手動停止要求（run_execution / run_monitoring の停止）:
  - プロセスに対する通常の SIGINT (Ctrl+C) で停止します。
  - またはプロジェクトの data/stop_requested.flag を作成すると、run_execution / run_monitoring のループが終了します。

- 自動停止（Kill Switch）:
  - 監視ロジックがリスク閾値（ドローダウン、ポジション上限など）を検知すると `data/kill.flag` を書き込みます。
  - ExecutionEngine 側（実装上の他モジュール）は kill.flag の存在を参照して安全に停止します（部分的な実装依存箇所があるため、独自の運用ルールを追加して下さい）。

---

## 実装上の注意点 / 運用メモ

- Paper Trading は production DB（monitoring.db）とは独立した PAPER_TRADING_SQLITE_PATH を使用します。
- Monitoring は常に Settings.sqlite_path（本番パス）を使って監視テーブルを初期化します（冪等操作）。
- logging_setup は全起動スクリプトから共通で呼び、標準出力と日次ファイル出力（logs/<app>.log）を行います。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- process_priority の設定には psutil の権限が必要な場合があります。設定に失敗しても警告が出てスキップされます。
- AI（OpenAI）呼び出しではリトライやバックオフロジックを実装していますが、API キーや利用上限に注意してください。
- DuckDB への書き込み処理では一部互換性のため executemany 空リストの扱いに注意（コード内でガードあり）。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールのみの抜粋です（実際のツリーはプロジェクトルート参照）。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定取得ロジック (.env 自動ロード含む)
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 起動前設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py          — SQLite 監視 DB 層（初期化・読み書き）
    - monitoring_engine.py      — 各 Monitor を束ねるエンジン
    - system_monitor.py         — CPU/メモリ/ディスク/データ鮮度監視
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — kill.flag の作成/管理
    - (trade_monitor.py 等)
  - execution/                  — ExecutionEngine, OrderManager, BrokerFactory 等
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 株数算出・リスク制約
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py        — momentum/volatility/value 等
    - feature_exploration.py    — forward returns, IC 等
  - ai/
    - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — 市場レジーム判定（MA200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py          — ログ設定ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ

- data/                          — 実行時に使用する DB / pid / flag 等（例: data/monitoring.db, data/paper_trading.db, data/stop_requested.flag）
- logs/                          — ログファイル出力先（デフォルト）

---

## よくある質問 (FAQ)

Q: データベースファイルはどこに置くべきですか？  
A: デフォルトは `data/kabusys.duckdb`（DuckDB）と `data/monitoring.db`（SQLite）。運用環境では永続化パスを環境変数で指定してください（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。

Q: Paper Trading と本番データは分離されていますか？  
A: はい。run_execution は KABUSYS_ENV=paper_trading の場合 PAPER_TRADING_SQLITE_PATH を使用し、本番監視 DB とは別ファイルに記録します。

Q: OpenAI API が無いとどうなる？  
A: ai.news_nlp や ai.regime_detector 等の機能は API キーが必要です。キー未設定時は ValueError を投げます。運用上は API を使わない（スキップ）ことも可能ですが、該当機能は無効になります。

---

この README はコードベースから読み取れる設計・実装情報に基づいて作成しています。実際の運用にあたっては config/*.yaml（存在する場合）の内容確認や、環境ごとの追加設定（ネットワーク、証明書、プロセス監視など）を行ってください。質問や追加のドキュメント（API、設計資料、運用手順）が必要なら教えてください。