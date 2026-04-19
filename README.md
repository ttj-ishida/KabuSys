# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（リサーチ / ポートフォリオ構築 / 発注 / 監視 / AI 補助機能）を構成するモジュール群です。各コンポーネントは疎結合で設計されており、ローカル開発・ペーパートレード・本番（live）を環境変数で切り替えて動作します。

---

## 概要（Project overview）

- モジュール群は次の責務を持ちます:
  - research: DuckDB 上の株価・財務データからファクター計算・特徴量解析
  - portfolio: 銘柄選定・重み付け・ポジションサイズ計算・リスク調整
  - execution: 発注エンジン（本番は実口座、`paper_trading` はモックブローカーで分離された SQLite に記録）
  - monitoring: システム状態・注文ログ・リスクを監視し、Kill Switch や通知を管理
  - ai: ニュース NLP（OpenAI）を用いたセンチメントスコアリング、レジーム検出
  - tools: 検証レポート生成などのユーティリティスクリプト
- 設定は `.env` ファイル（または環境変数）で行い、`kabusys.config` から一元的に取得できます。
- ログはコンソール（stdout）と日次ローテートファイル（logs/*.log）へ出力します。

---

## 主な機能一覧（Features）

- 環境設定ウィザード（`python -m kabusys.config_setup`）で .env を対話的に作成
- 設定検証 CLI（`python -m kabusys.validate_config`）で起動前チェック（`--strict` あり）
- ExecutionEngine（発注エンジン）
  - KABUSYS_ENV=`paper_trading` 時は MockBrokerClient を使用し data/paper_trading.db に記録
  - 本番 / ペーパーで DB を分離
  - PID ファイル / 停止フラグによる制御
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス監視
  - TradeMonitor / RiskMonitor: 注文の滞留、約定異常、ドローダウン、ポジション上限などを監視
  - KillSwitch: 条件を満たすと data/kill.flag を作成して ExecutionEngine を止める
  - Monitoring DB（SQLite）への永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- Portfolio modules（純粋関数群）
  - 候補選定、等金額・スコア加重、ポジションサイズ算出、セクター制約、レジーム乗数
- Research modules
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を参照）
  - IC（Information Coefficient）や将来リターンの計算、統計サマリー
- AI 機能（OpenAI）
  - ニュースの銘柄ごとセンチメントスコア算出（ai_scores テーブルへ書き込み）
  - 市場レジーム判定（ma200 とマクロニュースを合成）
  - リトライ・レスポンス検証・スコアクリップなど堅牢な実装
- ツール
  - Paper Trading の検証レポート出力（`python -m kabusys.tools.paper_verification_report`）

---

## 前提（Prerequisites）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証を行う場合に必要）
- SQLite は標準ライブラリで利用可能
- （任意）OpenAI を利用する場合は OPENAI_API_KEY を用意

インストール例（環境に応じて仮想環境を利用してください）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ requirements.txt が用意されている場合は `pip install -r requirements.txt` を推奨します。

---

## セットアップ手順（Setup）

1. リポジトリをクローン:
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. .env の作成（推奨: ウィザードを使用）:
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークン、kabuAPI パスワード、DB パス、環境（development/paper_trading/live）などを設定します。

3. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告を厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

4. ログディレクトリ確認:
   - デフォルトは `logs/`。必要に応じて `LOG_DIR` 環境変数で変更できます。
   - `LOG_LEVEL` 環境変数でログレベルを調整（例: DEBUG, INFO）。

5. （AI 機能を使う場合）OpenAI API キーを設定:
   - 環境変数: `OPENAI_API_KEY`
   - もしくは関数呼び出し時に引数で渡す

---

## 使い方（Usage）

主な起動スクリプトはモジュール実行（-m）を想定しています。

- ExecutionEngine（発注エンジン）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV 環境変数:
    - `development`: 発注なし（開発用）
    - `paper_trading`: MockBroker を使用。DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）
    - `live`: 本番 API を使用（KABU_API_PASSWORD 等必須）
  - 停止制御:
    - `data/stop_requested.flag` が存在すると起動中のループは停止します
    - `data/execution.pid` に PID を書き込みます
  - ExecutionEngine は内部でリスク制御（RiskManager）や OrderManager 等を組み立てます

- Monitoring（監視プロセス）を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒数で上書き（デフォルト: 60）
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を参照します（KABUSYS_ENV に依存しない）
  - stop フラグ: 上位の `data/stop_requested.flag` を検知すると監視ループを終了します

- .env 作成ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI / Research / Portfolio モジュールはプログラムからインポートして使用します。
  例（Python スクリプト内）:
  ```py
  from kabusys.ai.news_nlp import score_news
  from kabusys.research import calc_momentum
  # DuckDB 接続を作り、score_news/score_regime 等を呼び出す
  ```

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（INFO デフォルト）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI キー（AI 機能で必要）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒、デフォルト 60）

---

## 停止 / Kill Switch の制御

- ExecutionEngine を停止したい（強制停止）場合:
  - `data/kill.flag` を作成すると ExecutionEngine 側で検出して停止される仕組みがあります（KillSwitch）。
  - Monitoring により条件が満たされると自動で `data/kill.flag` が作成されます。
- 監視プロセス自体の停止には `data/stop_requested.flag` を作成するか、プロセスに SIGINT（Ctrl+C）を送ってください。

---

## ディレクトリ構成（Directory structure）

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数と Settings クラス（.env 自動読み込み）
    - config_setup.py          — .env 対話型ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading の検証レポート生成
    - ai/
      - news_nlp.py            — ニュース NLP（OpenAI）による銘柄スコアリング
      - regime_detector.py     — 市場レジーム判定（ma200 + マクロセンチメント）
    - research/
      - factor_research.py     — Momentum / Volatility / Value 等のファクター計算
      - feature_exploration.py — 将来リターン / IC / 統計サマリー
    - portfolio/
      - portfolio_builder.py   — 候補選定・重み計算
      - position_sizing.py     — 株数算出・aggregate cap 処理
      - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - monitoring/
      - monitoring_db.py       — SQLite に対する永続化層（テーブル作成・CRUD）
      - system_monitor.py      — システム状態・データ鮮度監視
      - monitoring_engine.py   — 各 Monitor を束ねるエンジン
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - trade_monitor.py       — （注文関連の監視 — 実装の詳細はファイル参照）
      - kill_switch.py         — Kill Switch 実装
      - alert_manager.py       — （通知管理 — 実装の詳細はファイル参照）
    - execution/
      - execution_engine.py    — ExecutionEngine（セッション実行・発注ループ）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
    - utils/
      - logging_setup.py       — ルートロガー設定（stdout + 日次ローテート）
      - process_priority.py    — プロセス優先度 / CPU affinity ヘルパ
    - data/                    — データファイル（例: data/*.db, flags, pid など） ※実行時に作成される
- pyproject.toml / その他のメタファイル（プロジェクトルート）

---

## 開発時のヒント

- .env は絶対にリポジトリにコミットしないでください（ウィザード内にも注記あり）。
- DuckDB は分析用で大規模データ処理向け、設定やスキーマは config/*.yaml と連携する想定です。
- AI 機能をテストする際は API 呼び出しをモックするユニットテストを推奨します（ライブラリ内で _call_openai_api を差し替え可能）。
- Monitoring の polling 間隔は MONITOR_POLL_INTERVAL で調整可能（短くすると負荷が増えるので注意）。
- 実稼働時は KABUSYS_ENV=live の設定を慎重に検証してください（validate_config の注意喚起あり）。

---

この README はコードベースの概観・使い方のガイドです。各モジュールの詳細な API・設計仕様は該当ファイルのドキュメンテーション文字列（docstring）やコメントを参照してください。問題や不明点があれば、該当モジュールのソースを参照して挙動を確認してください。