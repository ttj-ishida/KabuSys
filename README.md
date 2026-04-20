# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README（日本語）。

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI（ニュース NLP / レジーム判定）などを含む、総合的な自動売買フレームワークです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主な役割は次の通りです。

- 発注エンジン（ExecutionEngine）: ブローカークライアントを介した注文発行・管理・リスク管理。
- 監視 (Monitoring): システム健全性、注文状態、リスク（ドローダウン／ポジション上限）を定期チェックしアラートや Kill Switch を発動。
- 研究（Research）: DuckDB を用いたファクタ計算・特徴量解析。
- ポートフォリオ構築（Portfolio）: 候補選定・重み計算・ポジションサイズ算出・セクター制約やレジーム調整。
- AI モジュール: ニュースの NLP スコアリング（OpenAI）・市場レジーム判定。
- ユーティリティ: ロギング設定・プロセス優先度・設定 (.env) 管理ツール 等。

本プロジェクトは、本番（live）とペーパートレード（paper_trading）を区別して設計されています。ペーパートレードでは MockBrokerClient を用い、本番 DB とは別ファイルに記録されます。

---

## 機能一覧

- 環境設定ウィザード（対話式 `.env` 作成）：`python -m kabusys.config_setup`
- 起動前設定検証：`python -m kabusys.validate_config`（`--strict` オプションあり）
- ExecutionEngine 起動スクリプト：`python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` の場合は専用の paper_trading DB（`data/paper_trading.db`）を使用
  - 停止フラグ・PID 管理対応
- Monitoring 起動スクリプト：`python -m kabusys.run_monitoring`
  - ポーリング間隔は `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - System / Trade / Risk 各モニタを巡回し Kill Switch・アラートを評価
- Paper Trading 検証レポート生成ツール：`python -m kabusys.tools.paper_verification_report`
- 研究用関数群（ファクター計算、IC、将来リターン等） — DuckDB 接続を受け取って実行
- ニュース NLP（OpenAI を用いた銘柄別センチメント）とレジーム判定（ETF MA + LLM）
- ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
- プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発／実行環境）

前提
- Python 3.10+
- 推奨: 仮想環境（venv / conda 等）

1. リポジトリをクローンして作業ディレクトリへ移動
   - （パッケージ化されている場合は `pip install .` などを併用）

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限の依存例（プロジェクトに requirements.txt がある場合はそれを使用してください）:
     - duckdb
     - psutil
     - openai
     - PyYAML（`validate_config` の YAML 検査を有効にしたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. ディレクトリ作成
   - データ・ログディレクトリを用意:
     - mkdir -p data logs

5. 環境変数設定（.env）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - `.env` を手動で用意する場合は `.env.example` を参考にしてください（このリポジトリに例ファイルがない場合は README の「環境変数」を参照）。

6. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は指摘に従い .env や config/*.yaml を修正

7. OpenAI を利用する場合
   - 環境変数 `OPENAI_API_KEY` を設定（または関数呼び出しでキーを渡す）

注意
- `.env` は機密情報を含むため、絶対に Git 等にコミットしないでください。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行モード
  - KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
    - paper_trading: MockBrokerClient を使い、paper 用 SQLite に記録
    - live: 本番動作（慎重に設定を確認）

- データベース / ファイルパス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: Execution PID（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch flag（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効。デフォルト 0。live での 1 は危険）

- ログ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）

- Monitoring / 実行動作
  - MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: paper_trading のフィルモード（instant|partial|never|reject。デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL 扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動:
  - python -m kabusys.run_execution
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - 停止は `data/stop_requested.flag` を作成するか、kill.flag（`Settings.kill_flag_path`、デフォルト data/kill.flag）で停止シグナルを出します。
  - 起動時は PID ファイル（`PID_FILE_PATH`）が用いられます。

- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は本番 sqlite_path（`SQLITE_PATH`）を常に使用します（KABUSYS_ENV に依存しない）

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 簡易チェック: 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ などを評価して PASS/FAIL を出力

- プログラム的利用（モジュール呼び出し）
  - AI スコアリング（ニュース）: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 研究系ユーティリティ（例）:
    - kabusys.research.calc_momentum(duckdb_conn, date)
    - kabusys.research.calc_volatility(...)
  - ポートフォリオユーティリティ:
    - kabusys.portfolio.select_candidates(...)
    - kabusys.portfolio.calc_equal_weights(...)
    - kabusys.portfolio.calc_position_sizes(...)

---

## 停止・Kill Switch 周辺

- 停止フラグ（run_* スクリプト）
  - data/stop_requested.flag が存在すると、run_monitoring/run_execution のループは終了します。
- Kill Switch（自動停止）
  - 監視コンポーネントにより条件（例: ドローダウン超過、ポジション上限超過）が満たされると、KillSwitch が `data/kill.flag` に理由を書き込み ExecutionEngine に停止通知を行います。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では推奨しません）。

---

## ログ

- ログはデフォルトで stdout（コンソール）とファイル（logs/<app_name>.log、日次ローテーション）に出力されます。
- ログディレクトリは `LOG_DIR` またはデフォルトの `logs/`。
- ログレベルは `LOG_LEVEL` で制御。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                  — 環境変数 / 設定取得
- config_setup.py            — 対話式 .env ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring 起動スクリプト
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py (参考: アラート送信ユーティリティ等)
- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
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
- monitoring/ (DB 関連は上記）
- その他：data/（実行時生成）、logs/（ログ）

（実際のリポジトリには上記以外の補助モジュール・ファイルも含まれる場合があります）

---

## 注意・運用上のヒント

- .env は機密情報を含むため絶対にバージョン管理に含めないでください。
- 本番環境（KABUSYS_ENV=live）での起動前に `python -m kabusys.validate_config` を実行して確認してください。
- `KILL_FLAG_CLEAR_ON_START=1` は開発時に便利ですが、本番ではオフ（0）を推奨します。
- OpenAI を利用する機能は API コストとレイテンシの影響があるため、運用設計に注意してください（リトライ・バックオフ・バッチ化は組み込まれています）。
- DuckDB / SQLite のファイルはバックアップ・管理を検討してください。特に本番データは定期的に安全に保管すること。

---

問題発見や改善提案、追加ドキュメントの要望があれば教えてください。README の補足（例: config/*.yaml の説明、実行例のログ抜粋、運用チェックリスト 等）も作成できます。