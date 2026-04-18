# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README（日本語）。

この README はコードベースの主要な機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買インフラ／ライブラリ群です。  
主な目的は以下：

- 戦略による銘柄選定・配分・株数決定（ポートフォリオ構築）
- 注文の発行・管理（ExecutionEngine、OrderManager 等）
- 監視（System / Trade / Risk の監視／アラート／Kill Switch）
- 研究用ユーティリティ（ファクター計算、特徴量探索）
- ニュースを使った NLP スコアリング（OpenAI を利用）
- ペーパートレード（本番 DB と分離して動作可能）
- レポート生成（Paper Trading 検証レポート）  

設計方針として、可能な限り副作用を抑え、DB（SQLite / DuckDB）を用いた永続化と、ライブラリ関数群（純粋関数）による再現性を重視しています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine による注文実行ワークフロー
  - 実運用（live）／ペーパートレード（paper_trading）切替（環境変数 KABUSYS_ENV）
  - RiskManager（ポジション上限、ドローダウン等）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス生存確認
  - TradeMonitor: 注文滞留・約定異常等の検出
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringEngine: 各 Monitor のポーリング統合
- Portfolio（純粋関数）
  - 銘柄選定（select_candidates）
  - 重み計算（等分・スコア加重）
  - ポジションサイズ計算（allocation メソッド複数）
  - セクターキャップ適用、レジーム乗数
- Research
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - news_nlp.score_news: OpenAI を用いたニュースのセンチメント → ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して日次レジーム判定
- Tools
  - paper_verification_report: ペーパートレード検証レポート生成
- 設定支援
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env / config/*.yaml の起動前検証

---

## 前提（依存関係）

最低限の依存パッケージ（主要）：

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能使用時)
- PyYAML（validate_config の YAML 検証を有効にする場合）

インストール例（プロジェクト配下で）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（実運用では requirements.txt を用意して管理することを推奨します）

---

## 環境変数（主要）

config_setup にある項目・config.py で参照される環境変数の一覧（主なもの）：

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用、任意）
- KILL_FLAG_CLEAR_ON_START（起動時に kill flag をクリアするか。デフォルト: 0）

その他：
- MONITOR_POLL_INTERVAL（run_monitoring でポーリング間隔を秒で上書き、デフォルト 60）
- PAPER_FILL_MODE（ペーパートレード時の約定モード: instant|partial|never|reject）

注意: .env を作る際は機密情報を含むため Git にコミットしないでください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb psutil openai PyYAML
   # 必要に応じて他パッケージを追加
   ```

4. .env を作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザード終了後、`.env` が生成されます。

5. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data logs
   ```

---

## 使い方（実行方法・主要スクリプト）

いくつかの主要な起動スクリプトと使い方を示します。

- ExecutionEngine を起動（本番 or ペーパートレードは KABUSYS_ENV に依存）
  ```bash
  # 環境変数をセットしてから
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  特記事項:
  - paper_trading の場合、MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在したら起動せず終了します。
  - 実行はスレッドで行われ、同じく data/stop_requested.flag を置くことで停止を通知できます。
  - PID ファイルはデフォルトで data/execution.pid。

- Monitoring を起動（ポーリング）
  ```bash
  # ポーリング間隔を上書きする場合:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  特記事項:
  - Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
  - 停止はプロジェクトルート data/stop_requested.flag を作成することで行います。

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ライブラリ API 使用例（ニュース NLP を手動で呼ぶ例）
  ```python
  # スクリプト例: score_news を直接呼ぶ
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect('data/kabusys.duckdb')
  n_written = score_news(conn, target_date=date(2026, 4, 10), api_key='sk-...')
  print("書き込んだ銘柄数:", n_written)
  conn.close()
  ```

---

## ロギング / ファイル・フラグについて

- ログ
  - ログは kabusys.utils.logging_setup.setup_logging により設定されます。
  - デフォルトログディレクトリ: logs/
  - アプリ名別に logs/<app_name>.log（日次ローテーション、30日保持）

- フラグ / PID
  - 停止要求（外部から監視や実行を止めたい時）: data/stop_requested.flag
  - Kill Switch（自動停止判定）: data/kill.flag
  - PID ファイル（ExecutionEngine）: data/execution.pid (デフォルト)
  - 設定でパスは上書き可能（Settings.pid_file_path, Settings.kill_flag_path）

---

## 主要ディレクトリ構成

リポジトリの主要モジュール構成（概略）:

- src/kabusys/
  - __init__.py
  - config.py            — 環境変数 / Settings 管理
  - config_setup.py      — .env 対話ウィザード
  - validate_config.py   — 起動前チェック CLI
  - run_execution.py     — ExecutionEngine 起動スクリプト
  - run_monitoring.py    — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py         — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py  — 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py    （アラート送信の実装がある場合）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記はコード内ファイルを抜粋したものです。細かいファイルはリポジトリをご確認ください）

---

## 運用上の注意 / ベストプラクティス

- 本番環境 (KABUSYS_ENV=live) 設定時は LINE 通知や KILL スイッチの設定を入念に確認してください。validate_config は live 用のガードチェックを含みます。
- 機密情報（APIキー等）は .env に格納し、絶対に Git へコミットしないでください。
- Monitoring は本番の監視 DB を直接操作します。テストやローカル検証では KABUSYS_ENV=paper_trading を使い、paper_trading 用 DB（data/paper_trading.db）を利用してください。
- OpenAI を使う機能は API レート制限やコストが発生します。API キーの管理と呼び出し頻度に注意してください。

---

## 開発者向けメモ

- 設計は「DB 参照は明示的に」「ライブラリは副作用を抑える」を意識しています。戦略や研究用の関数群は純粋関数化されています（テストしやすい）。
- 外部 API 呼び出しはリトライ／バックオフを備えています（news_nlp, regime_detector）。
- DuckDB は分析用途（prices_daily / raw_financials 等）に使われ、SQLite は監視 / 取引ログ用に使われます。

---

必要に応じて README を拡張します（例: CI / テスト手順、requirements.txt の追加、データベース初期化スクリプト、デプロイ手順など）。ほかに追記したい項目があれば教えてください。