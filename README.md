# KabuSys

KabuSys は日本株向けの自動売買支援システム（ライブラリ＋起動スクリプト群）です。  
本リポジトリには取引エンジン起動スクリプト、監視・アラート、ポートフォリオ構築ロジック、リサーチ／ファクター計算、LLM を用いたニュース NLP 等のモジュールが含まれます。

バージョン: 0.1.0

---

## 概要

- 実取引（live）・ペーパートレード（paper_trading）・開発（development）を環境切替して動作可能
- ExecutionEngine（発注/注文管理/リスク管理）と Monitoring（システム監視 / Kill Switch / アラート）を分離して起動
- DuckDB を用いたリサーチ（ファクター計算・特徴量解析）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（ai/news_nlp）および市場レジーム判定（ai/regime_detector）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- 運用補助ツール：.env 対話式ウィザード、設定検証、ペーパートレードの検証レポート生成 など

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（KABUSYS_ENV により paper_trading 用のモックブローカーを使用）
  - run_monitoring.py — SystemMonitor ポーリングループ（MONITOR_POLL_INTERVAL で間隔制御）
- 環境設定 / 検証
  - config_setup.py — 対話式に .env を生成 / 更新
  - validate_config.py — .env / config/*.yaml の静的検証（--strict オプションあり）
- 監視
  - monitoring/monitoring_db.py — SQLite ベースの監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタ
  - monitoring/kill_switch.py — 条件により data/kill.flag を書き込み ExecutionEngine を停止させる仕組み
  - monitoring/monitoring_engine.py — 各モニタを束ねるポーリングエンジン
- 発注 / 実行（エンジン本体は execution パッケージ）
  - BrokerClientFactory により実際のブローカー or Mock を選択
  - RiskManager, OrderManager, Reconciler, ExecutionEngine 等で発注制御・リスク管理
- リサーチ / ファクター計算
  - research/factor_research.py — Momentum, Value, Volatility, Liquidity 等のファクター計算（DuckDB 経由）
  - research/feature_exploration.py — 将来リターン計算、IC（Information Coefficient）、統計サマリ
- ポートフォリオ構築
  - portfolio/portfolio_builder.py — 候補選定・重み付け
  - portfolio/position_sizing.py — 株数計算（リスク制御・単元丸め・キャップ）
  - portfolio/risk_adjustment.py — セクター上限・レジーム乗数
- AI（LLM）連携
  - ai/news_nlp.py — ニュース記事を集約し OpenAI に投げて銘柄ごとのセンチメントを ai_scores に書き込む
  - ai/regime_detector.py — ETF MA とマクロニュースの LLM 評価を合成して market_regime を判定
- ユーティリティ
  - utils/logging_setup.py — 統一的なログ設定（stdout + 日次ローテーション）
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - tools/paper_verification_report.py — ペーパートレードの検証レポート生成（稼働率 / 成功率 / レイテンシ等）

---

## 前提 / 依存関係

- Python 3.10 以上（PEP 604 の型記法 などを使用）
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml を検証したい場合）
- 標準で利用する DB: SQLite（組み込み）、DuckDB（パッケージ）
- 実行環境に応じて kabuステーション API 等の外部接続が必要（本番での利用時）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
注: requirements.txt はリポジトリに含めていない場合があります。プロジェクト固有のバージョン管理がある場合はそちらに従ってください。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb psutil openai pyyaml
   ```

4. 対話式に .env を作成／更新
   ```bash
   python -m kabusys.config_setup
   ```
   - J-Quants トークンや KABU_API_PASSWORD、KABUSYS_ENV（development / paper_trading / live）などを入力します。
   - 生成される .env は絶対に公開リポジトリにコミットしないでください。

5. 設定検証
   ```bash
   python -m kabusys.validate_config        # 警告は出るが exit 0
   python -m kabusys.validate_config --strict  # 警告を fail として exit 1
   ```

6. データディレクトリ / ログディレクトリの確認（必要なら作成）
   - デフォルト DB / ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
     - PID / kill flag: data/execution.pid, data/kill.flag
   - これらのパスは環境変数で上書きできます（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR）。

---

## 使い方

- ExecutionEngine を起動（本番 / paper_trading / development は KABUSYS_ENV で制御）
  ```bash
  # ペーパートレードで起動する例
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に取引ログを記録し、本番 DB（monitoring.db）とは分離されます。
  - 実行中、data/stop_requested.flag を作成すると起動中のループにより優雅に停止処理が行われます。

- Monitoring を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。

- 停止 / Kill Switch
  - Kill Switch は監視コンポーネント（RiskMonitor 等）が条件を満たした場合に data/kill.flag を書き込みます。ExecutionEngine は起動時にこのフラグの有無やループ中の flag をチェックし、検出されれば停止します。
  - 手動で停止フラグを検出させたい場合は data/stop_requested.flag を作成します（run_monitoring/run_execution が検知します）。

- ペーパートレード検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定するか、`--db` オプションで指定できます。
  - 出力には稼働率、注文成功率、送信率、P95 レイテンシなどが含まれます。

- AI / ニューススコアリング（ライブラリ呼び出し例）
  - DuckDB 接続を用意し、ライブラリ関数を呼ぶことでニューススコアを生成できます。
    - 例: kabusys.ai.score_news(conn, target_date, api_key=...)
    - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を利用

---

## 主要設定（環境変数）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring)（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（ai/*.py が利用）

（.env は config_setup.py で対話的に作成できます）

---

## ディレクトリ構成（抜粋）

以下はソースツリー（src/kabusys）内の主なファイル／ディレクトリです（完全な一覧ではありません）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite DB スキーマと永続化 API
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py       — （trade_monitor 実装あり）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信管理: LINE 等）
  - execution/               — ExecutionEngine, OrderManager, BrokerFactory 等（主要ロジック）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py

---

## 運用上の注意 / 重要な挙動

- Monitoring はデフォルトで本番用の sqlite_path（SQLITE_PATH）を使用します。監視ログは環境にかかわらず本番 DB に書き込まれる点に注意してください。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合、paper_trading 用の別 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と完全に分離します。
- ログは stdout と日次ローテートされたファイル（logs/<app_name>.log）へ出力されます。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみとなります。
- Kill Switch（監視により自動的に停止フラグを立てる）は強力な操作です。本番環境では KILL_FLAG_CLEAR_ON_START などの設定値に注意してください（config_setup にて設定可能）。
- OpenAI API の呼び出しはエラー時にリトライやフォールバックを行う実装ですが、API キーや利用料金には注意してください。

---

## 開発 / デバッグのヒント

- ロギングレベルを DEBUG にして詳細ログを確認する:
  ```bash
  export LOG_LEVEL=DEBUG
  python -m kabusys.run_monitoring
  ```
- 設定ファイルの問題や足りない環境変数は `python -m kabusys.validate_config` で事前検出できます。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- テスト時は OpenAI 呼び出し等をモック化して副作用を防ぐことを推奨します（各モジュール内で外部呼び出しをまとめているため差し替えが容易です）。

---

この README はコードベースの主要点を要約したものです。各モジュールの詳細な挙動や API 仕様はソースコメント（docstring）を参照してください。必要があれば起動手順や設定例（.env.example 形式）の追加を行いますので、その旨をお知らせください。