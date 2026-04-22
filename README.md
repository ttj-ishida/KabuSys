# KabuSys

日本株自動売買システムの軽量実装（ライブラリ / 起動スクリプト / 各種ユーティリティ群）

この README はリポジトリ内の主要コンポーネントの概要、セットアップ方法、使い方、及びディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の主要機能を提供するモジュール群です。

- 取引エンジン起動スクリプト（ExecutionEngine）
- 運用監視（Monitoring）およびアラート / Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチ（ファクター計算 / 特徴量探索）
- AI 補助（ニュースセンチメント解析 / レジーム判定。OpenAI を利用）
- 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証）
- ペーパートレード用の検証レポート生成ツール

設計方針として、DB（SQLite / DuckDB）を永続化層 / 分析層として利用し、AI 関連処理は外部 API（OpenAI）にアクセスします。実行環境は環境変数や `.env` で制御します。

---

## 主な機能一覧

- Execution
  - 起動スクリプト: `kabusys.run_execution`
  - Paper trading 時は MockBrokerClient を使用し、paper_trading 専用 DB を使用して本番 DB と分離
  - プロセス優先度設定（high）・PID ファイル管理・停止フラグ検知

- Monitoring
  - 起動スクリプト: `kabusys.run_monitoring`
  - System / Trade / Risk の監視コンポーネントを束ねて定期ポーリング
  - Kill Switch（条件により data/kill.flag を書き込む）
  - 監視ログを SQLite（monitoring.db）に永続化

- Portfolio（純粋関数群）
  - 候補選定（score 順）
  - 等金額 / スコア加重の重み算出
  - ポジションサイズ算出（risk-based 等）、単元株丸め、aggregate cap 調整
  - セクター上限適用、レジーム乗数

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials テーブル参照）
  - 将来リターン / IC 計算 / 統計サマリ

- AI
  - ニュース NLP（OpenAI）による銘柄別センチメント取得 → ai_scores へ保存
  - レジーム判定（ETF MA とマクロセンチメントの合成）

