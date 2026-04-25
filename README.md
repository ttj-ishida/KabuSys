# KabuSys

日本株向け自動売買・運用支援プラットフォームの小規模実装です。  
このリポジトリは、戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）や AI を使ったニュース評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つモジュール群から成る:

- データ/リサーチ: DuckDB を用いた株価・財務データの集計・ファクター計算（research/）
- ポートフォリオ構築: シグナル選定、重み付け、株数計算（portfolio/）
- Execution: 発注ロジック・リスク管理・注文管理（execution/）。`paper_trading` モードではモックブローカーを使用し、本番 DB と分離して動作。
- Monitoring: システム稼働・注文状況・リスクを監視してログ・アラート・Kill Switch を管理（monitoring/）
- AI: OpenAI を使ったニュースセンチメント評価や市場レジーム判定（ai/）
- ユーティリティ: ロギングやプロセス優先度設定、設定読み込みなど（utils/）
- CLI ツール: .env ウィザード、設定検証、ペーパートレードの検証レポート等（config_setup.py, validate_config.py, tools/）

起動スクリプトの代表例:
- 監視ループ: python -m kabusys.run_monitoring
- 発注エンジン: python -m kabusys.run_execution
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話生成）
- 設定検証ツール（.env と config/*.yaml の存在・整合性チェック）
- ロギング（コンソール + 日次ローテートファイル出力）
- プロセス優先度設定（Windows / POSIX を抽象化）
- 監視:
  - システム・プロセス稼働監視（CPU/メモリ/ディスク・プロセス死活）
  - 注文ログ監視（滞留注文、異常約定価格など）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件発動時に data/kill.flag を書込）
- Execution:
  - 本番・ペーパートレード分離（PAPER_TRADING モード）
  - ブローカークライアント抽象化（MockBroker を切替）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine の連携
- ポートフォリオ:
  - 候補選定（スコアやランキング）
  - 重み付け（等金額、スコア加重）
  - ポジションサイジング（リスクベース、上限、単元株丸め）
  - セクターキャップ、レジーム乗数
- リサーチ:
  - モメンタム / ボラティリティ / バリュー等のファクター算出（DuckDB）
  - 将来リターン、IC（Information Coefficient）などの解析
- AI（OpenAI）:
  - ニュースの銘柄別センチメント評価（gpt-4o-mini など）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定
- ツール:
  - Paper Trading の検証レポート生成（成功率・レイテンシ・稼働率等）

---

## セットアップ手順

最低限の手順（仮想環境推奨）:

1. Python (3.9+) を準備し、仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai
   - PyYAML は config ファイルの検証で利用する（任意）:
     pip install pyyaml

   ※ requirements.txt がある場合はそちらを使用してください（本サンプルでは要件ファイルは付属しない想定）。

3. プロジェクトルートで .env を作成:
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは `.env.example` を参考に `.env` を作成（存在しない場合は .env を作成してください）。

4. 設定の事前検証（任意）:
   - python -m kabusys.validate_config
   - 本番準備で警告も致命的扱いにする場合:
     python -m kabusys.validate_config --strict

5. DuckDB / SQLite の初期テーブルは実行時に自動作成されます。監視 DB（SQLite）は monitoring コンポーネントが起動時に init します。

環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 推奨 / 便利:
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。run_monitoring で使用。デフォルト 60）

注意点:
- KABUSYS_ENV=paper_trading の場合は発注に MockBrokerClient が使われ、ペーパートレード用 DB（data/paper_trading.db）に記録され、本番 DB と分離されます。
- OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。

---

## 使い方

主な起動・実行コマンド:

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV が paper_trading の場合、MockBroker を用いて data/paper_trading.db に記録されます。
    - 起動前に data/stop_requested.flag が存在すると起動をスキップします（停止フラグ）。
    - 実行中は data/execution.pid に PID を書きます。停止は stop フラグを書き込むことで行えます。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は常に production 向け sqlite_path（Settings.sqlite_path）を使い DB を初期化します。

- Paper Trading の検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH （PAPER_TRADING_SQLITE_PATH をオーバーライド）

- AI 機能呼び出し（プログラム的に）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key=...) など

ログ:
- setup_logging を各スクリプトで呼んでおり、デフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力されます。ログディレクトリは LOG_DIR 環境変数で指定可能。

停止制御:
- data/stop_requested.flag — run_execution / run_monitoring の外側で使用される「即時停止」ファイル（起動スクリプトで参照）。
- data/kill.flag — KillSwitch が書き込むフラグ。ExecutionEngine に対する停止シグナルとして利用。

---

## 主要ファイル・ディレクトリ構成

ルートからの主要構成（省略あり）:

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                 # 環境変数読み込み / Settings
   ├─ config_setup.py           # .env 対話ウィザード
   ├─ validate_config.py        # 設定検証 CLI
   ├─ run_execution.py          # ExecutionEngine 起動スクリプト
   ├─ run_monitoring.py         # Monitoring 起動スクリプト
   ├─ utils/
   │   ├─ logging_setup.py      # ログ設定
   │   └─ process_priority.py   # プロセス優先度・affinity 設定
   ├─ execution/                # 発注関連コンポーネント（Engine, OrderManager 等）
   ├─ monitoring/
   │   ├─ monitoring_db.py      # monitoring 用 SQLite ラッパ
   │   ├─ system_monitor.py
   │   ├─ trade_monitor.py
   │   ├─ risk_monitor.py
   │   ├─ monitoring_engine.py
   │   ├─ kill_switch.py
   │   └─ alert_manager.py
   ├─ portfolio/                # ポートフォリオ構築ロジック
   │   ├─ portfolio_builder.py
   │   ├─ position_sizing.py
   │   └─ risk_adjustment.py
   ├─ research/                 # ファクター・特徴量・IC 等
   │   ├─ factor_research.py
   │   └─ feature_exploration.py
   ├─ ai/                       # OpenAI を使用したニューススコア等
   │   ├─ news_nlp.py
   │   └─ regime_detector.py
   └─ tools/
       └─ paper_verification_report.py
```

重要なファイル:
- src/kabusys/config.py — Settings クラスが環境変数を抽象化。自動でプロジェクトルートの .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- src/kabusys/run_execution.py — ExecutionEngine の起動ロジック。paper_trading の場合は paper_db を使用。
- src/kabusys/run_monitoring.py — SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔変更可。
- src/kabusys/monitoring/monitoring_db.py — SQLite スキーマ作成・簡易操作ラッパ。
- src/kabusys/ai/news_nlp.py, regime_detector.py — OpenAI を用いる箇所。OPENAI_API_KEY の設定が必要。

---

## 運用上の注意 / ベストプラクティス

- 本番で稼働させる場合は KABUSYS_ENV=live を設定し、LINE 通知などのアラート設定を確認してください（validate_config は live 時に追加警告を出します）。
- .env は決して Git にコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- OpenAI キーや API トークンは権限管理を徹底してください。AI 呼び出しはコスト発生やレート制限（429）に注意。
- 監視と Execution は異なる DB / PID / フラグファイルで制御されますが、起動前に data ディレクトリの状態（kill.flag, stop_requested.flag 等）を確認してください。
- ログディレクトリの作成に失敗するとファイル出力を行わずコンソール出力のみになります。権限やパスを確認してください。

---

## 開発 / テストのヒント

- DuckDB 接続を受け取る純粋関数群が多く、ユニットテスト用にメモリ DB（またはテスト専用ファイル）で簡単にテスト可能です。
- 外部 API 呼び出し（OpenAI / ブローカー）は抽象化されており、ユニットテストではモック可能です（コード中に patch 用の注記あり）。
- 設定自動読み込みはプロジェクトルートの検出に依存するため（.git または pyproject.toml）、パッケージ配布後の動作を確認する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってテストを分離できます。

---

必要であれば、README に以下の追記が可能です:
- 依存関係の厳密な requirements.txt
- systemd / supervisor 用のユニット例（運用向け）
- DB スキーマ詳細や各コンポーネントの API ドキュメント
- 開発者向けの contribution guide / テスト実行手順

追加で書いてほしい節や、運用向けユニットファイルのサンプルがあれば教えてください。