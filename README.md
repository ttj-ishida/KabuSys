# KabuSys

日本株自動売買システムの参照実装ライブラリ / 実行ユーティリティ群です。  
本リポジトリは以下の責務を持ちます。

- 注文実行エンジン（ExecutionEngine） / 発注管理
- 監視デーモン（Monitoring）・Kill Switch（停止シグナル）
- ポートフォリオ構築・ポジションサイズ計算（純粋関数群）
- リサーチ / ファクター計算（DuckDBベース）
- AI を使ったニュースセンチメント / レジーム判定（OpenAI）
- 開発支援ツール（.env ウィザード・設定検証・レポート生成）

バージョン: 0.1.0

---

## 主な機能一覧

- Execution
  - 実口座・ペーパートレードを切り替え可能（KABUSYS_ENV）
  - 発注管理、リスク管理、リコンシリエーション等のコンポーネントを組み合わせてセッションを実行
  - Paper Trading は専用 SQLite（デフォルト: data/paper_trading.db）へ記録し本番 DB と分離

- Monitoring
  - システムリソース（CPU/メモリ/ディスク）監視、データ鮮度チェック、プロセス生存監視
  - 監視ログを SQLite に永続化（data/monitoring.db）
  - リスク監視（ドローダウンやポジション上限）と Kill Switch（data/kill.flag）連携
  - アラート送信フック（AlertManager 経由で LINE 等）

- Portfolio（純粋関数）
  - 候補選定、等金額/スコア加重、セクター上限適用、レジーム乗数
  - ポジションサイズ（単元株丸め、aggregate cap）計算

- Research
  - DuckDB を利用したファクター計算（Momentum/Volatility/Value）
  - 将来リターンや IC（Information Coefficient）計算、統計サマリー

- AI
  - ニュース記事を OpenAI（gpt-4o-mini 等）でセンチメント化し ai_scores に保存
  - マクロニュース + ETF（1321）MA200 を合成した市場レジーム判定

- ツール
  - .env 対話ウィザード（python -m kabusys.config_setup）
  - 起動前設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

---

## 必要な依存ライブラリ（代表例）

- python 3.9+
- duckdb
- psutil
- openai (AI 機能を使用する場合)
- PyYAML（設定ファイル検証を行う場合に推奨）

requirements.txt は本リポジトリに含まれていないため、上記を pip でインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージをインストール）
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数の初期設定
   - 対話式ウィザードを使う（推奨）
     ```
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルートに `.env` が生成されます。
   - 手動で設定する場合は `.env` または環境変数で以下を設定します（主要項目）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV  -> development | paper_trading | live
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI機能使用時)
     - LOG_LEVEL, LOG_DIR など

4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   ```
   警告も厳密に扱いたい場合は `--strict` を付けると警告で失敗扱いになります。

5. データディレクトリ・ログディレクトリを用意（多くは自動作成されますが権限に注意）
   - デフォルト DB/ログパス: data/, logs/

---

## 使い方（主要スクリプト）

- ExecutionEngine を起動（デーモン的に実行）
  - 注意: KABUSYS_ENV により動作が変わります（paper_trading は MockBroker を使用）
  ```
  python -m kabusys.run_execution
  ```
  - paper_trading の場合は paper 用 DB が使われ、本番 DB と完全分離されます。
  - 起動中は pid ファイル（デフォルト: data/execution.pid）が作成されます。
  - 停止は `data/stop_requested.flag` を作るか、Execution 側が kill.flag を検出した場合に停止処理が走ります。

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を指定可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番 SQLite（Settings.sqlite_path）を使用してログを残します。
  - 監視ループの停止は `data/stop_requested.flag` の作成を検出して終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションか環境変数 `PAPER_TRADING_SQLITE_PATH` を使用。

- AI 機能
  - OpenAI API を使う機能（ニューススコア・レジーム判定）は `OPENAI_API_KEY` を設定してください。
  - 例: ai.score_news / ai.score_regime を直接呼ぶか、上位スクリプトから呼び出して利用します。

---

## 重要な運用メモ

- KABUSYS_ENV:
  - development: 開発用（発注なし等の挙動）
  - paper_trading: ペーパートレード（MockBrokerClient、独立 DB）
  - live: 本番（実際に発注）

- Kill / Stop
  - Kill Switch: `data/kill.flag` を書き込むと ExecutionEngine に対する停止シグナルとして扱われる（監視経由での評価により作成される）。
  - Stop flag: `data/stop_requested.flag` が存在すると run_execution / run_monitoring のメインループが終了します（運用停止用）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では推奨されません）。

- ログ:
  - デフォルトで `logs/` ディレクトリにアプリ別ログ（execution.log / monitoring.log 等）が日次ローテーションで保存されます。
  - ログレベルは `LOG_LEVEL` 環境変数または Settings.log_level で制御します。

- DB:
  - DuckDB: 分析用データベース（デフォルト: data/kabusys.duckdb）
  - SQLite: 監視ログや paper trading の注文履歴（data/monitoring.db, data/paper_trading.db）

---

## ディレクトリ構成（抜粋）

以下は主要なパッケージ構成の抜粋です。詳細はリポジトリ内の `src/kabusys` を参照してください。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みと Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 実行関連コンポーネント（engine / broker / order_manager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
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
  - tools/
    - paper_verification_report.py

---

## よくあるトラブルと対処

- .env がロードされない / 自動ロードを抑止したい:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます。

- ログファイルが作成されない:
  - `LOG_DIR` 環境変数や権限を確認してください。ディレクトリ作成に失敗した場合、コンソール出力のみになります（警告が出ます）。

- OpenAI API 呼び出しで RateLimit / 5xx が発生:
  - AI モジュールはリトライ（指数バックオフ）を実装していますが、APIキー/クォータを確認してください。Fail-safe 実装により重大な例外は通常上位に伝播しません（スコアを 0 にフォールバック等）。

- DuckDB / SQLite の互換性:
  - DuckDB バージョンにより executemany の空リスト取り扱いなど互換性差があるため、AI / DB 書き込み部で注意して実装されています。問題があれば DuckDB のバージョンアップ/ダウングレードを検討してください。

---

## 開発・テストのヒント

- MonitoringEngine.run_once を使えばポーリングを1回だけ実行でき、ユニットテストが書きやすい設計です。
- portfolio / research の関数群は副作用がなく純粋関数になっているため、単体テストが容易です。
- OpenAI を呼ぶ箇所は内部呼び出し関数（_call_openai_api 等）をモックしやすく設計されています。

---

README はここまでです。プロジェクトの特定箇所（ExecutionEngine の細かい設定、Broker 実装、AlertManager の実装など）について詳しいドキュメントや実行上の疑問があれば、対象ファイル名や機能を指定して質問してください。