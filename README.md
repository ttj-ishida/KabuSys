# KabuSys

日本株自動売買システムのコードベース（ライブラリ＋起動スクリプト群）です。  
この README はリポジトリ内の主要スクリプト・モジュールの使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の役割を持つモジュール群で構成されています。

- 自動売買の ExecutionEngine（発注・注文管理・リスク管理）
- 監視（System / Trade / Risk）と Kill Switch（異常発生時の停止フラグ）
- 研究用モジュール（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- AI 製品（ニュース NLP によるセンチメントスコア、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定読み込みウィザードなど）
- 各種 CLI ツール（設定ウィザード・設定検証・Paper Trading レポート生成）

設計上の特徴：
- Paper Trading（模擬取引）と Live（本番）を DB 等で分離可能
- DuckDB を研究/分析用に使用、SQLite を軽量な永続化（監視・取引ログ）に使用
- OpenAI API を用いたニュースの自動スコアリング等を含む（APIキー必須）
- .env ファイルの自動読み込み / 対話式生成・検証ツールを提供

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの切り替え（paper_trading では Mock を使用）
  - 注文管理・リスク管理・リコンシリエーション

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス生存確認・データ鮮度チェック
  - TradeMonitor：注文滞留・約定異常などの検出
  - RiskMonitor：ドローダウン・ポジション上限監視、リスクログ記録
  - KillSwitch：条件を満たすと `data/kill.flag` を書き込み Execution を停止
  - run_monitoring.py：ポーリングループで監視を継続実行（MONITOR_POLL_INTERVAL 調整可）

- Research / Portfolio
  - ファクター計算（momentum/value/volatility 等）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
  - 候補選定、重み付け、ポジションサイズ決定、セクター制限・レジーム乗数

- AI
  - news_nlp: raw_news から銘柄ごとのセンチメントを LLM でスコア化して ai_scores に書込み
  - regime_detector: ETF の MA 乖離 + マクロニュースセンチメントから日次レジーム判定

- ツール
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

- ユーティリティ
  - 統一ログ設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）
  - 設定ファイルの自動読み込み（config.py）

---

## セットアップ手順

以下は開発環境のセットアップ例です。

1. Python 仮想環境の作成（例）
   - python3 -m venv .venv
   - source .venv/bin/activate

2. 依存ライブラリをインストール
   - 必須（コードからの推測）:
     - duckdb
     - psutil
     - openai
     - （SQLite は標準ライブラリ）
   - 任意:
     - PyYAML（config の YAML 検証に使用）

   例:
   - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合はそれを使用してください）

3. プロジェクトルートに移動して .env を準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成。主な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live） — デフォルト: development
     - OPENAI_API_KEY（AI機能利用時に必須）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）
     - LOG_LEVEL（デフォルト: INFO）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意：本番アラート用）

4. 設定の検証（起動前推奨）
   - python -m kabusys.validate_config
   - strict モード（警告もエラー扱い）：python -m kabusys.validate_config --strict

5. データ / ログ ディレクトリ
   - デフォルトでは `data/` に DB・PID・フラグを格納します。`logs/` にログファイルを生成します。
   - `LOG_DIR` 環境変数でログ出力先を変更可能。

注意:
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも記載あり）。
- 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

## 使い方（代表的なコマンド）

- 実行（ExecutionEngine）
  - 本番または paper_trading モードで Engine を起動:
    - python -m kabusys.run_execution
  - 起動時に `data/execution.pid` を生成し、`data/stop_requested.flag` / `data/kill.flag` による停止を監視します。
  - paper_trading モード（KABUSYS_ENV=paper_trading）の場合、MockBroker を使用し paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に書き込みます。

- 監視（Monitoring）
  - 監視ループを起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は監視データを常に production sqlite_path（Settings.sqlite_path）に書き込みます（環境に関係なく本番監視 DB を参照する仕様）。

- 設定ウィザード / 検証
  - .env を対話式で作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
    - 問題があれば stdout に ERROR/WARNING を出力し、exit code を返します（--strict を使うと警告も失敗扱い）。

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（スコア付与 / レジーム判定）
  - OpenAI API キーを `OPENAI_API_KEY` に設定した上で、アプリケーションコード内から関数を呼び出します。
    - 例（Python REPL）:
      - from kabusys.ai.news_nlp import score_news
      - score_news(duckdb_conn, target_date, api_key=None)  # api_key None の場合は環境変数を使う
    - レジーム判定:
      - from kabusys.ai.regime_detector import score_regime
      - score_regime(duckdb_conn, target_date)

備考:
- 多くのモジュールは duckdb の接続オブジェクト（DuckDBPyConnection）を受け取る設計です。
- AI 呼び出しはリトライ・フェイルセーフ（失敗時に 0.0 などでフォールバック）を組み込んでありますが、API キーは必須です。

---

## 重要なファイル / フラグ

- data/
  - kill.flag — KillSwitch が発動した理由文を保持（ExecutionEngine に停止シグナル）
  - stop_requested.flag — run_monitoring / run_execution の外部停止用フラグ（存在するとループ終了）
  - execution.pid — 実行中の ExecutionEngine の PID（プロセス管理用）
  - monitoring.db / paper_trading.db — SQLite データベース（監視 / paper trading）

- logs/
  - 実行時ログ（例: execution.log, monitoring.log）を日次ローテートで保持（デフォルト 30 日）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 自動読み込み、Settings
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py             — SQLite 永続化（テーブル初期化・アクセスラッパー）
    - system_monitor.py            — システム / データ鮮度監視
    - trade_monitor.py             — 注文イベント監視（該当ファイルあり）
    - risk_monitor.py              — ドローダウン・ポジション制限監視
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン
    - kill_switch.py               — フラグファイルによる停止判定
    - alert_manager.py             — 通知管理（LINE 等、存在する場合）
  - execution/
    - execution_engine.py          — 実行エンジン（run_session 等）
    - broker_factory.py            — BrokerClient の生成（Mock / 実装分岐）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                   — ニュース NLP スコアリング
    - regime_detector.py            — レジーム判定
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - utils/
    - logging_setup.py              — 共通ログ設定
    - process_priority.py           — プロセス優先度 / CPU affinity

※ 実際のリポジトリには上記以外にもモジュールや補助スクリプトが含まれることがあります。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — AI 機能利用時に必須
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（paper_trading 用）
- PAPER_FILL_MODE — instant | partial | never | reject（paper_trading の約定挙動）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動読み込みを無効化

---

## 運用上の注意 / トラブルシューティング

- ログディレクトリが作成できない場合、ファイルハンドラは無効化されコンソール出力のみになります。権限を確認してください。
- run_execution / run_monitoring は stop フラグや kill.flag を検知して安全に終了する仕組みを持ちます。手動停止時は `data/stop_requested.flag` を作成すると良いです。
- Paper Trading と本番 DB は分離されていますが、設定ミスで本番 DB を参照する可能性があります。validate_config で DB パス等を確認してください。
- OpenAI 呼び出しはネットワークやレート制限で失敗する可能性が高いため、リトライとフォールバックが実装されています。しかし過度の失敗は機能低下に繋がるため API キー・レート制限・課金状況を事前確認してください。

---

この README はコードベースの主要ポイントをまとめたものです。詳細な API 仕様や設計書（PortfolioConstruction.md / StrategyModel.md 等）が別途ある場合はそちらも参照してください。必要に応じて README の追加・修正を行いますので、不足・改善点があれば教えてください。