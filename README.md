# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。  
この README ではプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

> 備考：このドキュメントは src/kabusys 配下のコードを参照して作成しています。

---

## プロジェクト概要

KabuSys は次のような要件を満たす自動売買基盤です：

- 戦略ファクター算出（DuckDB 上の株価データを用いたファクター計算）
- ポートフォリオ構築（候補選定・重み付け・ロット丸め・位置サイズ算出）
- ExecutionEngine（発注管理、リスク制御、リコンシリエーション等）
- 監視（System / Trade / Risk モニタ）と Kill Switch（条件により ExecutionEngine を停止）
- Paper Trading（実口座と分離したモード）と実稼働モードの切替
- OpenAI を用いたニュース NLP（センチメント）とレジーム検出
- 各種ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

設計方針として、DB（DuckDB / SQLite）を用いてデータ永続化・分析を行い、外部 API（kabuステーション、J-Quants、OpenAI）への接続を分離しています。Paper Trading モードでは本番 DB と完全に分離されます。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成）：`kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml の事前チェック）：`kabusys.validate_config`
- ExecutionEngine 起動スクリプト：`kabusys.run_execution`
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper DB を使用
  - 停止は data/stop_requested.flag、Kill Switch は data/kill.flag を利用
- Monitoring のポーリング実行：`kabusys.run_monitoring`
  - システム状態・データ鮮度・取引／リスク監視を定期実行
  - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視永続化（SQLite）用ユーティリティ：monitoring_db
- ポートフォリオ構築（候補選定・重み付け・位置サイズ算出）
- 研究用モジュール（ファクター計算 / 特徴量探索）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- ツール：Paper Trading 検証レポート生成スクリプト

---

## 前提（Prerequisites）

- Python 3.10 以上推奨（コードは 3.10+ の構文を使用）
- 必須ライブラリ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml 内容検証を行う場合は任意で推奨）
- SQLite は標準ライブラリで使用可能

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（requirements.txt があれば `pip install -r requirements.txt` を推奨）

---

## セットアップ手順

1. リポジトリをクローン・移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境の作成と依存ライブラリのインストール（上記参照）

3. 環境変数ファイル (.env) を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードに従って必須項目（J-Quants トークン、kabu API パスワード等）を入力してください。
   - 生成される .env のデフォルト配置はプロジェクトルートの `.env`。

4. 設定検証（必須環境変数・パス・YAML 等の事前チェック）
   ```
   python -m kabusys.validate_config
   ```
   問題がある場合はメッセージに従い .env / config を修正してください。`--strict` を付けると警告もエラー扱いになります。

5. 必要なディレクトリの作成（自動でも作成されますが、手動で用意しておくと権限問題等を避けられます）
   - data/（SQLite や PID / flag を置く）
   - logs/（ログファイル）
   ```
   mkdir -p data logs
   ```

6.（任意）OpenAI 機能を利用する場合は環境変数 `OPENAI_API_KEY` を設定してください。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（本番／paper_trading は KABUSYS_ENV で切替）
  ```
  python -m kabusys.run_execution
  ```
  - Paper Trading ではデフォルトで `data/paper_trading.db` を使用し、本番 DB と分離されます。
  - 実行中の PID は `data/execution.pid` に書き込まれます。
  - 停止するには `data/stop_requested.flag` を作成するか、Kill Switch により `data/kill.flag` が書き込まれると停止します。

- Monitoring を起動（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）。
  - 監視は本番 sqlite_path を常に参照（モニタは環境にかかわらず本番監視 DB を使用します）。

- .env の作成／更新（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能（デフォルト: data/paper_trading.db）

- AI 関連（ニュース NLP / レジーム検出）はライブラリ関数経由で呼び出します（OPENAI_API_KEY が必要）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — AI 機能利用時に必須
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒）
- PAPER_FILL_MODE — Paper Trading のフィルモード（instant|partial|never|reject）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START — 本番での Kill Switch 自動クリア (0|1)

既定値や検証は `kabusys.config.Settings` と `kabusys.validate_config` を参照してください。

---

## ログ & ファイル位置

- ログ: logs/<app_name>.log（setup_logging により stdout とファイル出力が設定されます）
  - app_name 例: "execution", "monitoring"
- データ:
  - DuckDB: DUCKDB_PATH（例: data/kabusys.duckdb）
  - Monitoring SQLite: SQLITE_PATH（例: data/monitoring.db）
  - Paper Trading SQLite: PAPER_TRADING_SQLITE_PATH（例: data/paper_trading.db）
- PID / フラグ:
  - Execution PID: data/execution.pid（run_execution によって書き込まれます）
  - 停止要求フラグ: data/stop_requested.flag（存在を確認してループを終了）
  - Kill Switch: data/kill.flag（KillSwitch が書き込むと ExecutionEngine 停止指示）

---

## 注意点 / 運用メモ

- Monitoring は本番の sqlite_path を参照します。テストやローカルでの確認時は意図した DB を使っているか確認してください。
- Paper Trading は本番 DB と分離されています（paper_trading モードで PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を利用する処理は外部 API への依存と料金が発生します。API キーの管理に注意してください。
- run_execution/run_monitoring はログや PID 管理、停止フラグのチェックなどを行います。運用時は systemd / supervisor / コンテナ等でプロセスマネージャに任せることを想定しています。
- kill.flag を自動でクリアする設定（KILL_FLAG_CLEAR_ON_START）は本番環境では危険です（validate_config が警告します）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要モジュールとその説明です（完全な一覧ではなく主要部のみ）。

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン情報
  - config.py — 環境変数 / 設定管理（Settings クラス）
  - config_setup.py — .env 作成ウィザード（対話式 CLI）
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py — 銘柄選定・スコアソート
    - position_sizing.py — 株数決定・スケールダウン・単元丸め
    - risk_adjustment.py — セクターキャップ適用、レジーム乗数
    - __init__.py — 上記 API を公開
  - monitoring/
    - monitoring_db.py — SQLite スキーマ/永続化ラッパ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （取引監視ロジック、ファイルに含まれるが省略）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 複数モニタを束ねるエンジン実装
    - alert_manager.py — （アラート送信ロジック、ファイルに含まれるが省略）
  - execution/
    - broker_factory.py — BrokerClient の生成（Mock / 実ブローカー切替）
    - execution_engine.py — 発注セッション、run_session 実装
    - order_manager.py — 注文管理ロジック
    - order_repository.py — 注文永続化層
    - reconciler.py — ブローカーと DB の突合せ
    - risk_manager.py — 発注前のリスクチェック（Rate limit 等）
  - research/
    - factor_research.py — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC 計算、統計サマリ
    - __init__.py — 研究用 API エクスポート
  - ai/
    - news_nlp.py — ニュースを集約し OpenAI でセンチメント付与（ai_scores 書込）
    - regime_detector.py — ma200 + マクロNLPでレジーム判定、market_regime への書込
    - __init__.py — ai の公開 API
  - utils/
    - logging_setup.py — 共通ログ設定（stdout + 日次ローテート）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

（上記に含まれていない補助モジュールも複数あります。詳細は各ファイルの docstring を参照してください。）

---

## 開発・拡張に関するヒント

- DuckDB のテーブルスキーマ（prices_daily / raw_financials / raw_news 等）に依存しています。データを投入してから research モジュールを実行してください。
- AI 関連のテストは OpenAI クライアント呼び出し部分をモックする設計になっています（テスト時は patch して外部依存を切る）。
- Monitoring / Execution の単体テストは DB のモックや一時ファイル（data 以下）を用いることで容易に実行できます。

---

## 最後に

まずは以下の手順を順に実行することを推奨します：

1. 依存ライブラリをインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定検証
4. 必要ならデータを準備（DuckDB / SQLite）
5. python -m kabusys.run_monitoring / python -m kabusys.run_execution を起動して動作確認

不明点があれば、各モジュールの docstring（ファイル冒頭）を参照してください。README に足りない箇所や、追加したい使用例があれば教えてください。