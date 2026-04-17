KabuSys — 日本株自動売買システム
================================

この README は、提供済みコードベース（src/kabusys 以下）についての概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
--------------
KabuSys は日本株の自動売買／リサーチ用プラットフォーム向けライブラリ群です。本プロジェクトは以下の目的を持ちます。

- 株価データを用いたファクター計算・研究（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み付け・サイズ決定）
- ExecutionEngine を介した発注（本番およびペーパートレード分離）
- 監視（System/Trade/Risk モニタ）と Kill Switch による安全停止
- OpenAI を利用したニュース NLP（センチメント）および市場レジーム判定
- ペーパートレード結果の検証レポート生成ツール

主な特徴 / 機能一覧
-----------------
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的に生成
- 設定検証 CLI（python -m kabusys.validate_config）で .env / config/*.yaml を事前チェック
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、本番 DB と分離（data/paper_trading.db）
  - 停止用フラグファイル（data/stop_requested.flag / data/kill.flag）および PID ファイル管理
- Monitoring（python -m kabusys.run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- MonitoringDB: SQLite を用いた監視ログ永続化（テーブル作成・マイグレーションを自動で実行）
- RiskMonitor: ドローダウン・ポジション上限監視とアラート記録
- TradeMonitor: 注文滞留・約定異常価格検出とリスクログ記録
- KillSwitch: 条件を満たした場合に data/kill.flag を書き込み ExecutionEngine を安全に停止
- portfolio パッケージ: 候補選定、等重/スコア加重、セクター制限、ポジションサイズ計算（ロット丸め等）
- research パッケージ: ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリー
- ai パッケージ: OpenAI を利用したニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
- tools: ペーパートレード検証レポート生成ツール（paper_verification_report）

前提（推奨）
------------
- Python 3.10 以上（型アノテーションに | を使用）
- SQLite 標準ライブラリ（同梱）
- 推奨/必要パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（config/*.yaml のパース検証に任意）
- 環境変数で外部 API キー等を設定（詳細は下記）

セットアップ手順
----------------
1. リポジトリをクローン / フォルダに配置
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - （検証用）pip install pyyaml
4. .env を用意
   - 対話式ウィザード: python -m kabusys.config_setup
     - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD は必須
     - KABUSYS_ENV=development | paper_trading | live を設定
   - 自動ロード:
     - config モジュールはプロジェクトルート（.git または pyproject.toml）を探し .env / .env.local を自動ロードします
     - テスト時に自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります
6. 初期データディレクトリ
   - デフォルトの DB パスは data/kabusys.duckdb（DuckDB）と data/monitoring.db（SQLite）
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN：J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD：kabuステーション API パスワード（必須）
- KABUSYS_ENV：実行環境（development / paper_trading / live）
- OPENAI_API_KEY：OpenAI API キー（ai.news_nlp / ai.regime_detector が必要）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH：監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH：ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL：監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START：起動時に kill.flag を自動削除するか（1=有効。本番では 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH：PID ファイル / kill.flag のパスを上書き可能

基本的な使い方（コマンド例）
----------------------------
- .env を作成（対話式）
  - python -m kabusys.config_setup
- 設定チェック
  - python -m kabusys.validate_config
- ExecutionEngine を起動（本番/ペーパートレードに応じて設定）
  - python -m kabusys.run_execution
  - 動作: PID ファイルを書き込み、Engine をスレッドで実行。data/stop_requested.flag 存在で停止。
  - ペーパートレード: KABUSYS_ENV=paper_trading に設定すると専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で調整可能
  - 監視結果・リスクログは SQLITE_PATH（monitoring.db）に保存
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB は environmental PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- AI 系（ニュースセンチメント・レジーム判定）
  - ai モジュールは OpenAI API キーが必須。関数を直接呼び出す:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - CLI から呼ぶラッパーは用意されていないため、スクリプト/ジョブで呼び出してください
- Kill Switch / 手動停止
  - KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止できます
  - 手動停止は data/stop_requested.flag を作成すると run_execution / run_monitoring のループで検知して安全停止します

注意点 / 実運用上のポイント
-------------------------
- .env は決して Git にコミットしないこと（config_setup.py の冒頭コメント参照）
- KABUSYS_ENV=live の場合は特に LINE 通知等の設定を確認すること（validate_config の警告参照）
- MONITORING は本コードベースでは常に本番 sqlite_path を使う（monitoring 用 DB は環境にかかわらず sqlite_path を参照）
- paper_trading は本番 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH）
- OpenAI 呼び出しはリトライ・フェイルセーフを実装していますが、API キーの管理・レート制限に注意してください
- process 優先度設定（psutil を使用）や CPU affinity は環境により権限不足で失敗する場合があります（ログで警告が出ます）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール／スクリプトの抜粋です。実際のツリーはリポジトリを参照してください。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI + MA）
  - research/
    - __init__.py
    - factor_research.py       — momentum / value / volatility 計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - portfolio/
    - __init__.py
    - portfolio_builder.py     — 候補選定・重み付け
    - position_sizing.py       — 株数決定・スケールダウン・ロット丸め
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（テーブル作成・マイグレーション）
    - monitoring_engine.py     — 各モニタの束ね
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - alert_manager.py         — （未表示だがアラート管理）
    - kill_switch.py           — Kill Switch 実装（flag ファイル）
  - execution/                 — Execution 関連（OrderManager, ExecutionEngine 等）
    - （実装ファイル群、発注ロジック・リポジトリ等）
  - utils/
    - __init__.py
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/monitoring_db.py — 監視 DB 実装（テーブル定義・MonitoringDB クラス）

（注）本 README は提供されたコード片に基づく要約です。実際の運用時はリポジトリ内の各モジュールの docstring とコメントを参照してください。

トラブルシューティング / よくある確認項目
---------------------------------------
- .env の自動ロードが期待通りに動かない場合:
  - プロジェクトルート判定は .git または pyproject.toml があるディレクトリを基準に行われます
  - テストで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI 呼び出しで失敗が多い場合:
  - OPENAI_API_KEY の有効性、レート制限、ネットワーク接続を確認
  - news_nlp / regime_detector はリトライ処理を実装していますが、完全な回復を保証するものではありません
- pid / flag ファイルの扱い:
  - data/execution.pid（または PID_FILE_PATH で指定）を監視して Process 存在チェックを行います
  - stale PID 検知時は削除してリスクログに記録します

ライセンス・貢献
----------------
リポジトリに LICENSE が含まれていればそちらを参照してください。開発・改善に貢献する場合は issue / pull request を作成してください。

最後に
------
この README はコードベースの迅速な理解と運用開始を支援するためのまとめです。詳細な挙動や API、内部アルゴリズムの仕様は各モジュールの docstring / コメントを参照してください。必要があれば README に追記したい項目（例: サンプル .env、システム図、データベーススキーマの詳細など）を教えてください。