- ツール
  - 設定ウィザード: `kabusys.config_setup`（対話式で .env を生成）
  - 設定検証: `kabusys.validate_config`（.env と config/*.yaml の検証）
  - Paper Trading レポート: `kabusys.tools.paper_verification_report`

- ユーティリティ
  - ロギング初期化（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定（psutil ベース）
  - DB 初期化 / マイグレーション補助

---

## 必要条件（依存関係）

主な依存パッケージ（例）:

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config の内容検証を行う場合、必須ではない）
- （お使いの環境に応じて）その他利用する Broker クライアントのライブラリ等

インストール例（仮想環境推奨）:
```
pip install duckdb psutil openai pyyaml
```

※ 実行環境に応じて追加の依存が必要な場合があります。

---

## 環境変数・設定 (.env)

このプロジェクトは環境変数（あるいは `.env`）から設定を読み込みます。プロジェクトルート（.git / pyproject.toml があるディレクトリ）を自動的に探索して `.env` / `.env.local` を読み込みます（無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

重要な環境変数（主要なもの）:
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY （AI 機能を使う場合）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
- PAPER_FILL_MODE: instant | partial | never | reject（paper trade の約定挙動）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、既定 60）

簡易 `.env` サンプル（.env は絶対に Git にコミットしないでください）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_pass_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

設定ウィザードを使うと `.env` を対話式に生成できます（下記参照）。

---

## セットアップ手順

1. リポジトリをチェックアウト / クローン
2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   ※ requirements.txt がない場合は前節の主要パッケージを個別にインストールしてください:
   ```
   pip install duckdb psutil openai pyyaml
   ```
4. 環境変数を用意
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     これで `.env` を生成・更新できます。
   - または手動で `.env` を作成（上記サンプル参照）
5. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   ```
   - 警告も失敗としたい場合:
     ```
     python -m kabusys.validate_config --strict
     ```
6. 初期 DB 周り
   - 実行スクリプト（monitoring / execution）が起動時に必要テーブルを作成します。事前に手動作成は不要です。

---

## 使い方（起動・主要スクリプト）

- ExecutionEngine（取引エンジン）起動:
  ```
  python -m kabusys.run_execution
  ```
  - 起動時にプロセス優先度を "high" に設定します。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 停止方法:
    - モニタ側が kill.flag を書き込むと停止する仕組みがあります（Kill Switch）。
    - また、プロジェクトの data/stop_requested.flag が存在すると起動を抑止・停止処理を行います。
  - PID ファイル: data/execution.pid（デフォルト）

- Monitoring（監視ループ）起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（既定 60 秒）。
  - Monitoring は環境にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを書きます。
  - 停止方法:
    - data/stop_requested.flag（スクリプトの親階層 data/stop_requested.flag）を置くとループを抜けます。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート出力（SQLite DB のパスを指定可）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定してから、該当モジュールを呼び出してください（例はライブラリ関数を通して使用）。
  - 例: kabusys.ai.score_news(conn, target_date) など（DuckDB 接続を渡す）

---

## ログ / 実行ファイル出力

- ログ初期化は共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を通して行われます。
- デフォルトログディレクトリ: `logs/`
- ログファイル名: `logs/<app_name>.log`（`run_execution` 起動時は app_name=`execution`、`run_monitoring` は `monitoring`）
- ローテーション: 日次、30日分保持
- 権限やディレクトリ作成に失敗した場合はコンソール（stdout）出力のみで継続します。

---

## 停止 / Kill Switch / フラグファイル

- 停止抑止/要求用フラグ:
  - data/stop_requested.flag — run_* スクリプトが監視している停止フラグ
  - data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine を停止させる目的）
- KillSwitch は RiskMonitor の結果等に基づき理由を記述して `kill.flag` を作成します。既存の kill.flag がある場合は再書き込みしません（冪等）。

---

## ディレクトリ構成（主要ファイル抜粋）

リポジトリ内の主な構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity
  - execution/                       — 実行エンジン関連（Engine, OrderManager, BrokerFactory 等）
    - (Engine, OrderManager, RiskManager 等の実装ファイル)
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層（テーブル初期化・読み書き）
    - system_monitor.py             — システム / データ鮮度監視
    - trade_monitor.py              — 注文 / 約定監視（省略ファイルあり）
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - kill_switch.py                — Kill Switch 実装
    - monitoring_engine.py          — 複数モニタを束ねるエンジン
    - alert_manager.py              — 通知管理（LINE など）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                    — ニュース NLP / OpenAI 呼び出しラッパー
    - regime_detector.py             — レジーム判定
  - tools/
    - paper_verification_report.py   — ペーパートレード検証レポート生成
  - data/                            — 実行時生成される DB / フラグ / PID 等（git 管理外にすること）

（実際のファイル一覧はリポジトリの tree を参照してください）

---

## 注意事項 / トラブルシューティング

- .env は秘密情報を含むため絶対に Git にコミットしないでください。
- Monitoring は監視用 DB（SQLITE_PATH）に常に書き込みます。paper_trading 環境でも監視 DB は本番のパスを使う設計です（実装上の注意）。
- Execution は KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用するため、本番用データと分離されます。
- OpenAI API を使う機能を実行するには OPENAI_API_KEY が必須です。設定されていないと例外が出ます。
- ログディレクトリの作成に失敗した場合はファイルログが無効になり、標準出力のみになります（警告ログが出ます）。
- MONITOR_POLL_INTERVAL は正の整数で指定してください。0 以下や不正文字列を指定するとデフォルト（60 秒）にフォールバックします。
- `psutil` によるプロセス優先度設定は OS により制限される場合があります（権限不足時は警告が出ます）。

---

## 開発 / 貢献

- 設定検証や対話式ウィザードを活用して、まずはローカルの `development` 環境で動作確認を行ってください。
- Paper Trading で動作確認 → Paper トレードのログ / レポートで検証 → 問題なければ live 環境へ移行する、という段階的な運用を推奨します。
- バグ報告 / プルリクエストはリポジトリの ISSUE / PR を利用してください。テストの追加やドキュメント改善歓迎します。

---

この README はコードベースの主要点をまとめたものです。より詳細な仕様（StrategyModel.md や PortfolioConstruction.md 等）がリポジトリ内にある場合はそちらも参照してください。必要があれば README の追記や起動手順のサンプル systemd / pm2 / supervisor の設定例も作成します。必要なら教えてください。