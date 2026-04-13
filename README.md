# KabuSys

日本株向けの自動売買システムのコアライブラリ（部分抜粋）。  
このリポジトリはトレード実行、モニタリング、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント・レジーム判定）などの機能群を含みます。

## プロジェクト概要
KabuSys は日本株自動売買のためのモジュール群です。主な役割は以下のとおりです。

- ExecutionEngine（発注・状態管理・リコンシリエーション）
- Monitoring（システム状態、注文滞留、ドローダウン等の監視）
- Portfolio construction（候補選定・重み決定・株数計算・リスク調整）
- Research（ファクター計算、特徴量探索、IC計算）
- AI（ニュースセンチメントスコアリング、レジーム判定） — OpenAI API を利用
- ユーティリティ（プロセス優先度設定、Streamlit ダッシュボード等）
- tools（Paper Trading 検証レポート生成スクリプト等）

設計方針の一部：
- DuckDB / SQLite を利用してデータ永続化・集計を行う（外部 API 呼び出しを最小化）
- Paper Trading と本番（live）を明確に分離（専用 SQLite を使用）
- ルックアヘッドバイアス防止のため、date/time を直接参照しない実装が多い

## 機能一覧
- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて mock / live ブローカーを切替）
- run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔設定）
- monitoring/:
  - SystemMonitor / TradeMonitor / RiskMonitor：監視ロジック
  - MonitoringDB：監視ログ（SQLite）読み書き
  - AlertManager：LINE Push による通知（オプション）
  - KillSwitch：フラグファイルによる ExecutionEngine 停止シグナル
  - streamlit_dashboard.py：Streamlit による監視ダッシュボード
- portfolio/: 候補選定、重み付け、単元切り捨て、セクター制限、レジーム乗数等
- research/: ファクター計算（Momentum/Volatility/Value）、特徴量探索、IC/統計サマリ
- ai/:
  - news_nlp.py：ニュース集合を LLM（OpenAI）でセンチメント評価して ai_scores に書き込み
  - regime_detector.py：ETF MA 等とマクロニュースセンチメントを合成して市場レジーム判定
- tools/paper_verification_report.py：Paper Trading 用検証レポート生成（稼働率・成功率・レイテンシ等）

## 前提・依存関係（例）
実際の pyproject / requirements.txt がない場合の参考例：

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボードを使う場合）

インストール例（仮）:
```bash
pip install duckdb psutil requests openai streamlit
```

プロジェクト配布時は pyproject.toml / requirements.txt を参照してください。

## 環境変数（主要）
自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数を上書きしない / .env.local は上書き）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数と説明（抜粋）:

- KABUSYS_ENV: 実行環境。`development`（デフォルト） | `paper_trading` | `live`
  - `paper_trading` の場合、MockBroker を使い DB は `data/paper_trading.db` に記録（本番 DB と分離）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定時は通知を送らずログのみ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject）（デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

注意:
- Settings モジュールは `.env` と OS 環境変数の自動読み込みを行います。 `.env.example` を元に必要な変数を用意してください。
- PAPER_FILL_MODE 等の値はバリデーションされます。

## セットアップ手順（簡易）
1. リポジトリをクローン / コピー
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```
   ※ 実際はプロジェクトの requirements.txt / pyproject.toml を使用してください。
4. 環境変数を準備（.env をプロジェクトルートに配置）
   - 最低限 KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN（および OpenAI を使う場合は OPENAI_API_KEY）を設定
   - 例（.env）:
     ```
     KABUSYS_ENV=development
     KABU_API_PASSWORD=your_kabu_password
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     OPENAI_API_KEY=sk-...
     ```
5. data ディレクトリを作成（必要なら）
   ```bash
   mkdir -p data
   ```
   スクリプト側が DB を自動作成しますが、権限やパスは事前に確認しておくと安全です。

## 使い方（主要スクリプト）
- ExecutionEngine を起動（本番 / Paper 切替は KABUSYS_ENV に依存）
  ```bash
  # Paper Trading で起動する例
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  ポイント:
  - Paper Trading の場合は `settings.paper_sqlite_path`（デフォルト data/paper_trading.db）を使用
  - 起動時にプロセス優先度を高に設定します（set_process_priority("high")）

- Monitoring（SystemMonitor のポーリング）を起動
  ```bash
  # ポーリング間隔を 30 秒に変更する例
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視 DB は `SQLITE_PATH`（デフォルト data/monitoring.db）に保存
  - run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視は実稼働 DB を見る想定）

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- Streamlit ダッシュボード（監視）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - ダッシュボードは読み取り専用で DB を開きます。MonitoringEngine を先に起動してデータを投入してください。

- AI モジュール（ニューススコアリング / レジーム判定）利用例（プログラム内から呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーが必要（引数または環境変数 OPENAI_API_KEY）

## 注意事項 / 運用メモ
- .env の自動読み込み:
  - プロジェクトルートは .git または pyproject.toml を基準に探索します。
  - OS 環境変数が優先され、.env ファイルは上書きされません（ただし .env.local は override=True で上書き）。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等で実行でき、必要なカラム追加（ALTER TABLE）等の簡易マイグレーション処理を含みます。
- PID / Kill フラグ:
  - ExecutionEngine は起動時に PID ファイルを書きます（Settings.pid_file_path）。
  - KillSwitch は `KILL_FLAG_PATH` にフラグを書き、ExecutionEngine 側で検知して安全に停止する想定です。
- Paper Trading:
  - Paper モードでは mock ブローカーを用いて本番 DB と完全分離します（PAPER_TRADING_SQLITE_PATH を使用）。
  - PAPER_FILL_MODE により約定挙動を制御できます（instant / partial / never / reject）。
- OpenAI 関連:
  - LLM 呼び出しはリトライ・バックオフ・レスポンス検証を行いますが、API キー・料金には注意してください。
  - レスポンスは JSON mode を利用して厳密な JSON を期待していますが、冗長テキストが混ざった場合の復元処理も実装しています。
- ログ:
  - スクリプトは標準 logging を使用します。必要に応じて logging.basicConfig を置き換えてログ出力先やフォーマットをカスタマイズしてください。

## ディレクトリ構成
主要ファイル・ディレクトリの概要（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動読込）
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 永続化層（監視テーブル）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他：broker_factory, execution_engine, order_repository 等 — 実装一部)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (想定)
    - kabusys.duckdb (DuckDB)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite, paper mode)

（実際のリポジトリでは上記に加えて data / docs / tests 等が存在する場合があります）

## 開発・拡張のヒント
- DuckDB によるファクター計算は SQL と Python を組み合わせて効率的に行えるよう設計されています。prices_daily / raw_financials 等のテーブルが前提です。
- AI 連携部分は外部サービス依存があるため、ユニットテストでは _call_openai_api をモックすることを推奨します（コード中でもその想定で実装）。
- position_sizing / risk_adjustment 等は純粋関数で副作用がないためユニットテストが容易です。
- モニタリングや KillSwitch により安全停止・アラートを行う設計になっています。運用時は alert_manager の LINE 通知設定やクールダウンに留意してください。

---

この README はコードベースから主要点を抜粋してまとめた概観です。詳細な API や実行時の振る舞いは各モジュールの docstring を参照してください。必要であれば、セットアップ用の requirements.txt / dockerfile / systemd ユニットファイルのテンプレート作成等も支援します。