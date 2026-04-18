# KabuSys — README

以下はこのコードベース（src/kabusys）向けの README です。日本語でプロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成を記載しています。

注意: .env や認証情報は決してリポジトリにコミットしないでください（config_setup.py にもその注意書きがあります）。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコアライブラリ群です。  
主な責務は次の通りです。

- データ取得・研究（DuckDB 上の時系列データ参照）
- ファクター計算・特徴量解析（research パッケージ）
- ポートフォリオ構築・ポジションサイジング（portfolio パッケージ）
- 発注エンジン（ExecutionEngine）と注文管理（execution パッケージ）
- 監視（MonitoringEngine）・アラート・Kill Switch（monitoring パッケージ）
- LLM を用いたニュースセンチメント / レジーム判定（ai パッケージ）
- Paper Trading 向けの検証レポート生成ツール（tools）

設計方針として、ルックアヘッドバイアス回避、DB 分離（本番 / ペーパートレード）、フェイルセーフ（API 失敗時に例外を投げず継続）などが考慮されています。

---

## 機能一覧

- 環境設定ウィザード（対話式 .env 作成）: konfig_setup
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替、PID/stop フラグ管理）
- Monitoring 起動スクリプト（SystemMonitor のポーリング）
- Monitoring 機能:
  - システム稼働監視（CPU / メモリ / ディスク / プロセス生存）
  - 注文監視（滞留注文・約定異常）
  - リスク監視（ドローダウン・ポジション上限）
  - Kill Switch（条件に応じて data/kill.flag を作成）
  - アラート連携（LINE など、設定次第）
- ポートフォリオ構築:
  - 候補選定、等配分・スコア配分、リスクベース配分
  - セクターキャップ適用、レジーム乗数
  - 単元での丸め・集約キャップ処理
- 研究（research）:
  - モメンタム / ボラティリティ / バリュー等ファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（LLM）:
  - ニュースを LLM に渡して銘柄別センチメントを ai_scores に書き込み（news_nlp.score_news）
  - マクロニュース + ETF MA200 乖離で市場レジーム判定（ai.regime_detector.score_regime）
- Paper Trading 検証レポート生成ツール（paper_verification_report）

---

## 必要条件（概略）

- Python 3.9+
- 外部ライブラリ（一部機能で必要）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite（組み込みの sqlite3 を使用）
- ネットワーク接続（OpenAI API を使う機能を使う場合）

requirements.txt はリポジトリに含まれていない想定のため、上記パッケージをインストールしてください。
例:
- pip install duckdb psutil openai pyyaml

---

## 重要な環境変数（必須 / 主要）

必須（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用関連（デフォルト値あり）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を使う機能で必要（ai.news_nlp / regime_detector 等）
- PAPER_FILL_MODE — paper_trading の MockBroker の約定挙動（instant|partial|never|reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — （任意）アラート通知用

監視・停止
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリア（"1" で有効、デフォルト "0"）

注意点:
- validate_config.py は重要な設定漏れを検出します。起動前に実行することを推奨します。

---

## セットアップ手順（例）

