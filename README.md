# KabuSys

日本株自動売買システムのサブパッケージ群。ポートフォリオ構築、発注実行、監視、リサーチ、AI（ニュースNLP / レジーム判定）などを含むモジュール群です。

以下はこのリポジトリの概要、機能、セットアップ・実行方法、ディレクトリ構成の説明です。

注意: この README はコードベースから抽出した情報に基づいて作成しています。実運用前に `python -m kabusys.validate_config` で設定検証を行ってください。

---

## プロジェクト概要

KabuSys は以下のようなコンポーネントで構成される自動売買プラットフォームを想定した実装群です。

- ExecutionEngine: 発注・注文管理・リスク管理を行うエンジン（本番 / ペーパートレード対応）
- Monitoring: システム稼働状況・注文状況・リスク指標を定期監視し、アラートや Kill Switch を発動
- Portfolio: 銘柄選定、重み計算、ポジションサイズ計算、セクター制限等
- Research: DuckDB を用いたファクター計算・特徴量探索
- AI: ニュースのセンチメント評価 / 市場レジーム判定（OpenAI API を利用）
- ユーティリティ: ロギング設定、プロセス優先度設定、設定（.env）読み込みウィザード等
- Tools: Paper Trading 検証レポート生成スクリプト等

設計方針としては、
- 本番 DB とペーパートレード DB を分離
- DuckDB を分析用に利用し、SQLite を監視/発注ログ用に利用
- LLM 呼び出しはフェイルセーフで設計（API エラー時はフォールバック）
- ルックアヘッドバイアスを避ける設計（date/datetime の扱いに注意）

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの `.env` / `.env.local`）
  - 対話式ウィザード: `python -m kabusys.config_setup`
  - 設定検証 CLI: `python -m kabusys.validate_config`（`--strict` オプションあり）

- 実行エンジン
  - 本番/ペーパー（KABUSYS_ENV）でのブローカー切替
  - 発注管理、リスク管理、Reconciler（注文整合性）
  - PID ファイル / stop flag を使った制御
  - Paper Trading 時は専用 SQLite（デフォルト: `data/paper_trading.db`）を使用して本番と分離

- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor のポーリング
  - Kill Switch（`data/kill.flag`）で ExecutionEngine の停止をトリガー
  - 監視ログ永続化（SQLite、`monitoring_db.py` にスキーマ定義あり）
  - run_monitoring スクリプトでループ起動（MONITOR_POLL_INTERVAL で間隔制御）

- ポートフォリオ構築
  - 候補選定、等重/スコア加重、リスクベースのポジションサイズ計算
  - セクター上限適用、レジーム乗数

- リサーチ
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）等の統計ユーティリティ

- AI（OpenAI 経由）
  - ニュースの銘柄別センチメント評価（`kabusys.ai.news_nlp`）
  - 市場レジーム判定（ETF の MA 乖離 + マクロニュースの LLM スコア）

- ツール
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）

---

## 前提 / 依存（概略）

- Python 3.10+（ソース中での型注釈や union 型 `X | Y` を使用）
- 主な Python パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- その他: SQLite（組み込み）、ファイルシステム書き込み権限

（requirements.txt がある場合はそちらを参照してください。なければ上記をインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしワークディレクトリへ移動
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. .env の作成
   - 対話式ウィザードで作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - または手動でルートの `.env` を作成。主な環境変数（例）:
     ```
     KABUSYS_ENV=development        # development | paper_trading | live
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PAPER_FILL_MODE=instant        # instant|partial|never|reject
     OPENAI_API_KEY=sk-...
     ```
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 設定検証（起動前に必須項目の確認）:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの作成（必要に応じて）
   ```bash
   mkdir -p data logs
   ```

---

## 使い方（主なエントリポイント）

- 実行エンジン（ExecutionEngine）起動:
  ```bash
  python -m kabusys.run_execution
  ```
  説明:
  - KABUSYS_ENV に応じて本番ブローカーまたは MockBroker を使用
  - paper_trading の場合は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録
  - プロセス優先度を "high" に設定します
  - 停止は `data/stop_requested.flag` を作成するか、プロセスに SIGINT を送る

