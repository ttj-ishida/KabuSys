# KabuSys

日本株向け自動売買システムのリポジトリ（軽量なコア実装群）。  
この README はコードベースの主要コンポーネント、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件
- セットアップ手順
- 環境変数（主なキー）
- 起動・利用方法（例）
- ツール / CLI
- ディレクトリ構成（主要ファイルと説明）
- 運用上の注意点

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
このリポジトリには、以下の主要機能が含まれます。

- ExecutionEngine（発注エンジン）とその周辺ユーティリティ
- Monitoring（システム監視 / リスク監視 / アラート）
- Portfolio Construction（銘柄選定・配分・ポジションサイジング）
- Research（ファクター計算・特徴量探索）
- AI モジュール（OpenAI を使ったニュースセンチメント / レジーム判定）
- 各種 CLI（環境設定ウィザード、設定検証、レポート生成 等）

設計方針として、可能な限り副作用を抑えた純粋関数群（ポートフォリオ計算等）と、DB（SQLite / DuckDB）を使った永続化を明確に分離しています。

---

## 主な機能一覧

- Execution
  - 実際のブローカー（kabuステーション）またはペーパートレード用 MockBroker を利用可能
  - 発注管理、秩序ある停止（kill.flag / stop フラグ）での安全停止
- Monitoring
  - CPU / メモリ / ディスク / プロセス稼働チェック
  - 注文滞留・約定異常・ドローダウン・ポジション上限の検出とログ化
  - Kill Switch（条件に応じて Execution を停止するフラグ）
- Portfolio
  - 候補選定（スコア順）、等分配・スコア加重、リスクベースのポジション決定
  - セクター上限適用、レジーム乗数適用
- Research
  - モメンタム / バリュー / ボラティリティ等のファクター計算（DuckDB）
  - 将来リターン計算・IC（Information Coefficient）などの評価関数
- AI
  - ニュース記事を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に保存
  - マクロニュース + ETF MA に基づく市場レジーム判定
- ツール
  - .env ウィザード（config_setup）
  - 設定検証（validate_config）
  - ペーパートレード検証レポート生成（tools.paper_verification_report）

---

## 必要条件

- Python 3.9+（型ヒントに依存する箇所があるためなるべく新しい 3.x を推奨）
- 必須 Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証を行う場合）
- SQLite（Python 標準ライブラリに含まれます）
- ネットワーク接続（実運用で kabu API / OpenAI を使う場合）

requirements.txt はリポジトリに含まれていない想定なので、必要なパッケージを手動でインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード
2. 仮想環境を作成して有効化（推奨）
3. 必要なパッケージをインストール（上記参照）
4. .env の準備
   - 対話式ウィザードで作成する（推奨）
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env.example を参考に手動で作成
5. 設定の検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告を厳密に扱いたい場合:
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリの作成（自動作成される場合もありますが事前に作ると安全）
   - data/
   - logs/

---

## 環境変数（主要なキー）

主な環境変数とデフォルト / 意味（抜粋）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading の場合、MockBrokerClient を使いデータは data/paper_trading.db に保存（本番 DB とは分離）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート用）
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動でクリアするか（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレード時の約定動作（instant|partial|never|reject）

その他はコード内の Settings クラスや config_setup の定義を参照してください。

---

## 起動・利用方法（代表的なコマンド）

- ExecutionEngine を起動（実行/ペーパー切替は KABUSYS_ENV に依存）
```
python -m kabusys.run_execution
```
- Monitoring を起動（デフォルトは本番 sqlite_path を使用）
```
python -m kabusys.run_monitoring
# MONITOR_POLL_INTERVAL で間隔を指定可能:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 設定ウィザード（.env 作成）
```
python -m kabusys.config_setup
```
- 設定検証（起動前チェック）
```
python -m kabusys.validate_config
```
- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report \
    --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```

---

## 各種ファイル / フラグ

- data/kill.flag — Kill Switch が書き込む停止フラグ（ExecutionEngine 停止のトリガー）
- data/stop_requested.flag — run_monitoring / run_execution の停止判定に使用されるフラグ
- data/execution.pid — Execution の PID ファイル（設定で変更可能）
- logs/<app>.log — 日次ローテーションでログ保存（logs ディレクトリ）

停止するにはフラグファイルを書き込むかプロセスを停止します。KillSwitch は RiskMonitor 等の評価結果に基づき kill.flag を生成します。

---

## ツール / CLI

- python -m kabusys.config_setup
  - 対話式に .env を生成 / 更新
- python -m kabusys.validate_config
  - .env と config/*.yaml の基本チェックを実行
- python -m kabusys.tools.paper_verification_report
  - ペーパートレード履歴から検証レポートを出力

---

## ディレクトリ構成（主要部のみ）

以下は src/kabusys 以下の主要ファイル・モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数 / 設定のロードと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト

- kabusys/execution/
  - execution_engine.py — エンジン本体（起動/セッション管理）
  - broker_factory.py — ブローカークライアント生成（本番 / Mock）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注関連コンポーネント

- kabusys/monitoring/
  - monitoring_db.py — SQLite を用いた監視ログ永続化層（テーブル初期化・CRUD）
  - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / プロセス監視
  - trade_monitor.py — 注文の滞留 / 約定異常検出（実装ファイルあり）
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - kill_switch.py — kill.flag の作成・管理
  - monitoring_engine.py — 各 Monitor を束ねてポーリング
  - alert_manager.py — アラート送信（LINE 等）※実装参照

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数決定、aggregate cap など
  - risk_adjustment.py — セクターキャップ、レジーム乗数
  - __init__.py — 公開関数のエクスポート

- kabusys/research/
  - factor_research.py — Momentum/Value/Volatility 等ファクター計算（DuckDB 利用）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー等
  - __init__.py

- kabusys/ai/
  - news_nlp.py — ニュース記事の OpenAI スコアリング（ai_scores 入力）
  - regime_detector.py — ETF MA + マクロニュースでレジーム判定

- kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成ツール

- kabusys/utils/
  - logging_setup.py — ログ設定ユーティリティ（コンソール + 日次ファイルローテーション）
  - process_priority.py — process priority / CPU affinity 設定ユーティリティ
  - その他ユーティリティ

- data/ （ランタイムに作られる想定）
  - monitoring.db （SQLite）
  - paper_trading.db （ペーパートレード用 SQLite）
  - kabusys.duckdb （DuckDB）
  - kill.flag / stop_requested.flag / execution.pid

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）での運用時は設定（特に APIキー / KILL フラグ関連 / LINE 通知設定）を慎重に確認してください。validate_config によるチェックを必ず行ってください。
- .env は絶対にバージョン管理に含めないでください（config_setup のヘッダにも警告あり）。
- Monitoring は環境に関係なく「本番用 sqlite_path」を使用する設計です（run_monitoring の挙動に注意）。
- ペーパートレード（KABUSYS_ENV=paper_trading）ではデータベースを分離しています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を用いる機能（news_nlp / regime_detector）は API 利用料が発生します。API キーと利用量に注意してください。
- プロセス優先度や CPU affinity の設定は OS 権限の制限により失敗する場合があります（ログに警告が出ます）。

---

必要に応じて README を拡張します。たとえば:
- 主要クラス（ExecutionEngine / MonitoringEngine / BrokerClientFactory）の詳しい設計と API サンプル
- config/*.yaml のテンプレートとフィールド説明
- 単体テストの実行方法

追加で欲しいセクションや深掘りしたい箇所を教えてください。