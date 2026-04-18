# KabuSys

軽量な日本株自動売買システムの主要モジュール群をまとめたリポジトリの README（日本語）です。  
この README はリポジトリ内のスクリプトやライブラリの使い方、設定方法、ディレクトリ構成をまとめた開発者向けドキュメントです。

---

目次
- プロジェクト概要
- 機能一覧
- 依存関係
- セットアップ手順
- 環境変数と .env の管理
- 使い方（起動スクリプト / ツール）
- 運用上の注意点（Kill Switch / Stop フラグ等）
- ディレクトリ構成（主要ファイル説明）
- トラブルシューティング（よくある問題）

---

## プロジェクト概要

KabuSys は日本株の自動売買（Execution）・監視（Monitoring）・リサーチ（Research）・ポートフォリオ構築（Portfolio）や AI を利用したニュースセンチメント評価などを含む、内製トレーディング基盤のコンポーネント群です。  
モジュールは可能な限り副作用を抑え、DuckDB / SQLite をデータ層に利用し、Paper Trading（検証）環境と Live（本番）環境を分離する設計になっています。

主要な設計方針の一部:
- 環境変数（.env）ベースで設定を管理
- Paper Trading は本番 DB と分離（data/paper_trading.db）
- ログは統一的にセットアップ（コンソール + 日次ローテートファイル）
- OpenAI（LLM）を用いたニュース分析・レジーム判定をサポート（フェイルセーフ設計）
- 監視コンポーネントは SQLite にログを書き、Kill Switch を通じて ExecutionEngine を停止可能

---

## 機能一覧

- Execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（本番/モック切替）
  - Order 管理、リコンシリエーション、リスク管理機能
- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク, データ鮮度, Execution プロセス監視）
  - TradeMonitor / RiskMonitor / MonitoringEngine（ポーリング統合）
  - KillSwitch（条件により data/kill.flag を書き込むことで強制停止）
  - monitoring DB（SQLite）用の永続化層（monitoring_db.py）
- Portfolio
  - 候補選定、重み計算（等金額 / スコア加重）
  - セクターキャップ適用、レジーム乗数、ポジションサイズ計算（単元丸め等）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン、IC、統計サマリ）
  - DuckDB を用いた SQL/Python 混合実装
- AI（OpenAI）
  - ニュースセンチメントのスコアリング（news_nlp）
  - マクロ + ETF MA を使った市場レジーム判定（regime_detector）
  - OpenAI 呼び出しはリトライ・パースの耐性あり
- ツール
  - 環境設定ウィザード（config_setup.py） — .env を対話式に作成
  - 設定検証 CLI（validate_config.py） — 起動前のチェック
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## 依存関係（主なパッケージ）

最低限必要な Python パッケージ（バージョンはプロジェクトに合わせて調整してください）:
- duckdb
- psutil
- openai
- PyYAML（config 検証時に任意）
- （標準ライブラリ）sqlite3, logging, threading, datetime, pathlib など

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt があればそれを使ってください。）

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成して依存ライブラリをインストールします（上記参照）。

2. .env を作成する
   - 対話式ウィザードを使う（推奨）:
     ```
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルート（スクリプトの検出により自動判定）に `.env` が作成・更新されます。
   - あるいは手動で `.env` を作成します（後述の主要環境変数を設定）。

3. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
   ```

4. データディレクトリ作成（必要なら）
   - デフォルトでは `data/` に SQLite / PID / flag ファイルを作成します。自動作成されますが権限や所有権に注意してください。

5. ログディレクトリ
   - デフォルトは `logs/`。必要なら `LOG_DIR` 環境変数で変更できます。

---

## 環境変数（主要）

自動ロード順: OS 環境変数 > .env.local > .env  
自動ロードを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

主要な環境変数（一部抜粋）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
  - paper_trading: MockBroker を使用し、paper 用 SQLite に書き込む
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（AI 関連処理で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート用）
- MONITOR_POLL_INTERVAL （監視ポーリング間隔秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START （起動時に kill.flag を自動でクリアするか、0/1）

環境変数が不足している場合、`validate_config` が検出します。`Settings` クラス（kabusys.config）経由でアクセスします。

---

## 使い方（コマンド／起動方法）

基本的にモジュールを -m で実行します。

1. ExecutionEngine（注文実行エンジン）を起動
   ```
   python -m kabusys.run_execution
   ```
   - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して `data/paper_trading.db` に記録します（本番 DB とは分離）。
   - 起動時に `data/stop_requested.flag` が存在すると起動せずに終了します。
   - 起動直後に `KILL_FLAG_CLEAR_ON_START=1` の場合やフラグのクリア動作に注意（本番では推奨しません）。
   - プロセス優先度を "high" に設定します（psutil の権限に依存）。

2. Monitoring（監視ループ）を起動
   ```
   python -m kabusys.run_monitoring
   ```
   - デフォルトのポーリング間隔は 60 秒。`MONITOR_POLL_INTERVAL` 環境変数で上書きできます（1 以上の整数）。
   - Monitoring は常に本番の sqlite_path（Settings.sqlite_path）を使用する仕様です。
   - 監視中、`data/stop_requested.flag` を検知するとループを終了します。

