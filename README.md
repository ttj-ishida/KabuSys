# KabuSys

日本株自動売買システムのコアライブラリ群（README はコードベースの抜粋に基づく要約）  

以下はプロジェクト内の主要スクリプト・モジュールの説明、セットアップ、使い方、ディレクトリ構成の案内です。

注意: これはプロジェクトの一部（ドメインロジックや外部依存の具象実装は省略）に基づく README です。実運用前に必ず config/*.yaml や .env の設定を確認してください。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのライブラリ／実行基盤です。  
主な目的は以下：

- データベース（DuckDB / SQLite）を利用したリサーチ・ファクター計算
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- ExecutionEngine（発注処理）とそれを監視する Monitoring 機構
- Paper Trading 用の分離された DB とモック挙動
- ニュース NLP / レジーム判定に OpenAI を利用したスコアリング
- 運用支援ツール（.env ウィザード、設定検証、検証レポート等）

---

## 機能一覧（抜粋）

- 環境変数・設定管理（kabusys.config）
- .env の対話式作成・更新ウィザード（kabusys.config_setup）
- 起動前の設定検証 CLI（kabusys.validate_config）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、本番 DB と分離（data/paper_trading.db）
  - stop フラグファイル検出で安全停止
- 監視ループ起動スクリプト（run_monitoring.py）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は本番の sqlite_path を使ってログを残す
- 監視サブシステム
  - SystemMonitor（プロセス死活・資源使用率・データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常）
  - RiskMonitor（ドローダウン・ポジション数上限）
  - KillSwitch（条件に応じた停止フラグの作成）
  - AlertManager（LINE Push による通知）
  - MonitoringDB（SQLite での永続化 + マイグレーション）
- ポートフォリオ構築ユーティリティ（portfolio パッケージ）
  - 候補選定・等重/スコア重み付け・ポジションサイズ計算・セクター制限など
- リサーチ／ファクター計算（research パッケージ）
  - momentum, volatility, value 等のファクター
  - forward returns, IC, factor summary
- AI 関連
  - ニュース NLP（OpenAI を使った銘柄別センチメント -> ai_scores テーブルに書込）
  - レジーム判定（ETF MA + マクロニュースの LLM スコア合成）
- 運用ツール
  - paper_verification_report：Paper Trading DB を基にパス/フェイル判定を出力

---

## 動作環境・依存

- Python: 3.10 以上を推奨（PEP 604 の `|` 型注釈等を使用）
- 推奨パッケージ（一部必須）
  - psutil
  - duckdb
  - openai
  - requests
  - （任意 / 設定検証で YAML 検証を行う場合）PyYAML
- その他: ネットワーク接続（kabuステーション API / OpenAI 等）やローカルファイル書き込み権限

インストール例（仮）:
pip install psutil duckdb openai requests PyYAML

---

## 環境変数（主要）

（デフォルト値や意味は `kabusys.config.Settings` の実装を参照）

必須（最低限設定するもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

よく使うオプション
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、paper 用 SQLite を利用して本番 DB と分離
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（INFO 等）
- OPENAI_API_KEY — OpenAI を使う機能（ニュース NLP / レジーム判定）で必要
- PAPER_FILL_MODE — ペーパートレードの約定振る舞い（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動でクリアするか（1 = 真、デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読込を無効化（テスト用途）

.env は絶対にリポジトリにコミットしないでください。

---

## セットアップ手順

1. Python 環境準備（3.10+）
2. 必要パッケージをインストール
   - 例: pip install psutil duckdb openai requests PyYAML
3. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example（プロジェクトにある場合）を参照
4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合: python -m kabusys.validate_config --strict
5. DB 初期化
   - run_monitoring / run_execution を起動すると MonitoringDB のテーブル作成（冪等）が行われます
   - DuckDB は使用する分析クエリで自動的にファイルを作成／参照します

---

## 使い方（主要スクリプト・コマンド）

プロジェクトルートで以下を実行します（Python モジュールとして）：

- .env 生成（対話ウィザード）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番／paper_trading に応じて動作）
  python -m kabusys.run_execution
  - 起動前に data/execution.pid などのファイルが管理されます
  - 停止は data/stop_requested.flag を作成するか、内部ルールで kill.flag が書かれると停止します

- 監視ループ起動（SystemMonitor をポーリング）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を指定可能（例: MONITOR_POLL_INTERVAL=30）
  - run_monitoring は KABUSYS_ENV にかかわらず「本番 sqlite_path」を使用して監視ログを残します

- Paper Trading 検証レポート生成（ローカル DB を参照）
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合: --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能

- AI（ニュース NLP / レジーム判定）
  - OpenAI の API キーが必要（OPENAI_API_KEY または関数引数）
  - 関数インターフェースは kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime

停止・制御に関するファイル
- data/stop_requested.flag — run_execution/run_monitoring のポーリングループを停止させるために存在確認されるファイル（生成すれば安全停止）
- data/kill.flag — KillSwitch により生成される停止フラグ（ExecutionEngine に停止シグナル）
- data/execution.pid — ExecutionEngine の PID ファイル（run_execution が管理）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数・設定管理（.env 自動読み込みロジック含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ（主なもの）
- ai/
  - news_nlp.py — ニュースの NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（OpenAI + MA）
- monitoring/
  - monitoring_db.py — SQLite 永続化層（テーブル作成・マイグレーション含む）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 発注・約定監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — 停止フラグ生成ユーティリティ
  - monitoring_engine.py — 各 Monitor を束ねる実行エンジン（テスト / 本番用）
  - alert_manager.py — LINE Push 通知
- execution/ — ExecutionEngine 周辺（OrderManager, RiskManager, BrokerFactory 等）
- portfolio/ — ポートフォリオ構築ロジック（builder, sizing, risk_adjustment）
- research/ — ファクター計算・特徴量探索
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/ — 実行時生成されるファイル（.pid, .flag, sqlite/duckdb ファイルなど）

（上記はコード抜粋に基づく要約です。実際のプロジェクト全体はさらに多くのファイルを含む可能性があります。）

---

## 開発・デバッグのヒント

- 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用）。
- Settings のプロパティアクセスは必須環境変数を参照すると例外を投げます（_require）。validate_config で事前チェックしてください。
- run_monitoring は監視ログの DB（SQLite）を常に本番パスから開く設計です。テスト用に別 DB を使いたい場合は Settings の環境変数を調整してください。
- OpenAI を利用するコードは API 呼び出し部分をラップしているため、単体テスト時は該当関数をモックしてください（コード内に patch しやすい実装あり）。

---

## よくあるトラブルと対処

- 必須環境変数未設定で起動時に例外が出る:
  - python -m kabusys.validate_config で原因を特定し .env を作成・更新してください。
- OpenAI 関連で "API key missing" が出る:
  - OPENAI_API_KEY を .env に設定、または関数呼び出し時に明示的に渡してください。
- monitoring/run_execution が即終了してしまう:
  - data/stop_requested.flag や data/kill.flag が存在していないか確認してください。
- psutil の権限エラー（プロセス優先度設定等）:
  - 実行ユーザの権限により一部操作（nice, cpu_affinity, priority）は失敗します。警告が出ますが実行そのものは継続します。

---

以上がこのコードベースの README.md 相当の要約です。必要であれば、README に入れる具体的なサンプル .env テンプレートや systemd unit の例（run_execution/run_monitoring をサービス化する方法）も作成できます。どの内容を追加しましょうか？