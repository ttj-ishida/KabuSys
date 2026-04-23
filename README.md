# KabuSys

日本株向け自動売買システムのコードベース README。  
（英語名: KabuSys）

この README はこのリポジトリに含まれる主要コンポーネントの概要、セットアップ方法、実行例、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的とした構成モジュール群です。主な機能は以下のとおりです。

- 発注エンジン（ExecutionEngine） — ブローカークライアント経由で注文を作成 / 管理する。
- 監視（Monitoring） — システム状態・取引状態・リスクを定期チェックしアラートやキルスイッチを制御。
- ポートフォリオ構築（Portfolio） — 候補選定、重み算出、ポジションサイズ計算、セクター制約など。
- リサーチ（Research） — DuckDB上の時系列データを使ったファクター計算、特徴量解析。
- AI 支援（AI） — OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価やレジーム判定。
- ユーティリティ群 — ログ設定・プロセス優先度設定・設定ウィザード・設定検証等。

設計方針として、実取引（live）とペーパートレード（paper_trading）を明確に分離し、データベース分離、フェイルセーフ（APIエラー時のフォールバック）等を備えています。

---

## 主な機能一覧

- ExecutionEngine（起動スクリプト: run_execution.py）
  - live / paper_trading を切り替え可能
  - RiskManager による発注制約（最大ポジション比率など）
  - OrderRepository / OrderManager / Reconciler による注文追跡

- Monitoring（起動スクリプト: run_monitoring.py）
  - CPU/メモリ/ディスク・プロセス生存確認・データ鮮度
  - トレード/リスクの監視および Kill Switch の評価
  - ログ・監視結果は SQLite（monitoring.db）に永続化

- Portfolio（portfolio/*）
  - 候補選定（スコア/順位）
  - 重み付け（等配分、スコア加重）
  - ポジションサイズ決定（リスクベース・ユーティリティ制限・単元丸め）
  - セクターキャップ、レジーム乗数

- Research（research/*）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB上で実行）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ

- AI（ai/*）
  - news_nlp: ニュースを LLM でセンチメント評価し ai_scores に格納
  - regime_detector: ETF とマクロニュースを組み合わせて市場レジーム判定

- ツール
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report

---

## 前提（Prerequisites）

- Python 3.10 以上（PEP 604 の型表記 `X | Y` を使用）
- pip を用いた依存ライブラリインストールが可能であること

主要依存パッケージ（必須 / 任意）:
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の検証を行う場合、オプション）

例（仮想環境内で）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（開発用にテスト・リンター等があれば追加でインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # もし requirements.txt があれば
   # または最低限:
   pip install duckdb psutil openai PyYAML
   ```

3. .env の初期作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは以下のような環境変数を作成します（代表例）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV = development | paper_trading | live
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
   - LOG_LEVEL
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
   - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、開発用）

4. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いにできます
   python -m kabusys.validate_config --strict
   ```

5. ディレクトリの確認（logs, data 等は自動作成されますが権限に注意）

注意:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env をロードしません（テスト用）。
- 本番（live）での起動は十分な確認後に実行してください（KILL_FLAG_CLEAR_ON_START=1 は危険）。

---

## 使い方（実行例）

### 実行エンジン起動（Execution）
- 通常（デフォルト env を利用）:
  ```bash
  python -m kabusys.run_execution
  ```
- ペーパートレード（MockBrokerClient を使用し data/paper_trading.db に記録）
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
- 起動時、既に data/stop_requested.flag があると起動せず終了します。

- 停止方法:
  - 監視／運用プロセスに対しては stop ロジックとしてプロジェクトルートの data/stop_requested.flag を作成します（存在検出してエンジンを停止）。
  - KillSwitch により data/kill.flag が書き込まれると Execution 側が停止対象となります（KillSwitch は監視エンジンが書き込む）。

### 監視プロセス起動（Monitoring）
- 監視ループを開始:
  ```bash
  python -m kabusys.run_monitoring
  ```
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
- 監視プロセスは Settings の sqlite_path（monitoring DB）を使ってログを保持します（duckdb も併用）。

### Paper Trading 検証レポート
- ペーパートレード DB に対する検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

### AI 機能（ニュース NLP / レジーム判定）
- OpenAI API キーが必要: 環境変数 OPENAI_API_KEY をセット
- ニューススコア生成は kabusys.ai.news_nlp.score_news を呼ぶか、ラッパー CLI を用意している場合それを利用
- 実行時は API レート制限やエラーに備えてリトライ/フォールバックが組み込まれています

---

## 環境変数（主なもの）

- 必須（少なくとも実行時必要）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行制御 / DB:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時使用）
  - PID_FILE_PATH: data/execution.pid（デフォルト）

- ロギング / モニタ:
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: デフォルト logs/
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

- AI:
  - OPENAI_API_KEY: OpenAI 呼び出し用

- Kill Switch 関連:
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 1/0（development でのみ 1 推奨）

（config_setup.py を実行すると主要項目を対話式で入力できます）

---

## 停止・フラグファイル

- 実行中のエンジン・監視はプロジェクトルートの data/stop_requested.flag の存在を監視します。手動で停止したい場合はこのファイルを作成してください。
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（自動/監視経由）。
- 起動時に kill.flag を自動消去する設定（KILL_FLAG_CLEAR_ON_START=1）がありますが、本番では 0 を推奨します。

---

## ロギング

- ログは標準出力（コンソール）とファイル（logs/<app_name>.log）に出力されます。ログは日次ローテート（30日保存）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されています。

---

## ディレクトリ構成（主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定の読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
  - execution/               — 発注エンジン関連コンポーネント（OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
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
    - news_nlp.py
    - regime_detector.py
  - data/                    — （ランタイム生成）DBファイル・フラグファイル等を配置する想定
  - logs/                    — ログファイル出力先（自動生成）

注: 一部サブパッケージ（execution 内の詳細実装など）は README 内では省略しています。各モジュール先頭に docstring があるため参照してください。

---

## 注意事項 / トラブルシューティング

- プロセス優先度設定（psutil）や CPU affinity は実行環境により権限不足で失敗することがあります。その場合は警告ログを出して処理を続行します。
- DuckDB / SQLite ファイルはデフォルトで data/ 配下に作成されます。権限やディスク容量に注意してください。
- OpenAI を用いる AI 機能は API キーと料金発生のリスクがあるため、テスト環境やペーパートレードで十分に検証してから本番へ展開してください。
- PyYAML が無い場合、validate_config は YAML 内容の検証をスキップします（警告）。

---

## 開発・拡張メモ

- research や portfolio モジュールは純粋関数的設計（副作用なし）で実装されています。単体テストが書きやすい設計です。
- AI モジュールは OpenAI SDK のエラーに対してリトライロジックを備えていますが、API 仕様の変更があれば修正が必要です。
- config/*.yaml（strategy や risk 等）は config_setup / validate_config を通じて生成・検証する想定です。サンプルは `config/` に置くか、scripts/generate_config.py を利用してください（プロジェクトに該当スクリプトがある場合）。

---

必要であれば、README に実際の .env.example の内容やよくある操作（例えば kill.flag を手動で消すコマンド、ログの確認例、監視アラートの例メッセージ等）を追加できます。どの情報を優先して追記しますか。