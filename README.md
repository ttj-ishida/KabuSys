# KabuSys

日本株自動売買システムの軽量コアライブラリ群と起動スクリプト集です。  
このリポジトリは、取引実行（ExecutionEngine）、監視（Monitoring）、リサーチ／ファクター計算、AI（ニュース/NLP）連携等の主要機能をモジュール化して提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を含みます。

- 実際の発注（live）やペーパートレード（paper_trading）用の ExecutionEngine
- 稼働監視（SystemMonitor）・発注/約定の監視（TradeMonitor）・リスク監視（RiskMonitor）
- Kill Switch による安全停止機構
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算、セクターキャップ適用）
- リサーチ（ファクター計算、将来リターン、IC 計算など）
- AI 経由のニュースセンチメント評価（OpenAI 使用）
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード / 検証 CLI、監査レポート生成 など

設計方針の一部：
- DB は DuckDB（分析）と SQLite（監視 / 履歴）を併用
- 環境依存の挙動は環境変数・.env により管理
- 本番 DB とペーパートレード DB は分離

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine（発注、リスク管理、オーダー管理、リコンサイル）
  - 環境切替: KABUSYS_ENV が `paper_trading` の場合は MockBroker（発注はローカル DB に記録）

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / Execution プロセスの生存確認、データ鮮度チェック
  - TradeMonitor: 注文の滞留や約定異常の検出（コード内に実装）
  - RiskMonitor: ドローダウンやポジション数上限の監視とアラート登録
  - KillSwitch: しきい値超過時に data/kill.flag を書き込み停止指示
  - MonitoringEngine: 各 Monitor を束ねて定期ポーリング

- ポートフォリオ構築
  - 候補選定、等金額/スコア加重配分、リスクベース配分、単元丸め、セクターキャップ、レジーム乗数

- リサーチ
  - Momentum / Volatility / Value 等ファクター計算（DuckDB 上の prices_daily / raw_financials を利用）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ

- AI（OpenAI）
  - ニュースから銘柄別センチメントを算出し ai_scores テーブルへ書き込み
  - マクロニュースと MA200 乖離から市場レジーム（bull/neutral/bear）を判定して DBへ書き込み

- ツール
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 必要な依存パッケージ（主要）

- Python 3.9+（型注釈は 3.10+/3.11 も想定）
- duckdb
- psutil
- openai
- （任意）PyYAML（config/*.yaml の内容検証で使用）

インストール例（pip）:
pip install duckdb psutil openai

PyYAML を使いたい場合:
pip install pyyaml

---

## セットアップ手順

1. リポジトリをクローン / 取得
   - git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は上記主要パッケージを個別にインストール）

4. 環境変数の作成（.env）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で .env を作成
   - 自動ロード: config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も FAIL としたい場合: python -m kabusys.validate_config --strict

6. データディレクトリとログディレクトリを確認
   - デフォルト SQLite / DuckDB パスは data/ 以下、ログは logs/ 以下に出力されます。
   - 必要に応じて環境変数（DUCKDB_PATH / SQLITE_PATH / LOG_DIR）で変更してください。

---

## 環境変数（主要一覧）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨/オプション:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/...
- LOG_DIR — ログ格納先（デフォルト logs/）
- OPENAI_API_KEY — AI 機能（news_nlp, regime_detector）で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（“1”で有効。注意して使用）

詳細は kabusys.config.Settings のプロパティと config_setup のウィザード出力を参照してください。

---

## 使い方（実行例）

- 環境構築（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（取引エンジン）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に発注記録を残します。
    - 起動時に data/stop_requested.flag が存在すると起動をせず終了します。
    - 実行中は data/execution.pid に PID を書きます。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します。
    - 停止は data/stop_requested.flag の作成で制御できます（ファイル存在でループ終了）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能／レジーム判定（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り DB テーブルへ書き込みを行います。OPENAI_API_KEY の設定が必要です。

停止フロー（手動）:
- Execution を安全に停止させたい場合は data/kill.flag を作成する（KillSwitch により検出されると Engine に停止命令が出ます）。
- 監視ループ／実行スクリプトは data/stop_requested.flag の存在チェックを行い、存在すると順次終了します。

ログ:
- ログは標準出力とログファイル（logs/<app_name>.log、日次ローテーション）に出力されます。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数/.env ロードと Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリングループ起動スクリプト

subpackages:
- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — マクロ + MA200 によるレジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 監視 DB 用永続化層
  - system_monitor.py      — システム/データ鮮度監視
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag 書き込み/評価
  - monitoring_engine.py   — Monitor を束ねるエンジン
  - alert_manager.py       — （アラート送信ロジック — コード参照）
  - trade_monitor.py       — （取引監視ロジック — コード参照）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/
  - monitoring_db.py
- utils/
  - logging_setup.py       — 共通ログ初期化
  - process_priority.py    — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py

その他:
- data/                   — デフォルト DB / フラグファイル保存先（自動生成されることが多い）
- logs/                   — ログ出力先（デフォルト）
- config/                 — YAML 設定テンプレート（system_config.yaml 等）

（実際のファイル配置はリポジトリのソースを参照してください）

---

## 開発・運用上の注意点

- 本番（KABUSYS_ENV=live）では環境変数（特に API トークンやライン通知など）と DB パスを慎重に確認してください。validate_config は live の場合に追加警告を出します。
- OpenAI を使う機能は API キーが必須です。未設定時は呼び出し側で ValueError を送出する関数が存在します（安全側設計）。
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- ログ / DB 更新処理で例外が発生してもシステムを停止させないようフェイルセーフ設計が多用されていますが、運用前に十分な検証を行ってください。
- Monitoring は MONITOR_POLL_INTERVAL 環境変数で間隔を制御できます（デフォルト 60 秒）。不適切な短い設定は API レートやコストに影響するため注意してください。
- process_priority による優先度設定は OS 権限に依存し、失敗時は警告のみ出力してスキップします。

---

## トラブルシューティングのヒント

- .env が読み込まれない場合:
  - プロジェクトルートが .git または pyproject.toml により特定されないと自動ロードはスキップされます。手動で .env をプロジェクトルートに置くか KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してカスタムロードしてください。
- OpenAI API 呼び出しで失敗する場合:
  - OPENAI_API_KEY が正しくセットされているか、ネットワークアクセス、レート制限を確認してください。ライブラリ内でリトライロジックがありますが、キー自体が無いと例外になります。
- ログファイルが作れない場合:
  - 権限やディスク空き容量を確認。ログディレクトリを environment で指定可能（LOG_DIR）。

---

必要に応じて README を拡張して、より詳細な起動手順、設定例、運用手順（例: systemd の unit ファイル、コンテナ化の指針）を追加できます。追加項目が必要であれば教えてください。