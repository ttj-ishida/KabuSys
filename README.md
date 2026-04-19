KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。市場データの集計・ファクター計算、ポートフォリオ構築、注文実行（実口座 / ペーパートレード切替）、システム監視・アラート、LLM を用いたニュースセンチメントや市場レジーム判定などの機能を提供します。

主な設計方針
- DuckDB / SQLite を用いたローカル DB 中心の設計（外部 DB 非依存）
- 本番・ペーパーを明確に分離（環境変数 KABUSYS_ENV）
- LLM (OpenAI) 連携機能はフェイルセーフ（API エラー時は安全なデフォルトで継続）
- 各機能はモジュール化され、プログラム的に呼び出せます

機能一覧
--------
- 実行（ExecutionEngine）
  - ブローカークライアント抽象化（実口座 / MockBroker 切替）
  - 注文管理、リスク管理、照合（reconciler）
  - PID ファイル、停止フラグに対応

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存チェック
  - TradeMonitor: 注文滞留・約定異常検出（ログから）
  - RiskMonitor: ドローダウンやポジション上限の判定とリスクログ
  - KillSwitch: 監視結果から停止フラグ（data/kill.flag）を生成
  - MonitoringEngine: 各モニタを統合したポーリングループ

- ポートフォリオ構築（純粋関数群）
  - 候補選定、等配分／スコア配分、リスク調整（セクター制限、レジーム乗数）
  - 位置サイズ計算（単元株丸め、利用可能現金によるスケーリング）

- 研究用モジュール
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Information Coefficient）、統計サマリ

- AI（OpenAI 統合）
  - ニュース NLP（銘柄単位のセンチメントスコアを ai_scores に書き込み）
  - レジーム判定（ETF MA200 とマクロニュースを合成）

- ユーティリティ
  - 環境変数 / .env の自動読み込み・ウィザード（config_setup）
  - 設定検証ツール（validate_config）
  - ロギング設定、プロセス優先度ユーティリティなど

- ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順
--------------
前提
- Python 3.10 以上（型注記に Union | を利用）
- Git リポジトリのルートにプロジェクトがあること（.env 自動検出のため）

1. リポジトリをクローン（例）
   - git clone <repo_url>
   - cd <repo_root>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai
   - （任意）PyYAML があると validate_config の YAML 検証が有効になります:
     pip install pyyaml

   ※ requirements.txt が提供されている場合は:
     pip install -r requirements.txt

4. 環境変数の準備
   - 簡単に行うにはウィザードを使う:
     python -m kabusys.config_setup
     → 対話式に .env を生成 / 更新します
   - あるいは .env.example を参考に直接 .env を作成してください。
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も厳密にチェックする場合:
     python -m kabusys.validate_config --strict

使い方（実行例）
----------------

- ExecutionEngine を起動（通常/本番・ペーパー切替は KABUSYS_ENV で制御）
  - 本番（デフォルト）:
    python -m kabusys.run_execution
  - ペーパートレード:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Command は PID ファイル（data/execution.pid）や停止フラグ（data/stop_requested.flag / data/kill.flag）に対応しています。

- Monitoring を起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒指定（デフォルト: 60）
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- プログラム的に呼び出す（AI / 研究機能の例）
  - DuckDB 接続を開いて関数を呼ぶ例（簡略）:
    from kabusys.ai import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,11), api_key="...")

環境・ファイルに関する重要ポイント
----------------------------------
- DB/ログのデフォルトパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/ (日次ローテーション)
- Kill Switch / Stop フラグ:
  - data/kill.flag — KillSwitch による ExecutionEngine 停止指示
  - data/stop_requested.flag — run_monitoring / run_execution がループ停止を検出するために使用
- PID ファイル:
  - data/execution.pid（ExecutionEngine のプロセス管理）
- Paper Trading 動作:
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_trading.db に記録
  - 本番 DB と完全分離されます

ディレクトリ構成（主要ファイル）
-------------------------------
以下はリポジトリ内の src/kabusys の主要ファイル群です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py             — .env 対話ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py               — ニュースから銘柄別センチメントを生成
    - regime_detector.py        — 市場レジーム判定（MA + マクロセンチメント）

  - monitoring/
    - monitoring_db.py          — SQLite 用永続化層
    - system_monitor.py         — CPU/メモリ/ディスク / データ鮮度監視
    - trade_monitor.py          — 注文ログ・異常検出（実装参照）
    - risk_monitor.py           — ドローダウン・ポジション数監視
    - kill_switch.py            — kill.flag の管理
    - monitoring_engine.py      — 各モニタの統合ポーリング

  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 株数決定・資金スケーリング
    - risk_adjustment.py        — セクター制限・レジーム乗数

  - research/
    - factor_research.py        — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py    — 将来リターン・IC・統計サマリ

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

  - utils/
    - logging_setup.py          — ログ設定ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity 設定

注意事項 / 運用上のヒント
-------------------------
- .env は絶対にリポジトリへコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- OpenAI 連携を使う場合は OPENAI_API_KEY を設定してください。AI 呼び出しは失敗に対してフェイルセーフ実装がありますが、APIキー未設定では該当機能は利用できません。
- 本番環境（KABUSYS_ENV=live）では kill.flag / KILL_FLAG_CLEAR_ON_START の値など慎重に設定してください（validate_config が警告を出します）。
- ログや DB のディレクトリは運用時に適切なローテーション・バックアップを検討してください。
- psutil によるプロセス優先度設定は権限に依存します。権限不足で警告が出ますが処理は継続します。

ライセンス / 貢献
-----------------
（ここにプロジェクト固有のライセンス情報や貢献ガイドを追加してください）

お問い合わせ / 追加ドキュメント
------------------------------
各モジュール内に詳細な docstring / コメントが含まれています。さらに運用ガイドやアーキテクチャ文書（PortfolioConstruction.md、StrategyModel.md 等）がリポジトリに含まれている場合はそちらも参照してください。