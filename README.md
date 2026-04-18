# KabuSys

日本株自動売買システムのコアライブラリおよび起動スクリプト群です。  
このリポジトリはバックテスト/リサーチ用のモジュール、発注実行エンジン、監視・アラート機能、AI を用いたニュース評価等を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供します。

- 発注 ExecutionEngine（本番 / ペーパートレード切替対応）
- 監視サブシステム（System / Trade / Risk のモニタリング、Kill Switch）
- ポートフォリオ構築（シグナル選定・重み付け・サイズ計算・セクター制約）
- リサーチ用ファクター計算（momentum / volatility / value 等）
- AI 支援モジュール（ニュースを LLM でスコアリング、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード / 検証）
- 運用向けツール（Paper Trading 検証レポート生成）

設計方針として「リークを防ぐため実行日時の固定」「本番 DB とペーパートレード DB の分離」「フェイルセーフ（API 失敗時はスキップして続行）」が採用されています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV により本番 / ペーパートレード切替）
  - run_monitoring.py — SystemMonitor のポーリングループを実行（定期監視）
- 設定関連
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — .env / config/*.yaml 等の設定検証 CLI
  - config.Settings — 環境変数の取得・検証
- 監視
  - monitoring/monitoring_db.py — SQLite ベースの永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - monitoring/system_monitor.py — システム状態・データ鮮度監視
  - monitoring/trade_monitor.py, monitoring/risk_monitor.py, monitoring/kill_switch.py, monitoring/monitoring_engine.py
- Execution（発注）
  - execution/* — Broker クライアント生成、ExecutionEngine、OrderManager、RiskManager、Reconciler 等（本体は execution パッケージ）
- ポートフォリオ構築
  - portfolio/ — 候補選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数
- リサーチ
  - research/ — factor 計算、特徴量探索（IC / 統計サマリ）
- AI
  - ai/news_nlp.py — OpenAI を用いた銘柄別ニュースセンチメントスコアリング
  - ai/regime_detector.py — マクロ + ETF MA を用いた市場レジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例）:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要なパッケージをインストール（最低限の例）
   - 必須ライブラリ: duckdb, psutil, openai
   - 開発時に便利: PyYAML（config ファイル検証用）
   ```
   pip install duckdb psutil openai
   pip install pyyaml    # 任意（validate_config が YAML パースを行う場合）
   ```

   ※ requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

3. プロジェクトルートに .env を作成（対話式推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードが起動して .env を対話式に生成します。生成後は以下で検証してください：
   ```
   python -m kabusys.validate_config
   ```
   必須環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   推奨/任意:
   - KABUSYS_ENV（development | paper_trading | live） デフォルト: development
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（デフォルト: INFO）
   - OPENAI_API_KEY（AI 機能を使う場合）

4. データディレクトリ等の作成（.env 内のパスに応じて）
   - デフォルトで logs/、data/ を使用します。ログディレクトリは logging_setup が自動作成しますが、権限等に注意してください。

---

## 使い方（起動・主要コマンド）

- ExecutionEngine 起動（通常）
  - 本番 / ペーパートレードは KABUSYS_ENV に依存します。
  - 例（デフォルト development は発注なしの開発モード）:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード（環境変数で切替）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    - paper_trading の場合、MockBrokerClient を使い DB は data/paper_trading.db に記録され、本番 DB と完全分離します。

- Monitor（監視ループ）起動
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
    ```
    python -m kabusys.run_monitoring
    ```
    例: 30 秒間隔で動かす:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```

- .env 対話式作成
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告を FAIL 扱い
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（プログラムからの呼び出し）
  - ニューススコアリング:
    ```
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")
    ```
  - 注意: OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を利用します。

- ログ/停止フラグ等
  - PID ファイル: data/execution.pid（run_execution が使用）
  - 停止フラグ（監視ループ / エンジン停止用）: data/stop_requested.flag
  - Kill Switch（Execution 停止を指示するファイル）: data/kill.flag
  - run_monitoring は stop flag を検知するとループを抜けます。KillSwitch は条件により kill.flag を書き込みます。

---

## 実行時の注意点 / 運用メモ

- process priority: 起動スクリプトは最初にプロセス優先度を "high" に変更しようとします（psutil を利用）。権限が無い場合は警告を出して継続します。
- DB の分離: 本番用の sqlite_path とペーパートレードの paper_sqlite_path は分離されています（KABUSYS_ENV=paper_trading のみ紙トレード DB を使用）。
- ロギング: kabusys.utils.logging_setup.setup_logging を全起動スクリプトで使用し、コンソール出力（stdout）と日次ローテートファイル出力を行います。ログディレクトリは LOG_DIR 環境変数で変更可能。
- AI 呼び出し: レート制限や接続障害を考慮し、news_nlp / regime_detector はリトライやフォールバック（スコア 0.0）ロジックを含んでいます。
- データの鮮度チェック: SystemMonitor は DuckDB の prices_daily を参照してデータ鮮度を評価します。データ不足や日付設定により監視結果が変わります。

---

## ディレクトリ構成（主要ファイル）

下記は `src/kabusys/` を起点とした主要ファイル・パッケージ構成の抜粋です。

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - execution/
    - (ExecutionEngine, BrokerFactory, OrderManager, RiskManager, Reconciler, OrderRepository 等)
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (アラート送信ロジック等)
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
  - monitoring/  (上に記載)
  - tools/
    - paper_verification_report.py
    - __init__.py

プロジェクトルートに以下のような補助ファイルが存在することが想定されます:
- .env (運用環境設定)
- data/ (sqlite/duckdb 等のデータファイル, stop/kill flag, pid ファイル)
- logs/ (ログファイル)
- config/*.yaml（各種設定テンプレート）

---

## よくある質問 / トラブルシューティング

- 「.env が読み込まれない」
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定していないか確認してください。自動ロードはプロジェクトルート（.git or pyproject.toml）を基準に行われます。
- 「OpenAI 呼び出しで失敗する」
  - OPENAI_API_KEY が環境変数に設定されているか、または score_news / score_regime に api_key を渡してください。ネットワーク・レート制限時は内部でリトライを行いますが、上限を超えるとスキップされます。
- 「ログファイルが作成されない」
  - ログディレクトリに書き込み権限があるか確認してください。ログディレクトリの作成に失敗した場合、ファイル出力は無効化されコンソールのみ出力になります。

---

必要に応じて README の補足（インストール要件の pin、例 .env.example、運用手順書、ユニットテスト実行方法など）を追加できます。どの情報を優先的に追加したいか教えてください。