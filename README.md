# KabuSys

日本株向けの自動売買システム（ライブラリ兼起動スクリプト群）。

このリポジトリは発注エンジン、監視・アラート、ポートフォリオ構築・サイズ計算、リサーチ（ファクター計算）、AI を用いたニュースセンチメント評価などを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は以下を目的とした内部向け自動売買基盤です。

- 戦略に従った銘柄選定・配分・株数決定（ポートフォリオ構築）
- 発注実行（本番 / ペーパートレード切替）
- 実行系の監視（システム状態、注文状態、リスク監視、Kill Switch）
- DuckDB / SQLite を用いたデータ格納とリサーチ処理
- OpenAI を利用したニュース NLP（センチメント）および市場レジーム判定
- ペーパートレードの検証レポート生成

設計方針の一部：
- DB（DuckDB / SQLite）を主体に計算・永続化
- 本番とペーパートレードは DB を分離
- LLM 呼び出しはフェイルセーフ（失敗しても例外伝播せず続行する設計が多い）
- .env による設定管理と対話式ウィザード・検証ツールを提供

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（本番 / paper_trading 切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動
- 設定管理
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - config.Settings — 環境変数ラッパ
- ポートフォリオ構築
  - portfolio.select_candidates / calc_equal_weights / calc_score_weights
  - position_sizing.calc_position_sizes
  - risk_adjustment.apply_sector_cap / calc_regime_multiplier
- 実行系（概要）
  - broker_factory, execution_engine, order_manager, risk_manager, reconciler 等（実装ファイル群）
- 監視系
  - monitoring_engine, system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_db
- AI モジュール
  - ai.news_nlp.score_news — ニュースを LLM でスコア化して ai_scores に保存
  - ai.regime_detector.score_regime — マクロ + ETF MA によるレジーム判定
- リサーチ
  - research.factor_research（Momentum / Volatility / Value 等の計算）
  - research.feature_exploration（将来リターン計算 / IC 等）
- ツール
  - tools.paper_verification_report — ペーパートレード検証レポート
- ユーティリティ
  - utils.logging_setup — 統一的ログ設定
  - utils.process_priority — プロセス優先度 / CPU affinity 設定

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.10+ を推奨

1. リポジトリをクローンして作業ディレクトリに移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate.bat  # Windows
   ```

3. 必要なパッケージをインストール
   - このリポジトリ内に requirements.txt がなければ、最低限以下を入れてください:
     - duckdb, psutil, openai, PyYAML（検証用）
   ```bash
   pip install duckdb psutil openai pyyaml
   ```
   （実環境では追加の依存やバージョン固定が必要になる可能性があります）

4. .env を作成
   - 対話式ウィザードで作る:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（.env.example を参考に）。`.env` は絶対に Git にコミットしないでください。

5. 設定を検証
   ```bash
   python -m kabusys.validate_config     # 警告は表示されるが exit 0
   python -m kabusys.validate_config --strict  # 警告も失敗扱い（exit 1）
   ```

6. データディレクトリ確認
   - デフォルトでは `data/` に SQLite / PID / フラグファイルが置かれます。必要なら予めディレクトリを作成してください。
   - ログはデフォルトで `logs/` に出力されます。

---

## 主要な環境変数（抜粋）

必須（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要オプション
- KABUSYS_ENV — execution モード: development / paper_trading / live （デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時）
- PAPER_FILL_MODE — ペーパートレードでの擬似約定モード（instant/partial/never/reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch フラグファイル（data/kill.flag 等）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（"1" で有効、開発用）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

（詳細は `kabusys.config.Settings` を参照）

---

## 使い方

### 起動スクリプト（CLI）

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV で切替）
  ```bash
  python -m kabusys.run_execution
  ```
  - 実行時に `data/stop_requested.flag` が存在すると起動しません。
  - 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると kill.flag を自動クリアします（本番では非推奨）。

- Monitoring（システム監視）を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず本番の `SQLITE_PATH` を使用して監視テーブルを書き込みます。

- .env ウィザード（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` を省略すると `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db` を参照します。

### ライブラリ機能（プログラムから呼ぶ例）

- ニューススコアリング（例）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
  print("書き込んだ銘柄数:", written)
  ```

- レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  written = score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```

- リサーチ関数例（モメンタム）
  ```python
  from datetime import date
  from kabusys.research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,4,10))
  ```

- ポートフォリオ計算例
  ```python
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_equal_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value=10000000, available_cash=7000000, current_positions={}, open_prices=price_map)
  ```

---

## 停止 / Kill Switch / フラグファイル

- 実行停止や監視ループ終了には `data/stop_requested.flag` を作成します（run_* スクリプトはこのファイルを検知して終了）。
- ExecutionEngine の停止命令（Trading 停止を目的）には `data/kill.flag` を使用します。KillSwitch が条件を満たすとこのファイルを書きます。`KILL_FLAG_CLEAR_ON_START=1` により起動時に自動クリアできますが、本番では推奨されません。
- PID ファイル: `data/execution.pid` に ExecutionEngine の PID を書く仕組みがあります。

---

## ログ

- ログは標準出力（STDOUT）と日次ローテーションされるファイルログ（デフォルト `logs/<app_name>.log`）の両方に出力されます。`LOG_DIR` / `LOG_LEVEL` で挙動を調整します。
- logging は `kabusys.utils.logging_setup.setup_logging` で一貫して設定されます。

---

## ディレクトリ構成（主要部分）

以下は主要モジュールの一覧（src/kabusys 以下）：

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定ラッパ
  - config_setup.py           — .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - data/ (実データは data/ に配置)
  - execution/                 — 発注関連（broker_factory, engine, order_manager 等）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
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
    - logging_setup.py
    - process_priority.py

（実際の実装ファイルは src/kabusys 以下にまとまっています）

---

## 注意事項 / 運用上のヒント

- .env ファイルは機密情報を含むため絶対にバージョン管理に含めないでください。
- 本番（KABUSYS_ENV=live）では kill.flag や自動クリア設定に注意してください。`validate_config.py` の `--strict` モードで設定を慎重に検証してください。
- OpenAI を使う機能は API キー・利用コストに注意して運用してください。API 呼び出しはリトライとフェイルセーフを備えていますが、過剰な呼び出しは避ける。
- DuckDB/SQLite のパスやログ出力先は環境変数で変更可能です。コンテナ運用等では永続ボリュームのマウント場所に注意してください。
- プロセス優先度は起動時に `high` に設定されます（OS 権限により失敗する場合あり）。

---

以上がこのコードベースの簡易 README です。必要であれば「デプロイ手順」「詳細な API ドキュメント」「各モジュールのシーケンス図」など更に詳しいドキュメントを生成しますので、優先度に応じて教えてください。