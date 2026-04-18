# KabuSys

日本株自動売買システムの Python コードベース向け README（日本語）

---

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境変数 (.env) — 重要項目
- 実行方法（主要スクリプト）
- 運用メモ / 注意点
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。発注ロジック（ExecutionEngine）、監視 / リスク管理（Monitoring）、ポートフォリオ構築、リサーチ（DuckDB を使ったファクター計算）、および OpenAI を利用したニュース NLP / レジーム検出などのコンポーネントを含みます。設計は本番（live）とペーパートレード（paper_trading）を明確に分離し、安全性を考慮した運用をサポートします。

---

## 主な機能

- ExecutionEngine（実際の発注/ペーパートレード）
  - KABUSYS_ENV=`paper_trading` 時は MockBrokerClient を使用し、data/paper_trading.db に記録
- Monitoring（システム監視）
  - CPU / メモリ / ディスク / 発注プロセスの稼働検知、データ鮮度チェック
  - Kill Switch（条件により data/kill.flag を作成して Execution を停止）
- RiskMonitor（ドローダウン・ポジション上限監視）
- TradeMonitor（発注ログ監視・滞留注文や異常約定検知）
- Portfolio（銘柄選定・ウェイト計算・ポジションサイズ計算）
- Research（DuckDB を使ったファクター計算、前方リターン、IC 計算等）
- AI モジュール
  - news_nlp: OpenAI を使ったニュースのセンチメントスコア付与（ai_scores テーブル）
  - regime_detector: ETF とマクロニュースを用いた市場レジーム判定
- ツール
  - config_setup: .env の対話式生成ウィザード
  - validate_config: .env / config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード検証レポート生成

---

## 前提条件

最低限必要なライブラリ（一例）
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config YAML の検証を行う場合・任意）

インストール例（仮の requirements.txt がない場合）:
```
pip install duckdb psutil openai pyyaml
```

※ 実際の運用では requirements.txt / 仮想環境を利用してください。

---

## セットアップ手順

1. リポジトリをクローン／展開する
2. 仮想環境を作成して依存パッケージをインストール
3. .env を用意する
   - 対話式で作るなら:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env.example を参考に手動作成
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   オプション `--strict` を付けると警告もエラー扱いになります
5. データディレクトリやログディレクトリが自動作成されます（logging_setup で `logs/`、デフォルト DB パスは `data/` 内）

---

## 環境変数（重要）

主に `.env` で管理します。最低限設定が必要なもの:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用に影響する主要項目:
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading`：MockBroker を用い DB は `data/paper_trading.db` を使用（本番 DB と分離）
  - `live`：本番
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（例: INFO）
- OPENAI_API_KEY — OpenAI を使う場合に必要（news_nlp / regime_detector）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60 秒）
- PID_FILE_PATH — ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（0 または 1）

簡易サンプル (.env の例):
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 実行方法（主要スクリプト）

- 実行エンジン（Execution）
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 挙動:
    - KABUSYS_ENV=`paper_trading` の場合、MockBrokerClient を使って発注をシミュレートし `data/paper_trading.db` に記録します。
    - 起動前に `data/stop_requested.flag` が存在する場合は起動せず終了します。
    - 実行中は `data/execution.pid` を作成します。停止は kill.flag によりシグナル送付、または stop_requested.flag によりループ中断。

- 監視ループ（Monitoring）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - 環境変数:
    - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト: 60）。
  - 注意:
    - Monitoring は環境に関わらず本番 sqlite_path（SQLITE_PATH）を使用します（監視ログは一箇所に集約）。
  - 停止:
    - リポジトリルート配下 `data/stop_requested.flag` が作成されると監視ループを終了します。

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
  デフォルト DB は `data/paper_trading.db`。`--db` オプションでファイルを指定可能。

---

## 運用メモ / 注意点

- データベース
  - DuckDB: 分析・研究用データベース（prices_daily / raw_financials 等）
  - SQLite: 監視ログ / トレードログ（monitoring.db）およびペーパートレード（paper_trading.db）
- Kill Switch / Stop フラグ
  - Kill Switch は `data/kill.flag` を作成して ExecutionEngine に停止を促す仕組み（Monitoring の KillSwitch が書き込む）。
  - `data/stop_requested.flag` は run_execution / run_monitoring の外部停止フラグとして使われます（起動スクリプトは存在を検知して終了します）。
- ログ
  - logs/ ディレクトリに日次ローテートでログを出力（`kabusys.utils.logging_setup.setup_logging`）。
- OpenAI
  - news_nlp / regime_detector は OpenAI を利用します。`OPENAI_API_KEY` を設定してください。
  - API 呼び出しはリトライ・フェイルセーフロジックを含み、失敗時は安全側のデフォルト（例: macro_sentiment = 0.0）で継続します。
- 環境による挙動差
  - `KABUSYS_ENV=paper_trading` では発注はシミュレーションに限定され、本番 DB を汚染しません（専用の paper DB を使用）。
  - `KABUSYS_ENV=live` は本番運用です。LINE 通知設定や Kill Switch の設定等を慎重に行ってください（validate_config は live 時に追加チェックを行います）。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なモジュールと役割の概略です。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数読み込み・検証、.env 自動ロードロジック
  - config_setup.py
    - .env を対話式に作成・更新するウィザード
  - validate_config.py
    - 起動前の環境・設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID 管理 / stop フラグ監視）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）
  - utils/
    - logging_setup.py
      - ルートロガーの設定（コンソール + 日次ファイルローテーション）
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定（psutil 利用）
  - execution/
    - （発注エンジン、OrderManager、RiskManager、Reconciler 等 — 起動は run_execution）
  - monitoring/
    - monitoring_db.py — SQLite スキーマと永続化層
    - system_monitor.py — CPU/メモリ/ディスク、データ鮮度、プロセス監視
    - trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py など
  - portfolio/
    - portfolio_builder.py — 候補選定、重み付け
    - position_sizing.py — 発注株数計算（単元丸め・リスク制約）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/バリュー/ボラティリティの計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py — ETF + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート出力

---

## トラブルシューティング / 開発ヒント

- .env の自動読み込み機能はプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- validate_config で PyYAML がない場合は YAML の検証をスキップします（警告）。
- DuckDB・SQLite に関するパス設定は Settings 経由で簡単に上書きできます（環境変数）。
- ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続します。
- OpenAI 呼び出しは外部サービス依存のため、テスト時は該当モジュールの API 呼び出し関数をモックして検証してください（コード内で _call_openai_api を切り替え可能な設計になっています）。

---

必要であれば、README に追加してほしい項目（依存関係の完全な一覧、実行例のログ抜粋、DB スキーマ説明、CI / デプロイ手順 など）を教えてください。