- 監視ループ起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  説明:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は監視用 SQLite（デフォルト `data/monitoring.db`）にログを残す
  - `data/stop_requested.flag` が存在するとループを終了します

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```
  環境変数 `PAPER_TRADING_SQLITE_PATH` で DB パスを指定することもできます。

- AI 関連（プログラムから呼び出す API）
  - ニュース NLP スコア付け:
    - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - `OPENAI_API_KEY` 環境変数、または引数で API キーを渡してください
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

注意: OpenAI API を利用する機能は API キーが必須です。API エラー時のフォールバック挙動（例: スコア=0.0）やリトライ機構が実装されていますが、APIキーが未設定のまま呼ぶと ValueError を送出します。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログファイル格納ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、production では 0 推奨）

---

## 停止 / フラグ制御

- run_execution / run_monitoring はプロセス内で `data/stop_requested.flag` を監視し、存在時に安全に停止します。
- Kill Switch: `data/kill.flag` を書き込む（KillSwitch）が評価条件を満たすと ExecutionEngine に対して停止要求を発行します。`KILL_FLAG_CLEAR_ON_START` により起動時に自動クリアするか制御できます（本番では自動クリアは推奨されません）。
- 実装側で PID ファイル（例: `data/execution.pid`）を扱います。

---

## ディレクトリ構成

（該当ソース配下の主要なファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / Settings
    - config_setup.py                — .env 対話式ウィザード
    - validate_config.py             — 設定検証 CLI
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート
    - ai/
      - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py           — 市場レジーム判定（OpenAI）
    - monitoring/
      - monitoring_db.py             — 監視用 DB スキーマ & 永続化
      - monitoring_engine.py         — 各モニタの統合実行
      - system_monitor.py            — システム状態・データ鮮度監視
      - risk_monitor.py              — ドローダウン・ポジション上限監視
      - trade_monitor.py             — （置換）注文監視ロジック
      - kill_switch.py               — Kill Switch 制御
      - alert_manager.py             — （アラート送信ロジック）
    - portfolio/
      - portfolio_builder.py         — 候補選定・重み計算
      - position_sizing.py           — 株数決定・スケーリング
      - risk_adjustment.py           — セクター制限・レジーム乗数
    - research/
      - factor_research.py           — ファクター計算
      - feature_exploration.py       — 将来リターン・IC等
    - utils/
      - logging_setup.py             — 統一ロギング設定
      - process_priority.py          — プロセス優先度 / CPU affinity
    - data/ (実行時に利用するファイル群)
      - monitoring.db (デフォルト)
      - paper_trading.db (ペーパー用)
      - kill.flag, stop_requested.flag, execution.pid
- logs/ （デフォルトログ出力先）

---

## 開発時の注意 / 推奨事項

- 本番運用前に `python -m kabusys.validate_config` を実行して設定に不備がないか確認してください。
- `.env` は絶対にリポジトリにコミットしないでください（`config_setup.py` もその旨を記載しています）。
- OpenAI を利用する機能は API コスト・レイテンシ・利用規約に注意して運用してください。
- Paper Trading 機能は本番 DB と完全に分離されるよう実装されています（`PAPER_TRADING_SQLITE_PATH` を確認）。
- ログは `kabusys.utils.logging_setup.setup_logging()` によりコンソールと日次ローテートファイルに出力されます。`LOG_DIR` を適切に設定してください。
- プラットフォーム依存の操作（プロセス優先度や CPU affinity）は `psutil` のアクセス権限に依存します。必要なら実行権限を確認してください。

---

README に書かれているコマンドや環境変数、ファイル/ディレクトリのパスはソース内のデフォルト値に基づいています。環境に合わせて .env を調整してください。追加の質問や特定の機能のドキュメント化（例: ExecutionEngine の詳細な起動引数や OrderManager の API 仕様）が必要であれば教えてください。