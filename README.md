# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ + 実行スクリプト群）

この README はコードベース（src/kabusys）を元にした概要、機能、セットアップ、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は、日本株自動売買のためのモジュール群と起動スクリプトを含むプロジェクトです。主な目的は以下：

- マーケットデータ（DuckDB）を使ったリサーチ・ファクター計算
- ポートフォリオ構築（銘柄選定、配分、ポジションサイズ計算）
- 実行エンジン（ExecutionEngine）による（実環境／ペーパートレード）発注処理
- 監視コンポーネント（System / Trade / Risk）のポーリングとアラート
- LLM（OpenAI）を使ったニュースセンチメント評価・市場レジーム判定
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針として、実行ロジックと DB・IO を分離し、テストしやすい純粋関数（ポートフォリオ／リサーチ系）を提供しています。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートを検出して .env / .env.local を読み込む）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行（Execution）
  - ExecutionEngine を起動するランチャ（python -m kabusys.run_execution）
  - 本番 / ペーパートレードの分離（KABUSYS_ENV による）
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - リスク管理モジュール（RiskManager）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring スクリプトによる定期ポーリング（python -m kabusys.run_monitoring）
  - 監視ログの永続化（SQLite）と簡易ダッシュボードテーブル
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止シグナル
- ポートフォリオ構築
  - 候補選定（score / rank ベース）
  - 重み計算（等分配・スコア加重）
  - ポジションサイズ計算（risk_based / equal / score、単元株丸め、集約上限処理）
  - セクター上限・レジーム調整
- リサーチ / 解析
  - Momentum / Volatility / Value 等のファクター計算（DuckDB による SQL 実行）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）連携
  - ニュースのセンチメント評価（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
  - API 呼び出しは冗長性を保つ設計（リトライ、部分失敗保護）
- 運用ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

1. Python 環境準備
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化（venv / pyenv 等）

2. 依存パッケージをインストール
   - 代表的な依存：
     - duckdb
     - psutil
     - openai
     - （検証用）PyYAML は任意（validate_config の YAML 検証に使用）
   - 例:
     - pip install duckdb psutil openai
     - （必要に応じて）pip install pyyaml

   ※ pyproject.toml / requirements.txt がある場合はそちらを使用してください。

3. リポジトリルートに移動（.git または pyproject.toml を基に自動検出されます）

4. .env の作成
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - あるいはテンプレートを参考に手動で作成（例）:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-...
   - 注意: .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います。

6. データディレクトリ作成（自動作成されることもありますが事前に作っておくと安全）
   - mkdir -p data logs

---

## 使い方（主要コマンド）

- ExecutionEngine 起動（本番 / ペーパー区別は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - Execution は data/execution.pid に PID を書きます（設定で変更可）。

- Monitoring ポーリング開始
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は常に production 用の sqlite_path を使用して監視ログを書きます（環境にかかわらず）。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ライブラリとしての利用例（Python スクリプト内）:
  - ポートフォリオ関数利用:
    from kabusys.portfolio import (
        select_candidates, calc_equal_weights, calc_score_weights,
        calc_position_sizes, apply_sector_cap, calc_regime_multiplier
    )
  - AI スコアリング（例）:
    from kabusys.ai.news_nlp import score_news
    # DuckDB 接続を渡して score_news(conn, target_date, api_key=...)
  - リサーチ関数:
    from kabusys.research import calc_momentum, calc_volatility, calc_value

- Kill Switch / 停止フラグ
  - 実行停止させたい場合は data/kill.flag を作成（内容は理由の文字列）。
  - monitoring は Kill Switch を評価し、必要時に Execution 停止を促します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされます（本番では危険なので 0 推奨）。

---

## 動作上の注意点・設定の概要

- KABUSYS_ENV: 実行モード
  - 有効値: development | paper_trading | live
  - paper_trading: ブローカーは MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
- DB
  - DuckDB（分析用）: デフォルト data/kabusys.duckdb（Settings.duckdb_path）
  - SQLite（監視ログ）: デフォルト data/monitoring.db（Settings.sqlite_path）
  - Paper trading 用 SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
- ログ
  - デフォルトのログディレクトリ: logs/
  - 各アプリ（execution / monitoring）は logs/<app_name>.log を出力（日次ローテーション、30日保持）
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び出します（psutil 権限に依存）
- OpenAI
  - news_nlp / regime_detector は OPENAI_API_KEY（または引数）を使用します
  - API 失敗時はフェイルセーフの挙動（スコア 0.0 など）を採ります

---

## ディレクトリ構成（抜粋）

以下は src/kabusys ディレクトリの主要モジュールと目的の簡易ツリーです。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + 指標）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py
    - trade_monitor.py       — （ファイル上に定義あり）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信を担う想定）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - data/
    - pipeline.py            — prices_daily などを扱うデータパイプライン（DuckDB 参照）
    - stats.py               — 正規化ユーティリティ等
  - utils/
    - logging_setup.py
    - process_priority.py
  - research/（上記参照）

（上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## よくある運用フロー（例）

1. リポジトリをクローンして依存をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定検証
4. DuckDB / SQLite の初期データ準備（データ取得パイプラインを実行）
5. 本番テスト:
   - KABUSYS_ENV=paper_trading で python -m kabusys.run_execution
   - python -m kabusys.run_monitoring を別プロセスで起動
6. Paper Trading の検証:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 開発・拡張のヒント

- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できます。
- DuckDB を用いたリサーチ関数は副作用がなく純粋関数的なので単体テストが容易です。
- OpenAI 呼び出し部分は内部で小さなラッパー関数を呼んでいるため、テストでは該当関数をモックすることを想定しています。
- monitor / execution の停止は data/stop_requested.flag または data/kill.flag を用いる運用設計になっています。

---

必要に応じて README に追記します。特に希望する点（例: より詳細な .env のテンプレート、各コマンドのログ例、データ初期投入スクリプトの説明など）があれば教えてください。