1. リポジトリをクローン／展開し、プロジェクトルート（pyproject.toml または .git がある場所）に移動する。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. 環境変数の初期化（推奨）: 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   ウィザードは .env を作成／更新します。生成された .env は絶対に Git 等にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   問題がある場合はエラーメッセージに従って .env または config/*.yaml を修正します。
   厳密モード:
   - python -m kabusys.validate_config --strict

6. DuckDB / SQLite の初期テーブルは実行時に自動的に作成される機能があります（monitoring DB の init など）。

---

## 使い方（主な CLI / モジュール）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中は data/execution.pid に PID を書き込みます。停止は data/stop_requested.flag を作成する、または Kill Switch による信号で行います。
    - 起動時に KILL_FLAG_CLEAR_ON_START=1 の場合、kill.flag を自動クリアする挙動を設定で制御できます（本番では 0 推奨）。

- Monitoring 起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL 環境変数（秒）で間隔を変更可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  動作:
    - プロセス優先度を high に設定し（可能な場合）、SystemMonitor を定期実行します。
    - Monitoring は常に production 用の sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）。
    - data/stop_requested.flag が存在するとループを抜けて終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き可能）
  出力: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などの簡易判定（PASS/FAIL）

- AI 関連（プログラムからの呼び出し）
  - news_nlp.score_news(conn: duckdb_conn, target_date: date, api_key: Optional[str]) — raw_news を集約して OpenAI に投げ、ai_scores を更新します。
  - regime_detector.score_regime(conn: duckdb_conn, target_date: date, api_key: Optional[str]) — ETF 1321 の MA200 乖離 + マクロニュースで regime を判定・保存します。
  ※ これらをコマンドラインから直接実行するスクリプトは付属していませんが、Python スクリプトやジョブから呼び出して使えます。

---

## 停止 / Kill Switch / フラグファイル

- 停止フラグ（run_monitoring / run_execution が参照）
  - data/stop_requested.flag — スクリプトが存在を検知すると安全にループを終了します（外部から停止を要求する際に使える）。
- Kill Switch（監視 → ExecutionEngine 停止）
  - data/kill.flag — KillSwitch が条件を満たしたときに書き込まれ、ExecutionEngine 起動時のフラグ・外部停止トリガーとして機能します。
  - ExecutionEngine は起動時に kill.flag を自動で消す設定（KILL_FLAG_CLEAR_ON_START=1）を行えますが、本番では自動クリアは推奨されません。

---

## 開発・テストのヒント

- 自動で .env ファイルをロードする挙動は、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって無効化できます（テストで明示的に環境を制御したい場合に有用）。
- settings（kabusys.config.Settings）はプロジェクトルート（.git / pyproject.toml）を基準に .env, .env.local を自動ロードします。パッケージ配布後も CWD に依存せず動作するよう設計されています。
- モジュール単位でのユニットテストでは、外部 API 呼び出し（OpenAI など）や時間依存部分をモックすることを想定しています（コード内に patch 可能な箇所がある）。

---

## ディレクトリ構成（主要ファイルの説明）

（src/kabusys/ 以下を想定）

- __init__.py
  - パッケージ版情報（__version__ など）

- config.py
  - Settings クラス：.env / 環境変数の読み込み・検証・デフォルト管理
  - 自動 .env ロード（.env → .env.local の優先順位）

- config_setup.py
  - 対話式ウィザードで .env を作成／更新する CLI

- validate_config.py
  - 起動前検証 CLI（必須環境変数・DB パス・YAML ファイルなど）

- run_execution.py
  - ExecutionEngine を起動するスクリプト（paper_trading 対応、PID / stop フラグ管理）

- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）

- ai/
  - news_nlp.py — ニュース記事を LLM で評価して ai_scores に書き込む
  - regime_detector.py — マクロニュース + ETF MA200 で市場レジーム判定
  - __init__.py

- monitoring/
  - monitoring_db.py — SQLite による監視ログの CRUD（テーブル初期化、upsert 等）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 滞留注文・約定異常検出
  - risk_monitor.py — ドローダウン / ポジション上限監視（Kill Switch トリガ用）
  - kill_switch.py — killing logic（flag ファイル書き込み）
  - monitoring_engine.py — 各モニタを束ねる
  - alert_manager.py — （アラート送信の抽象 : 実装は省略されている場合あり）

- execution/
  - （ExecutionEngine や BrokerClientFactory、OrderManager, OrderRepository 等：発注関連コード）

- portfolio/
  - portfolio_builder.py — 候補選定、等配分 / スコア配分
  - position_sizing.py — 発注株数算出（リスクベース・等配分等）
  - risk_adjustment.py — セクターキャップ、レジーム乗数
  - __init__.py

- research/
  - factor_research.py — モメンタム / ボラティリティ / バリューの計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - __init__.py

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール
  - __init__.py

- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - __init__.py

- data/
  - （実行時生成される DB ファイル、pid / flag ファイル等を置くディレクトリ）
  - 例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag

---

## デフォルト値（参考）

- MONITOR_POLL_INTERVAL = 60 秒（run_monitoring）
- DUCKDB_PATH = data/kabusys.duckdb
- SQLITE_PATH = data/monitoring.db
- PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
- PID_FILE_PATH = data/execution.pid
- KILL_FLAG_PATH = data/kill.flag

---

以上が本リポジトリ（src/kabusys）に対する README の概要です。  
追加で「デプロイ手順」「systemd / Supervisor 用のサービスファイル例」「詳細な設定項目の説明（config/*.yaml）」などが必要であれば、用途に合わせて追記します。