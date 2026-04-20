# KabuSys

日本株向け自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI を組み合わせた日本株自動売買基盤の一部実装を含みます。  
README はこのコードベースの概要、セットアップ、使い方、主要コンポーネントの説明を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群から構成されています。

- データ処理・リサーチ（DuckDB 経由のファクター計算、将来リターン計算）
- ポートフォリオ構築（候補選定、重み計算、株数算出、リスク調整）
- Execution（発注エンジン・ブローカークライアントの抽象化。paper_trading モードあり）
- 監視（System / Trade / Risk Monitoring、Kill Switch、アラート）
- AI 補助（ニュースセンチメント評価、レジーム判定 — OpenAI API を使用）
- 運用ツール（.env ウィザード、設定検証、Paper Trading レポート生成 等）

設計上の方針として、実際の発注 API 呼び出しは BrokerClient の抽象を介して分離され、paper_trading（モック）と本番を切り替えられるようになっています。監視は SQLite、分析は DuckDB を想定しています。

---

## 主な機能一覧

- 設定管理（src/kabusys/config.py）
  - .env の自動読み込み（プロジェクトルート基準）
  - 必須/任意設定の抽象化（Settings クラス）

- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV による paper_trading 切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）

- 監視機能
  - system_monitor: CPU/メモリ/Disk、データ鮮度、Execution プロセス監視
  - trade_monitor: 注文滞留や約定異常の検出（trade_logs を参照）
  - risk_monitor: ドローダウン・ポジション上限の検出とログ記録
  - kill_switch: 条件により data/kill.flag を書き込むことで ExecutionEngine を停止

- ポートフォリオ構築（純粋関数）
  - 候補選定 / スコア・等配分ウェイト / position sizing / セクター制約 / レジーム乗数

- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC・統計サマリ等

- AI（OpenAI）
  - news_nlp: ニュースを LLM でセンチメント評価し ai_scores に書込み
  - regime_detector: マクロ記事 + ma200 を合成し市場レジームを決定

- 運用ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env / config/*.yaml の起動前検証
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

---

## 必要要件（概略）

- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML の検証時にあると便利）
- SQLite（標準ライブラリで利用）
- （オプション）kabuステーション API に接続する場合は専用クライアント設定とパスワード

インストール例:
```
pip install duckdb psutil openai PyYAML
```
※ 実プロジェクトでは requirements.txt を用意して pip install -r requirements.txt を使用してください。

---

## セットアップ手順（推奨フロー）

1. リポジトリをクローンし、仮想環境を作成して依存をインストール。

2. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - ウィザードは .env を作成／更新します。生成された .env は絶対にバージョン管理にコミットしないでください。

3. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります。

4. データディレクトリ等の確認
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH で変更可)
     - SQLite (監視): data/monitoring.db (SQLITE_PATH)
     - Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
     - PID/kill flag: data/execution.pid, data/kill.flag
     - ログディレクトリ: logs/ (LOG_DIR 環境変数で変更可)

5. （必要なら）DuckDB に prices_daily / raw_financials 等のテーブルを準備

6. OpenAI を利用する場合:
   - 環境変数 `OPENAI_API_KEY` に API キーを設定
   - AI 機能はキー未設定時にエラーを投げる箇所があります（明示的に api_key を渡すことも可能）

---

## 使い方（基本コマンド）

- ExecutionEngine を起動（本番 or paper_trading は KABUSYS_ENV）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録されます。
  - 起動時に data/stop_requested.flag が既に存在すると起動せず終了します。
  - 起動中に stop フラグが作成されるとエンジンに停止命令を送り安全に終了します。

- Monitoring を起動（常時監視）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルを作成・更新します。
  - 停止は data/stop_requested.flag ファイルの作成で行えます（run_monitoring はこのファイル検出でループを抜けます）。

- Paper Trading 検証レポート（任意期間）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルトの DB は環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。

- 設定ウィザード / 検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

---

## 主要環境変数（抜粋）

必須（最低限セットが必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API（システムによって必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注する場合必須）

重要なオプション（デフォルト値）
- KABUSYS_ENV — 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（例: data/paper_trading.db）
- LOG_LEVEL — ログレベル（INFO 等）
- LOG_DIR — ログディレクトリ（デフォルト logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

その他は config_setup.py のウィザードで案内されます。

---

## ロギング

- 全起動スクリプトは共通のロギングセットアップ（kabusys.utils.logging_setup.setup_logging）を使用します。
- デフォルトではコンソール出力（stdout）と日次ローテートされたファイルログ（logs/<app_name>.log）を出力します。
- LOG_DIR / LOG_LEVEL により設定を変更できます。

---

## データファイルとフラグ

- 停止制御:
  - run_execution/run_monitoring はプロジェクトの data/stop_requested.flag を監視して停止動作を行います。
  - kill flag（Kill Switch）は data/kill.flag に書き込まれ、ExecutionEngine に停止命令を送るために使用されます（監視コンポーネントが書き込みます）。

- DB:
  - 監視用 DB: SQLite（init_monitoring_db が必要テーブルを作成）
  - 分析用 DB: DuckDB

---

## ディレクトリ構成（主要ファイル）

プロジェクトルート下の `src/kabusys` を中心に記載します。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 起動前検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP スコアリング (OpenAI)
    - regime_detector.py         — レジーム判定 (OpenAI + ma200)
  - monitoring/
    - monitoring_db.py           — SQLite の永続化層
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - system_monitor.py          — システム / データ鮮度監視
    - trade_monitor.py           — (trade 関連監視) ※詳細はコード参照
    - risk_monitor.py            — ドローダウン・ポジション監視
    - kill_switch.py             — Kill Switch の実装
    - alert_manager.py           — (アラート送信管理) ※存在（参照）あり
  - execution/
    - execution_engine.py        — 実行エンジン（セッション管理）
    - broker_factory.py          — BrokerClient の生成・抽象化
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py       — 候補選定 / weight 計算
    - position_sizing.py         — 株数算出・制約適用
    - risk_adjustment.py         — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py         — ファクター計算（momentum / value / volatility）
    - feature_exploration.py     — IC / forward return / summary
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 用検証レポート
  - utils/
    - logging_setup.py           — ログ共通設定
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/*.py, portfolio/*.py, research/*.py など多数のサブモジュール
- data/                           — デフォルトの DB / flag / pid を置く想定ディレクトリ
- logs/                           — ログ出力先（デフォルト）

---

## 運用上の注意点

- KABUSYS_ENV=live の設定は本番環境です。validate_config は live 時に追加警告を出します。LINE 通知など本番用設定が未設定だとアラートが届きません。
- .env の値（特にパスワードやトークン）はプレースホルダのままにしないでください。
- run_monitoring は本番 sqlite_path を使用します（環境にかかわらず監視ログは本番 DB を想定）。
- paper_trading モードは本番 DB と分離するため PAPER_TRADING_SQLITE_PATH を使用します。
- AI 機能は OpenAI API との通信に依存します。API の利用制限やコストを考慮してください。

---

## 開発・拡張のヒント

- DuckDB 接続は各モジュールに注入しており、テスト時は一時 DB を渡すことで副作用を抑えられます。
- AI 呼び出し部分（news_nlp._call_openai_api など）はテスト時にモック差し替えしやすい設計になっています。
- monitoring_db.init_monitoring_db は冪等でスキーマの簡単なマイグレーションも行います。

---

## 参考コマンドまとめ

- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config [--strict]
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README を更新します。特に実際のブローカー接続や config/*.yaml の仕様、requirements.txt、起動サービス（systemd / docker-compose など）のサンプルを追加すると運用が容易になります。