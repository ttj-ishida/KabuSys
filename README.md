# KabuSys

日本株自動売買システム（KabuSys）  
このリポジトリは、アルゴリズム売買のコアロジック、実行エンジン、監視・アラート、研究用ファクター計算、ニュースNLP を組み合わせた自動売買フレームワークです。

バージョン: 0.1.0

---

## 概要

KabuSys は次の主要コンポーネントで構成されます。

- ExecutionEngine：実際の発注ロジック（本番/ペーパートレード両対応）
- Monitoring（監視）：システム稼働状況、注文/約定ログ、リスク監視、Kill Switch
- Portfolio モジュール：銘柄選定、重み算出、ポジションサイズ計算、セクター制限等
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI モジュール：OpenAI を通じたニュースセンチメント評価、レジーム判定
- CLI ユーティリティ：.env ウィザード（config_setup）、設定検証（validate_config）、レポート生成ツール等
- ユーティリティ群：ログ設定、プロセス優先度制御など

設計上のポイント：

- 環境変数/.env による設定管理（config.Settings）
- DuckDB（分析用）と SQLite（監視／ペーパートレード用）を併用
- 本番環境とペーパートレードのデータ分離が可能
- AI 機能は環境変数で OpenAI API キーを指定して使用

---

## 機能一覧

- 実行エンジン
  - 本番・ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBrokerClient を用意）
  - リスク管理（ポジション上限、利用率、ドローダウン等）
  - 注文管理・照合（OrderManager/Reconciler）

- 監視
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（DuckDB 上の株価データ）
  - 監視ログ（SQLite）への永続化（system_status, trade_logs, risk_logs, positions, dashboard）
  - Kill Switch（条件成立時に data/kill.flag を作成）
  - stop_requested.flag による外部停止フラグ対応

- ポートフォリオ構築
  - 候補選定、等金額/スコア加重の重み算出
  - セクター集中制限の適用
  - ポジションサイズ決定（単元丸め、aggregate cap）

- 研究・解析
  - Momentum、Volatility、Value 等のファクター計算（DuckDB）
  - 将来リターン・IC 計算・統計サマリ

- AI（任意）
  - ニュースを LLM（gpt-4o-mini）で評価し銘柄別センチメントを ai_scores に保存
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定

- ツール
  - .env 対話式ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 要求環境（推奨）

- Python 3.10 以上（typing による新構文使用のため）
- 必要となる Python パッケージ例（実行する機能により異なる）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (validate_config の YAML 検証を使う場合)
- SQLite は標準ライブラリに含まれます

※ 実際の requirements.txt はプロジェクトに応じて用意してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（例）
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - AI 機能を使わない場合は openai は不要
   - validate_config の YAML 検証は PyYAML があると有効化されます

4. 初期設定（.env）を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト）を作成・更新します。J-Quants トークンや kabu API パスワードは必須です。

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ確保
   - デフォルトでは以下のファイル/ディレクトリを使用します:
     - data/kabusys.duckdb
     - data/monitoring.db
     - data/paper_trading.db（KABUSYS_ENV=paper_trading）
     - logs/ （ログ保存先）
   - これらは自動作成されますが、必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。

---

## 使い方

主要な起動・ユーティリティの実行方法を示します。

- 実行エンジン（ExecutionEngine）起動
  - 本番・ペーパーは KABUSYS_ENV により切替
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 起動すると PID ファイル（data/execution.pid）を作成します。

- 監視プロセス起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  ```
  python -m kabusys.run_monitoring
  ```
  - 監視は本番 sqlite_path を使用（監視 DB は環境に依らない）

- .env ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（SQLite DB を読み取り）
  ```
  python -m kabusys.tools.paper_verification_report
  ```
  期間指定や DB パス指定:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）の注意
  - OpenAI を呼ぶ機能は OPENAI_API_KEY を設定する必要があります。
  - 例（環境変数経由）:
    ```
    export OPENAI_API_KEY=sk-...
    ```
  - AI 呼び出しは課金対象のため、テストやローカル実行時は注意してください。

- Kill Switch / stop フラグ
  - 監視が Kill 条件を検出すると data/kill.flag を作成します（ExecutionEngine は起動時や監視でこのファイルをチェックして停止します）。
  - 明示的に kill.flag をクリアするにはファイルを削除してください（KillSwitch.clear() を利用するか、手動で削除）。
  - 外部の停止要求（stop_requested.flag）は run_monitoring / run_execution が検知して処理を終了します。

---

## 環境変数（主なもの）

デフォルト値は Settings クラスで定義されています。主な項目：

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）

- データベース
  - DUCKDB_PATH — 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）

- ログ / デバッグ
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR — ログディレクトリ（デフォルト: logs/）

- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector などで使用）

- その他
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
  - PAPER_FILL_MODE — ペーパートレード時の約定モード（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

詳しくは kabusys.config.Settings のドキュメントを参照してください。

---

## ディレクトリ構成

以下は主要なファイル・モジュールの一覧と簡単な説明（src/kabusys 以下を想定）。

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数/.env 管理（Settings）
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト

  - execution/
    - execution_engine.py — 実行エンジン本体（セッション管理等）
    - broker_factory.py — Broker クライアント抽象化 / Mock 実装切替
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 実行周りのコンポーネント

  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化（テーブル作成 / read/write）
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文/約定監視（ログ解析）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — 条件により kill.flag を作成
    - monitoring_engine.py — 各モニタを束ねるループ
    - alert_manager.py — アラート送信（LINE 等のラッパー）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 発注株数算出
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ

  - ai/
    - news_nlp.py — ニュース記事の LLM センチメント評価・ai_scores 書き込み
    - regime_detector.py — ETF MA + マクロニュースでレジーム判定

  - tools/
    - paper_verification_report.py — Paper Trading レポート生成スクリプト

  - data/ (ランタイム生成想定)
    - monitoring.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - paper_trading.db (ペーパートレード用 SQLite)
    - kill.flag / stop_requested.flag / execution.pid などの制御ファイル

  - utils/
    - logging_setup.py — 統一的なログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## よくある運用上の注意

- validate_config を起動前に実行して設定漏れを検出してください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（誤って Kill Switch をクリアしない為）。
- AI モジュールは外部 API と課金を伴うため、キー管理と実行ポリシーに注意してください。
- ログディレクトリ作成に失敗した場合、システムはコンソール出力（stdout）にフォールバックします。ログディレクトリの権限を確認してください。
- run_monitoring / run_execution の停止は以下のファイルで制御できます:
  - data/stop_requested.flag — 外部からの停止要求（ファイルを作成するとプロセスは graceful に終了）
  - data/kill.flag — 監視側が危険と判断した際に作成（ExecutionEngine によるチェックで停止）

---

## トラブルシューティング

- 「環境変数が足りません」エラー:
  - 必須変数 JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD を .env に設定し、python -m kabusys.validate_config で確認してください。

- DuckDB / SQLite ファイルが見つからない:
  - デフォルトパスは data/ 以下。別パスを使う場合は DUCKDB_PATH / SQLITE_PATH を設定してください。

- OpenAI 呼び出しが失敗する:
  - OPENAI_API_KEY が正しいか、ネットワークアクセス、レート制限を確認してください。news_nlp/regime_detector はエラー成立時にフェイルセーフ（スコア 0 など）で継続する設計です。

---

README はプロジェクトの導入・運用の基本をまとめたものです。より詳細な設計方針・アルゴリズム（PortfolioConstruction.md、StrategyModel.md 等）は別ドキュメントを参照してください（リポジトリ内に存在する場合）。必要であれば各モジュールの使い方や設計ドキュメントを追記します。