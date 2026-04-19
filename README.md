# KabuSys

日本株自動売買システムの一部をまとめたリポジトリ用 README（日本語）。

この README ではプロジェクト概要、主要機能、セットアップ手順、各種の使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買・運用支援を目的としたソフトウェア群です。本リポジトリには以下の機能群が含まれます（一部モジュールのみを抜粋）:

- 実行エンジン（ExecutionEngine）起動スクリプト
- 監視用プロセス（System / Trade / Risk モニタ）と監視ループ
- 環境設定ウィザード（.env 作成）および設定検証ツール
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- 研究用ファクター計算・特徴量探索モジュール（DuckDB 経由）
- AI（OpenAI）を用いたニュース NLP / レジーム判定
- Paper Trading 向け検証レポート生成ツール
- ロギング / プロセス優先度設定などのユーティリティ

設計方針として、データ解析部分は DuckDB、監視・注文ログは SQLite を使用し、環境変数（.env）で挙動を切り替えられるようになっています。

---

## 機能一覧（抜粋）

- 実行・監視
  - run_execution.py: ExecutionEngine を起動、Paper Trading 環境は専用 DB に隔離
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定）
  - Kill Switch / stop フラグで外部から安全に停止可能

- 環境設定
  - config_setup.py: 対話式ウィザードで .env を作成・更新
  - validate_config.py: .env と config/*.yaml の基本チェック（--strict オプションあり）

- ポートフォリオ
  - 銘柄選定（score/equal）、配分計算、ポジションサイズ算出、セクター上限適用などの純粋関数群

- 研究・解析
  - research/*: ファクター (momentum/value/volatility)、将来リターン計算、IC 計算、統計サマリ

- AI（OpenAI）
  - news_nlp: ニュース記事のセンチメントを LLM でスコア化して ai_scores に保存
  - regime_detector: ETF とマクロニュースを組み合わせ市場レジームを判定して保存

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成（uptime, fill rate, latency 等）

- ユーティリティ
  - utils/logging_setup.py: 一元的なログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: プラットフォーム差異を吸収した優先度 / CPU affinity 設定

---

## 要件（推奨）

- Python 3.10 以上（typing の | 演算子などを使用）
- 必須 Python パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 省略可能:
  - PyYAML (validate_config が config/*.yaml を検証する場合に必要)

インストール例:
```
python -m pip install duckdb psutil openai
# YAML 検証を行う場合:
python -m pip install PyYAML
```

（sqlite3 は標準ライブラリに含まれます）

---

## 環境変数（主要なもの）

主に .env ファイルで設定します（config_setup で対話的に生成可能）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

その他（主要なもの）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading のとき、Execution は MockBrokerClient を使い DB は data/paper_trading.db を使います（本番 DB と分離）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API を使う機能で必要
- LOG_LEVEL — ログレベル（DEBUG / INFO / ...）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、production では 0 推奨）

注意:
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する設計です（監視ログは共有 DB 想定）。
- Paper Trading は Execution 側で paper_sqlite_path を使用して本番 DB と分離します。

---

## セットアップ手順

1. Python と依存パッケージをインストール
   - 例: python -m pip install -r requirements.txt
     （requirements.txt がない場合は前述のパッケージを個別にインストール）

2. プロジェクトルートに移動し、.env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     これで .env を生成できます。

   - もしくは手動で .env を作成（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```

3. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

4. 必要に応じてログディレクトリや data ディレクトリを作成（多くは自動作成されますが確認推奨）
   ```
   mkdir -p data logs
   ```

---

## 使い方（起動・ツール）

基本的には Python モジュールとして起動します。

- 実行エンジン（ExecutionEngine）を起動
  - Paper Trading の場合:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 本番 / dev の場合は KABUSYS_ENV を適切に設定して実行:
    ```
    export KABUSYS_ENV=development
    python -m kabusys.run_execution
    ```
  実行時に PID ファイル（デフォルト data/execution.pid）を作成し、停止フラグ（data/stop_requested.flag）や kill.flag 機構が組み合わさります。

- 監視プロセスを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に変更できます（デフォルト 60 秒）。不正な値や 0/負数はデフォルトにフォールバックします。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境にかかわらず本番 DB を参照する仕様）。

- Paper Trading 検証レポート出力
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスを指定する場合:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- .env の作成・更新（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- AI 機能（ニュース NLP / レジーム判定）を使うとき
  - 環境変数 OPENAI_API_KEY を設定
  - モジュール関数を呼ぶか、別途スクリプトから呼び出します（例: kabusys.ai.score_news、kabusys.ai.regime_detector.score_regime）
  - OpenAI 呼び出しではリトライや JSON バリデーションが組み込まれており、失敗時は安全側にフォールバックします

---

## 停止 / Kill Switch / フラグ

- 外部から安全に停止するにはプロジェクトルート下の data/stop_requested.flag を作成します（run_execution/run_monitoring は起動時にこのファイルの存在をチェックします）。
- Execution 側の強制停止判定（重大なリスク等）は kill.flag（デフォルトパスは Settings.kill_flag_path）を監視します。KillSwitch がトリガーされると kill.flag が書き込まれ Execution を停止するよう設計されています。
- 起動時に kill.flag を自動でクリアしたい場合は .env に KILL_FLAG_CLEAR_ON_START=1 を設定できますが、本番環境では 0 を推奨します。

---

## ログ

- ロギングは kabusys.utils.logging_setup.setup_logging() により標準出力（stdout）と日次ローテーションされるファイルの両方へ出力されます。
- デフォルトのログディレクトリ: logs/
- ログファイル名は app_name（例: execution, monitoring）により logs/<app_name>.log になります。
- ログレベルは LOG_LEVEL と引数で制御可能（デフォルト: INFO）。

---

## 主要ファイル・ディレクトリ構成

（src/kabusys 配下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定取得ロジック（Settings クラス）
  - config_setup.py — .env 対話型ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・投下額スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数

  - research/
    - factor_research.py — momentum/volatility/value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ

  - ai/
    - news_nlp.py — ニュースを LLM でスコア化
    - regime_detector.py — マクロ + ETF によるレジーム判定

  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化と永続化レイヤ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （取引監視：ファイルには含まれるがここでは省略）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — （アラート通知の抽象レイヤ：ファイルは存在）

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート

  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定補助

（実際のリポジトリにはさらに execution, data, strategy 等のサブパッケージが含まれる場合があります）

---

## 開発・運用上の注意点

- Python バージョンは 3.10 以降を推奨（型ヒントの構文使用のため）。
- 環境変数は .env に保存しますが、.env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。
- Paper Trading 用データベースは本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH / KABUSYS_ENV=paper_trading）。
- OpenAI を用いる機能は API キーが必要です。API 制限・課金に注意してください。
- run_monitoring は監視用 DB（設定で指定した SQLITE_PATH）に書き込みます。必要な権限・ディスク容量を確保してください。
- process priority / CPU affinity の設定は権限によって失敗する場合があります（警告ログのみ）。

---

## よく使うコマンドまとめ

- .env の対話型生成:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動:
  ```
  export KABUSYS_ENV=development   # または paper_trading / live
  python -m kabusys.run_execution
  ```

- 監視プロセス起動:
  ```
  python -m kabusys.run_monitoring
  # MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  # 間隔を上書き
  ```

- Paper Trading 検証レポート（期間指定）:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README の補足（詳細な API 仕様、ExecutionEngine の設定や strategy/データパイプラインの使い方等）を追記できます。特定のセクションを詳しく書いてほしい場合はその旨を教えてください。