3. Paper Trading 検証レポート生成
   ```
   python -m kabusys.tools.paper_verification_report
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   ```
   - 簡易的に Paper Trading の稼働率・注文成功率・レイテンシ等の集計を出力します。

4. 設定検証 / ウィザード
   - ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 設定検証:
     ```
     python -m kabusys.validate_config
     ```

5. AI 関連（スクリプトから利用）
   - news_nlp.score_news(conn, target_date, api_key=None)
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらは DuckDB の接続オブジェクトを受け取り DB に結果を書き込みます。API キーは引数または OPENAI_API_KEY 環境変数を使用。

---

## 運用上の注意点

- Kill Switch / Stop フラグ
  - data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine はこのファイルの存在を検知して停止されます。
  - data/stop_requested.flag: run_monitoring.py / run_execution.py が外部からの停止要求としてチェックするフラグファイル。
  - KillSwitch はリスク閾値（ドローダウンやポジション上限）を満たすと `kill.flag` を書き込みます。既に存在する場合は書き込みしません（冪等）。

- ログ
  - setup_logging() により stdout と日次ローテーションファイル（logs/<app_name>.log）に出力します。
  - ログディレクトリを作成できない場合、ファイル出力をスキップしてコンソールのみとなります。

- データベース
  - DuckDB: 分析用メイン DB（デフォルト: data/kabusys.duckdb）
  - SQLite: 監視ログなど（デフォルト: data/monitoring.db）。paper_trading では paper専用DB（data/paper_trading.db）に切り替わります。
  - init_monitoring_db() はテーブルの作成と簡単なマイグレーション（カラム追加）を行います（冪等）。

- OpenAI 呼び出しに関して
  - API はリトライや JSON パースの耐性を持ちますが、API キーがない場合は ValueError が投げられます。
  - モデル指定は gpt-4o-mini 等（ソース内定義）を使用。API コールの負荷・料金に注意してください。

- プロセス優先度
  - 実行スクリプトは起動時に set_process_priority("high") を呼びます。権限が無い環境では警告が出ますが動作は継続します。

---

## 主要ファイル・ディレクトリ構成（抜粋）

リポジトリの `src/kabusys` を想定した主要構成:

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings 管理（自動 .env ロード機能あり）
  - config_setup.py                 — 対話式 .env ウィザード
  - validate_config.py              — 起動前設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — 優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層（テーブル定義・CRUD）
    - system_monitor.py             — システム監視（CPU/メモリ/ディスク/データ鮮度）
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - trade_monitor.py (存在想定)  — 注文関連監視（ソースに依存）
    - monitoring_engine.py          — 複数モニタ束ねるエンジン
    - kill_switch.py                — kill.flag の生成 / 管理
    - alert_manager.py (存在想定)  — LINE 等への通知管理
  - execution/                       — ExecutionEngine 周り（OrderManager, RiskManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                    — ニュースを LLM でスコアリング
    - regime_detector.py             — マクロ + ETF でレジーム判定
  - tools/
    - paper_verification_report.py   — Paper Trading の性能検証レポート生成

（上記は実ファイルに基づく抜粋です。詳細なファイルは repo の tree を参照してください。）

---

## 使い方の例（簡単なワークフロー）

1. .env を作成（config_setup を利用）
2. validate_config で設定チェック
3. DuckDB / SQLite ファイルがなければ作成（起動スクリプトが自動的にテーブルを作ります）
4. Paper トレードで動作確認:
   - KABUSYS_ENV=paper_trading を設定
   - python -m kabusys.run_execution
   - python -m kabusys.run_monitoring
   - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
5. 本番移行は KABUSYS_ENV=live に変更し、設定を慎重に確認（validate_config の warning を重視）

---

## トラブルシューティング（よくある問題）

- 必須環境変数が未設定
  - validate_config で確認、必須項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）を .env に設定してください。

- OpenAI 関連で例外
  - OPENAI_API_KEY が未設定だと ValueError を投げます。テスト時は API をモックしてください。

- ログファイルが作れない
  - `LOG_DIR` のパスや権限を確認。作成失敗時はコンソールのみの出力になりますが動作自体は継続します。

- psutil 関連の権限エラー（プロセス優先度 / affinity）
  - root 権限が必要な操作がある場合は警告を出してスキップします。これは必須ではありません。

- DuckDB / SQLite の SQL エラー（テーブル存在しない等）
  - init_monitoring_db() は必要テーブルを作成しますが、schema mismatches が生じた場合はマイグレーションロジックを確認してください。

---

必要に応じて README に追記します。追加で以下を提供可能です:
- .env.example のテンプレート
- 実行時の systemd / supervisor の Unit ファイル例（デプロイ手順）
- より詳細なモジュール API ドキュメント（関数・パラメータ一覧）

ほかに README に含めたい項目や、デプロイ手順（systemd / Docker / Kubernetes）など希望があればお知らせください。