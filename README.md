# KabuSys

日本株向け自動売買システムのコアライブラリ群。システム監視、注文実行（本番 / ペーパートレード）、ポートフォリオ構築、ファクター計算、ニュース NLP（LLM）連携などの機能を提供します。

> バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。主な役割は以下の通りです。

- ExecutionEngine：ブローカークライアント経由の発注管理（本番／ペーパー切替対応）
- Monitoring：システム健全性・注文状態・リスクの定期監視とアラート、Kill Switch
- Portfolio：候補銘柄選定・重み計算・ポジションサイズ決定・セクター制約
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI：ニュースのセンチメントを LLM（OpenAI）で評価し ai_scores に格納／市場レジーム判定
- ユーティリティ：設定管理、ログ設定、プロセス優先度制御など

設計方針の一部：
- DuckDB / SQLite をデータ永続化に使用
- 環境変数（.env / .env.local）で設定を管理
- 本番（live）／ペーパー（paper_trading）／開発（development）モードをサポート
- OpenAI API は失敗に対してフェイルセーフな設計（部分失敗を許容）

---

## 主な機能一覧

- 実行（Execution）
  - BrokerClientFactory による本番／モック（ペーパートレード）クライアント選択
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）にロギング

- 監視（Monitoring）
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / Execution プロセス存在チェック
  - TradeMonitor：発注ログの監視（滞留注文、約定異常など）
  - RiskMonitor：ドローダウン・ポジション数監視、ダッシュボード更新、リスクログ記録
  - KillSwitch：閾値超過時に data/kill.flag を書き込むことで ExecutionEngine を停止
  - MonitoringEngine：各モニタのポーリング・アラート発行

- ポートフォリオ構築
  - 候補選定（スコア降順）
  - 等金額／スコア重み・リスクベースのポジションサイズ計算
  - セクターキャップ・レジーム乗数の適用

- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ

- AI（OpenAI）
  - ニュース記事を LLM に送信して銘柄ごとのセンチメント（ai_scores）を作成
  - マクロニュースの LLM 結果と ETF MA 乖離を合成して日次の市場レジーム判定

- ツール
  - 設定ウィザード（.env の対話式作成）: kabusys.config_setup
  - 設定検証 CLI（.env / config/*.yaml の簡易チェック）: kabusys.validate_config
  - Paper Trading 検証レポート生成: kabusys.tools.paper_verification_report

- ユーティリティ
  - ログ設定の集中管理（コンソール + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - 設定管理クラス（Settings）: 環境変数取得・バリデーション

---

## 前提 / インストール

推奨 Python バージョン: 3.10+

必須・推奨パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml を詳しく検証したい場合に任意）
- （標準ライブラリ）sqlite3 等

pip での簡単なインストール例:
```bash
python -m pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / 展開する。

2. Python の依存パッケージをインストールする（上記参照）。

3. .env を作成する（2つの方法）:
   - 対話式ウィザードを使う（推奨）:
     ```bash
     python -m kabusys.config_setup
     ```
     デフォルトでプロジェクトルートの `.env` に保存します。
   - 手動で作成: .env.example（存在する場合）を参考に必要な環境変数を設定。

4. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   その他の主な環境変数:
   - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
   - LOG_LEVEL（DEBUG/INFO/…）
   - OPENAI_API_KEY（AI 機能を使う場合）

5. データディレクトリやログディレクトリを作る（コード側で自動作成することもありますが事前作成推奨）:
   - data/
   - logs/

6. 設定検証（任意）:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（実行例）

- 監視ループを起動（監視プロセス）:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は Settings が指す sqlite_path を常に使用します。

- ExecutionEngine を起動（発注エンジン）:
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、ペーパートレード専用 DB（data/paper_trading.db）に記録されます。
  - エンジン停止は data/stop_requested.flag や Kill Switch (data/kill.flag) により制御されます。
  - 実行時に PID ファイル（既定: data/execution.pid）が作られます。

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- 設定ウィザード（.env 作成 / 更新）:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- ログ:
  - デフォルトログディレクトリ: logs/
  - アプリケーション名ごとにファイルが作成されます（例: logs/execution.log, logs/monitoring.log）。

停止・Kill Switch の仕組み:
- KillSwitch は RiskMonitor 等が判定した場合に `data/kill.flag` を作成します。ExecutionEngine は起動時/ループ内でこのフラグを確認し停止します。
- 管理者が強制停止を要求する場合は `data/stop_requested.flag` を作成することで run_monitoring / run_execution のループを終了させることができます。

---

## 環境変数一覧（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用関連
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）

- DB パス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

- AI
  - OPENAI_API_KEY

- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

- ペーパートレード
  - PAPER_FILL_MODE: instant | partial | never | reject

- その他
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）

（詳細は `kabusys.config.Settings` クラスをご参照ください）

---

## 開発者向けメモ

- 設定の自動ロード:
  - デフォルトでプロジェクトルートの `.env` および `.env.local` を自動で読み込みます（OS 環境変数が優先されます）。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- DuckDB / SQLite:
  - リサーチ系（ファクター計算など）は DuckDB 接続を受け取り SQL を実行します。prices_daily / raw_financials 等のテーブルを参照します。
  - 監視・発注ログは SQLite（monitoring.db / paper_trading.db）へ書き込みます。

- OpenAI 呼び出しは外部 API のためテストで差し替え可能に設計しています（内部関数を patch する等）。

- ロギング:
  - 共通の setup_logging を用いることでコンソール + 日次ファイル出力を統一しています。

---

## ディレクトリ構成

リポジトリ内の主要なディレクトリ／ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
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
  - tools/
    - paper_verification_report.py
  - data/ (実行時に生成)
  - logs/ (実行時に生成)
- config/
  - *.yaml (system_config.yaml 等 — 一部ツールが参照)

※上記は主要ファイルの抜粋です。実際のツリーはリポジトリの状態により多少異なる可能性があります。

---

## よくある運用フロー（例）

1. `.env` を作成（config_setup）し、`python -m kabusys.validate_config` でチェックする。
2. データ投入（prices_daily / raw_financials / raw_news 等）を用意（DuckDB）。
3. 毎朝:
   - `python -m kabusys.run_execution` を起動してトレード日セッションを開始。
   - 別プロセスで `python -m kabusys.run_monitoring` を常時起動し健全性を監視。
4. 週次／任意で `python -m kabusys.tools.paper_verification_report` を実行してペーパー運用の評価。

---

## ライセンス / 貢献

（この README テンプレートにはライセンス情報や貢献ガイドは含まれていません。プロジェクトに適した LICENSE を追加してください。）

---

README に記載してほしい追加情報や、実際の運用環境（systemd / Docker / コンテナ化等）でのデプロイ手順をご希望でしたら教えてください。必要に応じてサンプル systemd ユニットや Dockerfile 例も作成します。