# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株向けの自動売買／リサーチ／監視ツール群です。  
本 README はプロジェクトの概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を含むパッケージです。

- 取引エンジン（ExecutionEngine）による発注制御（本番 / ペーパートレード対応）
- ポートフォリオ構築（銘柄選定、重み付け、株数決定、リスク調整）
- ファクター計算や特徴量探索などのリサーチ機能（DuckDB を用いた時系列解析）
- ニュース NLP / レジーム判定（OpenAI API を使ったセンチメント解析）
- システム監視（プロセス稼働確認、データ鮮度、リスク監視、Kill Switch）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針として、DB は DuckDB（分析用）と SQLite（監視・発注履歴等）を使い、外部 API へのアクセスは最小限に抑えつつ、フェイルセーフ（API失敗時は安全側にフォールバック）を重視しています。

---

## 主な機能一覧

- 設定管理
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行/監視
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV=paper_trading 時は MockBroker を使用し `data/paper_trading.db` を用いる
  - Monitoring ポーリング（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- モニタリング
  - SystemMonitor: CPU/MEM/Disk、Execution プロセス生存、データ鮮度チェック
  - TradeMonitor: 発注ログの滞留／約定異常チェック（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、risk_logs 書込み
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み ExecutionEngine を停止させる仕組み
- ポートフォリオ構築
  - 候補選定（スコア降順）、等重／スコア重みの計算
  - セクター集中制限やレジームに応じた乗数適用
  - 株数算出（リスクベース、等配分／スコア配分）、単元株丸め、aggregate cap 調整
- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン、IC（Spearman）などの統計解析ユーティリティ
- AI（OpenAI）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
  - バッチ・リトライ・レスポンス検証等の耐障害設計あり
- 運用ツール
  - ペーパートレード検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（ソースで | 型合併演算子を利用）
- DuckDB（Python パッケージ: duckdb）
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定ファイルの YAML 検証を行う場合、任意）

例（最低限のインストール例）:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb psutil openai PyYAML
```

※requirements.txt が無い場合は上記パッケージを個別にインストールしてください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 用）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）
- OPENAI_API_KEY（AI 機能利用時）

その他:
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（1=yes）

設定は .env / .env.local で管理できます。自動ロード機能が有効（デフォルト）です。

---

## セットアップ手順（推奨）

1. リポジトリをクローン／チェックアウト
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell 等)
   ```
3. 必要パッケージのインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb psutil openai PyYAML
   ```
4. .env を作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザード後、.env が生成されます。生成後は設定検証を実行してください。

5. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗にする場合:
   python -m kabusys.validate_config --strict
   ```
6. 必要に応じてデータディレクトリ作成:
   ```bash
   mkdir -p data logs
   ```

---

## 使い方（実行例）

- ExecutionEngine（注文エンジン）を起動:
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を利用し、`data/paper_trading.db` に記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動を行わず終了します。
  - 実行中に `data/stop_requested.flag` を作成すると終了要求を検知してセッションを停止します。
  - ExecutionEngine は PID ファイル（デフォルト: data/execution.pid）を出力します。

- Monitoring（監視ループ）を起動:
  ```bash
  # ポーリング間隔を環境変数で変更したい場合:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。
  - 監視は本番 sqlite_path を使用（環境に依存せず監視 DB は本番 DB を参照）。

- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連関数の呼び出し（Python から直接）:
  - ニューススコアリング:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - ※APIキーは引数に渡すか環境変数 OPENAI_API_KEY を設定してください。

- ログ
  - ログはデフォルトで `logs/<app_name>.log` に日次ローテートで保存されます（`kabusys.utils.logging_setup.setup_logging` による）。
  - 標準出力も併せて出力されます。

---

## ファイル／フラグ制御（運用に関する注意）

- 停止制御:
  - data/stop_requested.flag: 外部からの停止要求（存在を検知してモジュールが終了）
  - data/kill.flag: KillSwitch が書き込むファイル（ExecutionEngine に停止命令を出す用途）
- PID:
  - Execution エンジンは PID ファイル（デフォルト: data/execution.pid）を出力します。

---

## ディレクトリ構成

以下はこのリポジトリの主要なファイル／ディレクトリ（src/kabusys 以下）の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定読み込みロジック
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - utils/
    - __init__.py
    - logging_setup.py          — 共通ログ設定
    - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB の初期化／読み書き
    - monitoring_engine.py     — 監視コンポーネント束ね（ポーリングループ）
    - system_monitor.py        — CPU/MEM/DISK/データ鮮度監視
    - trade_monitor.py         — 発注ログ監視（存在: ファイルでは省略）
    - risk_monitor.py          — ドローダウン・ポジション監視
    - kill_switch.py           — KillSwitch 実装
    - alert_manager.py         — アラート管理（存在: ファイルでは省略）
  - execution/
    - execution_engine.py      — ExecutionEngine 本体（存在: ファイルの一部のみ）
    - broker_factory.py        — ブローカークライアント生成（Mock / 本番判定）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数算出・集約制限
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py       — モメンタム / ボラ / バリュー等ファクター
    - feature_exploration.py   — 将来リターン・IC / 統計サマリー等
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — レジーム判定（MA + マクロセンチメント）
  - data/                      — 実行時に使用する SQLite / DuckDB / フラグファイル等（推奨）
  - logs/                      — ログ出力先（デフォルト）

（注）リポジトリ内には他にも補助モジュールやファイルが含まれます。上記は主なファイルの抜粋です。

---

## 運用上の注意事項 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）での起動前に必ず `python -m kabusys.validate_config` を実行し、警告・エラーを確認してください。
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダでも注意喚起あり）。
- OpenAI API を使う処理はコストとレート制限に注意してください（内部でリトライとバッチ処理を実装していますが、運用時の制限は不可避です）。
- ペーパートレードモードでは発注処理が完全に分離された専用 DB を使用します（PAPER_TRADING_SQLITE_PATH）。
- Kill Switch / stop flag の扱いは慎重に（特に live 環境では自動クリア設定 KILL_FLAG_CLEAR_ON_START=1 は危険）。

---

## サポート・拡張ポイント（開発者向けメモ）

- DuckDB を用いた分析関数は外部 API に依存しないため、オフライン検証が容易です。
- AI モジュール（news_nlp, regime_detector）は OpenAI SDK の API 変更に対して保護層（例外処理・ステータスコード判定）を設けているため、実装を流用しやすい設計になっています。
- ポートフォリオ構築ロジック（weight 計算 / position sizing）は純粋関数群として分かれているため、ユニットテストや戦略差し替えが容易です。

---

必要であればこの README をベースに「運用手順書」「デプロイ手順」「設計ドキュメント（各モジュールの詳細）」を別途作成できます。どの項目を詳しく補足したいか教えてください。