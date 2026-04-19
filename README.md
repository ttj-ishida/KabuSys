# KabuSys

日本株向け自動売買システム（モジュール群）  
このリポジトリは取引エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）等を提供する小規模なフレームワークです。  
（この README は提供されたソースコードを元に作成しています。）

---

## プロジェクト概要

KabuSys は以下の主要な責務を持つモジュール群で構成されています。

- Execution Engine（発注エンジン） — run_execution.py で起動。実売買/ペーパートレードに対応。
- Monitoring（監視） — run_monitoring.py で起動。システム状態、データ鮮度、注文状況、リスク等をポーリングして永続化・アラート・Kill Switch を管理。
- Portfolio（銘柄選定・配分・ポジションサイズ計算） — 等金額・スコア加重・リスクベース等の純粋関数。
- Research（ファクター計算・特徴量解析） — DuckDB を用いたファクター計算・IC 等の統計解析。
- AI（ニュース NLP / レジーム判定） — OpenAI を用いてニュースをセンチメント化し、マーケットレジームを推定。
- ユーティリティ — ログ設定、プロセス優先度設定、設定読み込みウィザード、設定検証 CLI など。
- Tools — Paper Trading の検証レポート生成スクリプト等。

---

## 主な機能一覧

- 設定管理（.env ファイルや環境変数）と自動読み込み（.env/.env.local）
- 対話式設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
  - system_status, trade_logs, risk_logs, positions, dashboard テーブルへの永続化（SQLite）
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止
  - ロギング（コンソール + 日次ローテーション）
- ExecutionEngine（ペーパートレードと live の分離。paper_trading は専用 DB を使用）
- Portfolio construction（候補選定・重み計算・ポジションサイズ算出、セクター制限、レジーム乗数）
- Research（Momentum / Volatility / Value 等のファクター計算、forward returns, IC）
- AI 機能
  - ニュースの銘柄別センチメントスコア算出（OpenAI）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（OpenAI）
- 各種ツール（例: Paper Trading 検証レポート生成）

---

## 要件（主要ライブラリ）

実行に必要な主なパッケージ（抜粋）:

- Python 3.10+
- duckdb
- psutil
- openai
- pyyaml（設定ファイル YAML 検証時に必要）
- （sqlite3 は標準ライブラリ）

※ requirements.txt がない場合は上記パッケージを個別にインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. 対話式で .env を作成（推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで J-Quants トークン、kabuAPI パスワード、DB パス、環境（KABUSYS_ENV）等を入力します。
   ※ .env は絶対にリポジトリへコミットしないでください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告もエラー扱いになります。

---

## 主要な環境変数（抜粋・デフォルト）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — AI 機能利用時に必要
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — INFO（デフォルト）
- LOG_DIR — logs/（デフォルト）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動で .env を読み込まない

自動ロードの優先順位: OS 環境変数 > .env.local > .env  
（ただし OS 環境変数は保護され、.env*.local が上書きしない）

---

## 使い方 / 実行例

### 監視プロセス起動

監視ループを起動します（デフォルトは 60 秒間隔）。MONITOR_POLL_INTERVAL 環境変数で秒数を変更できます。

```
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使います（KABUSYS_ENV に依存せず）。
- 停止するにはプロジェクトルートの data/stop_requested.flag を作成するか、プロセスを終了してください（Ctrl+C 等）。

### 実行エンジン起動（ExecutionEngine）

```
python -m kabusys.run_execution
```

- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録して本番 DB と分離します。
- 実行は内部で PID ファイルを作成します（data/execution.pid 等）。
- 停止シグナルは監視側の kill.flag（Settings.kill_flag_path）経由で伝達されます。kill.flag が存在すると起動を止めます。

### 設定ウィザード / 検証

- 対話式設定: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]

### ツール: Paper Trading 検証レポート

Paper Trading 結果を解析してレポート出力:

```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を明示
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

生成される指標: 稼働率、注文成功率、送信率、P95 レイテンシ等。閾値を満たすか PASS/FAIL を判定します。

### AI 機能（ニュース NLP / レジーム判定）

これら機能は OpenAI API キー（OPENAI_API_KEY）が必要です。DuckDB に必要な raw_news / news_symbols / ai_scores / market_regime / prices_daily 等のテーブルが存在する前提です。

- ニュースセンチメントスコア取得: kabusys.ai.score_news（モジュール関数を直接呼ぶ）
- レジーム判定: kabusys.ai.regime_detector.score_regime

（CLI 用スクリプトは用意されていないため、スクリプト/ジョブとして実行する想定です）

---

## 停止・Kill Switch

- 監視は data/stop_requested.flag ファイルの存在でループを抜けます。
- 実行エンジンの停止は監視側の KillSwitch が data/kill.flag を書き込むことで伝達します（kill.flag を書けば ExecutionEngine は次チェックで停止する設計）。
- Settings.kill_flag_clear_on_start=1 を設定すると起動時に自動で kill.flag を消去しますが、本番では 0 を推奨します。

---

## ログ

- ログは stdout（コンソール）と日次ローテートされたファイル（デフォルト logs/<app_name>.log）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出します。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主な構成は次の通りです（提供されたファイルに基づく）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 読み込み・Settings
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py      — 共通ログ設定
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層
    - system_monitor.py     — システム監視
    - risk_monitor.py       — ドローダウン・保有数監視
    - kill_switch.py        — kill.flag 管理
    - monitoring_engine.py  — 各 Monitor を束ねる実行ロジック
    - ...（TradeMonitor / AlertManager 等が想定）
  - execution/              — Execution に関するモジュール（OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュースセンチメント（OpenAI）
    - regime_detector.py    — 市場レジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py

その他に `data/`（DB・flag・pid 等）や `logs/` ディレクトリが想定されます。

---

## 開発メモ / 注意事項

- .env や API キー等の秘密情報は絶対にコミットしないでください。
- Paper Trading 環境（KABUSYS_ENV=paper_trading）は本番 DB と分離するよう設計されています。必ず PAPER_TRADING_SQLITE_PATH を確認してください。
- AI 関連は外部 API コールを伴うため、API の料金・レートリミットに注意してください。エラー時はリトライやフォールバックが組み込まれていますが、運用ポリシーを決めてください。
- ローカルでのテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます。
- DuckDB と SQLite のスキーマはコード内の init/SQL に従って作成・マイグレーションされます。運用時はバックアップを取ってからマイグレーションを検討してください。

---

README はここまでです。必要であれば次の内容を追加できます: 具体的な API （モジュール）リファレンス、ユニットテストの実行方法、運用／デプロイ手順（systemd / Supervisor / Docker）など。どれを優先しますか？