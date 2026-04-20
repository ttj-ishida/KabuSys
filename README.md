# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム「KabuSys」の実装コード群です。戦略・ポートフォリオ構築・発注実行・監視・レポート・研究用ユーティリティを含みます。README はローカルでのセットアップ、主要機能、運用上の注意点、主要コマンドを日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール化された自動売買プラットフォームです。

- 戦略（ファクター計算・特徴量生成）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 発注実行（ExecutionEngine、ブローカークライアント抽象化、paper trading モードをサポート）
- 監視（SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch）
- AI 支援（ニュース NLP によるセンチメント、レジーム判定）
- 運用ユーティリティ（環境設定ウィザード、設定検証、レポート生成）

設計上、各コンポーネントはできるだけ疎結合にし、テストしやすい単純関数／クラス群としています。Paper Trading は本番 DB と分離され、OpenAI を用いる機能は環境変数で API キーを指定して有効化します。

---

## 機能一覧

- 環境設定ウィザード（.env の対話式生成）
  - `python -m kabusys.config_setup`
- 設定検証（.env と config/*.yaml のチェック）
  - `python -m kabusys.validate_config [--strict]`
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード（KABUSYS_ENV=paper_trading）をサポート
  - ブローカークライアントを抽象化（MockBrokerClient 等）
  - PID ファイル管理、停止フラグ検出
  - `python -m kabusys.run_execution`
- Monitoring（監視エンジン）
  - SystemMonitor（CPU/メモリ/ディスク、プロセス死活、データ鮮度）
  - TradeMonitor / RiskMonitor（滞留注文、約定異常、ドローダウン等）
  - KillSwitch（閾値超過時に data/kill.flag を書き込んで Execution を停止）
  - `python -m kabusys.run_monitoring`
  - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で指定可能（秒、デフォルト 60）
- Paper Trading 検証レポート
  - `python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]`
- 研究用モジュール（DuckDB 経由）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC 計算・統計サマリ
- AI モジュール
  - ニュース NLP（OpenAI を用いた銘柄別センチメント算出）
  - レジーム判定（ETF MA + マクロセンチメントの合成）
  - OpenAI API キーは環境変数 `OPENAI_API_KEY` または関数引数で指定
- ロギングユーティリティ、プロセス優先度設定ユーティリティ、DB マイグレーション（監視 DB の初期化／カラム追加）

---

## 前提 / 必要要件

- Python 3.10+（typing の一部表記などを考慮）
- パッケージ（主に）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定 YAML の検証を行う場合に任意）
- SQLite（標準ライブラリで対応）
- ネットワーク接続（kabuステーション API / J-Quants / OpenAI を利用する場合）

※実際の運用では仮想環境（venv, pipenv, poetry など）で依存を分離してください。

推奨インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン
   - 例: `git clone <repo-url> && cd <repo-dir>`

2. 仮想環境作成・依存インストール
   - 上記「前提 / 必要要件」を参照

3. .env を作成（対話式推奨）
   - `python -m kabusys.config_setup`
   - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`
   - AI 機能を使う場合: `OPENAI_API_KEY` を環境変数で設定（または実行時に引数で渡せる関数あり）
   - 重要: `.env` をリポジトリにコミットしないでください（機密情報が含まれるため）

4. 設定検証
   - `python -m kabusys.validate_config`
   - 本番稼働前は `--strict` を付けて警告も FAIL 扱いにすることを推奨

5. ディレクトリとファイル（初回起動で自動作成されることがある）
   - デフォルト DB / ログパス:
     - DuckDB: `data/kabusys.duckdb`
     - SQLite (監視): `data/monitoring.db`
     - Paper trading SQLite: `data/paper_trading.db`
     - ログ: `logs/`（`LOG_DIR` で変更可）
     - PID / フラグ: `data/execution.pid`, `data/kill.flag`, `data/stop_requested.flag`

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 動作モード
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading: 発注はモック。`PAPER_TRADING_SQLITE_PATH` に記録。
- DB / ログ
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- AI
  - OPENAI_API_KEY — OpenAI 呼び出し用（AI 関連機能）
- Monitoring
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- Kill Switch / 起動クリア
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（"1" で有効）

---

## 使い方（主なコマンド例）

- 環境設定ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 本番前に厳格チェック: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意: `KABUSYS_ENV=paper_trading` の場合は専用のペーパートレード DB に記録され、本番 DB と分離されます

- Monitoring（監視プロセス）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔変更: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: `--db path/to/paper_trading.db` または環境変数 `PAPER_TRADING_SQLITE_PATH`

- AI 機能（プログラム的に呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

運用例（systemd / supervisor 等）:
- Execution と Monitoring を別プロセスで常時稼働させ、ログを `logs/` に保存する。
- 停止は `data/stop_requested.flag`（loop を終了するためのローカル停止フラグ）や `data/kill.flag`（Execution 停止のための Kill Switch）を利用。

---

## 運用上の注意点

- KABUSYS_ENV が `live` の場合は本番口座で実際に発注されます。環境設定・LINE 通知などを事前に十分確認してください。
- Paper Trading は SQLite を切り分けています（`PAPER_TRADING_SQLITE_PATH`）。本番 DB 存在に注意して切り分けること。
- Kill Switch: RiskMonitor 等の条件で `data/kill.flag` が書き込まれると ExecutionEngine に停止シグナルが送られます。`KILL_FLAG_CLEAR_ON_START=1` は本番では危険なので推奨されません。
- ロギング: `kabusys.utils.logging_setup.setup_logging` により stdout と日次ローテートされたファイルが出力されます。ログディレクトリに書き込む権限が必要です。
- Process Priority: 起動スクリプトは最初に `set_process_priority("high")` を呼び出します。権限や OS によって設定に失敗する場合がありますが、安全に無視されます（警告ログ）。
- DB マイグレーション: `init_monitoring_db` は冪等でテーブルを作成し、既存 DB に対して必要カラム（例: latency_ms, peak_value）を追加するマイグレーション処理を含みます。

---

## ディレクトリ構成（主要ファイルの説明）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定取得ユーティリティ（Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し、スコア保存）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py — 候補選定・等配分／スコア配分
    - position_sizing.py — 株数決定・投下資金制限・単元丸め
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - monitoring/
    - monitoring_db.py — 監視用 SQLite の初期化と読み書き層
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — システム状態・データ鮮度の監視
    - trade_monitor.py — （注文監視ロジック）
    - risk_monitor.py — ドローダウン・ポジション上限の監視
    - kill_switch.py — kill.flag の生成/クリアロジック
    - alert_manager.py — LINE 等への通知管理（実装を参照）
  - execution/
    - execution_engine.py — 発注実行エンジンのコア
    - broker_factory.py — BrokerClient の生成（本番／モック切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注関連コンポーネント
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/ — デフォルトのデータベース / フラグ / PID 保存場所（実行時に使用）

---

## 開発・拡張のヒント

- DuckDB を用いて prices_daily / raw_financials / raw_news 等の分析テーブルに対し SQL を混ぜた処理を行っています。研究用関数は副作用がなくテストしやすい設計です。
- AI 呼び出し（OpenAI）は再試行・入力トリム・レスポンス検証などのフェイルセーフを備えています。テスト時は API 呼び出し部分をモック（例: unittest.mock.patch）してください。
- 監視・発注は別プロセスで実行する前提です。監視は本番 sqlite_path（monitoring DB）を使い、Execution は paper_trading の場合に別 DB を使う点に注意してください。
- 設定ファイル（config/*.yaml）は `validate_config` で存在・パースチェックできます（PyYAML がインストールされている場合）。

---

## ライセンス / 責任

実際に証券会社 API へ接続して取引を行うコードを含むため、本リポジトリを本番で使う場合は十分な検証とリスク管理を行ってください。本 README はリポジトリ内のコードに基づく概要説明であり、運用に伴う損失等についての保証はありません。

---

必要であれば README に README.md の簡易的な systemd ユニットのサンプル、docker-compose の例、より詳しい環境変数一覧（全てのキー）や開発・テストの方法（ユニットテストの実行方法）を追加できます。どの情報を優先的に追加しますか？