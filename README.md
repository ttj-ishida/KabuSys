# KabuSys

日本株向け自動売買基盤（ライブラリ & 起動スクリプト群）

本リポジトリは、取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースNLP / レジーム判定）などを含む自動売買システムのコア実装です。

## 概要

- モジュール化されたコンポーネント（ExecutionEngine、Monitoring、Portfolio、Research、AI）を持つ。
- SQLite（監視・ペーパートレード）と DuckDB（分析・リサーチ）を利用する。
- 環境変数と `.env` による設定管理、対話式ウィザード・検証ツールを提供。
- OpenAI を利用したニュースセンチメント評価機能を持つ（環境変数 `OPENAI_API_KEY` 必須）。
- Paper trading 用の分離された DB をサポート（`KABUSYS_ENV=paper_trading`）。

## 主な機能一覧

- Execution
  - 実際の発注/モック発注（`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用）
  - 注文管理・リスク管理・リコンシリエーション等の ExecutionEngine
- Monitoring
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文ログ監視
  - Kill Switch（ドローダウンやポジション超過で停止フラグを書込）
  - 監視用 SQLite DB の初期化 / 永続化（`monitoring_db.py`）
- Portfolio
  - 候補選定、重み計算（等金額・スコア加重）、ポジションサイズ計算、セクターキャップ
- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - ニュースを LLM（OpenAI）でスコア化して `ai_scores` に書込む（`kabusys.ai.news_nlp`）
  - マクロニュース + ETF MA を使った市場レジーム判定（`kabusys.ai.regime_detector`）
- ツール
  - 対話式 `.env` 生成ウィザード（`python -m kabusys.config_setup`）
  - 設定検証 CLI（`python -m kabusys.validate_config`）
  - Paper Trading 検証レポート生成（`python -m kabusys.tools.paper_verification_report`）

## 要求環境

- Python >= 3.10（型記法や union 型使用のため）
- 推奨パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML ファイル検証に任意で必要）
- 実行環境に応じた外部サービス設定（kabuステーション、J-Quants、OpenAI 等）

pip でのインストール例（requirements.txt が無い場合は個別に）:
```bash
pip install duckdb psutil openai PyYAML
```

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/上書き可能項目（デフォルトを示す）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- OPENAI_API_KEY — OpenAI を使う場合必須
- LOG_LEVEL — default: INFO
- LOG_DIR — default: logs/
- PID_FILE_PATH — default: data/execution.pid
- KILL_FLAG_CLEAR_ON_START — default: 0（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ループの秒間隔（`run_monitoring` 用、デフォルト 60）

PAPER_FILL_MODE の有効値:
- instant | partial | never | reject

自動 `.env` ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

## セットアップ手順（基本）

1. リポジトリをクローン・チェックアウト
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存ライブラリをインストール
   ```bash
   pip install duckdb psutil openai PyYAML
   ```
4. 対話式ウィザードで `.env` を作成（推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - 生成後、`python -m kabusys.validate_config` で検証してください。
5. データディレクトリの確認（必要に応じて作成）
   - デフォルトで使用するディレクトリ: data/, logs/

## 使い方（主要エントリポイント）

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- .env 対話式作成/更新
  ```bash
  python -m kabusys.config_setup
  ```

- Execution Engine 起動
  - 本番（live）や開発（development）設定に応じて `KABUSYS_ENV` を指定してください。
  - ペーパートレード:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 本番:
    ```bash
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - 起動時、`data/execution.pid` に PID を書き、`data/stop_requested.flag` や `data/kill.flag` で停止制御します。

- Monitoring 起動
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - 監視は常に本番 sqlite_path（`SQLITE_PATH`）を使用します。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI / レジーム判定・ニューススコアリング（プログラム呼び出し）
  - OpenAI キーが必要:
    - 環境変数: `OPENAI_API_KEY`
  - 例（Python から呼ぶ）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - `kabusys.ai.regime_detector.score_regime` も同様に呼べます。

## ログ

- ログ設定は `kabusys.utils.logging_setup.setup_logging` で統一管理。
- デフォルト出力先:
  - コンソール（stdout）
  - 日次ローテートファイル: logs/<app_name>.log（30日保持）
- ログディレクトリの指定:
  - 環境変数 `LOG_DIR` または `setup_logging(log_dir=...)`

## Kill / Stop 制御

- ExecutionEngine 停止トリガ:
  - `data/kill.flag` — KillSwitch により書かれる。存在すると Engine は停止する。
  - `data/stop_requested.flag` — 外部から監視スクリプト等に「停止してほしい」ことを伝えるためのフラグ。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に `kill.flag` を自動でクリアします（開発時のみ注意して使用）。

## 主要ディレクトリ構成（抜粋）

src/kabusys の構成（主要ファイルのみ抜粋）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env の読み込み・Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                 — Execution 関連（broker / engine / order_manager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py

（実際のツリーはリポジトリの `src/kabusys` を参照してください）

## 開発メモ / 注意事項

- Settings は `.env` 自動ロード機能を持ちます（プロジェクトルートの検出は `.git` または `pyproject.toml` を基準にします）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
- `Settings` は環境に応じて `is_paper` / `is_live` を提供します。ペーパートレードは本番 DB と分離された `PAPER_TRADING_SQLITE_PATH` を使用します。
- DuckDB 操作用の SQL はリサーチモジュールで多用されます。大規模データを想定したクエリ設計がされているため、DuckDB のファイルパスと容量に注意してください。
- OpenAI 呼び出しはレート制限や一時エラーに対して指数バックオフでリトライする実装がありますが、APIキーと費用には十分ご注意ください。
- ローカルで動作確認する際は `KABUSYS_ENV=development` にして発注系を無効化した挙動でテストすることを推奨します。

---

問題点の報告や改善提案は issue を作成してください。README の補足や実運用に関するドキュメント化が必要であれば提供します。