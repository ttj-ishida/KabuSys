# KabuSys

日本株向け自動売買システムのリポジトリ（抜粋）。本 README はリポジトリ内の主要モジュールに基づいて作成した簡易ドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を支援する Python モジュール群です。主な機能は以下の通りです：

- 注文実行エンジン（ExecutionEngine）
- 監視サブシステム（System / Trade / Risk モニタ）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- リサーチ（ファクター計算、特徴量解析）
- ニュース NLP によるセンチメント評価（OpenAI API を利用）
- ペーパートレード検証ツール・レポート生成
- 設定ウィザード・設定検証 CLI

設計上のポイント：
- 設定は .env / 環境変数で管理（自動ロード機能ありが無効化可）
- Paper Trading と本番（live）は DB を分離して運用可能
- ロギングとプロセス優先度設定など運用向けユーティリティを含む

---

## 主な機能一覧

- 設定管理
  - .env の対話式作成（kabusys.config_setup）
  - 起動前に環境・設定を検証（kabusys.validate_config）
- 実行系
  - 実際の発注エンジン起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用 DB に記録
- 監視系
  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - システム状況・データ鮮度・取引状態・リスクを定期チェック
    - Kill Switch（条件により ExecutionEngine を停止させる flag）連携
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等配分/スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（lot rounding、aggregate cap 等）
- リサーチ
  - モメンタム / ボラティリティ / バリュー 等のファクター算出（DuckDB を使用）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- AI（OpenAI）
  - ニュース記事のセンチメント評価と ai_scores への格納（kabusys.ai.news_nlp）
  - 市場レジーム判定（ma200 とマクロセンチメントの合成）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提
- Python 3.9+ 推奨（モジュールは type hints 等を使用）
- OS により追加の依存（psutil のネイティブ拡張等）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 依存ファイルがない場合、最低限次を入れてください:
     - pip install duckdb psutil openai
   - 追加（任意）:
     - PyYAML（config/*.yaml の検証に必要）: pip install pyyaml
   - 開発インストール（パッケージとして扱いたい場合）:
     - pip install -e .
4. 環境変数 / .env を用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（例は下）
5. 設定検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - 厳格モード（警告を FAIL 扱い）: python -m kabusys.validate_config --strict

サンプル .env（最小）
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO
- OPENAI_API_KEY=sk-xxxxx  # AI 機能を利用する場合

注:
- 自動 .env ロードはデフォルトで有効です。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（起動と主要コマンド）

基本的にモジュールを直接実行します。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が既にある場合は起動せず終了
    - 実行中に data/stop_requested.flag を作成するとシャットダウンをトリガ（Graceful shutdown）
    - 実行時に data/execution.pid を作成

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - オプション（環境変数）:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。0 以下は無効としてデフォルトにフォールバック。
  - 監視は Settings の sqlite_path（data/monitoring.db がデフォルト）を使用（KABUSYS_ENV にかかわらず本番 sqlite_path を参照）
  - 監視は data/stop_requested.flag の存在でループを終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH で代替可）
  - 出力: コンソールに検証指標と PASS/FAIL 判定を出力

- AI 系（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定してから、該当関数を呼び出す（API キーを引数で渡すことも可）
  - news_nlp.score_news(...) / regime_detector.score_regime(...)

運用上のファイル（data ディレクトリ）
- data/kill.flag: Kill Switch により ExecutionEngine 停止を指示するフラグファイル（KillSwitch が作成）
- data/stop_requested.flag: run_* スクリプトの外部停止トリガ
- data/execution.pid: 実行エンジンの PID（run_execution が作成）
- DB: data/monitoring.db（監視用） / data/paper_trading.db（ペーパートレード）

ロギング
- ログは console とファイル（logs/<app_name>.log）へ出力（Daily ローテーション、30日分保持）
- ログレベルは LOG_LEVEL または setup_logging の引数で制御

プロセス優先度
- 起動時に set_process_priority("high") を呼び、psutil による優先度設定を試みます（失敗しても警告のみ）

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) — default: instant
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — default: INFO
- OPENAI_API_KEY — AI 機能を使う場合に必須
- MONITOR_POLL_INTERVAL — run_monitoring の間隔（秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings 定義（自動 .env ロード含む）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化（テーブル作成・読み書き）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （取引監視、コードベース参照）
    - risk_monitor.py — ドローダウン・保有数監視
    - kill_switch.py — Kill Switch 実装（flag ファイル操作）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート通知管理）
  - execution/ — ExecutionEngine 関連（broker, order_manager, reconciler, risk_manager 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 数量計算・ラウンド処理
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 先行リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースを OpenAI で評価して ai_scores に格納
    - regime_detector.py — レジーム判定
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート

（上記は抜粋です。詳細は各ファイルの docstring を参照してください。）

---

## 運用上の注意点 / ベストプラクティス

- 本番 (KABUSYS_ENV=live) では .env を Git にコミットしないこと（config_setup でも注意書きあり）。
- validate_config を起動前に実行し、必須環境変数や DB パスなどを検証すること。
- Paper Trading 実行時は paper_trading 用 DB に分離されるため、本番 DB への誤発注リスクを下げられますが、設定ミスに注意してください。
- OpenAI API 呼び出しはレート制限やネットワーク障害を考慮したリトライ実装がありますが、API キーやコスト管理は運用で注意してください。
- kill.flag / stop_requested.flag の取り扱いを運用ルールとして定め、誤ってクリアしないように注意する（KILL_FLAG_CLEAR_ON_START の設定に注意）。

---

README はここまでです。各機能の詳細（ExecutionEngine の内部、OrderManager・Broker の実装、monitoring の各チェックロジックなど）については該当ソースファイルの docstring コメントを参照してください。必要であれば特定サブモジュールの詳細 README を追補します。