# KabuSys

日本株向け自動売買・研究プラットフォームのミニマル実装（ライブラリ + 起動スクリプト群）

このリポジトリは、アルゴリズムトレーディングの主要コンポーネント（データ処理、ファクター計算、ポートフォリオ構築、発注実行、監視、AI支援のニュース解析など）をモジュール化して実装したものです。運用用途にも配慮した設計（.env ウィザード、設定検証、監視用 DB、Kill Switch 等）を含みます。

バージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 機能一覧
- 必要な依存関係
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要）
- 実行時の挙動メモ
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを想定したコードベースです。主な役割は以下です。

- データベース（DuckDB / SQLite）を用いたデータ保存・分析
- ファクター計算（モメンタム・バリュー・ボラティリティ等）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- 発注実行エンジン（paper_trading モードあり）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ニュースの NLP スコアリング（OpenAI を利用したセンチメント算出）
- 各種ツール（.env ウィザード、設定検証、Paper Trading レポート生成 など）

設計上、実際のブローカー接続はファクトリ経由で抽象化されており、`paper_trading` 環境では MockBrokerClient を用いて本番 DB と分離された `data/paper_trading.db` にログを残します。

---

## 機能一覧

- 環境設定ウィザード (.env の対話的作成) — `python -m kabusys.config_setup`
- 設定検証 CLI — `python -m kabusys.validate_config`
- ExecutionEngine 起動スクリプト（発注エンジン） — `python -m kabusys.run_execution`
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用
  - paper_trading 用 DB を分離して記録
- Monitoring 起動スクリプト（定期ポーリング） — `python -m kabusys.run_monitoring`
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト: 60 秒）
  - 監視ログは SQLite（monitoring.db）へ保存
- Kill Switch（データ/ファイルベース）による Engine 停止
- Paper Trading 検証レポート生成ツール — `python -m kabusys.tools.paper_verification_report`
- 研究用モジュール（DuckDB を使ったファクター計算 / 特徴量探索）
- ニュース NLP（OpenAI で銘柄ごとのスコアを算出）
- ロギングの統一化ユーティリティ（コンソール + 日次ローテーションファイル）

---

## 必要な依存関係

最低限の実行には以下が必要です（pip 等でインストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定 YAML 検証を行う場合に推奨。ただし必須ではない）

例:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 展開する
2. 仮想環境を作成して依存をインストール
3. .env ファイルを作成（ウィザード推奨）

対話的ウィザードで .env を作る:
```
python -m kabusys.config_setup
```
ウィザードに従い、必須値（J-Quants リフレッシュトークン、kabuステーション API パスワード 等）を入力してください。

重要: `.env` を Git にコミットしないでください（ウィザードのヘッダにも記載されています）。

4. 設定検証:
```
python -m kabusys.validate_config
```
必要に応じて `--strict` をつけると警告も失敗扱いになります。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（発注エンジン）
  - 本番／ペーパーは KABUSYS_ENV により切り替え
  ```
  python -m kabusys.run_execution
  ```

- Monitoring を起動（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を上書き:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- .env ウィザード（設定ファイル作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（SQLite パスを指定可能）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- ライブラリ呼び出し（プログラムから利用）
  - 研究用ファクター計算:
    - kabusys.research.calc_momentum / calc_volatility / calc_value
  - ニュース NLP:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 環境変数（主要）

主に .env で管理します。代表的なもの:

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）

- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）

- ログ
  - LOG_LEVEL — DEBUG/INFO/WARNING/...
  - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）

- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 使用時）

- 監視 / Kill Switch
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で有効。production では 0 推奨）

- その他
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - PAPER_FILL_MODE — ペーパートレードの約定シミュレーションモード（instant/partial/never/reject）

env ファイルの雛形はウィザードで生成されます。

---

## 実行時の挙動メモ / 運用に関する注意

- run_execution / run_monitoring 両スクリプトは起動時にプロセス優先度を "high" にセットしようとします（プラットフォーム依存）。
- run_execution は `data/stop_requested.flag` を監視しており、フラグが存在する場合は起動しないかセッションを停止します。Monitoring も同様に停止フラグを検出します。
- Kill Switch（監視モジュール）はリスクやドローダウン等の条件で `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。起動時の `KILL_FLAG_CLEAR_ON_START=1` は慎重に扱ってください（本番で自動クリアは危険）。
- Monitoring は監視ログ（system_status、trade_logs、risk_logs、positions、dashboard）を SQLite に永続化します。スキーマのマイグレーション処理も実装済みです。
- Paper Trading モードは本番 DB と分離され、別ファイルに記録されます（デフォルト: data/paper_trading.db）。実際のブローカーに注文を送らないため検証に利用できます。
- AI 機能を利用する場合は OpenAI API キーが必要です。API 呼び出し時はリトライ・バックオフや応答バリデーションが実装されていますが、API コスト・レート制限に注意してください。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートの src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + LLM）
    - __init__.py
  - research/
    - factor_research.py      — momo/value/volatility ファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC・統計要約
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ & ラッパー
    - system_monitor.py
    - trade_monitor.py        — （trade 側モニタ: ロジックあり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/（実行時に使用される想定ファイル）
    - kabusys.duckdb (default: data/kabusys.duckdb)
    - monitoring.db (default: data/monitoring.db)
    - paper_trading.db (paper_trading 用, default: data/paper_trading.db)
    - kill.flag, stop_requested.flag, execution.pid などのフラグ / PID ファイル

---

## 参考・補遺

- logging は `kabusys.utils.logging_setup.setup_logging()` で統一して設定します。ファイル出力は日次ローテーション（30世代保持）です。ログディレクトリが作成できない場合はコンソール出力のみになります。
- DuckDB を分析用データベースとして採用。research / ai モジュールは DuckDB 接続を受け取って SQL ベースで処理します。
- 設定ファイル（config/*.yaml）は検証の対象です。PyYAML がインストールされていない場合は YAML の検証はスキップされます。

---

もしREADMEに追記したい運用手順（例: systemd ユニットファイル、cron / Supervisor での実行例）や、より詳細な API ドキュメント（各関数の使用例）等が必要であれば、目的に合わせてサンプルを追加します。