# KabuSys

日本株向け自動売買システムのミニマム実装（ライブラリ・運用スクリプト群）。

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI支援（ニュースセンチメント、レジーム判定）などを含むコンポーネント群をまとめたものです。実行スクリプトはローカル開発・ペーパートレード・本番（live）いずれのモードに対応しています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要スクリプト・モジュールの実行例）
- 環境変数一覧（主要）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は次の機能を持つモジュール群で構成されています。

- データ解析 / リサーチ（DuckDB を利用してファクター計算や特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限等）
- ExecutionEngine（ブローカークライアントを介した発注管理・注文リポジトリ）
- 監視（System / Trade / Risk のポーリングとログ・アラート、kill switch）
- AI モジュール（ニュース NLP によるセンチメント、マクロニュースを用いたレジーム判定）
- 運用ユーティリティ（.env ウィザード、設定検証、ログ設定、プロセス優先度）

設計上のポイント：
- DuckDB を分析用 DB に使用、SQLite を監視・注文ログ用に使用（paper_trading は別 SQLite）。
- .env / 環境変数管理を提供し、プロジェクトルートにある .env(.local) を自動で読み込み（無効化可）。
- 実行スクリプトはプロセス優先度の設定、ログの統一設定、DB 初期化を行う。

---

## 機能一覧

- settings: 環境変数読み込み・検証（`kabusys.config.Settings`）
- .env ウィザード: `python -m kabusys.config_setup`
- 設定検証 CLI: `python -m kabusys.validate_config`
- 監視ループ: `python -m kabusys.run_monitoring`
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 監視は本番の sqlite_path を使用（環境に依らず本番監視 DB を参照）。
- 実行エンジン: `python -m kabusys.run_execution`
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB（data/paper_trading.db）へ記録。
  - 停止フラグ（data/stop_requested.flag）で安全停止。
- Monitoring 系
  - SystemMonitor（CPU/メモリ/Disk・データ鮮度・PID ファイル確認）
  - TradeMonitor（滞留注文や約定異常検出）
  - RiskMonitor（ドローダウン・ポジション数監視）
  - KillSwitch（条件で data/kill.flag を書き込み、Execution を停止）
  - MonitoringDB（SQLite に対する読み書きラッパー）
- Portfolio（候補選定・重み付け・ポジションサイズ）
- Research（ファクター計算、Forward Returns、IC、統計サマリ）
- AI
  - News NLP: DuckDB の raw_news を集約して OpenAI へ送り銘柄ごとのセンチメントを ai_scores に格納（`kabusys.ai.score_news`）
  - Regime Detector: ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成して market_regime を設定（`kabusys.ai.regime_detector.score_regime`）
- ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## セットアップ手順

前提
- Python 3.10 以上（Union 型の `|` を使用）
- 仮想環境推奨（venv / pyenv など）

1. リポジトリをクローンして仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # POSIX
   .venv\Scripts\activate      # Windows
   ```

2. 依存ライブラリをインストール
   （プロジェクトに requirements.txt がない場合は最低限以下を入れてください）
   ```
   pip install duckdb psutil openai
   ```
   - PyYAML は設定検証で YAML ファイルをパースする場合に任意で必要になります:
     ```
     pip install pyyaml
     ```

3. .env を作成
   - 対話式ウィザードを利用するのが簡単です:
     ```
     python -m kabusys.config_setup
     ```
   - または `.env.example` を参考に `.env` を作成してください（必須変数は README 下部参照）。

4. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   ```
   --strict オプションで警告もエラー扱いにできます:
   ```
   python -m kabusys.validate_config --strict
   ```

5. DB の初期化は起動スクリプト側で自動的に行われます（`init_monitoring_db` が呼ばれます）。

---

## 使い方（主要スクリプト）

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を設定可（例: 30）。
  - ストップはプロジェクトルートの data/stop_requested.flag（ファイル作成で検知）を利用。

- Execution Engine を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB（別ファイル）を使うため本番 DB と分離されます。
  - エンジンは data/execution.pid を利用してプロセス管理します。
  - プロセス停止は data/stop_requested.flag 書き込みで検知します。

- .env ウィザード（初期設定）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（例: 期間指定）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。`--db` オプションでパス指定可。または環境変数 PAPER_TRADING_SQLITE_PATH を利用。

- AI スコア（プログラム的に呼ぶ場合）
  - OpenAI API キー（環境変数 OPENAI_API_KEY）を設定してから呼び出してください。
  - 例（Python REPL/スクリプト内で）:
    ```py
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

- ログ設定
  - 全スクリプトは `kabusys.utils.logging_setup.setup_logging` を呼び出して統一的にログを出力します。
  - 環境変数 LOG_DIR（デフォルト `logs/`）と LOG_LEVEL（デフォルト `INFO`）で挙動を変更できます。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

AI 関連:
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で必須）

DB / ログ:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）

システム / 動作:
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト development）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — Paper trading の約定モード（instant/partial/never/reject）

Kill/Stop:
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- PID_FILE_PATH — 実行エンジンの PID ファイルパス（デフォルト: data/execution.pid）

自動 .env ロードの無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env 読み込みをスキップします（テスト用）。

---

## 運用上の注意点

- 起動時にプロセス優先度を "high" に設定する処理があります（管理者権限が必要なケースでは失敗しても警告のみ）。
- 監視は常に本番の sqlite_path を参照するため、環境に関わらず監視 DB の位置に注意してください。
- Paper Trading は意図的に本番データと分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- Kill Switch（data/kill.flag）は一度書き込まれると ExecutionEngine の起動を阻止します。運用時は取り扱いに注意してください。
- OpenAI を利用する AI 機能は外部 API 呼び出しを行います。API レート・コスト・レスポンス形式に注意してください。ネットワーク障害時はフェイルセーフで継続するように設計されていますが、APIキーは必須です。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・ディレクトリの構成例です。

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ config_setup.py
   ├─ validate_config.py
   ├─ run_monitoring.py
   ├─ run_execution.py
   ├─ utils/
   │   ├─ __init__.py
   │   ├─ logging_setup.py
   │   └─ process_priority.py
   ├─ monitoring/
   │   ├─ monitoring_db.py
   │   ├─ system_monitor.py
   │   ├─ trade_monitor.py
   │   ├─ risk_monitor.py
   │   ├─ monitoring_engine.py
   │   ├─ kill_switch.py
   │   └─ alert_manager.py
   ├─ execution/
   │   ├─ execution_engine.py
   │   ├─ order_manager.py
   │   ├─ order_repository.py
   │   ├─ broker_factory.py
   │   ├─ reconciler.py
   │   └─ risk_manager.py
   ├─ portfolio/
   │   ├─ __init__.py
   │   ├─ portfolio_builder.py
   │   ├─ position_sizing.py
   │   └─ risk_adjustment.py
   ├─ research/
   │   ├─ __init__.py
   │   ├─ factor_research.py
   │   └─ feature_exploration.py
   ├─ ai/
   │   ├─ __init__.py
   │   ├─ news_nlp.py
   │   └─ regime_detector.py
   ├─ data/
   │   └─ (DB・フラグファイルなど: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid)
   └─ tools/
       └─ paper_verification_report.py
```

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定チェック
  ```
  python -m kabusys.validate_config
  ```

- 監視起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- DuckDB を用いた AI スコアリング（プログラム呼び出し）
  - `kabusys.ai.score_news(conn, target_date, api_key=...)`
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)`

---

もし README に追加したい項目（例:詳細な設定ファイルテンプレート、CI/デプロイ手順、テストの実行方法など）があれば教えてください。必要に応じて追記します。