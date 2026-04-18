# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリには、監視（Monitoring）、発注（Execution）、リサーチ、ポートフォリオ構築、AI（ニュース NLP / レジーム判定）などの主要コンポーネントが含まれます。

---

## プロジェクト概要

KabuSys は日本株に対する自動売買基盤を構成するモジュール群です。  
主な目的は以下のとおりです。

- データ基盤（DuckDB / SQLite）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- 発注エンジン（実際のブローカー API / Mock を切替可能）
- 監視（システム・注文・リスクを定期チェック）
- AI を用いたニュースセンチメント / レジーム判定
- ペーパートレード検証レポート生成

設計方針としては「本番と検証の分離」「ルックアヘッドバイアス回避」「外部 API 呼び出しを明示的に管理」などを重視しています。

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（.env / .env.local）
  - 設定ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）

- 実行（Execution）
  - 実際のブローカー / Mock ブローカーの切替（KABUSYS_ENV に依存）
  - リスクマネジメント（position limit、drawdown 等）
  - 実行プロセスの PID 管理・停止フラグ連携（data/execution.pid, data/kill.flag）

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status / trade_logs / risk_logs / dashboard 等の永続化（SQLite）
  - kill.flag の自動書き込み（危険検出時に ExecutionEngine を停止）

- リサーチ
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- ポートフォリオ構築
  - 候補選定・重み計算（等配分・スコア重み）
  - 単元株丸め・リスクベースの株数計算
  - セクターキャップ適用、レジーム乗数

- AI 関連
  - ニュース NLU（OpenAI）を用いた銘柄別センチメント付与（ai_scores テーブルへ）
  - マクロニュース + ETF MA を用いた市場レジーム判定（market_regime テーブルへ）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 必要条件 / 依存ライブラリ

- Python 3.9+（型アノテーション等に合わせて推奨）
- ライブラリ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時のみ必須）
- 標準ライブラリ: sqlite3, logging, datetime, os, pathlib 等

（requirements.txt は本リポジトリに含まれていない場合があります。環境に合わせてインストールしてください。）

例:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開
2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```
4. 環境変数設定
   - 対話式ウィザードで .env を作成
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（ルートに配置）。主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR など
5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```
6. 必要なディレクトリの作成（通常は起動スクリプトが自動作成するが事前に作る場合）
   ```
   mkdir -p data logs
   ```

---

## 使い方

主要なスクリプト／エントリポイントの実行例を示します。

- 実行エンジンを起動（Execution）
  - 本番/開発/ペーパーは KABUSYS_ENV に依存します。
  - paper_trading の場合、MockBrokerClient を使用し paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  ```
  # 例: ペーパートレード（環境変数で切替）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - 起動時に data/stop_requested.flag がある場合は起動を中止します。
  - 実行中は data/execution.pid に PID が書かれます。停止フラグは data/kill.flag（KillSwitch）や stop_requested.flag を利用します。

- 監視ループを起動（Monitoring）
  ```
  # MONITOR_POLL_INTERVAL でポーリング間隔（秒）をオーバーライド可能（デフォルト: 60）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に本番用 sqlite_path（settings.sqlite_path）を参照します（環境によらず）。
  - data/stop_requested.flag を置くとループを終了します。

- 設定ウィザード / 検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（ニューススコア / レジーム判定）
  - OPENAI_API_KEY を設定し、対応する関数を呼び出します（ライブラリ API）。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ。

注意点:
- stop_requested.flag / kill.flag の利用方法
  - data/stop_requested.flag: 外部から監視 / 実行ループを静かに停止させたい場合に使用
  - data/kill.flag: KillSwitch により書き込まれる（重大リスク検出時）。ExecutionEngine はこれを検出して停止します。
- ログはデフォルト `logs/<app_name>.log` に日次ローテーションで保存されます。

---

## 主要ディレクトリ構成

以下は src/kabusys 配下の主要ファイルと簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（.env 自動ロード含む）
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル作成 / 永続化用 API（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
      - システムリソース監視、データ鮮度チェック、process 停止検出
    - risk_monitor.py
      - ドローダウン・ポジション上限の監視
    - trade_monitor.py
      - （トレード関連監視: 滞留注文や約定異常など）※ソース内に実装あり
    - kill_switch.py
      - kill.flag を生成するロジック
    - monitoring_engine.py
      - 各 Monitor を束ねるエンジンとアラート連携
    - alert_manager.py
      - LINE などへの通知（ソース参照）
  - execution/
    - ブローカーファクトリ、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算
    - position_sizing.py
      - 株数計算、単元丸め、aggregate cap 処理
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数
  - research/
    - factor_research.py
      - momentum / volatility / value 等のファクター計算（DuckDB を利用）
    - feature_exploration.py
      - 将来リターン、IC、統計サマリ関数
  - ai/
    - news_nlp.py
      - raw_news を集約し OpenAI へ投げて銘柄別スコアを ai_scores に保存
    - regime_detector.py
      - ETF MA とマクロセンチメントの合成によるレジーム判定
  - tools/
    - paper_verification_report.py
      - ペーパートレード DB から検証レポートを生成

その他:
- data/
  - monitoring DB、paper_trading DB、フラグファイル（kill.flag / stop_requested.flag）等を配置する既定ディレクトリ
- logs/
  - ログファイルを出力する既定ディレクトリ

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（動作モード）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: DB ファイルパス
- LOG_LEVEL / LOG_DIR: ログの設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）

---

## 運用上の注意

- KABUSYS_ENV=live の場合は、本番設定（LINE 通知、kill_flag の扱いなど）を慎重に確認してください。validate_config は live の追加チェックを行います。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI など外部 API を利用する操作はレート制限やコストに注意してください（リトライ・バックオフは実装済みですが運用の配慮は必要です）。
- SQLite / DuckDB のバックアップ・権限管理を運用フェーズで検討してください。

---

## 開発・貢献

バグ修正や機能追加の際は、まずコードの意図を確認のうえテストを追加してください。  
大きな変更は事前に設計方針（特にリスク管理・発注ロジック）について議論してください。

---

ライセンスや詳細な開発フローはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。