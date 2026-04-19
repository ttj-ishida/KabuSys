# KabuSys

日本株向け自動売買システムのライブラリ/実行スクリプト群です。  
このリポジトリは売買ロジック（ポートフォリオ構築・ポジションサイズ計算等）、研究用ファクター計算、AI を使ったニュースセンチメント評価、監視（Monitoring）周りのユーティリティを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件 / 依存パッケージ
- セットアップ手順
- 使い方（実行方法）
- 主要環境変数
- ファイル / ディレクトリ構成（抜粋）
- 運用上の注意

---

## プロジェクト概要

KabuSys は以下の目的で構成された Python ベースのモジュール群です。

- 戦略のためのファクター計算（DuckDB 経由で prices_daily / raw_financials を参照）
- ポートフォリオ構築（候補選定・重み計算）とポジションサイズ算出
- Paper Trading（模擬発注）を含む ExecutionEngine（発注・注文管理・リスク管理）
- 監視（System/Trade/Risk）と Kill Switch（停止フラグ）の実装
- ニュースセンチメント評価（OpenAI を用いた NLP）
- 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証、レポート生成）

コードは src/kabusys 以下に格納されており、複数の実行用スクリプト（モジュール）を提供します。

---

## 主な機能一覧

- portfolio
  - 候補選定（select_candidates）
  - 等金額/スコア加重配分（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）: 単元株丸め・aggregate cap 等を実装
  - セクター上限適用、レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- research
  - momentum / volatility / value ファクター計算（DuckDB）
  - 将来リターン計算、IC 計算、統計サマリ
- ai
  - ニュース NLP による銘柄単位センチメント算出（OpenAI）
  - 市場レジーム判定（ETF MA + LLM マクロセンチメント合成）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor：DB にログ保存しチェック・アラート生成
  - KillSwitch：drawdown やポジション上限で kill.flag を書き、ExecutionEngine に停止を促す
  - MonitoringEngine：各 Monitor を定期実行してアラート処理・KillSwitch 評価
- utils
  - ロギングセットアップ（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定（psutil ベース）
- ツール
  - 環境設定ウィザード（config_setup）
  - 起動前の設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）

---

## 必要条件 / 依存パッケージ

- Python 3.10 以上（PEP 604 の | 型表記等を使用）
- 必須（機能利用時）:
  - duckdb
  - psutil
- AI 機能を使う場合:
  - openai（OpenAI の Python SDK）
- optional:
  - PyYAML（config/*.yaml の構文チェックに使用。なければ警告を出してスキップ）

インストール例（仮の requirements がある場合）:
```bash
python -m pip install duckdb psutil openai PyYAML
```

（requirements.txt がない場合は上記のパッケージを個別にインストールしてください）

---

## セットアップ手順

1. ソースを取得して、仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb psutil openai PyYAML
   ```

3. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードに従って J-Quants トークン、kabu API パスワード等を設定してください。
   - 生成された .env は絶対に Git にコミットしないでください。

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 厳格モード（警告も失敗扱い）:
   python -m kabusys.validate_config --strict
   ```

5. 必要なデータディレクトリ（data）やログディレクトリ（logs）は自動作成されますが、権限に注意してください。

---

## 使い方（実行方法）

プロジェクトはモジュールとして実行できます。パッケージルートが PYTHONPATH に含まれているか、プロジェクト直下で実行してください。

- 監視ループ（SystemMonitor を定期実行）
  - デフォルトポーリング間隔: 60 秒
  - 環境変数で上書き: MONITOR_POLL_INTERVAL（秒）
  ```bash
  python -m kabusys.run_monitoring
  # 例: 30秒間隔に変更
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 注意: Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用します。

- ExecutionEngine（発注エンジン）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは data/paper_trading.db に記録されます（本番 DB と分離）。
  ```bash
  # 本番環境相当
  KABUSYS_ENV=live python -m kabusys.run_execution

  # ペーパートレード
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - ExecutionEngine 起動時・稼働中は data/execution.pid や data/stop_requested.flag の扱いに注意してください。
  - 停止シグナル: data/stop_requested.flag（作成されると監視/実行ループが終了します）

- .env 管理
  ```bash
  python -m kabusys.config_setup      # 対話式ウィザードで .env を作成/更新
  python -m kabusys.validate_config  # 起動前に設定を検証
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report \
      --from 2026-04-01 --to 2026-04-11 \
      --db path/to/paper_trading.db
  ```
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / NLP 機能
  - OpenAI API を利用する機能（ai.news_nlp / ai.regime_detector）は OPENAI_API_KEY を環境変数に設定するか、関数呼び出し時に api_key を渡してください。
  - 例: score_news をライブラリから使う場合は DuckDB 接続と target_date を渡します。

---

## 主要環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

設定例 / 任意:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- PAPER_FILL_MODE — ペーパートレードにおける fill モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=クリア、0=しない。default 0、本番では 0 推奨）

参考: .env は config_setup で生成できます。

---

## ディレクトリ構成（主なファイル / モジュール）

ルート（src/kabusys）内の主要構成:

- kabusys/__init__.py
- kabusys/config.py
- kabusys/config_setup.py      — .env 対話式ウィザード
- kabusys/validate_config.py   — 設定検証 CLI

- run scripts
  - kabusys/run_monitoring.py   — SystemMonitor ポーリングループ起動
  - kabusys/run_execution.py    — ExecutionEngine 起動

- ai/
  - news_nlp.py                 — ニュースの LLM スコアリング
  - regime_detector.py          — レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py            — SQLite テーブル初期化 + DB ラッパー
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (存在する場合)
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py            — 共通ログ設定（stdout + 日次ローテート）
  - process_priority.py         — psutil を使った優先度設定

（上記は抜粋です。実際のファイル群は src/kabusys 以下を参照してください）

---

## 運用上の注意 / 補足

- DB 初期化
  - monitoring の SQLite スキーマは run_monitoring / run_execution 実行時に自動で作成・マイグレーションされます（init_monitoring_db）。
  - DuckDB 側はファクター計算や AI 処理で利用するテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）を事前に用意する必要があります。

- ログ
  - ログは stdout とファイル（logs/<app_name>.log）に出力され、日次ローテーションされます。LOG_DIR で変更可能です。

- プロセス優先度
  - run_monitoring / run_execution は起動時に set_process_priority("high") を呼びます。psutil の権限不足で失敗する場合は警告が出てスキップされます。

- Kill Switch / Stop フラグ
  - KillSwitch（data/kill.flag）はリスク条件により ExecutionEngine を停止させるためのフラグです。ExecutionEngine は stop フラグや stop_requested.flag を監視して安全に停止します。実運用では KILL_FLAG_CLEAR_ON_START の設定に注意してください（本番では自動クリアは推奨されません）。

- AI 呼び出しのリトライ
  - OpenAI 呼び出しはレートリミット・一時エラーに対して指数バックオフでリトライしますが、API キーや料金、レート制限に注意して運用してください。

- テスト・開発
  - KABUSYS_ENV=development の場合は発注処理は行われない（もしくは安全措置がある）想定です。ペーパートレードは完全に本番 DB と分離されます。

---

もし README に追加してほしい具体的な情報（例: 実際の設定例ファイル、詳細な起動スクリプト内引数仕様、DuckDB テーブルスキーマ定義、ExecutionEngine の API 仕様など）があれば教えてください。必要に応じてサンプル .env やよくあるトラブルシューティングも追記します。