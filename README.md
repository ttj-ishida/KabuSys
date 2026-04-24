# KabuSys

日本株自動売買システムの参照実装（ライブラリ + 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・注文実行（実稼働/ペーパートレード両対応）、監視・アラート、研究用ユーティリティ、AI（ニュースセンチメント／レジーム判定）などを含むモジュール群で構成されています。

## プロジェクト概要
- 目的: 日本株向け自動売買ワークフローの主要コンポーネントを実装し、運用・検証を支援すること。
- 主な要素:
  - ExecutionEngine: ブローカークライアントを介した発注・注文管理・リスク管理
  - Monitoring: システム状態・注文状態・リスクの定期チェック、Kill Switch による停止制御
  - Research: DuckDB に蓄積された株価データを用いたファクター計算・解析機能
  - Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制約などの純粋関数群
  - AI: OpenAI を用いたニュースセンチメント評価と市場レジーム判定（APIキー必須）
  - CLI ユーティリティ: .env ウィザード、設定検証、ペーパートレード検証レポート作成など

## 主な機能一覧
- 実行（run_execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - MockBrokerClient によるペーパートレード（DB を分離）
  - リスク管理（position limit、drawdown 等）
  - 発注履歴 / 約定ログの永続化（SQLite）
- 監視（run_monitoring）
  - CPU/メモリ/ディスク使用率、Execution プロセス生存監視
  - データ鮮度チェック（DuckDB の prices_daily）
  - Trade / Risk モニタリングとアラート発火、Kill Switch 判定
  - ポーリング間隔は環境変数で調整可能
- 研究（research/*）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 使用）
  - 将来リターン・IC 計算・統計サマリー
- ポートフォリオ構築（portfolio/*）
  - 候補抽出、等配分・スコア加重、リスクベースのポジションサイズ算出
  - セクター上限適用、レジーム乗数
- AI（ai/*）
  - ニュース記事を LLM（gpt-4o-mini）でセンチメント評価して ai_scores へ書込
  - マクロニュースと ETF MA200 を合成して市場レジーム判定
  - API 呼び出しはリトライ・フォールバック実装あり
- ツール
  - .env 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

## セットアップ手順（開発・運用向け）
1. Python 環境を準備
   - 推奨: Python 3.9+（コードは型注釈・標準ライブラリの機能を使用）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Unix/macOS) または .venv\Scripts\activate (Windows)

2. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config/*.yaml の検証に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt はリポジトリに含まれていないため、使用する機能に応じて上記を個別にインストールしてください。

3. プロジェクトルートに .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または手動で .env を作成（例）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=（AI 機能利用時に設定）
   - 自動で .env/.env.local を読み込む仕組みがあります（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. データディレクトリの準備
   - ログディレクトリ: デフォルトは logs/
   - DB / フラグ類: data/ 以下にファイルが置かれます（自動作成されることが多い）。
   - 必要に応じて権限や配置を確認してください。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

## 使い方（起動例）
- ExecutionEngine を起動（ローカル開発/ペーパートレード/本番は KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録されます。
    - 実稼働環境では各 API の設定・認証情報を正しく設定してください。
    - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。

- Monitoring を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数で変更可:
    - MONITOR_POLL_INTERVAL=30  # 30秒ごとにポーリング
  - 停止: data/stop_requested.flag を作成するとループを安全に終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- .env の作成・更新
  - python -m kabusys.config_setup

- 設定検証（CI/起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- AI 機能（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続と OpenAI API キー（または環境変数 OPENAI_API_KEY）が必要です。

## 環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 運用/オプション:
  - KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時のみ使用）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒、run_monitoring 用）
  - KILL_FLAG_CLEAR_ON_START — 本番で kill.flag を自動クリアするか（0/1、安全のためデフォルト 0 推奨）
  - その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知用）

## 停止・Kill Switch の仕組み
- 停止促し（外部からの安全停止）
  - data/stop_requested.flag を作成すると run_execution/run_monitoring の起動ループが検知して終了します。
- Kill Switch（自動停止判定）
  - モニタリング側の判定により data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - 実行エンジンは起動時に KILL_FLAG_CLEAR_ON_START の設定に従い kill.flag をクリアするかどうかを決めます。

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下をプロジェクトルートにコピーした想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - data/                    — データ操作系（別モジュール想定）
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig / run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュースセンチメント評価（OpenAI 使用）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - logs/                    — デフォルトログ出力先（実行時に作成）
  - data/                    — DB / pid / flag 等（実行時に作成）

## 開発・運用上の注意点
- 本番（KABUSYS_ENV=live）では設定・シークレットを厳重に管理してください。validate_config は本番に関する警告を出します。
- .env は絶対にリポジトリにコミットしないでください。
- DuckDB は分析用途、SQLite は監視・注文履歴の永続化に使われます（実行ロジックは DB パスを Settings から取得）。
- AI モジュールは外部 API に依存します。API 失敗時はフォールバックロジック（0.0）で継続する設計ですが、料金・レート制限・プライバシーについて運用ルールを定めてください。
- process_priority, cpu_affinity は psutil を使います。権限によっては設定に失敗する場合があります（その場合は警告ログ）。

---

README はプロジェクトの導入・起動に必要な最低限のガイドを含めています。必要であれば、実行例・設定ファイルのテンプレート・詳細な設計ドキュメント（API 仕様、DB スキーマ、シーケンス図 等）を別途追加できます。必要な追加項目を指示してください。