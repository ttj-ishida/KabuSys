# KabuSys

日本株向け自動売買システムのライブラリ兼起動スクリプト群です。  
このリポジトリは監視 / 発注エンジン、ポートフォリオ構築、リサーチ、AI ベースのニュース解析などの機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 発注実行（ExecutionEngine）とその監視（Monitoring）
- ポートフォリオ構築（シグナル選定、重み付け、ポジションサイズ計算）
- リスク管理（ドローダウン検出、ポジション上限監視、Kill Switch）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- ニュースの NLP によるセンチメント評価（OpenAI API を利用）
- ペーパートレード向けの分離された DB と検証レポート生成

設計方針として、可能な限り純粋関数で実装されており、DB 参照有無が明確になっています（分析用は DuckDB、運用ログは SQLite を使用）。

---

## 主な機能一覧

- ExecutionEngine（発注実行）:
  - 本番（live） / ペーパートレード（paper_trading）モードを切替え可能
  - リスク管理、オーダーマネージャ、リコンシリエーション等を組み合わせて動作
- Monitoring（監視）:
  - システムリソース・プロセス状態・データ鮮度・取引ログの監視
  - Kill Switch（条件を満たしたら停止フラグを出力）
  - AlertManager と連携して通知（LINE など）
- Portfolio（配分計算）:
  - 候補選定（スコア順）、等金額 / スコア加重配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイジング（リスクベース / 重みベース等）
- Research（リサーチ）:
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（ニュース NLP / レジーム判定）:
  - OpenAI を用いたニュースセンチメントの銘柄別スコアリング
  - マクロニュースと ETF（1321）の MA200 を組み合わせた市場レジーム判定
- ツール:
  - .env 設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.10 以上（Union 型 `|`、match を使わないが | 演算子が使われているため）
- システムに duckdb, psutil, openai 等がインストール可能であること

1. リポジトリをクローン / コピー

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 必須: duckdb, psutil, openai
   - optionally: PyYAML（config の YAML 検証用）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   （requirements.txt がない場合は上記のように個別インストール）

4. .env の作成（簡易ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - このウィザードは .env を対話式で生成します。
   - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合は OPENAI_API_KEY を設定してください（ai モジュールで参照）。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗（exit 1）扱いになります。

6. データディレクトリの作成（必要なら）
   - デフォルト DB / ファイルパスは .env の設定値、または以下デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper DB: data/paper_trading.db

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 用）
- OPENAI_API_KEY: OpenAI API キー（ai ニュース解析・レジーム判定で使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）

---

## 使い方（代表的なコマンド）

- 監視ループ起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番（settings.sqlite_path）を使って監視 DB に書き込みます。
  - 停止はプロジェクトルート/data/stop_requested.flag ファイルを作成することで行えます（監視プロセスはこのファイルを検知して終了します）。

- 実行エンジン起動（Execution）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（ペーパートレード）を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db） に記録します。
  - 実行中の Engine を停止するにはプロジェクトルート/data/stop_requested.flag を作成するか、Monitoring の Kill Switch が動作して data/kill.flag を作成します。
  - 実行は data/execution.pid に PID を書きます。

- .env 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（CLI）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB パスは env または data/paper_trading.db

- ライブラリ関数を使ったリサーチ / ポートフォリオ計算
  - DuckDB 接続を渡してファクター計算を呼ぶ例（スクリプト内で利用）:
    ```py
    import duckdb
    from kabusys.research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, date(2026, 4, 1))
    ```
  - ポートフォリオ関数は純粋関数（DB 参照なし）なのでユニットテストが容易です:
    ```py
    from kabusys.portfolio import select_candidates, calc_equal_weights
    candidates = select_candidates(signals, max_positions=10)
    weights = calc_equal_weights(candidates)
    ```

---

## 停止 / Kill フラグについて

- stop_requested.flag
  - run_monitoring.py / run_execution.py がループを安全に終了するために監視するファイルです。存在するとループは終了します。
  - パス: プロジェクトルート/data/stop_requested.flag（ソース内で参照）

- kill.flag
  - KillSwitch により書き込まれるファイルで、ExecutionEngine に対する強制的な停止シグナルを表します。
  - path は Settings.kill_flag_path（デフォルト data/kill.flag）
  - ExecutionEngine は起動時にこのファイルの存在をチェックし、存在する場合は起動しません。

---

## ログ

- ログはデフォルトで stdout とファイル（logs/<app_name>.log）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に設定されます。
- ログディレクトリ: デフォルト `logs/`。環境変数 LOG_DIR で変更可能。

---

## 依存ライブラリ（主要）

- duckdb
- psutil
- openai
- PyYAML（オプション：config の YAML 検証）

必要に応じて適切なバージョンを pip でインストールしてください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings の管理、自動 .env 読み込み
  - config_setup.py — .env 作成ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成 CLI
  - utils/
    - __init__.py
    - logging_setup.py — 共通ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite テーブルの初期化 / 永続化層
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （取引ログ監視）※実装は該当ファイルを参照
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — 停止フラグ操作
    - alert_manager.py — 通知管理（実装参照）
  - execution/
    - broker_factory.py — ブローカークライアント生成
    - execution_engine.py — ExecutionEngine 本体
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行関連コンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケールダウン・lot 丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラ / バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で銘柄別スコアを生成
    - regime_detector.py — ETF MA + マクロニュースでレジーム判定
    - __init__.py

（上記は抜粋です。詳細はリポジトリのソースを参照してください。）

---

## 注意事項 / 運用上の留意点

- 本番環境（KABUSYS_ENV=live）での実行は慎重に行ってください。validate_config の警告は必ず確認してください。
- .env ファイルは決して Git にコミットしないでください（config_setup にもその旨の警告があります）。
- OpenAI API キーはセキュアに管理してください。ai モジュールは API キーが未設定だと例外を投げます。
- Monitoring は監視用 DB（SQLite）に常に「本番用」パスを利用するため環境に依らず同じファイルに書き込みます。ペーパートレードのログは paper_trading 用 DB に分離されます。
- プロセス優先度 / CPU affinity の設定は OS の権限に依存します。権限不足で失敗することがありますが、警告ログのみで継続します。

---

もし README に追記してほしい項目（例: API ドキュメント、テスト手順、CI 設定、詳細なログの読み方など）があれば教えてください。