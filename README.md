# KabuSys

日本株向け自動売買システムのリファレンス実装です。戦略の研究（research）、ポートフォリオ構築（portfolio）、発注/実行（execution）、監視（monitoring）、および AI を使ったニュース解析（ai）など複数のコンポーネントで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群で構成された自動売買基盤です。

- 市場データからファクターを計算する research モジュール
- 銘柄選定・重み付け・株数決定を行う portfolio モジュール
- 発注ロジック・エンジンの起動を行う execution モジュール（paper_trading モードあり）
- システム健全性・注文状況・リスクを監視する monitoring モジュール
- OpenAI 等を利用したニュースセンチメント評価などの ai モジュール
- 各種ユーティリティ（ログ設定・プロセス優先度設定・設定管理など）

設計上の特徴:
- DuckDB を分析用 DB、SQLite を監視・発注ログ用に利用
- .env ベースの設定管理（`config_setup.py` によるウィザード）
- monitoring は環境にかかわらず本番用の sqlite_path を参照（監視ログは本番 DB を使って集約）
- paper_trading 環境は発注処理を MockBroker に置き換え、paper 用 SQLite に記録して本番と分離

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成/更新）: `python -m kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml のチェック）: `python -m kabusys.validate_config`
- ExecutionEngine 起動スクリプト: `python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` 時は MockBroker を使い `data/paper_trading.db` に記録
  - 停止はフラグファイル（`data/stop_requested.flag` / `data/kill.flag`）で制御
- Monitoring 起動スクリプト: `python -m kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可（デフォルト 60 秒）
  - SystemMonitor、TradeMonitor、RiskMonitor を定期実行し Kill Switch を評価
- Paper Trading 検証レポート生成スクリプト: `python -m kabusys.tools.paper_verification_report`
- ニュース NLP（OpenAI による銘柄別センチメント評価）: `kabusys.ai.news_nlp.score_news`
- 市場レジーム判定（ETF の MA200 とマクロニュースを合成）: `kabusys.ai.regime_detector.score_regime`
- ポートフォリオ構築ユーティリティ（候補選別・重み付け・ポジションサイズ計算）
- ログ設定ユーティリティ（コンソール + 日次ローテートファイル、デフォルト logs/）

---

## セットアップ手順

前提
- Python 3.10 以上（ソースで `X | Y` 型等を使用）
- SQLite、標準ライブラリは OS により提供済み

1. リポジトリを取得
   - git clone などで取得してください。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（最低限）:
     - duckdb
     - psutil
   - AI 関連を使う場合:
     - openai
   - オプション:
     - PyYAML（`python -m kabusys.validate_config` が YAML 検証を行うため）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは `.env.example` を参考に手動で `.env` を作成

5. 設定の検証
   - python -m kabusys.validate_config
   - 本番に近いチェックを行う場合は `--strict` を付けると警告も FAIL 扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリの作成
   - デフォルトでは `data/` と `logs/` を使用します。必要に応じて作成または `.env` の `DUCKDB_PATH` / `SQLITE_PATH` を設定してください。

---

## 使い方

基本的な実行例:

- 監視（Monitoring）を起動:
  - MONITOR_POLL_INTERVAL を指定してポーリング間隔を変えたい場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトは 60 秒。監視は常に設定された（本番）SQLite パスを使います。

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading をセットすると MockBroker を使用し paper 用 DB に記録されます:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 停止方法:
  - 監視ループ / エンジンはプロジェクトルート下の `data/stop_requested.flag` を検知すると起動済みのループを終了します（`run_execution.py` / `run_monitoring.py` で利用）。
  - Kill Switch により `data/kill.flag` が書き込まれると ExecutionEngine に停止シグナルを送ります（`KillSwitch` により作成）。
  - Execution 起動時に PID ファイル `data/execution.pid` が生成されます（プロセス管理に利用）。

- Paper Trading の検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB は `PAPER_TRADING_SQLITE_PATH` 環境変数または引数 `--db` で指定可能（デフォルト `data/paper_trading.db`）。

AI 機能:
- OpenAI を使う機能（news_nlp / regime_detector）は環境変数 `OPENAI_API_KEY` をセットするか、関数呼び出し時に `api_key` 引数を渡してください。
- 失敗時はフェイルセーフ挙動（スコア 0.0 など）で継続する実装が多く用意されています。

ログ:
- ログはデフォルトで stdout に出力され、さらに `logs/<app_name>.log` に日次ローテーションで保存されます（30 日分保持）。
- ログディレクトリは環境変数 `LOG_DIR` または `setup_logging` の引数で変更可能。

環境変数の主な例:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト data/paper_trading.db)
- OPENAI_API_KEY (AI 機能で必要)

---

## 主要ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - .env 自動ロード、Settings クラス（アプリ設定取得）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py — ニュース文章を LLM でスコアリングして ai_scores に保存
  - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite スキーマと読み書きラッパー
  - system_monitor.py — システム状態・データ鮮度チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の作成・評価
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py (参照用: アラート送信実装)
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
    - 発注・リスク管理・リコンサイルの実装（ExecutionEngine の中核）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・資金配分ロジック
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン・IC・統計サマリなど
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力
- utils/
  - logging_setup.py — 統一ログ設定
  - process_priority.py — プロセス優先度・CPU affinity 設定

データ・ログ:
- data/ — デフォルトの DB / PID / フラグなどが置かれるディレクトリ
  - monitoring.db (SQLITE_PATH のデフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
  - stop_requested.flag, kill.flag, execution.pid
- logs/ — アプリケーションログ（app_nameごとにファイル）

---

## 注意事項 / 運用上のポイント

- 本リポジトリはサンプル実装です。実運用ではエラー処理・監査ログ・秘密情報の扱い（.env の機密保持）等を厳重に実装してください。
- 本番（KABUSYS_ENV=live）での起動前に必ず `python -m kabusys.validate_config --strict` を実行し、設定と guard（LINE 通知など）を確認してください。
- OpenAI を利用する機能は API コストとレイテンシを考慮して運用設計してください。LLM 呼び出しはリトライ・バックオフが組み込まれていますが、障害時のフェイルオーバー設計が必要です。
- monitoring は監視ログを本番 DB に書き込む設計のため、監視データの取り扱いに注意してください。
- `MONITOR_POLL_INTERVAL`（秒）は監視のポーリング間隔を上書きできますが、あまり短く設定するとシステム負荷や API レートに影響します。

---

## トラブルシューティング

- .env が読み込まれない／自動ロードを無効化したい:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードをスキップします。
- ログファイルが作成されない:
  - `LOG_DIR` を確認。ディレクトリ作成に失敗した場合はコンソール（stdout）へのみ出力されます。権限やパスを確認してください。
- process priority / cpu affinity の設定に失敗した:
  - 権限不足や未サポート OS の可能性があります。ワーニングが出ますが処理は継続します。

---

必要に応じて README を拡張します。特に運用手順（systemd ユニット例、Docker 化、モニタリングの Slack/LINE 連携など）を追加したい場合は指示してください。