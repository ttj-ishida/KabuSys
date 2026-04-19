# KabuSys

日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージ群です。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI を用いたニュースセンチメント評価などの主要コンポーネントの実装が含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するモジュール群です。主な役割は次のとおりです。

- Execution: 注文発行、オーダー管理、リスク管理、リコンサイル（実行エンジン）
- Monitoring: システム稼働監視、取引監視、リスク監視、Kill Switch（停止フラグ）
- Portfolio: 候補選定、配分（等配分・スコア重み）、銘柄別株数決定（ポジションサイズ）
- Research: DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）や特徴量解析
- AI: OpenAI を用いたニュースセンチメント評価・レジーム判定（必要に応じて OpenAI API キーを設定）
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定、プロセス優先度管理 など

設計上のポイント:
- 環境変数を中心に設定を管理（.env / .env.local の自動読み込みを実装）
- DuckDB（分析用）と SQLite（監視 / ペーパートレード用）を利用
- 開発・ペーパートレード・本番を区別する `KABUSYS_ENV`（development / paper_trading / live）
- フェイルセーフ設計（LLM 呼び出し失敗時はフォールバック / kill.flag による停止制御 等）

---

## 機能一覧

主な機能（抜粋）:

- Execution（起動スクリプト: run_execution）
  - Paper trading と実口座（live）を切り替え
  - Broker クライアント抽象化（Mock / 実ブローカーの切替）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立てて実行
  - 停止フラグ (data/stop_requested.flag) による安全停止

- Monitoring（起動スクリプト: run_monitoring）
  - SystemMonitor: CPU/Mem/Disk, プロセス生存チェック, データ鮮度チェック
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常、ドローダウン監視
  - KillSwitch: 閾値超過時に data/kill.flag を書き込み ExecutionEngine に停止指示
  - アラート送信（LINE 等）を想定した AlertManager（実装部は必要に応じて接続）

- Portfolio
  - 候補選定（スコア順）、等配分・スコア加重配分
  - ポジションサイズ計算（リスクベース／等配分）、単元株丸め、aggregate キャップ処理
  - セクター集中制限、レジーム乗数（bull/neutral/bear）

- Research
  - DuckDB を使ったファクター計算: momentum / volatility / value
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI
  - ニュースセントメント（OpenAI）を用いた銘柄別スコアリング
  - 市場レジーム判定（ETF MA200 とマクロニュースの LLM 結果を合成）

- ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）

---

## セットアップ手順

下記は一般的なセットアップ手順です。環境によって適宜調整してください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール  
   （requirements.txt がある場合: `pip install -r requirements.txt`。なければ主要依存を手動で）
   推奨パッケージ:
   - duckdb
   - psutil
   - openai
   - PyYAML (設定 YAML の検証で使用)
   - （必要に応じて本番ブローカークライアントの依存）

   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. 環境変数設定（.env の作成）
   - 対話式ウィザードで .env を生成:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定を検証:
     ```
     python -m kabusys.validate_config
     ```
     警告も FAIL にしたい場合:
     ```
     python -m kabusys.validate_config --strict
     ```

   主に必要な環境変数（一部）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能を使う場合）

   自動ロード:
   - プロジェクトルートに .env / .env.local があれば、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可）。

5. データディレクトリ（logs / data 等）の作成は自動的に行われますが、アクセス権限に注意してください。

---

## 使い方

以下はよく使うエントリポイントとオプション例です。各コマンドはパッケージルートから実行してください。

- 環境設定ウィザード（対話式 .env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine（取引実行）の起動
  - デフォルトで設定された環境（KABUSYS_ENV）に応じて paper_trading / live の動作が切り替わります。
  - 停止フラグ: data/stop_requested.flag を作成するとスレッドが停止します。Execution 側は data/stop_requested.flag を確認して安全終了します。
  ```
  python -m kabusys.run_execution
  ```

- Monitoring（監視） の起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は monitoring DB（SQLite）にログを書き込みます（monitoring は常に本番 sqlite_path を使用する仕様に注意）。
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポートの生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # SQLite ファイルを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- ログ
  - ログはデフォルトで logs/<app_name>.log（日次ローテート）に出力されます。例: logs/execution.log, logs/monitoring.log
  - 標準出力にもログが出力されます。

- Kill Switch / 強制停止
  - KillSwitch は監視側が条件を満たすと data/kill.flag を書き込みます。ExecutionEngine は kill.flag をチェックしてアクションを取る設計です。
  - 実行中のループを外部から即時に停止したい場合は、data/stop_requested.flag を作成してください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — DEBUG/INFO/…（ログレベル）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 利用時）
- OPENAI_API_KEY — AI 機能（news_nlp / regime_detector）で使用
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant|partial|never|reject）

.env 例（簡易）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主なファイル）

プロジェクトは src/kabusys 配下に実装されています。主要ファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 自動読み込み・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）によるスコア付け
    - regime_detector.py      — 市場レジーム判定（LLM + MA200）
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 / 永続化層
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （取引監視）※実装参照
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - monitoring_engine.py    — 統合ポーリングエンジン
    - kill_switch.py          — Kill Switch（kill.flag の書き込み）
    - alert_manager.py        — アラート管理（通知送信）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度・CPU affinity ユーティリティ

プロジェクトルートには config/*.yaml やデータディレクトリ（data/）が期待されます。validate_config や config_setup で補助操作が可能です。

---

## 運用上の注意

- KABUSYS_ENV が `live` の場合は特に注意して設定してください（validate_config でも警告が出ます）。
- 本番 DB（SQLite / DuckDB）のパスに間違いがないか必ず確認してください。paper_trading は専用 DB に分離することを推奨します。
- OpenAI を使用する機能は API コストとレイテンシを伴います。API キー管理・レート制御に注意してください。
- ログディレクトリへの書き込み権限、ファイルローテーション設定（デフォルトは 30 日分保持）に注意してください。
- Kill Switch（data/kill.flag）や停止フラグ（data/stop_requested.flag）の取り扱いは慎重に行ってください。特に `KILL_FLAG_CLEAR_ON_START` が 1 に設定されていると起動時に自動クリアされるため本番での誤設定は危険です。

---

## 追加情報 / 開発メモ

- DuckDB は分析用途（prices_daily / raw_financials 等）に用います。データ投入パイプラインは kabusys.data.pipeline 等で管理する想定です（該当実装を参照）。
- AI 周り（news_nlp / regime_detector）は LLM の JSON Mode を利用し、レスポンスのバリデーションやリトライロジックを実装しています。
- テストや CI を含めた追加ドキュメントは別途整備してください（ユニットテスト、モックによる API 呼び出しの差し替え等の方針がコード内に記載されています）。

---

必要であれば、README にサンプル .env のより詳しい項目一覧、運用チェックリスト、よくあるトラブルシュート（例: ログディレクトリ作成失敗、psutil の権限エラー）などを追記します。どの情報を優先して補足しますか？