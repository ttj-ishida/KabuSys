# KabuSys

KabuSys は日本株の自動売買システム（プロトタイプ）です。  
シグナル → ポートフォリオ構築 → 発注（実口座 / ペーパートレード）を行う ExecutionEngine、稼働監視・アラート・Kill Switch を提供する Monitoring、ファクター計算 / 研究用ユーティリティ、ニュース NLP を用いた AI モジュールなどを含みます。

バージョン: 0.1.0

---

## 主要機能

- Execution Engine
  - 実口座（kabuステーション）およびペーパートレード（MockBrokerClient）対応
  - リスク管理 (RiskManager)、注文管理 (OrderManager)、再整合処理 (Reconciler)
  - Execution 起動スクリプト: `run_execution.py`
- Monitoring
  - システム稼働監視（CPU / メモリ / ディスク）、プロセス死活監視、データ鮮度チェック
  - 取引ログ監視、リスク監視（ドローダウン・ポジション上限）
  - Kill Switch（条件に合致した場合に `data/kill.flag` を書き込み Execution を停止）
  - Monitoring 起動スクリプト: `run_monitoring.py`
- Portfolio 構築ユーティリティ（純粋関数）
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数など
- Research / Factor 計算
  - ファクター（Momentum / Volatility / Value）計算、将来リターン、IC 計算、統計サマリ
  - DuckDB を用いたデータ処理
- AI（OpenAI 統合）
  - ニュースのセンチメントスコアリング（`kabusys.ai.news_nlp.score_news`）
  - マーケットレジーム判定（`kabusys.ai.regime_detector.score_regime`）
  - OpenAI API の呼び出しはリトライやバリデーション処理を備える
- ツール
  - `.env` 対話式生成ウィザード: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
  - ペーパートレード検証レポート生成: `kabusys.tools.paper_verification_report`

---

## 前提 / 必要環境

- Python 3.10 以上（ソースで `X | None` 等の構文を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（`validate_config` が config/*.yaml の構文チェックを行う場合）

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして checkout
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - 主要必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: `development` / `paper_trading` / `live`
     - OPENAI_API_KEY（AI 機能を使う場合）
   - デフォルト DB パス:
     - DUCKDB_PATH: `data/kabusys.duckdb`
     - SQLITE_PATH: `data/monitoring.db`
     - PAPER_TRADING_SQLITE_PATH: `data/paper_trading.db`（ペーパートレード時）
4. 設定を検証（推奨）
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```
5. データ・ログ用ディレクトリ（`data/`, `logs/`）は、起動時に自動作成される場合がありますが、必要に応じて手動で作成してください。

---

## 使い方

- ExecutionEngine を起動
  - 本番・開発切替は KABUSYS_ENV で制御
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い、データは `data/paper_trading.db` に分離して保存されます。
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 停止:
    - 外部から停止する場合、`data/stop_requested.flag` を作成すると監視・実行ループが検知して終了します。
    - Kill Switch による停止は `data/kill.flag` が書き込まれることで Execution 停止がトリガーされます。

- Monitoring を起動
  - デフォルトポーリング間隔は 60 秒。環境変数で上書き可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に本番の sqlite_path（`SQLITE_PATH`）を使用します（環境に依らず監視 DB に記録）。
  - 監視ループを止めたい場合は `data/stop_requested.flag` を作成。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスはオプション `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI 関連（プログラムから呼び出す）
  - ニューススコアリング:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...) による接続
    score_news(duckdb_conn, target_date, api_key=None)
    ```
    - API キーは引数で渡すか `OPENAI_API_KEY` 環境変数を使用
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=None)
    ```

---

## 重要な運用ノート

- KABUSYS_ENV
  - 許容値: `development`, `paper_trading`, `live`
  - `live` では本番発注が行われるため、環境変数と設定を十分に確認してください。`validate_config` は `live` 時に追加の警告を出します。
- Kill Switch
  - KillSwitch は RiskMonitor の判定（ドローダウン超過・ポジション上限超過等）で `data/kill.flag` を書き込み、ExecutionEngine 側が停止します。
  - `KILL_FLAG_CLEAR_ON_START=1` は本番で危険です（自動クリアされるため意図せず再起動される可能性）。
- ログ
  - ログはデフォルトで `logs/` に保存され、日次ローテーション（30日保持）されます。`LOG_DIR` 環境変数で変更可能。
- DB
  - DuckDB（分析用）と SQLite（監視 / orders は別）を併用します。
  - Paper trading は専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使い本番 DB と分離します。
- OpenAI API
  - LLM 呼び出しを行う機能は `OPENAI_API_KEY` を必要とします。API 呼び出しはリトライやレスポンス検証を行い、失敗時は安全側にフォールバックします（例: macro_sentiment=0.0）。

---

## ディレクトリ構成（抜粋）

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ config_setup.py
   ├─ validate_config.py
   ├─ run_execution.py
   ├─ run_monitoring.py
   ├─ utils/
   │   ├─ logging_setup.py
   │   └─ process_priority.py
   ├─ execution/
   │   ├─ execution_engine.py
   │   ├─ order_manager.py
   │   ├─ order_repository.py
   │   ├─ broker_factory.py
   │   └─ ...
   ├─ monitoring/
   │   ├─ monitoring_db.py
   │   ├─ system_monitor.py
   │   ├─ trade_monitor.py
   │   ├─ risk_monitor.py
   │   ├─ kill_switch.py
   │   ├─ monitoring_engine.py
   │   └─ alert_manager.py
   ├─ portfolio/
   │   ├─ portfolio_builder.py
   │   ├─ position_sizing.py
   │   └─ risk_adjustment.py
   ├─ research/
   │   ├─ factor_research.py
   │   └─ feature_exploration.py
   ├─ ai/
   │   ├─ news_nlp.py
   │   └─ regime_detector.py
   ├─ monitoring/
   ├─ tools/
   │   └─ paper_verification_report.py
   └─ data/   # 実行時に生成するファイルを置く想定
       ├─ monitoring.db
       ├─ paper_trading.db
       ├─ kill.flag
       ├─ stop_requested.flag
       └─ execution.pid
```

（実際のリポジトリにはさらに多くのモジュールが存在します。上は主要ファイルの抜粋です）

---

## 開発者向け補足

- 型注釈や設計により、関数は副作用を最小化するよう分離されています（例: portfolio モジュールは DB を参照せず純粋関数で実装）。
- テスト可能性を考慮し、OpenAI 呼び出し等は内部関数を patch して差替え可能です。
- 設定は .env ファイルと OS 環境変数を組み合わせて読み込まれます（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
- `validate_config` は .env と `config/*.yaml` の存在・整合性チェックを行います（PyYAML があれば YAML のパース検証も実施）。

---

README に書かれている手順で動かして問題が出た場合や、特定コンポーネント（AI モジュール・Execution の Broker 接続等）の使い方を詳しく知りたい場合は、どの箇所についてのドキュメントを追加すれば良いか教えてください。必要に応じてサンプル .env テンプレートや起動例、トラブルシュート欄を追記します。