# KabuSys

日本株自動売買システム (KabuSys) の README。  
このリポジトリは、戦略研究・ポートフォリオ構築・発注実行・監視・AI支援スコアリング等を含む自動売買基盤の実装です。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの自動売買システムです。主な機能群は次の通りです。

- 市場データを用いたファクター計算・特徴量探索（research）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 発注実行エンジン（ExecutionEngine） — 本番 / ペーパートレード切替
- 監視コンポーネント（System / Trade / Risk モニタ、Kill Switch、アラート）
- AI を用いたニュースセンチメント評価・レジーム判定（OpenAI を利用）
- ペーパートレード検証レポート生成ツール

設計方針のポイント:
- データ保存に DuckDB（分析用）と SQLite（監視・発注ログ用）を併用
- 環境変数 / .env による設定管理（対話式ウィザード・検証スクリプトあり）
- 本番とペーパートレードを明確に分離（DB も分離）
- LLM 呼び出しはフェイルセーフに設計（失敗時はスコアを 0 にフォールバック等）

---

## 主な機能一覧

- config:
  - .env 自動ロード / Settings クラスによる集中管理
  - 対話式ウィザード: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
- execution:
  - ExecutionEngine（本番/ペーパー両対応）
  - BrokerClientFactory によりブローカー実装を切替
  - OrderManager / RiskManager / Reconciler 等の発注制御
- monitoring:
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、プロセス生存検知）
  - TradeMonitor（発注の滞留・異常約定検出等）
  - RiskMonitor（ドローダウンやポジション上限監視）
  - KillSwitch（リスク閾値到達で kill.flag を書き込み停止指示）
  - MonitoringEngine（複数モニタ統合のポーリング）
  - monitoring DB（SQLite）と永続化 API
- research:
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - forward returns / IC 計算 / 統計サマリ等
- portfolio:
  - 候補選定、等比重 / スコア加重、リスク調整、ポジションサイズ計算
- ai:
  - news_nlp: ニュース記事を OpenAI でセンチメント評価して ai_scores に格納
  - regime_detector: マクロ記事と ETF MA 乖離を組み合わせた市場レジーム判定
- tools:
  - paper_verification_report: ペーパートレードの性能検証レポート生成

---

## セットアップ手順

前提:
- Python 3.10 以上（Type hint の union 演算子 `|` 等を使用）
- git レポジトリルートに配置して利用する想定

1. リポジトリをクローン / 作業ディレクトリを作成
   (省略)

2. 仮想環境を作る（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows (PowerShell)
   ```

3. 必要パッケージをインストール

   requirements.txt が無い場合は最低限以下をインストールしてください:

   - duckdb
   - psutil
   - openai
   - PyYAML（config YAML 検証を行う場合）
   - （SQLite は標準ライブラリ）

   例:
   ```bash
   pip install duckdb psutil openai pyyaml
   ```

4. 環境変数の初期化（.env）
   - 対話式ウィザードで作成できます:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動で作成してください（.env.example を参照してください）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 本番運用時は KABUSYS_ENV を `live`、ペーパートレードは `paper_trading` に設定

5. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. ログディレクトリ / データディレクトリの確認
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/<app>.log
   - これらは環境変数で上書きできます（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_DIR）。

---

## 使い方

### 実行系: ExecutionEngine を起動する

- 本番（KABUSYS_ENV=live）やデフォルトの起動:
  ```bash
  export KABUSYS_ENV=live        # Unix/macOS
  # Windows (PowerShell): $env:KABUSYS_ENV = "live"

  python -m kabusys.run_execution
  ```

- ペーパートレードで起動（MockBroker を使用。DB は data/paper_trading.db に保存）
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 起動時、プロセス優先度が高に設定され、指定された SQLite / DuckDB に接続してエンジンを開始します。既に data/stop_requested.flag が存在する場合は起動を中止します。

- 停止:
  - ExecutionEngine 側は kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）や stop_requested.flag（data/stop_requested.flag）を監視して停止します。監視プロセスや管理運用でフラグファイルを書き込むことで安全に停止させられます。

### 監視: Monitoring を起動する

- 監視プロセスを起動:
  ```bash
  python -m kabusys.run_monitoring
  ```

- ポーリング間隔を環境変数で変更可能（デフォルト 60 秒）:
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- run_monitoring はプロセス優先度を高に設定し、監視用 DB に接続して SystemMonitor のポーリングループを実行します。停止トリガーは data/stop_requested.flag の存在検知です。

### 設定・検証

- .env の作成:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

### ツール: ペーパートレード検証レポート生成

- ペーパートレード DB を指定して検証レポートを生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- 出力は標準出力のテキストレポート（稼働率、注文成功率、レイテンシ等）です。

### AI 機能（OpenAI）

- ニューススコアリング / レジーム判定は OpenAI API キーを必要とします。環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に明示的に api_key を渡してください。
- 例:
  ```bash
  export OPENAI_API_KEY=sk-...
  # スクリプトから呼ぶ場合は AI モジュールの公開関数を利用
  # 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  ```

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- LOG_DIR — default: logs/
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）、default: 60
- OPENAI_API_KEY — OpenAI 使用時に必須

---

## ディレクトリ構成（主要ファイル・モジュール）

リポジトリルートの src/kabusys 配下を中心に説明します。

- src/kabusys/
  - __init__.py
  - config.py                — Settings / .env 自動読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証ツール
  - ai/
    - news_nlp.py             — ニュース NLP (OpenAI) によるスコア付け
    - regime_detector.py      — マクロ + MA によるレジーム判定
  - research/
    - factor_research.py      — ファクター計算（momentum, volatility, value）
    - feature_exploration.py  — forward returns, IC, summary
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数計算・スケーリング
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - monitoring/
    - monitoring_db.py        — SQLite のテーブル初期化 & 永続化 API
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — （発注関連監視）※詳細は実装参照
    - risk_monitor.py         — ドローダウン / ポジション数監視
    - kill_switch.py          — kill.flag の書き込み制御
    - monitoring_engine.py    — 各 Monitor を束ねるループ
    - alert_manager.py        — （アラート送信）※実装参照
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py        — ロギング初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - research/, portfolio/, ai/ のテスト可能な純粋関数群（DB 参照部分は DuckDB 接続を受け取る設計）

補足:
- data/ および logs/ は起動時に自動生成されることを想定していますが、ディレクトリのアクセス権限等をご確認ください。
- config/*.yaml（system_config.yaml 等）は外部設定用に想定されています。validate_config はこれらの存在と YAML パースをチェックします（PyYAML 必要）。

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START 等の設定に注意してください。validate_config は live 時に特別な警告を出します。
- OpenAI の利用はコストが発生します。API 呼び出しのレートやトークン制限に注意してください。
- 発注系は実際の金融商品への注文を行います。ペーパートレードで十分な検証を行ってから本番運用へ移行してください。
- ロギングはデフォルトで stdout + 日次ローテートされたファイル出力（logs/<app>.log）があります。LOG_DIR / LOG_LEVEL で調整可能です。

---

## 開発・テスト

- モジュールは可能な限り純粋関数・DI（DuckDB 接続や broker オブジェクト注入）で設計されているためユニットテストが書きやすくなっています。
- OpenAI 呼び出しなど外部 API は内部でラップしており、テスト時はモック（unittest.mock.patch 等）で置き換え可能です（ソース内にその旨の注記あり）。

---

必要に応じて README にチュートリアルや設定ファイルのサンプル（.env.example、config/*.yaml の雛形）を追加できます。追加希望があれば教えてください。