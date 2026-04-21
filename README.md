# KabuSys

日本株自動売買システムのコアライブラリ / 起動スクリプト群。

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・研究用ユーティリティ・AI ベースのニュース評価などを含むモジュール群で構成されています。各コンポーネントは単独で実行可能なエントリポイント（`python -m kabusys.*`）を提供します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム（プロトタイプ）です。主な設計方針は次の通りです。

- モジュール化された設計（戦略 / ポートフォリオ / 発注 / 監視 / 研究 / AI）
- 本番 / ペーパートレードの分離（環境変数 `KABUSYS_ENV`）
- DuckDB を用いたリサーチ・フェクタ計算、SQLite を用いた監視・トレードログ永続化
- OpenAI（LLM）を利用したニュース NLP、レジーム判定機能（API キーは外部で管理）
- 監視（Monitoring）と Kill Switch による自動停止機構

---

## 機能一覧

- 実行エンジン（ExecutionEngine）起動スクリプト（`run_execution.py`）
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` に完全分離で記録
  - 発注・注文管理・リスク管理・約定整合（reconciler）を統合

- 監視（Monitoring）ポーリングループ（`run_monitoring.py`）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、取引ログ監視、リスク監視を実行
  - Kill Switch 判定（`data/kill.flag` を書き込む）・アラート通知連携

- 設定ウィザード（`config_setup.py`）
  - .env の対話的作成・更新サポート

- 設定検証 CLI（`validate_config.py`）
  - 環境変数や `config/*.yaml` の妥当性チェック（`--strict` で警告も失敗扱い）

- Paper Trading 検証レポート（`tools/paper_verification_report.py`）
  - ペーパートレード DB を集計し、稼働率・注文成功率・レイテンシを評価

- ポートフォリオ構築ユーティリティ（`kabusys.portfolio`）
  - 候補選定、重み算出、位置サイズ計算、セクター制限、レジーム乗数

- 研究用モジュール（`kabusys.research`）
  - ファクタ計算（モメンタム・バリュー・ボラティリティ）、将来リターン、IC 計算、統計サマリー

- AI モジュール（`kabusys.ai`）
  - ニュースの NLP スコアリング（OpenAI 使用）、市場レジーム判定

- ユーティリティ（`kabusys.utils`）
  - ロギング設定（コンソール + 日次ローテーションファイル）、プロセス優先度 / CPU affinity 設定 等

---

## 必要条件（主な依存）

本 README 作成時点のコードから想定される主な依存ライブラリ：

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（設定ファイル検証を行う場合に任意で必要）

（プロジェクトに requirements.txt が付属している場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存インストール
   - pip install duckdb psutil openai PyYAML

   （実際のプロジェクトでは requirements.txt / poetry 等を推奨）

4. .env を作成
   - 対話式に作る場合:
     - python -m kabusys.config_setup
   - 手動で作る場合は `.env.example` を参照して `.env` をプロジェクトルートに配置：
     - 主要環境変数（必須）:
       - JQUANTS_REFRESH_TOKEN（必須）
       - KABU_API_PASSWORD（必須）
     - その他（デフォルト値あり）
       - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
       - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
       - SQLITE_PATH — デフォルト: data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
       - LOG_LEVEL / LOG_DIR
       - OPENAI_API_KEY（AI 機能を使う場合）
       - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）
       - PAPER_FILL_MODE（paper_trading の Fill モード: instant|partial|never|reject）

   - 自動 .env ロードについて:
     - 起動時に `KABUSYS_DISABLE_AUTO_ENV_LOAD` を 1 にすると自動ロードを無効化できます。
     - 自動ロードはプロジェクトルート（.git または pyproject.toml の位置）から `.env` → `.env.local` を読み込みます。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗とする）: python -m kabusys.validate_config --strict

---

## 実行方法（主要スクリプト）

- ExecutionEngine を起動（本番 / ペーパー分岐は KABUSYS_ENV）
  - python -m kabusys.run_execution

  実行の挙動:
  - 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続します。
  - `KABUSYS_ENV=paper_trading` の場合は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用し、Mock ブローカーを用いるため本番 DB と分離されます。
  - 停止制御:
    - プロジェクトルートの `data/stop_requested.flag` ファイルの存在を監視し、存在するとエンジンを停止します。
    - Kill Switch（`data/kill.flag`）が書き込まれると強制停止のトリガになります。
  - PID ファイル: `data/execution.pid`（設定で変更可）

- Monitoring ポーリングループを起動
  - python -m kabusys.run_monitoring

  実行の挙動:
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）
  - Monitoring は起動環境にかかわらず監視用の本番 sqlite_path を利用します（コード上の設計）
  - 停止制御: `data/stop_requested.flag` の存在でループを終了

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは `--db PATH` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定

---

## 環境変数（主なもの）

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能使用時)
  - LINE_CHANNEL_ACCESS_TOKEN（任意）
  - LINE_USER_ID（任意）

- 実行 / モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の振る舞い）
  - KILL_FLAG_CLEAR_ON_START: 0|1（起動時に kill.flag を自動クリアするか。デフォルト 0 推奨）

- データパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB, デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）

- ログ
  - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）
  - LOG_DIR（デフォルト logs/）

- 監視
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）

注意: `.env` ファイルは絶対にリポジトリにコミットしないでください。

---

## ロギング

- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name="...")` で統一的に行われます。
- 出力:
  - コンソール（stdout）
  - 日次ローテーションファイル（デフォルト: logs/<app_name>.log、30 日保持）
- ログディレクトリが作成できない場合はファイル出力をスキップしてコンソールのみで継続します。

---

## 停止・Kill 機構

- stop_requested.flag
  - `data/stop_requested.flag`（プロジェクトルート基準）を作成すると、`run_monitoring` / `run_execution` のループが検知して安全に終了します。

- kill.flag（Kill Switch）
  - 監視（KillSwitch）により `data/kill.flag` が書き込まれると ExecutionEngine に停止シグナルを送ります。
  - `KILL_FLAG_CLEAR_ON_START` が 1 の場合、起動時に kill.flag を自動でクリアします（本番では 0 を推奨）。

---

## ライブラリとしての利用例

- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

- 研究用・ファクター計算
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

- AI ニューススコアリング（DuckDB コネクション渡し）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")

（各関数は引数や戻り値の形式がドキュメントコメントに記載されています）

---

## ディレクトリ構成（抜粋）

以下はソースの主要ファイル構成です（`src/kabusys` 配下）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py           — 市場レジーム判定（LLM 統合）
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数決定・規模調整
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum/value/vol）
    - feature_exploration.py       — 将来リターン / IC / 統計
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — （取引監視ロジック）
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — kill.flag 書き込みロジック
    - monitoring_engine.py         — 各 monitor を束ねる実行ループ
    - alert_manager.py             — （アラート送信ロジック、LINE 等）
  - execution/
    - broker_factory.py            — ブローカークライアントファクトリ
    - execution_engine.py          — 発注エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - __init__.py
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity

補足: 実際のリポジトリには上記に加えて `data/`（DB / フラグファイル）、`config/`（yaml 設定テンプレート）などが存在する想定です。

---

## 運用上の注意

- .env は必ずローカル専用にして Git にコミットしないでください。
- 本番環境（`KABUSYS_ENV=live`）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します。validate_config で本番向けのガードチェックを行なっています。
- OpenAI API 呼び出しを行うモジュール（news_nlp / regime_detector）は API コストとレート制限に注意してください。`OPENAI_API_KEY` は安全に管理してください。
- ログディレクトリが作成できない場合はファイル出力が無効化されコンソールのみになることがあります。監視環境では `LOG_DIR` の権限を確認してください。

---

## よく使うコマンドまとめ

- 環境変数対話設定:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README は以上です。実行やデプロイ時に特定の実装・依存が変わっている可能性があるため、実際のプロジェクトルートにある `pyproject.toml` / `requirements.txt` / `config/*.yaml` / `.env.example` を参照して環境を整えてください。必要であれば README に含める具体的なコマンドや追加説明を追記します。