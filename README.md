# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ内 README.md です。  
このドキュメントはプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ用ライブラリ兼実行基盤です。  
主な目的は以下：

- 市場データ（DuckDB）を用いたファクター計算・研究機能
- ポートフォリオ構築（銘柄選定・配分・株数決定）
- ExecutionEngine による発注・注文管理（本番 / ペーパー両対応）
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
- ニュース/NLP を用いた AI スコアリング、レジーム判定
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針の一例：外部 API 呼び出しを行う箇所（OpenAI、取引所 API 等）は明示的に分離し、フェイルセーフ（API失敗時のフォールバック）を備えています。DB（DuckDB / SQLite）はファイルベースでローカル運用に適しています。

---

## 主な機能一覧

- 実行コア
  - ExecutionEngine（発注・リスク管理・注文再整合）
  - BrokerClientFactory による本番 vs ペーパートレード切替
- 監視
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存監視
  - TradeMonitor: 注文滞留/約定異常などの監視（trade_logs 参照）
  - RiskMonitor: ドローダウン・保有上限の監視（dashboard/positions）
  - MonitoringEngine: 各モニタを束ね、KillSwitch 評価・アラート発行
- ポートフォリオ構築
  - 銘柄選定、等重/スコア重み、リスクベースの株数計算（単元丸め含む）
  - セクター制約・レジーム乗数の適用
- リサーチ / ファクター
  - Momentum / Value / Volatility 等のファクター計算（DuckDB 経由）
  - 特徴量探索：将来リターン、IC、統計サマリ
- AI 関連
  - news_nlp: OpenAI を用いたニュースセンチメント集約（ai_scoresへ書き込み）
  - regime_detector: ma200 とマクロニュースを組み合わせた市場レジーム判定
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前の設定検証 CLI
  - paper_verification_report: ペーパートレード検証レポート生成

---

## 必要条件（概略）

- Python 3.10 以上（typing の表記に依存）
- パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に YAML のパースを行う場合に必要）
- 標準ライブラリ：sqlite3, logging, threading, datetime, pathlib 等

※ requirements.txt はプロジェクトに含まれていない可能性があるため、上記を手動でインストールしてください。

例（venv 作成後）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに移動
2. Python 仮想環境の作成・有効化
3. 必要パッケージのインストール（上記参照）
4. .env の用意
   - 対話式ウィザードを使う（推奨）
     ```bash
     python -m kabusys.config_setup
     ```
     ウィザードは既存の .env を読み込み、対話的にキーを設定して .env を保存します。
   - 手動で作成する場合は、プロジェクトルートに `.env` を置き、以下のようなキーを設定します（最低限必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （運用時）OPENAI_API_KEY
     - KABUSYS_ENV=development|paper_trading|live
     - その他：DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, PAPER_TRADING_SQLITE_PATH（paper_trading 使用時）など
5. 設定検証（任意・起動前推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
6. 必要なら data ディレクトリや logs ディレクトリを作成（多くは自動作成されます）

注意点:
- `.env` は機密情報を含みうるため、絶対にバージョン管理にコミットしないでください（config_setup.py でも注意喚起あり）。
- 自動 .env ロードは Settings モジュールで行われます。テスト時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。

---

## 使い方（主な実行スクリプト）

プロジェクトはモジュール実行可能なスクリプトを含みます。いずれもプロジェクトルートで実行してください。

1. ExecutionEngine（発注エンジン）起動
   - デフォルト（KABUSYS_ENV に従う）
   ```bash
   python -m kabusys.run_execution
   ```
   - 挙動
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは `data/paper_trading.db`（もしくは env で指定した PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と完全分離されます。
     - プロセス優先度を高く設定（set_process_priority("high")）します。
     - `data/stop_requested.flag` があれば起動を中止または実行中に停止をトリガーします。
     - `data/execution.pid` に PID を書く挙動あり（PID ファイルパスは Settings で管理）。
