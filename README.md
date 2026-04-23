# KabuSys

日本株自動売買システムのコードベース。戦略・ポートフォリオ構築・発注エンジン・監視・調査ツール・AI ベースのニュース解析までを含むモジュール群です。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの自動売買プラットフォームの一部実装です。本リポジトリには下記の機能群が含まれます。

- 発注実行エンジン（ExecutionEngine）とブローカー抽象化（本番 / ペーパートレード切替）
- システム監視（プロセス/CPU/メモリ/ディスク、データ鮮度等）
- リスク監視（ドローダウン・ポジション数上限等）と Kill Switch
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制限）
- リサーチモジュール（ファクター計算、特徴量 / IC 計算）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）
- ロギング・プロセス優先度ユーティリティ等のユーティリティ群

設計方針としては「本番データへの誤発注を避ける分離」「ルックアヘッドバイアスを排除する日時設計」「フェイルセーフで継続すること」を重視しています。

---

## 主な機能一覧

- Execution
  - run_execution.py：ExecutionEngine 起動スクリプト
  - Paper trading 用に本番 DB と分離された paper_trading DB に記録
  - BrokerClientFactory により実ブローカー・Mock ブローカーを切替可能
- Monitoring
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト
  - MonitoringDB（SQLite）: system_status、trade_logs、positions、risk_logs、dashboard を管理
  - Kill Switch：リスク条件で data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：各監視コンポーネントを束ねるポーリング実装
- Portfolio
  - 候補選定（select_candidates）、重み計算（等重・スコア重み）
  - ポジションサイジング（risk_based / equal / score）
  - セクター上限適用・レジーム乗数
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等） — DuckDB を利用
  - 特徴量探索・IC（Information Coefficient）計算
- AI
  - news_nlp：OpenAI を使ったニュースセンチメント (ai_scores テーブルへの書込み)
  - regime_detector：ETF の MA とマクロニュースで市場レジーム判定
- Tools
  - config_setup.py：.env 対話式ウィザード（.env 作成・更新）
  - validate_config.py：環境変数 / config/*.yaml の検証 CLI
  - paper_verification_report：ペーパートレード検証レポート生成

---

## セットアップ手順（ローカル開発向け）

1. Python の準備
   - 推奨: Python 3.9 以上（DuckDB / psutil / openai 等の互換性を確認）
2. 依存パッケージをインストール
   - 必須（代表例）:
     - duckdb
     - psutil
     - openai
     - （開発時のみ）PyYAML（validate_config の YAML 検証に使用）
   - 例:
     ```bash
     python -m pip install duckdb psutil openai PyYAML
     ```
   - requirements ファイルがある場合はそちらを利用してください（本リポジトリ内にない場合は上記を参照）。
3. プロジェクトルートに移動して .env を作成
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動作成（.env.example を参考にしてください）
   - 自動ロード: .env / .env.local は起動モジュールが自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
4. 設定の検証
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリの作成（必要に応じて）
   - デフォルトの DB / pid / flag 保存先は `data/`。自動作成される場所もありますが、権限等に注意してください。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: MockBroker を使用し paper_trading.db (PAPER_TRADING_SQLITE_PATH) に記録
  - live: 本番
- JQUANTS_REFRESH_TOKEN: J-Quants API (必須)
- KABU_API_PASSWORD: kabuステーション API パスワード (必須)
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- その他: LINE 通知用の LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID など

.env 自動読み込みの挙動:
- OS 環境変数 > .env.local > .env の優先順で読み込まれます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。

---

## 使い方（主要スクリプト）

- ExecutionEngine を起動（デーモン / systemd 等で運用想定）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し data/paper_trading.db に記録します。
  - 起動前に data/stop_requested.flag が存在すると起動を行いません。
  - 実行中に data/stop_requested.flag を書くとエンジンは停止します。
  - PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）に出力されます。

- Monitoring を起動（監視プロセス）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（環境にかかわらず）。
  - 監視は stop_requested.flag の存在を確認して終了します。

- 環境設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（プログラムから呼び出し）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
  - どちらも OPENAI_API_KEY（引数でも可）が必要になります。

---

## 停止・運用関連

- 停止フラグ / PID
  - data/stop_requested.flag: run_execution / run_monitoring のループ終了判定に使用
  - data/kill.flag: KillSwitch が書き込み、ExecutionEngine 停止を誘発
  - PID: data/execution.pid（ExecutionEngine が書き出す）

- Kill Switch
  - RiskMonitor 等の判定により KillSwitch が理由をファイルへ書き込み、必要に応じアラート送信します。
  - Settings.kill_flag_clear_on_start を 1 にしていると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

- ロギング
  - 共通の logging 設定ユーティリティ（kabusys.utils.logging_setup.setup_logging）を使用
  - デフォルトは logs/<app_name>.log 日次ローテート（30 日保持）と stdout 出力

---

## ディレクトリ構成

（抜粋 — 主要ファイル / 主要パッケージ）
```
src/kabusys/
├── __init__.py
├── config.py                # Settings / .env 自動ロード
├── config_setup.py          # .env 対話ウィザード
├── validate_config.py       # 設定検証 CLI
├── run_execution.py         # ExecutionEngine 起動スクリプト
├── run_monitoring.py        # SystemMonitor 起動スクリプト
├── tools/
│   └── paper_verification_report.py
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py
│   └── regime_detector.py
├── monitoring/
│   ├── monitoring_db.py
│   ├── system_monitor.py
│   ├── trade_monitor.py      # (詳細ソースは省略)
│   ├── risk_monitor.py
│   ├── kill_switch.py
│   ├── monitoring_engine.py
│   └── alert_manager.py      # (参照: alert_manager の存在)
├── execution/                # 発注周りの実装（broker_factory, execution_engine 等）
│   ├── broker_factory.py
│   ├── execution_engine.py
│   ├── order_manager.py
│   ├── order_repository.py
│   ├── reconciler.py
│   └── risk_manager.py
├── portfolio/
│   ├── __init__.py
│   ├── portfolio_builder.py
│   ├── position_sizing.py
│   └── risk_adjustment.py
├── research/
│   ├── __init__.py
│   ├── factor_research.py
│   └── feature_exploration.py
└── utils/
    ├── __init__.py
    ├── logging_setup.py
    └── process_priority.py
```

---

## 開発上の注意点 / 補足

- DuckDB はリサーチ・AI 用の分析 DB として利用しています。データの読み書き・テーブルスキーマはコード内の SQL を参照してください。
- Monitoring は常に「本番用の sqlite_path」を参照する設計です（環境にかかわらず）。Execution は KABUSYS_ENV に応じて paper_trading DB を分離します。
- AI モジュールは OpenAI API を使用します。API レスポンスの不安定さに対してはリトライ・フォールバックの実装がありますが、API キー・コスト管理には注意してください。
- validate_config は PyYAML がインストールされている場合に config/*.yaml の構文チェックも行います。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダーにも注記あり）。

---

必要であれば以下を追加で作成します:
- requirements.txt（推奨依存一覧）
- systemd / Docker 起動例
- 詳細なアーキテクチャ図（プロセス間通信・DB 分離図）
- テスト実行方法（ユニット / 統合）

どれを優先して追加しますか？