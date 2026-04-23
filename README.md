# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ＋起動スクリプト群）。

以下はリポジトリ内の主要コンポーネントに対する概要・セットアップ・使い方の説明です。

---

## プロジェクト概要

KabuSys は以下の役割を持つモジュール群で構成された自動売買フレームワークです。

- 実行エンジン（ExecutionEngine）：注文発行・注文管理・リスク管理・約定整合などを行う。
- 監視（Monitoring）：システム状態・注文ログ・リスク（ドローダウンやポジション数）を定期チェックし、アラートや Kill Switch を発動する。
- ポートフォリオ構築：候補選定、重み計算、ポジションサイズ算出、セクター制限等の純粋関数ライブラリ。
- リサーチ：DuckDB を用いたファクター計算・特徴量解析モジュール。
- AI モジュール：OpenAI を用いたニュースセンチメント評価、レジーム判定（LLM を利用）。
- ユーティリティ：環境設定ウィザード、設定検証、ログ設定、プロセス優先度設定など。
- ツール：Paper Trading の検証レポート生成など。

設計方針として、可能な限り副作用を限定し、DB とファイル（data/）で状態を管理する構成になっています。

---

## 主な機能一覧

- 実行環境モード
  - KABUSYS_ENV = development | paper_trading | live
  - paper_trading では MockBrokerClient を用い、本番 DB と分離した paper_trading DB に記録
- 監視（System / Trade / Risk）
  - CPU / メモリ / ディスク、プロセス生存チェック、データ鮮度チェック
  - 滞留注文・約定異常・ドローダウン・ポジション上限の検出
  - Kill Switch（data/kill.flag）生成による ExecutionEngine 停止
- ポートフォリオ構築
  - 候補選定（スコア順）、等重・スコア重み、リスクベースの株数計算、セクターキャップ適用
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）
  - ニュース記事のセンチメント集約（ai_scores へ格納）
  - マクロニュースと ETF MA を使った市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト
- 開発支援
  - .env 設定ウィザード（対話式）
  - 設定検証 CLI（config/.yaml チェックなど）
  - 統一ログ設定（コンソール + 日次ローテート）

---

## 必要条件（開発環境例）

- Python 3.10+（型アノテーションの記述に合わせて）
- 推奨パッケージ（一部は必須）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証に必要）
- OS: Linux / macOS / Windows（プロセス優先度設定は一部制約あり）

依存は pyproject.toml / requirements.txt があればそこからインストールしてください。ない場合は主要パッケージを手動で入れてください。

例（venv 使用）:
- python -m venv .venv
- source .venv/bin/activate
- pip install -U pip
- pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
2. 依存パッケージをインストールする（上記参照）
3. .env ファイルの作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークン / kabu API パスワード 等を入力
   - 生成された .env は決してリポジトリにコミットしないこと
4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱う
5. 必要に応じて data/ ディレクトリや logs/ を作成（いくつかのモジュールは起動時に自動作成します）

デフォルトのデータ・ログパス（Settings のデフォルト）:
- DuckDB: data/kabusys.duckdb
- SQLite (監視): data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID / flag: data/execution.pid, data/kill.flag
- ログ: logs/<app_name>.log

注意: run_monitoring は「どの KABUSYS_ENV であっても本番 sqlite_path（SQLITE_PATH）」を使用します（コードの仕様）。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector 等）で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（development 用。デフォルト 0）

（その他、config_setup のウィザードで扱う項目があるため .env を確認してください）

---

## 使い方（主要コマンド）

各スクリプトはモジュールとして実行できます（Python パッケージパスに src が含まれるか、パッケージをインストールしている想定）。

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - python -m kabusys.run_monitoring
  - 特記事項:
    - 監視は Settings.sqlite_path（SQLITE_PATH）を使用（KABUSYS_ENV に依存しない）
    - 監視プロセスは data/stop_requested.flag が存在するとループを終了する（ファイルを置くことで停止）

- 実行エンジン起動（Execution）
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（例: data/paper_trading.db）に記録されます
  - python -m kabusys.run_execution
  - 実行中の PID は data/execution.pid に書かれます
  - 停止シグナル:
    - run_execution も data/stop_requested.flag の存在を監視し、検知でエンジンを停止します
    - Kill Switch（監視側）が条件を満たすと data/kill.flag を書き、実行エンジンはこれを検出して安全停止する設計です

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI モジュール（プログラムから呼び出す）
  - OpenAI キーが必要（OPENAI_API_KEY）
  - 例（Python から）:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="sk-...")

（上記は主要操作の抜粋です。各モジュールはライブラリ関数としても利用できます）

---

## 停止・Kill の仕組み

- stop_requested.flag
  - run_monitoring.py / run_execution.py は data/stop_requested.flag の存在を監視して、存在するとループを止めて終了します（手動で停止したい場合にファイルを作成）。

- kill.flag（Kill Switch）
  - 監視ロジック（KillSwitch）が致命的なリスク条件を検出した場合に data/kill.flag を書き込みます。
  - 実行エンジンは kill.flag を検出して安全に停止する設計です。
  - Settings.KILL_FLAG_CLEAR_ON_START が 1 の場合、起動時に kill.flag を自動でクリアする挙動を許容しますが、本番では推奨されません（危険）。

---

## ロギング

- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
- ログ出力:
  - コンソール（stdout）
  - ファイル（logs/<app_name>.log）: 日次ローテーション、30日分保持
- LOG_DIR 環境変数でログ保存先を上書き可能

---

## 開発者向けメモ

- DB 初期化:
  - monitoring 用の SQLite スキーマは kabusys.monitoring.monitoring_db.init_monitoring_db() が起動時に冪等的に作成します。
- DuckDB:
  - リサーチ / AI のデータ処理は DuckDB 接続を受け取り SQL + Python で行います（prices_daily, raw_financials 等のテーブルを前提）。
- テスト容易性:
  - OpenAI 呼び出しやプロセス優先度設定などは関数レベルで差し替え可能に設計されており、ユニットテストでモックを当てやすい構成です。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュールです（抜粋）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring の起動スクリプト
  - run_execution.py         — ExecutionEngine の起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU Affinity
  - monitoring/
    - monitoring_db.py       — SQLite スキーマと永続化ヘルパ
    - system_monitor.py
    - trade_monitor.py       — （注文関連の監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
  - execution/
    - broker_factory.py
    - execution_engine.py
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
  - tools/
    - paper_verification_report.py

（上記はコードベースの主要ファイルを示しています。細かなモジュールや補助ファイルは実際のリポジトリを参照してください）

---

## 例: 典型的な起動フロー（ローカルでの検証）

1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. Paper トレードで Execution を動かす
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution
4. 別プロセスで監視を動かす
   - python -m kabusys.run_monitoring
5. 終了は data/stop_requested.flag を作成する（空ファイルで可）、またはプロセスを Ctrl-C

---

## 注意事項

- 本番運用（KABUSYS_ENV=live）の場合、設定（特に API キー・パスワード・通知設定）は慎重に管理してください。
- .env は絶対にリポジトリにコミットしないでください。
- OpenAI API を利用する機能はコスト・レイテンシ・利用制限に注意してください。API エラーはフェイルセーフ（スコア 0 等）になるよう設計されていますが、運用ポリシーを作成してください。
- process priority / CPU affinity に関しては OS のパーミッション制約で設定に失敗する場合があります（警告ログを出してスキップします）。

---

必要であれば、README に含めるコマンドの具体例や .env のサンプル（セキュアでないダミー値）を追加します。どの程度のサンプルが必要か教えてください。