# KabuSys

KabuSysは日本株向けの自動売買システム（プロトタイプ）です。本リポジトリは、発注エンジン・監視・リスク管理・ポートフォリオ構築・リサーチ・AI（ニュースNLP / レジーム判定）などの主要コンポーネントを含むモジュール群で構成されています。

以下はこのコードベースの概要、機能、セットアップ方法、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要
- 日本株自動売買のためのモジュール群（発注エンジン、監視、リスク管理、ポートフォリオ構築、ファクター計算、ニュースNLP など）。
- SQLite（監視・ペーパートレード用）と DuckDB（分析用）を利用して永続化・集計を行う。
- OpenAI（gpt-4o-mini 等）を利用したニュースのセンチメント評価やマクロセンチメントを組み合わせた市場レジーム判定を実装。
- 設定は環境変数 / .env ファイルで管理。`.env` 作成支援ツール・検証ツールを提供。

---

## 主な機能一覧
- ExecutionEngine（発注エンジン）
  - 実際のブローカークライアントまたは MockBrokerClient を選択（KABUSYS_ENV により切替）
  - リスク管理（最大ポジション率、資金利用率、サーキットブレーカー等）
  - OrderRepository / OrderManager / Reconciler 等の実装
- Monitoring（監視）
  - システムリソース・プロセスの生存確認・データ鮮度チェック
  - 取引ログ / リスクログ / ダッシュボードの永続化（SQLite）
  - Kill Switch（ドローダウンやポジション上限到達での停止フラグ書き込み）
- Portfolio（銘柄選定・ウエイト計算・ポジションサイズ算出）
  - 候補選定、等金額/スコア重み、リスクベース割当
  - セクター上限、レジーム乗数適用
- Research（ファクター計算・特徴量探索）
  - モメンタム、ボラティリティ、バリュー等のファクター算出（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）等の統計関数
- AI（ニュースNLP / レジーム検出）
  - raw_news を LLM でセンチメント化して ai_scores に保存
  - ETF（1321）MA200 とマクロニュースセンチメントを合成して市場レジーム判定
- ユーティリティ
  - .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート出力ツール（kabusys.tools.paper_verification_report）
  - ロギング設定ユーティリティ（kabusys.utils.logging_setup）
  - プロセス優先度設定ユーティリティ（kabusys.utils.process_priority）

---

## 要件（例）
- Python 3.9+
- 主要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を行う場合）
- SQLite（標準ライブラリに含まれます）
- その他、requirements.txt がある場合はそれに従ってください。

（実際のパッケージバージョンはプロジェクトの packaging / requirements を参照）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（プロジェクトに requirements があればそれを利用）。
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成（対話式ウィザードを推奨）
   - python -m kabusys.config_setup
   - ウィザードに沿って J-Quants トークンや kabu API のパスワード、DB パスなどを入力して .env を作成します。
   - 重要: .env は Git にコミットしないでください（ウィザードのヘッダに注意書きあり）。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリ（data）やログディレクトリ（logs）は自動作成されますが、必要に応じて手動で作成・権限を確認してください。

---

## 主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill flag（デフォルト: data/kill.flag）
- ログ関連
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ出力先（デフォルト: logs/）
- Paper trading
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- OpenAI
  - OPENAI_API_KEY: OpenAI の API キー（ニュースNLP / レジーム判定で使用）

---

## 基本的な使い方（コマンド例）

- .env の作成（対話形式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 監視ループの起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: export MONITOR_POLL_INTERVAL=30

  動作概要:
  - 監視は monitoring DB（Settings.sqlite_path）へログを保存します（環境にかかわらず本番 sqlite_path を使用）。
  - 停止: リポジトリルートの data/stop_requested.flag が存在すると監視ループは終了します。

- 実行エンジンの起動（ExecutionEngine）
  - 本番（実際のAPIを使う）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - ペーパートレード（MockBroker を使用し、data/paper_trading.db に記録）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

  動作概要:
  - paper_trading の場合、専用の paper_sqlite_path を使用し本番 DB とは分離されます。
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に data/stop_requested.flag を作成するとエンジンに停止命令を出します（Polling中に engine.stop() を呼びます）。

- Kill Switch（監視側による強制停止）
  - KillSwitch が条件に合致すると data/kill.flag を書き込みます（Settings.kill_flag_path）。
  - ExecutionEngine の起動時に kill_flag_clear_on_start=1 が設定されていると自動でクリアする設定があります（本番では 0 推奨）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定: python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- ライブラリ API（例）
  - ポートフォリオ関数:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - 研究機能:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI（ニュースセンチメント）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

---

## 停止・再起動フロー（運用メモ）
- 即時停止（全体の強制停止）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します。
- Execution の安全停止（監視による）
  - KillSwitch が条件を満たすと data/kill.flag を作成 → ExecutionEngine 側が検知して安全停止を行います。
- 起動時の kill.flag の取り扱い
  - Settings.KILL_FLAG_CLEAR_ON_START が 1 の場合、起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

---

## ディレクトリ構成（主要部分）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（.env 自動ロード機構含む）
  - config_setup.py         — .env 作成ウィザード（対話式）
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py      — SQLite 監視 DB 初期化・永続化層
    - system_monitor.py     — システム状態監視
    - trade_monitor.py      — 取引ログ監視（存在）
    - risk_monitor.py       — ドローダウン・ポジション監視
    - kill_switch.py        — kill.flag 管理
    - monitoring_engine.py  — 監視エンジンの統合ループ
    - alert_manager.py      — 通知（LINE 等）管理（存在）
  - execution/
    - execution_engine.py   — ExecutionEngine（実装本体）
    - broker_factory.py     — ブローカークライアント生成
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
    - news_nlp.py           — ニュースをLLMでスコア化
    - regime_detector.py    — マクロ + MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py

- data/                     — データファイル（デフォルトパス; DB・flag・pid等）
  - monitoring.db
  - paper_trading.db
  - kill.flag
  - stop_requested.flag
  - execution.pid

- logs/                     — ログファイル（デフォルト）

---

## よくあるトラブルと対処
- .env の必須値が未設定 → python -m kabusys.config_setup で設定、または env を export
- 権限エラーで logs/ または data/ が作成できない → ディレクトリの所有権・書き込み権限を確認
- OpenAI API エラー（キー未設定 / レート制限） → OPENAI_API_KEY を設定、レート制限はリトライロジックがあるが制限緩和を検討
- DuckDB / SQLite に接続できない → パス設定（DUCKDB_PATH / SQLITE_PATH）とファイルの存在・権限を確認
- psutil の権限エラーでプロセス優先度設定が失敗 → ログに警告が出るが処理は継続（権限を付与するかスキップ）

---

## 開発者向けメモ
- 自動で .env を読み込む仕組みがあります（Settings モジュール）。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して下さい（テスト時に便利）。
- DuckDB 接続は分析ワークフローで多用します。SQL の最適化やインデックスの検討は運用次第で必要になります。
- LLM 呼び出し部分は外部 API の変化に対する耐性としてリトライやレスポンスバリデーションを多めに実装していますが、実運用ではさらに監視やモニタリングを強化してください。

---

この README はコードを読みやすくするための入門ドキュメントです。詳細な設計や理論（PortfolioConstruction.md、StrategyModel.md 等参照が示唆されているドキュメント）は別途参照してください。もし README の補足（例: デプロイ方法、systemd / Supervisor の unit ファイル例、Docker コンテナ化手順 など）が必要であれば教えてください。