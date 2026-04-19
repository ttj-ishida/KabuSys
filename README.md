# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ。  
本READMEはこのコードベースの概要、機能、セットアップ手順、使い方、主要ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール化されたシステムです。主なコンポーネントは以下のとおりです。

- ExecutionEngine：注文発行・リスク管理・約定管理を行うエンジン。paper_trading（ペーパートレード）モードをサポート。
- Monitoring：システム稼働状況、注文状況、リスク（ドローダウンやポジション数）を監視し、必要に応じて Kill Switch を発動する。
- Portfolio モジュール：候補選定、配分、リスク調整、ポジションサイズ計算などの純粋関数群。
- Research / AI：ファクター計算、特徴量探索、OpenAI を用いたニュース NLP（センチメント）や市場レジーム判定。
- Tools：Paper Trading 検証レポート生成などのユーティリティスクリプト。

設計上の特徴：
- 設定は .env / 環境変数中心で管理（Settings クラス経由で読み取り）。
- DuckDB（分析用）と SQLite（監視・注文履歴等）を併用。
- Paper Trading は本番 DB と分離（デフォルトで data/paper_trading.db を使用）。
- OpenAI（gpt-4o-mini）を使った NLP 機能を一部に持つ（API キーは環境変数で管理）。

---

## 主な機能一覧

- 実行エンジン（ExecutionEngine）
  - ブローカークライアント抽象化（実ブローカ / モックの切り替え）
  - 発注・注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager）
  - 再整合（Reconciler）とセッション管理

- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・プロセス生存チェック
  - TradeMonitor：注文の滞留や異常約定チェック（trade_logs 参照）
  - RiskMonitor：ドローダウン、ポジション上限の監視
  - KillSwitch：条件を満たしたら data/kill.flag を書き込み、ExecEngine 停止を促す
  - AlertManager（通知機能を差し替え可能）

- ポートフォリオ構築
  - 候補選定（スコア順）
  - 各種配分方式（等分・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap、コストバッファ）

- リサーチ / 分析
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
  - ニュース NLP（OpenAI）による銘柄別センチメント算出
  - 市場レジーム判定（ETF MA + マクロニュースの LLM スコア合成）

- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境の作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - YAML を利用した設定検証を行う場合は PyYAML もインストール:
     - pip install pyyaml

   （プロジェクトに requirements.txt があればそれを利用してください）

3. プロジェクトルートで .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または手動で .env を作成（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     OPENAI_API_KEY=sk-xxxxx   # AI 機能を使う場合
     ```

   注意: .env は機密情報を含むため Git にコミットしないでください。

4. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの作成（自動作成される場合もあるが手動で）
   - mkdir -p data logs

---

## 使い方（実行方法）

### 起動スクリプト

- 実行エンジン（ExecutionEngine）を起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV で切り替え
  - 実行:
    - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番と完全分離）
    - 起動時に data/stop_requested.flag が存在する場合は起動を行わず終了する
    - 実行中は data/execution.pid に PID を書きます
    - プロセス優先度を "high" に設定（set_process_priority）

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60秒。1秒未満や不正値はデフォルトにフォールバック）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず同じ監視 DB を参照）

### ツール

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - --db PATH   （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

### .env / 環境変数の主なキー

- 必須（実行時に必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 環境 / 動作制御
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - KILL_FLAG_CLEAR_ON_START: 0 | 1

- データベースパス
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）

- AI / OpenAI
  - OPENAI_API_KEY（news_nlp / regime_detector で使用する）

- 監視
  - MONITOR_POLL_INTERVAL（run_monitoring 用、秒）

---

## 実装上の注意・運用メモ

- Paper Trading 分離
  - KABUSYS_ENV=paper_trading の場合、ExecutionEngine は paper_sqlite_path を使用し、本番 SQLite と分離されます。

- Kill Switch / Stop フラグ
  - KillSwitch は data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります（ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START を見て自動クリア可）。
  - 手動で停止を要求するには data/stop_requested.flag を作成すると、run_execution / run_monitoring のループが検知して停止します。

- ロギング
  - ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（TimedRotatingFileHandler、30日分保持）。
  - setup_logging() が全起動スクリプトで共通して使われます。

- DB スキーマ
  - 監視用 SQLite には system_status / trade_logs / positions / risk_logs / dashboard テーブルがあり、init_monitoring_db() により冪等に作成・マイグレーションされます。

- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び出します。実行ユーザの権限により設定できない場合は警告に留まります。

- OpenAI 呼び出し
  - ニュース NLP とレジーム判定は OpenAI を利用します。API 失敗時はフォールバック（0.0 等）で続行するようフェイルセーフ設計になっています。
  - API キーは環境変数 OPENAI_API_KEY を使用してください。
  - LLM によるレスポンスは JSON モードを使い、結果のバリデーションが行われます。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なモジュール・ファイルを抜粋して説明します（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス：環境変数 / .env の読み込みとプロパティアクセス
  - config_setup.py
    - .env を対話式に生成/更新するウィザード
  - validate_config.py
    - 起動前に設定やファイル存在を検証する CLI
  - run_execution.py
    - ExecutionEngine を起動するスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト

- src/kabusys/execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  （注文発行・リスク制御に関する実装）

- src/kabusys/monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
  （監視・Kill Switch・ログ永続化）

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py

- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py

- src/kabusys/utils/
  - logging_setup.py
  - process_priority.py

- src/kabusys/tools/
  - paper_verification_report.py

- その他
  - config/ （YAML テンプレート等）
  - data/ （デフォルトの DB / flag / pid ファイルの配置場所）
  - logs/ （ログ出力先）

---

## よくある運用コマンド（例）

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視プロセス起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート（過去期間）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## セキュリティと運用上の注意

- 機密情報（API トークン・パスワード等）は .env に保存しますが、必ず .gitignore に入れてコミットしないでください。
- KABUSYS_ENV=live を設定する前に validate_config で警告・設定を慎重に確認してください。
- Kill Switch 設定（KILL_FLAG_CLEAR_ON_START）は本番では `0` を推奨します。自動クリア（1）は危険です。
- OpenAI キーを扱う機能は API 呼び出し費用やレート制限に注意して運用してください。

---

## 参考情報 / 補足

- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db

- ログ:
  - デフォルト logs/<app_name>.log（app_name は "execution" / "monitoring" など）

- サポートライブラリ:
  - duckdb（分析クエリ）
  - psutil（CPU/メモリ/プロセス制御）
  - openai（AI 機能）
  - pyyaml（config ファイル検証, 任意）

---

この README はコードの主要な部分と運用フローに基づいて作成しています。細かな実装・追加設定やデプロイ手順は運用環境に依存するため、必要に応じて運用ガイドやデプロイ手順を別途用意してください。質問や補足があれば教えてください。