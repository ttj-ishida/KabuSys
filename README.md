# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリは、戦略評価・ポートフォリオ構築・発注エンジン・監視・AI を組み合わせたモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントから成る自動売買フレームワークです。

- 発注エンジン（ExecutionEngine）: ブローカークライアントを通じて注文を管理・実行します。  
  - `run_execution.py` で起動。`KABUSYS_ENV=paper_trading` の場合はモックブローカー（ペーパートレード）を使用し、専用の SQLite DB に記録します。
- 監視（Monitoring）: システム・注文・リスクの状態を定期的にチェックし、アラートや Kill Switch を管理します。  
  - `run_monitoring.py` で起動。
- ポートフォリオ構築（portfolio）: 候補選定、重み計算、ポジションサイズ計算、セクター制限等の純粋関数群。
- リサーチ（research）: DuckDB を用いたファクター計算・特徴量解析・IC 計算など。
- AI（ai）: ニュースの NLP スコアリングや市場レジーム判定（OpenAI API 利用）。
- ユーティリティ（utils）: ログ設定、プロセス優先度設定、設定読み込み等。
- ツール（tools）: ペーパートレード検証レポート生成などの実用スクリプト。

設計方針の一部:
- 環境変数（.env）で設定管理
- DuckDB / SQLite をローカル分析・ログ永続化に使用
- ペーパートレードと本番 DB を分離（完全分離）
- 外部 API 呼び出し（OpenAI 等）は API キーで制御し、失敗時はフェイルセーフ（例: スコア 0 にフォールバック）

---

## 主な機能一覧

- Execution
  - ブローカー抽象化（実ブローカ or MockBroker）
  - 注文管理、リスクチェック（Rate limit、ドローダウン、ポジション上限など）
- Monitoring
  - CPU / メモリ / ディスク使用率、プロセス稼働監視
  - 注文ログ監視（滞留注文、約定異常）
  - リスク監視（ドローダウン検出、ポジション上限）
  - Kill Switch（条件により `data/kill.flag` を書き込む）
- Portfolio
  - 候補選定（スコア降順）、等重／スコア重み付け
  - ポジションサイズ計算（リスクベース、等配分等）、単元株丸め
  - セクターキャップ、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC（Spearman）計算、統計サマリー
- AI
  - ニュースを LLM（gpt-4o-mini）でセンチメント化し ai_scores に保存
  - マクロニュース + ETF MA200 による市場レジーム判定
- Tools
  - ペーパートレード検証レポート生成（成功率・レイテンシ・稼働率等）

---

## セットアップ手順

以下はローカル開発・動作確認向けの手順です。

1. Python 環境準備
   - 推奨: Python 3.9+
   - 仮想環境作成:
     ```bash
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows
     ```

2. 必要パッケージをインストール
   - 必須（主なもの）:
     - duckdb
     - psutil
     - openai
   - オプション:
     - pyyaml（config ファイル検証時）
   - 例:
     ```bash
     pip install duckdb psutil openai pyyaml
     ```
   - （実運用用の requirements ファイルがある場合そちらを使用してください）

3. プロジェクトルートで .env を作成
   - 対話式ウィザードを利用:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（`.env.example` を参考）。必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: `.env` は絶対に Git にコミットしないでください。

4. 設定検証
   - 自動検証スクリプト:
     ```bash
     python -m kabusys.validate_config       # 警告は出力するが exit 0
     python -m kabusys.validate_config --strict  # 警告も FAIL 扱いで exit 1
     ```

5. データ/ログディレクトリ作成（通常は起動時に自動作成されますが手動でも可）
   - デフォルト:
     - DB: data/monitoring.db（SQLite）, data/paper_trading.db（ペーパー）
     - DuckDB: data/kabusys.duckdb
     - ログ: logs/
   - PID/フラグ:
     - data/execution.pid
     - data/kill.flag
     - data/stop_requested.flag（プロセス停止制御用）

6. OpenAI を使う場合
   - 環境変数 `OPENAI_API_KEY` を設定（または ai 関数に明示的に渡す）
   - モデルはコード内で `gpt-4o-mini` を利用

---

## 使い方

基本的な起動・ユーティリティコマンド:

- 環境設定ウィザード（.env 作成・更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 本番（KABUSYS_ENV=live）/ 開発（development）/ ペーパー（paper_trading）に応じて動作が変わります。
  - ペーパートレード:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    - ペーパートレード時は MockBroker を使い、`data/paper_trading.db` に記録されます。
  - 本番/開発:
    ```bash
    python -m kabusys.run_execution
    ```
  - 起動時、プロセス優先度を高に設定し、`data/execution.pid` を管理します。
  - 起動前に `data/stop_requested.flag` が存在すると起動を行いません。

- Monitoring 起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず本番 DB を参照する設計）。
  - 停止は `data/stop_requested.flag` を作成して行います（スクリプトはフラグ検知でループ終了）。

- ペーパートレード検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 処理（プログラムから呼び出し）
  - ニューススコアリング:
    ```python
    from kabusys.ai import score_news
    # conn: duckdb connection, target_date: datetime.date, api_key optional
    score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

注意点:
- Kill Switch（`KillSwitch`）はリスク監視結果に応じて `data/kill.flag` を作成します。ExecutionEngine はこのフラグを検知して安全に停止します。
- `KILL_FLAG_CLEAR_ON_START=1` を本番で設定するのは危険です（自動で Kill Flag をクリアしてしまうため）。
- ログは `logs/<app_name>.log`（日次ローテーション、30 日保存）がデフォルトです。ログディレクトリは `LOG_DIR` 環境変数で上書き可能。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- LOG_DIR: ログ保存ディレクトリ
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 0|1（起動時に kill.flag を自動クリアするか）

---

## ディレクトリ構成

（プロジェクトルートに `src/kabusys` 以下のパッケージが配置されている想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/               — 発注関連コンポーネント（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                    — デフォルトデータ / DB ファイル（git 管理外）
  - logs/                    — ログ出力先（デフォルト）

補足:
- `config/` 配下に YAML 設定ファイル（system_config.yaml 等）がある想定。`validate_config` はこれらの存在・パースもチェックします（PyYAML がインストールされている場合）。
- DB ファイル（SQLite / DuckDB）はデフォルトで `data/` に作成します。パスは環境変数で変更可能。

---

## 開発者向けメモ

- モジュールはできるだけ純粋関数 / 副作用の少ない設計を心がけています（例: portfolio モジュールは DB を参照しない）。
- 時刻の扱いはルックアヘッドバイアス回避のため、原則として外部から date を渡す形や UTC で管理する設計になっています。
- OpenAI 呼び出しはリトライ・バリデーション・クリッピングを備え、API 失敗時はフェイルセーフ（例: スコア 0 / 処理スキップ）で動作します。
- ロギングは各起動スクリプトから `kabusys.utils.logging_setup.setup_logging()` を呼ぶことで統一されます。

---

## よくある操作例

- ペーパートレードで全体検証を行う（.env 設定済み）:
  1. Execute エンジン起動（別ターミナル）
     ```bash
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     ```
  2. Monitoring 起動（別ターミナル）
     ```bash
     python -m kabusys.run_monitoring
     ```
  3. 検証レポート生成（期間指定）
     ```bash
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     ```

---

問題や改善提案があれば README を更新するか、Issue を立ててください。