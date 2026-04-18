# KabuSys

日本株向け自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、システム監視・発注エンジン・ポートフォリオ構築・リサーチ・AI ベースのニュース評価などを含む自動売買プラットフォームのコア部分を提供します。設計方針として「本番データベースとの安全な分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（API失敗時は安全にフォールバック）」を重視しています。

---

## 主な機能一覧

- Execution（発注エンジン）
  - ExecutionEngine と OrderManager を中心とした注文実行フロー
  - paper_trading モードでは MockBrokerClient を使い、本番 DB と分離して `data/paper_trading.db` に記録
  - プロセス優先度設定 / PID 管理 / 停止フラグ対応

- Monitoring（監視）
  - システム状態（CPU/メモリ/ディスク）、実行プロセス死活、データ鮮度のポーリングと永続化
  - リスク監視（ドローダウン・ポジション数上限）と Kill Switch（flag ファイルによる停止）
  - アラート発行フック（AlertManager 経由、LINE 連携等を想定）

- Portfolio（銘柄選定・配分・株数算出）
  - 候補選定（スコア降順）、等重・スコア加重配分、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数適用などの調整ロジック

- Research（ファクター計算・特徴量解析）
  - モメンタム / ボラティリティ / バリューなどのファクター計算（DuckDB を利用）
  - 将来リターン計算・IC（Information Coefficient）等の分析ユーティリティ

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（ai_scores テーブルへの書込み）
  - マクロニュース + ETF（1321）MA200乖離の合成による市場レジーム判定（market_regime テーブル）

- ツール
  - 設定ウィザード（.env 生成 / 更新）
  - 設定検証 CLI（環境変数 & config/*.yaml のチェック）
  - Paper Trading 検証レポート生成スクリプト

- ユーティリティ
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env 自動ロード（プロジェクトルートに基づく）

---

## 動作要件（推奨）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
- 任意（機能に応じて）
  - PyYAML（config/*.yaml の検証）
- OS: Linux / macOS / Windows（ただしプロセス優先度・CPU affinity はプラットフォーム依存の振る舞いあり）

※ requirements.txt はリポジトリに含まれていないため、用途に応じて必要なパッケージをインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   git clone <repo_url>
   cd <repo_root>

2. 仮想環境を作成して有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb psutil openai PyYAML

4. 初期設定（.env）を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参照のこと）

5. 設定検証
   python -m kabusys.validate_config
   # 警告もエラーにしたい場合:
   python -m kabusys.validate_config --strict

6. データディレクトリやログディレクトリが自動で作成されます（ログはデフォルトで `logs/`、DB は `data/` 下に作成されます）。

---

## 環境変数（主なもの）

必須（少なくとも開発テスト時に設定が必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要な任意/設定:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/...
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading モードの SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant/partial/never/reject）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリア（"1" で有効。生産環境では "0" 推奨）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

重要ファイル・フラグ:
- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine 停止トリガー）
- data/stop_requested.flag — run_monitoring / run_execution がループ終了に使うローカル停止フラグ
- data/execution.pid — 実行エンジンの PID ファイル（Execution 起動時に使用）

---

## 使い方（主要スクリプト）

- 設定ウィザード（.env の作成・更新）
  python -m kabusys.config_setup
  --env-file オプションでパス指定可

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  # 警告も失敗扱いにする:
  python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  python -m kabusys.run_execution
  挙動のポイント:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し paper_trading 用 DB に記録
  - 起動時に data/stop_requested.flag が存在すると起動せず終了
  - 停止は data/stop_requested.flag の作成で行える（監視プロセスや手動で作成）

- Monitoring（ポーリング）起動
  python -m kabusys.run_monitoring
  環境変数:
  - MONITOR_POLL_INTERVAL でポーリング秒数を上書き（例: MONITOR_POLL_INTERVAL=30）
  注意:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視テーブルを作成/更新します（設計上の動作）

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
  --db PATH を指定すると任意の SQLite ファイルを使用（デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- ライブラリ関数の呼び出し例（Python スクリプト内）
  from kabusys.research import calc_momentum
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 4, 1))

  AI: ニューススコアリング
  from kabusys.ai import score_news
  count = score_news(conn, date(2026,4,1), api_key="sk-...")

  レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026,4,1), api_key="sk-...")

---

## ログ・データ配置（デフォルト）

- logs/
  - execution.log, monitoring.log, ... （TimedRotatingFileHandler による日次ローテーション、デフォルト 30 日保持）
- data/
  - kabusys.duckdb（DuckDB のデフォルトパス）
  - monitoring.db（SQLite: 監視ログ）
  - paper_trading.db（paper_trading 用 SQLite）
  - kill.flag / stop_requested.flag / execution.pid などの制御ファイル

ログは stdout にも出力されます（setup_logging は stdout を StreamHandler に設定）。

---

## ディレクトリ構成

（リポジトリ先頭からの主要ファイル/ディレクトリ）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定取得用
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading レポート生成
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）による ai_scores 書き込み
    - regime_detector.py      — マクロ + ETF MA によるレジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （存在）取引監視ロジック（コードベース内に実装あり）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 各 Monitor を束ねる実行ループ
    - alert_manager.py        — アラート送信管理（通知処理）
  - execution/
    - execution_engine.py     — 発注エンジン本体
    - broker_factory.py       — BrokerClient の生成（Mock / Live 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py        — ログの統一設定（stdout + 日次ファイル）
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

---

## 運用上の注意 / ベストプラクティス

- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知や Kill Switch の挙動を事前に確認してください。
- KILL_FLAG_CLEAR_ON_START は本番では "0" を強く推奨します（"1" にすると起動時に誤って kill.flag を消してしまう可能性があります）。
- Monitoring は監視 DB に常に本番 sqlite_path を使用します。監視対象の分離が必要な場合は環境変数でパスを調整してください。
- OpenAI を利用する機能は API キーの管理（環境変数 / シークレット管理）に注意してください。API 呼び出し失敗時は安全にフォールバックする設計になっていますが、コスト・レート制限に注意してください。
- DuckDB / SQLite のファイルは定期バックアップを推奨します。

---

## 開発者向け補足

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行います。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- tests やユニットテストを書く際は、Settings の自動ロードや外部 API 呼び出しをモックすることを推奨します（例: OpenAI 呼び出し関数を patch）。
- DuckDB 接続は高速分析向けに用意されています。research モジュールは DuckDB 接続を受け取る純粋関数群で構成されています。

---

この README はコードベースの主要な使い方と設計方針をまとめたものです。実運用前には必ず
- python -m kabusys.config_setup（.env 作成）
- python -m kabusys.validate_config（検証）
を実行し、設定とファイルパスが正しいことを確認してください。

もし README の内容を英語版にしたい、あるいは個別のコマンド事例やデプロイ手順（systemd / supervisor / コンテナ化）を追記したい場合は知らせてください。