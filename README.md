# KabuSys

日本株自動売買システムのコードベース README（日本語）

このリポジトリは、注文実行エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ポートフォリオ構築・リサーチ、AI ベースのニュース解析などを含む自動売買システムのユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤を想定したライブラリ／ツール群です。主な役割は次の通りです。

- 注文生成・発注を行う ExecutionEngine（本番 / ペーパートレード切替）
- システム状態（CPU / メモリ / ディスク）や注文状態、リスク指標を監視する Monitoring 系
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター制限、レジーム補正）
- Research：DuckDB 上で稼働するファクター計算・特徴量探索
- AI モジュール：ニュースの NLP スコアリング、マクロレジーム判定（OpenAI を利用）
- ユーティリティ：設定ウィザード、設定検証、ログ設定、プロセス優先度設定 等

設計方針の一例：
- 環境変数 / .env による設定管理
- Paper Trading（ペーパートレード）は本番 DB と分離
- OpenAI 呼び出しは失敗してもシステム停止としないフェイルセーフ実装
- DuckDB / SQLite をデータストアに利用

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine の起動（KABUSYS_ENV により paper_trading モードをサポート）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）

- 設定管理
  - config_setup.py — 対話式 .env ウィザード（.env 作成/更新）
  - validate_config.py — .env と config/*.yaml の事前検証 CLI

- 監視（monitoring）
  - monitoring_engine.py — 各 Monitor（System / Trade / Risk）を束ねるポーリングエンジン
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 個別の監視ロジック
  - kill_switch.py — ドローダウン等での止めスイッチ（data/kill.flag の書き込み）

- Execution（execution）
  - broker_factory, ExecutionEngine, OrderManager, Reconciler, RiskManager, OrderRepository（発注・リスク管理）

- Portfolio（portfolio）
  - 銘柄選定・重み計算・株数計算・セクター制限等（純粋関数群）

- Research（research）
  - factor_research.py, feature_exploration.py — DuckDB を用いたファクター / 将来リターン計算、IC 計測等

- AI（ai）
  - news_nlp.py — ニュース記事を OpenAI で解析してスコアを ai_scores に格納
  - regime_detector.py — マクロ＋ETF MA200 を用いた市場レジーム判定

- ツール
  - tools/paper_verification_report.py — Paper Trading の実績検証レポート生成

- ユーティリティ
  - utils/logging_setup.py — 共通ログ設定（コンソール + ローテートファイル）
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定
  - config.py — 環境変数 / Settings 管理

---

## セットアップ手順（開発者向け）

前提：
- Python 3.10+
- 必要な外部パッケージ（例: duckdb, psutil, openai, PyYAML（任意））

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - ※ requirements.txt が無い場合は少なくとも次を入れてください:
     - duckdb, psutil, openai
     - （YAML の検証を使う場合）PyYAML

4. デフォルトディレクトリの作成（logs, data 等）
   - mkdir -p data logs

5. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env.example を参照して手動作成

6. 設定検証
   - python -m kabusys.validate_config
   - 本番を想定して厳密チェックする場合は --strict を付与

7. OpenAI を利用する機能を動かす場合
   - 環境変数 OPENAI_API_KEY を設定（または score_news / score_regime に api_key を渡す）

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0|1、デフォルト 0）
- PID_FILE_PATH, KILL_FLAG_PATH: PID / kill flag のパス（設定可能）

注意:
- run_monitoring は監視用 DB に対して「環境にかかわらず」settings.sqlite_path（通常 data/monitoring.db）を使用します（コード内にその旨の注記あり）。
- run_execution は KABUSYS_ENV=paper_trading の場合、専用の PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離します。

---

## 使い方（主要コマンド例）

- 設定ウィザード（.env の生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- Execution エンジン起動
  - python -m kabusys.run_execution
  - 挙動:
    - 起動時にプロセス優先度を "high" に設定します（可能な場合）。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - data/stop_requested.flag が存在すると起動しない／実行中に停止します。
    - PID ファイル（デフォルト data/execution.pid）を使用します。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
  - stop flag: data/stop_requested.flag を検出するとループを抜けます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定（--db）または環境変数 PAPER_TRADING_SQLITE_PATH を利用

- AI スコアリング / レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news（DuckDB 接続・target_date を渡す）
  - kabusys.ai.regime_detector.score_regime（DuckDB 接続・target_date を渡す）
  - いずれも OPENAI_API_KEY が必要（関数引数で上書き可能）

---

## ロギング

- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。
- コンソール出力（stdout）も行われます。
- ログ設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼び出して統一されています。
- ログディレクトリを変更したい場合は環境変数 LOG_DIR を設定するか setup_logging に引数で渡します。

---

## Kill / Stop フラグ

- Kill Switch（強制停止、ExecutionEngine 停止のため）
  - data/kill.flag を書き込むことで ExecutionEngine に対して停止シグナルを送ります（KillSwitch を用いる）。
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。

- Stop リクエスト（デーモン停止）
  - data/stop_requested.flag を配置すると run_monitoring / run_execution のループや起動を停止します（コード中に _STOP_FLAG が参照されています）。

---

## 主要ファイルとディレクトリ構成

リポジトリ内のおおまかな構成（src/kabusys 配下）:

```
src/
  kabusys/
    __init__.py
    config.py
    config_setup.py
    validate_config.py

    run_execution.py
    run_monitoring.py

    utils/
      __init__.py
      logging_setup.py
      process_priority.py

    monitoring/
      monitoring_db.py
      monitoring_engine.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py        # ※実装ファイルがある想定（一覧に基づく）

    execution/
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py

    portfolio/
      __init__.py
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      __init__.py
      factor_research.py
      feature_exploration.py

    ai/
      __init__.py
      news_nlp.py
      regime_detector.py

    tools/
      __init__.py
      paper_verification_report.py
```

（上記は主要ファイルの抜粋です。実ファイル群に基づいています。）

---

## 設定・動作に関する注意事項 / トラブルシューティング

- .env の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env を自動で読み込みます。
  - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- KABUSYS_ENV の値:
  - 有効値は development / paper_trading / live。live は注意深く扱ってください（validate_config は警告を出します）。

- Paper Trading:
  - ペーパートレードは本番 DB と分離されます。PAPER_TRADING_SQLITE_PATH を確認してください。
  - PAPER_FILL_MODE の有効値: instant | partial | never | reject

- OpenAI 関連:
  - OPENAI_API_KEY が未設定の場合、AI 関連関数は ValueError を送出します（起動スクリプトで直接呼ばない限りは例外で停止しない実装の箇所もありますが、キーが必要な処理では必須）。
  - API 呼び出しはリトライ機構を持ちますが、レート制限・ネットワークエラーでの完全失敗時は該当処理をスキップしてシステムの継続を優先します。

- ログディレクトリ作成失敗:
  - ログディレクトリが作成できない場合、ファイル出力は無効化されコンソール出力のみになります。権限を確認してください。

- DuckDB / SQLite:
  - デフォルトは data/kabusys.duckdb（DuckDB）と data/monitoring.db（SQLite）。環境変数で上書き可能です。
  - 初回起動時に data ディレクトリを作成しておくとスムーズです。

---

## 開発／拡張のヒント

- 各モジュールは比較的独立しており、DuckDB / SQLite 接続や broker client を差し替えることでテスト可能です。
- AI API 呼び出し箇所（news_nlp._call_openai_api / regime_detector._call_openai_api）はテストでモックしやすいように分離されています。
- monitoring_db にはマイグレーション処理（カラム追加チェック）が含まれているため、古い DB からのアップデートをある程度自動で吸収します。

---

## 最後に

この README はコードベースの導入と運用に必要な基本情報をまとめたものです。詳細な設計方針やアルゴリズムの仕様は各モジュール内の docstring / コメントを参照してください。追加のドキュメント（例: PortfolioConstruction.md, StrategyModel.md 等）がある場合はそちらも合わせて参照することを推奨します。