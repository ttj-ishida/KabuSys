# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。本リポジトリは取引エンジン、監視、リサーチ、ポートフォリオ構成、AI 補助（ニュース NLP / レジーム判定）などを含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール化された自動売買システムです。

- 市場データ（DuckDB）を用いたファクター計算・研究機能
- 発注エンジン（ExecutionEngine）とモックブローカーによるペーパートレード分離
- モニタリング（System / Trade / Risk）と Kill Switch による安全停止
- ニュースの LLM（OpenAI）を用いたセンチメントスコア化・レジーム判定
- 構成ウィザード・検証ツール・レポート生成ツール

主要な起動スクリプト:
- run_execution.py — 発注エンジン起動
- run_monitoring.py — 監視ポーリングループ起動
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- tools/paper_verification_report.py — ペーパートレード検証レポート生成

---

## 機能一覧（抜粋）

- 環境設定ウィザード（.env の対話的生成 / 更新）
- 設定の事前検証（必須環境変数・パスや YAML ファイルの整合性チェック）
- ExecutionEngine（本番 / ペーパートレード切替）
  - Paper Trading 時は MockBrokerClient を使用し DB を分離（data/paper_trading.db）
- 監視機能（SystemMonitor, TradeMonitor, RiskMonitor）
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - Kill Switch（閾値超過で data/kill.flag を書き込み ExecutionEngine 停止）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- リサーチ（ファクター計算 / 将来リターン / IC 計算 / 統計サマリ）
- AI モジュール
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメントを ai_scores に書き込み
  - レジーム判定（ETF MA と LLM による合成スコア）
- ユーティリティ
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度設定（Windows / POSIX を吸収）

---

## 前提条件（依存ライブラリ）

少なくとも以下が必要です（プロジェクトの実際の requirements を参照してください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI モジュール使用時)
- PyYAML（validate_config の YAML 検証を行う場合）

例（pip）:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリのクローン / 配置
2. Python 仮想環境を作成して依存をインストール
3. .env の作成（対話ウィザード推奨）

対話ウィザードで .env を作る:
```
python -m kabusys.config_setup
```

設定の検証:
```
python -m kabusys.validate_config
# 警告を FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

必要な環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN — （必須）
- KABU_API_PASSWORD — （必須）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — AI 機能使用時に必要
- LOG_LEVEL — ログレベル（例: INFO）

ローカル開発時は .env を作成し、必須値を設定してください。.env は決して VCS にコミットしないでください（config_setup にも注意書きがあります）。

ログやデータディレクトリの作成（手動で必要な場合）:
```
mkdir -p data logs
```

---

## 使い方

基本コマンド（プロジェクトルートで実行）:

- ExecutionEngine（実際の注文または paper_trading）起動:
```
python -m kabusys.run_execution
```
挙動:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にデータを書きます。
- 起動時に `data/stop_requested.flag` が存在すると起動しません。
- 起動中に `data/stop_requested.flag` を作成するとエンジンへ停止シグナルを送り終了します。
- PID ファイル: data/execution.pid（設定で変更可能）

- Monitoring（ポーリング）起動:
```
python -m kabusys.run_monitoring
```
挙動:
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60）。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを残します。
- 停止: `data/stop_requested.flag` を作成するとループ終了します。

- 設定ウィザード:
```
python -m kabusys.config_setup
```

- 設定検証:
```
python -m kabusys.validate_config
```

- ペーパートレード検証レポート生成:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを明示する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- AI 機能（プログラム的に呼び出す例）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - OpenAI API を呼ぶために OPENAI_API_KEY を設定するか、引数で渡します。

注意:
- run_monitoring / run_execution はそれぞれプロセス優先度を "high" に設定しようとします（psutil を利用）。権限や OS によっては警告になりますが、処理は継続します。
- Monitoring は監視用 DB（SQLite）に system_status 等を記録します。一方、Execution はペーパートレード時に DB を分離します。

環境変数の重要な挙動:
- KABUSYS_ENV=paper_trading → ExecutionEngine は paper_sqlite_path を使用
- Monitoring は常に sqlite_path（監視 DB）を使用（env に依存しない）
- KILL フラグ: Settings.kill_flag_path（デフォルト data/kill.flag）により ExecutionEngine 停止を指示
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアする（本番では推奨しない）

---

## 運用上の留意点

- 本番運用（KABUSYS_ENV=live）は非常に注意が必要です。validate_config は live 設定時に追加の警告を出します。
- .env にプレースホルダ（your_value, *_here）が残ったままにならないよう注意してください。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では推奨されません。
- PID / stop flag / kill flag は data/ 配下のファイルを介してプロセス間の信号伝達を行います。cron/systemd など外部から制御することも可能です。
- ログはデフォルト logs/<app_name>.log に日次ローテートで保存されます（logs/ ディレクトリが作成できない場合はコンソール出力のみになります）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 内の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - execution/
    - (ExecutionEngine / OrderManager 等の実装モジュール)
  - monitoring/
    - monitoring_db.py        — SQLite テーブル作成 + DB 書き込みラッパー
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
  - tools/
    - paper_verification_report.py

（実際のファイル・サブパッケージは上記以外にも存在します。詳細はリポジトリを参照してください）

---

## 開発 / デバッグのヒント

- モジュール単体をインポートして関数を呼べます（例: portfolio.calc_position_sizes などは副作用なしの純粋関数）。
- MonitoringEngine は run_once() で単発処理が可能なためユニットテストしやすい設計です。
- AI 系関数は外部 API 呼び出し箇所を容易にモックできるよう分離されています（テスト時は呼び出し関数を patch 推奨）。

---

## よく使うコマンドまとめ

- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README を拡張します（依存関係の厳密なバージョン、systemd ユニット例、開発用テスト手順など）。追加の要望があれば教えてください。