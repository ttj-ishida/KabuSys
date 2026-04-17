# KabuSys

日本株向けの自動売買システム（リサーチ・ポートフォリオ構築・発注・監視・検証ツール群）

このリポジトリは、戦略ファクター計算、ポートフォリオ構築、発注エンジン、監視（Monitoring）、ペーパートレードの検証・レポート作成、LLM を用いたニュース解析 / レジーム判定などのコンポーネントを備えた統合システムです。

---

## 主要機能（抜粋）

- 戦略リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）解析、特徴量サマリ
- ポートフォリオ構築
  - 候補選定、等金額・スコア加重配分、リスクベースの銘柄ごとの株数決定
  - セクター集中抑制、レジームに応じた資金乗数
- 発注（Execution）
  - ExecutionEngine（本番／ペーパートレード切替可）
  - BrokerClient ファクトリで実口座／モック切替
  - リスク管理（ポジション上限・ドローダウン等）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス状態、データ鮮度監視
  - TradeMonitor: 注文滞留（stale order）、約定価格異常検出
  - RiskMonitor: ドローダウンやポジション上限の検出とログ記録
  - Kill Switch: 危険時に flag ファイルを書き込み ExecutionEngine を停止
  - MonitoringEngine: 各モニタの統合ポーリングループ
- AI（LLM）連携
  - news_nlp: ニュース記事を OpenAI に投げて銘柄ごとのセンチメントを ai_scores テーブルに保存
  - regime_detector: ETF（1321）の MA200 とマクロニュースから市場レジーム（bull/neutral/bear）判定
- ユーティリティ
  - .env 対話ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report）

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（抜粋）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config で YAML 検証を行う場合）
- 任意: SQLite を扱うための標準ライブラリは Python に含まれます

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ 実際の requirements.txt は本リポジトリに含まれていないため、プロジェクト実行に必要なパッケージは用途に応じてインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. .env を作成（対話ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードで J-Quants リフレッシュトークン、kabuAPI パスワード、DB パス等を設定します。
   - .env は Git にコミットしないでください。
4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - 警告も厳密に扱う場合は `--strict` を付けてください。
5. （AI 機能を使う場合）OpenAI API キーを環境変数に設定
   ```
   export OPENAI_API_KEY="sk-..."
   ```
6. 初回起動時にデータディレクトリ（`data/`）や DB の場所を確認しておくと安全です。デフォルト:
   - DuckDB: data/kabusys.duckdb
   - SQLite (monitoring): data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db

---

## 使い方（主要コマンド・環境変数）

- 実行環境指定:
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録します。
  - 例: export KABUSYS_ENV=paper_trading

- .env の主な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能利用時必須)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
  - LOG_LEVEL (INFO 等)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート用）
  - PAPER_FILL_MODE（paper_trading の約定挙動: instant, partial, never, reject）
  - KILL_FLAG_CLEAR_ON_START (0/1) — ExecutionEngine 起動時の kill.flag 自動クリア（本番では 0 推奨）
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）

- ExecutionEngine（発注エンジン）起動
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 停止:
    - data/stop_requested.flag を作成すると起動中の run_execution / run_monitoring はループを終了します。
    - Kill Switch は data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります（監視側が判断して書き込みます）。
  - PID ファイル:
    - data/execution.pid に PID を書いてプロセス存在を監視します。

- Monitoring 起動
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御（秒、デフォルト 60）

- ペーパートレード検証レポート
  - 期間指定で実行:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB 指定:
    ```
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- 設定検証（再掲）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- .env ウィザード（再掲）
  ```
  python -m kabusys.config_setup
  ```

- AI 関連（ライブラリ関数）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を直接受け取り、AI キーは引数または環境変数 OPENAI_API_KEY を参照します。

---

## 実装上の注意点 / 動作上の挙動

- Monitoring は環境（KABUSYS_ENV）にかかわらず sqlite_path（production 想定のパス）を使用します。実行中の監視データは常に同じ監視 DB に記録されます。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite DB を使用して本番 DB と分離します。
- process_priority 設定: 起動時にプロセス優先度を "high" に試行的に設定します（プラットフォーム毎に実装。権限不足時は警告でスキップ）。
- DB マイグレーション: monitoring_db.init_monitoring_db() は起動時に必要テーブルを作成し、既存 DB に列（peak_value, latency_ms）がなければ追加します（安全な冪等操作）。
- Kill Switch:
  - 監視がドローダウンやポジション上限などを検出した場合、data/kill.flag を書き込んで ExecutionEngine を停止させます。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を自動クリアします（本番では注意）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数・設定管理（.env 自動ロード等）
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

サブパッケージ（主要ファイル）
- ai/
  - news_nlp.py             — ニュースの LLM スコアリング
  - regime_detector.py      — 市場レジーム判定（LLM + MA200）
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py       — システム状態・データ鮮度監視
  - trade_monitor.py        — 注文滞留・約定異常監視
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
  - kill_switch.py          — フラグファイルによる停止信号
  - alert_manager.py        — （アラート送信の抽象化）
- execution/
  - （発注関連の Engine / broker / order_manager 等 — 実装ファイル群）
- portfolio/
  - portfolio_builder.py    — 銘柄選定・重み付け
  - position_sizing.py      — 株数決定・投下資金スケール
  - risk_adjustment.py      — セクター制限・レジーム乗数
- research/
  - factor_research.py      — Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py  — 将来リターン / IC / 統計サマリ
- tools/
  - paper_verification_report.py — ペーパートレード結果の検証レポート生成
- utils/
  - process_priority.py     — プロセス優先度 / CPU_affinity ユーティリティ
- monitoring/monitoring_db.py  — 監視 DB 初期化・読み書きクラス（上記）

（実際の repo にはさらに各種モジュールが存在します。ここでは主要ファイルを抜粋しています。）

---

## よくある運用上のワークフロー（例）

1. .env 作成
   - python -m kabusys.config_setup
2. 設定検証
   - python -m kabusys.validate_config
3. （Paper Trading の場合）発注エンジン起動
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution
4. 監視プロセス起動（別プロセスで）
   - python -m kabusys.run_monitoring
5. トラブル時
   - data/stop_requested.flag を作成して run_execution/run_monitoring を優雅に停止
   - 監視が自動で data/kill.flag を書くと ExecutionEngine が停止（Kill Switch）

---

## 開発・拡張メモ

- DuckDB を用いて時系列価格や財務データを SQL で効率的に処理します。research モジュールは DuckDB 接続を受け取り純粋関数として動作する設計です。
- AI 系は外部 API の失敗をフェイルセーフに扱い、部分スコアのみを更新することで部分失敗時のデータ喪失を避ける設計です。
- 設定ファイル（config/*.yaml）が必要な場合は scripts 等で生成する想定（validate_config で存在チェック）。PyYAML がない場合は YAML 検証をスキップします。

---

この README はコードベースから抽出した概要ドキュメントです。運用時は必ず .env を正しく設定し、validate_config でチェックしてからプロセスを起動してください。必要があれば README をプロジェクト固有の運用ルールに合わせて追記してください。