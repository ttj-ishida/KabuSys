# KabuSys — README

日本株自動売買システムの一部（ライブラリおよび運用スクリプト群）です。  
この README はコードベース（src/kabusys）に含まれる主要コンポーネントの概要、セットアップ、実行方法、ディレクトリ構成をまとめたものです。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境設定（.env）と検証
- 実行方法（Monitoring / Execution / ツール）
- 主要環境変数
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークの一部実装です。  
主な目的は以下のとおりです。

- 市場データやファクター計算（DuckDB）に基づくリサーチ機能
- ポートフォリオ構築、ポジションサイズ計算（純関数群）
- ExecutionEngine（発注エンジン）とその監視（Monitoring）
- Paper Trading（ペーパートレード）用分離 DB と Mock ブローカー
- ニュースを LLM（OpenAI）で解析する NLP モジュール、および市場レジーム判定
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

本リポジトリはライブラリ的にインポートして使うことも、スクリプトとして単体実行することも想定されています。

---

## 機能一覧

主な機能（抜粋）

- 環境設定管理（.env の自動ロード、config.Settings）
- 対話式設定ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のとき MockBroker を使い data/paper_trading.db に記録
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - システム状態、注文・約定の監視、リスク監視、Kill Switch 連動
- MonitoringDB（SQLite）永続化層と監視用 API（monitoring/）
- Trade / System / Risk のモニタ＆アラート統合（MonitoringEngine）
- Portfolio 構築ユーティリティ（選定・重み付け・ポジションサイズ計算・セクター制約）
- Research（DuckDB を用いたファクター計算、forward returns、IC など）
- AI モジュール
  - news_nlp: ニュースを OpenAI でスコアリングし ai_scores に書き込み
  - regime_detector: ma200 とマクロニュースで市場レジーム判定
- 運用ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート出力

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を用意（推奨: 3.10+）
2. 必要パッケージをインストール（プロジェクトに requirements.txt がある前提）:
   - 例:
     ```
     python -m pip install -r requirements.txt
     ```
   - 最低限必要になりやすいライブラリ:
     - duckdb
     - psutil
     - openai
     - （Paper report / YAML 検証用に PyYAML があると便利）
3. プロジェクトルートに移動（README と同じ階層に .env を置く想定）
4. 初期 .env を作成（対話式）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードに従って J-Quants トークン、kabu API パスワード、DB パス等を設定します。
5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   問題がなければ OK が表示されます。--strict を付けると警告も失敗扱いになります。

注意:
- 自動で .env を読み込む機能があり、プロジェクトルート（.git または pyproject.toml を基準）を検出して .env / .env.local を読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要環境変数（抜粋とデフォルト）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant, partial, never, reject）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- LOG_LEVEL: ログレベル（INFO 等）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START, KILL_FLAG_PATH, PID_FILE_PATH など運用フラグ関連

---

## 環境設定と検証

- 対話式で .env を作成/更新:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証（.env と config/*.yaml をチェック）:
  ```
  python -m kabusys.validate_config
  ```
  --strict を付けると WARNING もエラー扱いになります。

---

## 実行方法

以下は主要な実行方法の例です。プロセスはそれぞれ PID ファイルやフラグファイル（data/stop_requested.flag, data/kill.flag）と連携します。

1. ExecutionEngine を起動（本番または paper_trading）
   - 環境例（paper_trading）:
     ```
     export KABUSYS_ENV=paper_trading
     python -m kabusys.run_execution
     ```
   - 説明:
     - paper_trading の場合は MockBrokerClient を使用し、記録先は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）で本番 DB と分離されます。
     - 起動時に data/stop_requested.flag が存在すると起動を行いません。
     - 実行中に stop flag を検知するとエンジン停止します。
     - PID ファイルは data/execution.pid（デフォルト）に書き込まれます。

2. Monitoring を起動
   ```
   python -m kabusys.run_monitoring
   ```
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
   - Monitoring は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを残します。
   - stop_requested.flag を検知するとループを終了します。

3. Paper Trading 検証レポート生成
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - PAPER_TRADING_SQLITE_PATH を環境変数で指定するか、--db にパスを与えます（デフォルト data/paper_trading.db）。
   - 稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL 判定を行います。

4. AI モジュール（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または関数引数で指定）。
   - 例（ライブラリ呼び出し）:
     ```py
     from datetime import date
     import duckdb
     from kabusys.ai.news_nlp import score_news

     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, target_date=date(2026,4,11), api_key="sk-...")
     ```

---

## 運用上の注意点

- Kill Switch:
  - risk モジュールや monitoring により `data/kill.flag` が書き込まれると ExecutionEngine 側で停止される仕組みです。
  - `KillSwitch.clear()` によって起動時にクリアする設定もあります（本番では自動クリアを有効にしないことを推奨）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブルとインデックスを作成し、既存 DB に対する軽微なカラム追加（マイグレーション）も含みます。
- ログレベルや閾値は .env / config ファイルで調整してください。
- OpenAI を利用する機能は API 呼び出しが外部依存になるため、失敗耐性（バックオフなど）が組み込まれていますが、APIキー管理には注意してください。

---

## ディレクトリ構成（主要ファイルと説明）

以下は src/kabusys 以下の主要モジュール一覧（本リポジトリに含まれるものに基づく）：

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数/.env 読み込み、各種デフォルト）
  - config_setup.py
    - .env を対話式で作成するウィザード
  - validate_config.py
    - 環境変数・config/*.yaml を検証する CLI
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント（paper_trading 切替あり）
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト（MONITOR_POLL_INTERVAL）
  - utils/
    - process_priority.py
      - プラットフォーム差分を吸収してプロセス優先度や CPU affinity を設定
  - monitoring/
    - monitoring_db.py
      - SQLite に対する永続化 API（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
      - プロセス生存、CPU/MEM/DISK、データ鮮度のチェック
    - trade_monitor.py
      - 注文滞留・約定価格異常のチェック
    - risk_monitor.py
      - ドローダウン・ポジション上限チェックと dashboard 更新
    - kill_switch.py
      - data/kill.flag の書き込み・クリア
    - monitoring_engine.py
      - 各 Monitor を束ねて定期実行・アラート送信
    - alert_manager.py
      - （アラート送信機能：LINE 送信等を想定する抽象）
  - execution/
    - order_repository.py, order_manager.py, execution_engine.py, reconciler.py, risk_manager.py, broker_factory.py, ...
      - ExecutionEngine の構成要素（発注・リポジトリ・リスク管理）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算
    - position_sizing.py
      - 発注株数・制約処理（lot 単位で丸め、集約キャップ考慮）
    - risk_adjustment.py
      - セクター制約、レジーム乗数
  - research/
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー計算（DuckDB）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py
      - raw_news を LLM で評価し ai_scores に書き込む
    - regime_detector.py
      - ma200 + マクロニュースの LLM スコアを合成して market_regime を更新
  - tools/
    - paper_verification_report.py
      - Paper Trading の DB を解析して検証レポートを出力

（実際のファイル・サブパッケージは上記に加えて細かな実装ファイルが含まれます）

---

## 参考: よく使うコマンド一覧

- 対話式 .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README に追加してほしい項目（例：requirements.txt の具体的な依存一覧、systemd ユニット例、Dockerfile、詳細な API ドキュメントなど）があれば教えてください。必要に応じて追記・整形します。