2. Monitoring（監視ループ）起動
   ```bash
   python -m kabusys.run_monitoring
   ```
   - 挙動
     - 定期ポーリングで SystemMonitor.check_once() を呼び出します（デフォルト 60 秒）。
     - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能。
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視用 DB として `SQLITE_PATH` を参照）。
     - `data/stop_requested.flag` が存在するとループを終了します。
3. 設定ウィザード
   ```bash
   python -m kabusys.config_setup
   ```
   - .env の初期作成・更新を対話式で行えます。
4. 設定検証
   ```bash
   python -m kabusys.validate_config
   ```
5. Paper Trading 検証レポート（ツール）
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - DB ファイルは `--db` オプション、または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。
6. AI モジュール（ニューススコア / レジーム判定）
   - OpenAI API を使用するため、`OPENAI_API_KEY` を .env または環境変数で設定してください。
   - 例：news_nlp の呼び出しはプログラム内 API を通して行います（外部実行スクリプトはありませんが、他モジュールから `kabusys.ai.score_news` を呼ぶことができます）。

ログ:
- setup_logging ユーティリティにより、標準出力ログと日次ローテーションファイルログ（デフォルト logs/<app_name>.log）を出力します。
- 環境変数 `LOG_DIR` / `LOG_LEVEL` で調整可能。

Kill Switch / 停止フラグ:
- `kabusys.monitoring.kill_switch.KillSwitch` は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります。
- `data/stop_requested.flag` を配置すると run_monitoring や run_execution がシャットダウン処理を行います。

---

## 主要設定（Settings）の概要

主要な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- OPENAI_API_KEY（AI 機能を使う場合必須）
- DUCKDB_PATH（DuckDB ファイル、デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用 SQLite、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（Kill Switch まわり）

Settings クラスは `kabusys.config.Settings` で提供され、.env 自動ロード機能があります（プロジェクトルートが特定できる場合）。

---

## ディレクトリ構成（抜粋）

プロジェクトは `src/kabusys` 以下にモジュールを配置しています。主な構成：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込みロジック（自動 .env ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — 監視 DB スキーマ + 永続化 API
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文監視（ファイル未表示部分）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の作成・管理
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - alert_manager.py       — （アラート送信ロジック: 未表示）
  - execution/
    - execution_engine.py    — ExecutionEngine 実装（起動/セッション管理）
    - broker_factory.py      — BrokerClientFactory（本番/モック切替）
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文リポジトリ（SQLite 操作）
    - reconciler.py          — 発注整合処理
    - risk_manager.py        — 発注リスク管理
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み算出
    - position_sizing.py     — 株数算出・集約キャップ処理
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Value / Volatility 計算
    - feature_exploration.py — IC 等の研究ユーティリティ
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（ma200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

DB テーブル（監視用）例（monitoring_db.init_monitoring_db に定義）:
- system_status
- trade_logs
- positions
- risk_logs
- dashboard

---

## 運用上の注意・ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では .env の設定を慎重に確認してください。validate_config は警告も表示します。
- .env に含む機密情報（APIキー等）は厳重に管理し、Git へコミットしないでください。
- OpenAI 利用箇所は API 呼び出し失敗時にフォールバックする設計ですが、APIキー漏洩やコストに注意してください。
- データベースファイル（DuckDB/SQLite）はバックアップを検討してください。
- Kill Switch（data/kill.flag）や stop_requested.flag を用いた安全停止フローを運用手順に組み込むことを推奨します。
- ログは logs/ に日次ローテートで保存されます。ログディレクトリが作れない環境ではコンソールのみでの出力になります。

---

## 開発・拡張のヒント

- DuckDB を使ったファクター計算は SQL と Python の組合せで書かれており、テーブル設計を揃えておけば容易に再利用できます。
- AI 関連処理（news_nlp, regime_detector）は OpenAI クライアント呼び出し部分をモック/差し替え可能な設計（テスト容易性配慮）です。
- ポートフォリオ関係の関数は純粋関数（副作用なし）で実装されているため、ユニットテストが容易です。

---

もし README の補足（例: 具体的な .env.sample、requirements.txt、UnitTest の実行方法、各モジュールの API 仕様書など）が必要であれば、どの項目を優先して追加するか教えてください。