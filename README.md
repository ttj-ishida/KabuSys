# KabuSys

軽量な日本株自動売買システムのコアライブラリ（プロトタイプ）。  
このリポジトリは、実行エンジン・監視/キルスイッチ・ポートフォリオ構築・リサーチ・AI ニューススコアリング等の主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買のための制御ロジック群と補助ツールの集合です。  
主な目的は次のとおりです。

- 発注エンジン（ExecutionEngine）による売買実行（実口座 / ペーパートレード両対応）
- 監視コンポーネントによるシステム安定性・注文状態・リスクの継続的監視とアラート / Kill Switch 発動
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター上限など）
- DuckDB を用いたファクター計算・リサーチ機能
- OpenAI を利用したニュース NLP（銘柄別センチメント）および市場レジーム判定
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

この実装はモジュール化されており、個別機能をライブラリとして再利用できます。

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式ウィザードで .env を作成する `kabusys.config_setup`
  - 設定検証 CLI `kabusys.validate_config`
- 実行エンジン
  - `run_execution.py`：ExecutionEngine の起動スクリプト
  - KABUSYS_ENV に応じてペーパートレードと本番を分離（paper_trading 用 DB）
  - stop フラグ（data/stop_requested.flag）で安全停止
- 監視
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプト
  - System / Trade / Risk モニタを束ねる MonitoringEngine
  - KillSwitch（条件を満たせば data/kill.flag を書き込み ExecutionEngine を停止）
  - 監視ログは SQLite（monitoring.db）に永続化
- ポートフォリオ構築
  - 候補選定、等金額 / スコア加重配分、リスクベースなポジションサイズ計算
  - セクター上限・レジーム乗数の適用
- リサーチ
  - DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）等の統計ユーティリティ
- AI（OpenAI）
  - ニュース集合を LLM でセンチメント化して ai_scores テーブルへ保存（score_news）
  - マクロニュース + ETF MA200 乖離で市場レジーム判定（score_regime）
  - 失敗 tolerant（レート制限・ネットワーク障害・5xx をリトライ、失敗時は安全側のフォールバック）
- ユーティリティ
  - 統一ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度／CPU affinity 設定ユーティリティ
  - ペーパートレード検証レポート生成ツール

---

## セットアップ手順（開発環境向け）

※ 実運用のためには適切なプロビジョニング・秘密情報管理が必要です（本 README はローカル起動手順の概略を示します）。

1. リポジトリをチェックアウトし、作業ディレクトリをルートにする（`src` を PYTHONPATH に含めるかパッケージインストールする）。
   - 例: `git clone ... && cd <repo>`
2. Python 仮想環境を作成・有効化
   - python >= 3.10 を推奨
   - 例: python -m venv .venv && source .venv/bin/activate
3. 依存ライブラリをインストール
   - requirements.txt がある場合: `pip install -r requirements.txt`
   - 主な依存（抜粋）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定 YAML 検証のみで必須ではない）
   - 例（最低限）:
     - pip install duckdb psutil openai
4. 環境変数 / .env の準備
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 本番チェックを厳密に行う場合は `--strict`
5. データディレクトリの作成（`data/`）
   - SQLite / DuckDB のデフォルトパスは `data/` 配下です。必要に応じて `.env` の `DUCKDB_PATH` / `SQLITE_PATH` を変更してください。
6. （オプション）OpenAI を利用する場合:
   - 環境変数 `OPENAI_API_KEY` を設定
7. ログディレクトリ
   - デフォルトは `logs/`。`LOG_DIR` を .env で上書き可能。

---

## 使い方（主要スクリプト）

パッケージのあるルートで `python -m` を使って実行できます（または PYTHONPATH に `src` を含める/パッケージをインストール）。

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いして exit(1)

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録（本番 DB と分離）
    - 起動時に `data/stop_requested.flag` があれば起動をスキップ
    - 停止は `data/stop_requested.flag` を作成することで行う

- 監視（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト: 60）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず本番監視 DB を参照）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - `--db` で別 DB を指定可。デフォルトは `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`

- AI スコアリング / レジーム判定（ライブラリ関数）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続 (`duckdb.connect(...)`) を引数に取り、内部で ai_scores / market_regime テーブルを更新します。
  - OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を利用

注意:
- 起動スクリプトは起動時にログ設定（stdout と logs/<app>.log）を行い、プロセス優先度を `high` に設定しようとします（権限がない場合は警告ログのみ）。
- 停止フラグは `data/stop_requested.flag`。KillSwitch 用のファイルは `data/kill.flag`（Settings.kill_flag_path）。

---

## 主な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: one of `development`, `paper_trading`, `live`（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI 呼び出しに必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする (0/1)

---

## 重要な設計上の注意点 / 運用上の留意点

- ペーパートレードは本番 DB と分離されています（`paper_trading` 環境では `paper_sqlite_path` を使用）。
- 監視モジュールは KABUSYS_ENV に依存せず、常に指定された監視 DB に接続します（監視データは本番 DB を想定）。
- KillSwitch はリスク条件に基づき `data/kill.flag` を作成します（存在すると実行エンジンは停止します）。本番での自動クリアは危険なため `KILL_FLAG_CLEAR_ON_START=0` が推奨されます。
- OpenAI 使用箇所は失敗に対してフォールバックを行う実装になっていますが、API キー管理・呼び出し頻度には注意してください（コスト・レート制限）。
- ログは stdout と `logs/<app>.log` に出力されます。ログディレクトリが作成できない場合はコンソールのみで継続します。
- DB スキーマの初期化・マイグレーションは `init_monitoring_db` で実行されます（冪等設計）。

---

## ディレクトリ構成（主要部分）

src/kabusys/
- __init__.py
- config.py
- config_setup.py        — .env 対話式ウィザード
- validate_config.py     — 設定検証 CLI
- run_execution.py       — ExecutionEngine 起動スクリプト
- run_monitoring.py      — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py
- execution/              — 発注周り（BrokerClientFactory, ExecutionEngine, OrderManager 等）
- data/ （運用時に生成される）
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード用デフォルト)
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/ （ログファイル出力先、デフォルト）

（注）一部ファイルは上記サマリに含めており、実際のリポジトリ全体構成はリポジトリ内のファイル一覧を参照してください。

---

## 開発者向けメモ

- DuckDB を使ってリサーチ処理（ファクター計算など）を高速に行う設計です。prices_daily / raw_financials / raw_news 等のテーブルが前提になります。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます。
- ロギング・プロセス優先度設定はユーティリティ関数を用いて統一されています。ユニットテスト時は外部副作用（ファイル書き込み・プロセス優先度変更・OpenAI 呼び出し）をモックしてください。

---

README の内容で不足している箇所（たとえば実行時の追加オプションや Broker 実装の詳細など）があれば、その部分を指定してください。必要に応じてコマンド例や .env のサンプルテンプレートを追記します。