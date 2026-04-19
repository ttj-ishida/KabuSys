# KabuSys

日本株自動売買フレームワークの軽量プロトタイプ。  
ポートフォリオ構築・ポジションサイジング、モニタリング、ExecutionEngine（発注管理）、AIベースのニューススコアリング・レジーム判定、Research（ファクター計算）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

このリポジトリは、以下の主要機能を持つ自動売買 / 研究基盤を想定した Python パッケージです。

- ExecutionEngine（実際の/模擬ブローカーを用いた発注実行）
- Monitoring（システム健全性・発注ログ・リスク監視）
- Kill Switch（閾値到達時に ExecutionEngine を停止）
- Portfolio construction: 候補選定、重み計算、ポジションサイズ計算、セクター制限等
- Research: ファクター計算（Momentum / Volatility / Value 等）、特徴量探索
- AI: ニュースの NLP による銘柄スコアリング、マクロニュース + MA に基づく市場レジーム判定
- ユーティリティ群: ログ設定、プロセス優先度、.env ウィザード、設定検証、レポート生成ツール 等

設計方針として、DB（SQLite / DuckDB）を利用したオフライン処理と、外部 API（kabuステーション / J-Quants / OpenAI 等）への接続を分離・抽象化しています。Paper Trading 環境は本番 DB と完全分離される仕組みを備えています。

---

## 主な機能一覧

- Execution
  - BrokerClientFactory による実ブローカー / MockBroker の切替（KABUSYS_ENV=paper_trading 時に Mock を使用）
  - ExecutionEngine（エンジンの起動 / 停止、PID ファイル管理）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働・データ鮮度監視
  - TradeMonitor: 発注ログの監視（滞留注文・約定異常など）
  - RiskMonitor: ドローダウン、ポジション上限監視、ダッシュボード更新
  - MonitoringEngine: 上記を束ね、定期的にポーリング・アラート通知・Kill Switch 評価
  - SQLite ベースの永続化層（monitoring_db）
- Portfolio
  - 候補選定（score / rank）、等重・スコア重み、ポジションサイズ計算（ロット丸め、資金配分、aggregate cap）
  - セクター制限、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - news_nlp: OpenAI を用いたニュースセンチメントの銘柄スコア化（ai_scores への書き込み）
  - regime_detector: ETF ma200 とマクロニュースの LLM スコアを組み合わせたレジーム判定
- ツール
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）
- ユーティリティ
  - 一貫したログ設定（ログローテーション）、プロセス優先度 / CPU affinity 設定、.env パーサ

---

## 前提（Prerequisites）

- Python 3.9+
- 必要パッケージ（一部抜粋）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- SQLite（標準ライブラリで利用可能）

要件ファイルは本リポジトリに含まれていない想定です。以下は例です：

pip install duckdb psutil openai PyYAML

（実運用時は requirements.txt を用意することを推奨します）

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成

   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   ```

2. 必要ライブラリをインストール

   ```
   pip install duckdb psutil openai PyYAML
   ```

3. 初期設定（.env の作成）

   - 対話式ウィザードで .env を生成：

     ```
     python -m kabusys.config_setup
     ```

     ウィザードは default / secret / optional の項目を案内します。生成後、`python -m kabusys.validate_config` で検証してください。

   - もしくは手動で .env を作成して環境変数を設定してください（以下に主なキー一覧を参照）。

4. DB ディレクトリ作成（必要に応じて）

   デフォルトで以下を利用します。これらの親ディレクトリは起動時に自動作成される場合がありますが、手動で作成して権限等を確認しておくと安全です。

   - data/kabusys.duckdb
   - data/monitoring.db
   - data/paper_trading.db (paper_trading 用)

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意（デフォルト値あり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）
- LOG_DIR: logs/
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0|1（起動時に kill.flag を自動クリア）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の擬似約定モード）

モニタリング設定（デフォルトあり）:
- CPU_THRESHOLD_PCT (例: 90.0)
- MEMORY_THRESHOLD_PCT
- DISK_THRESHOLD_PCT

その他:
- OPENAI_API_KEY — OpenAI API を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（optional）

詳しくは `src/kabusys/config.py` 内の Settings クラスを参照してください。

---

## 使い方（起動コマンド例）

package をパスに含めている状態を前提に、モジュールを -m で起動します。

- 設定検証（CLI）

  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 環境設定ウィザード（.env 作成）

  ```
  python -m kabusys.config_setup
  ```

- Monitoring（常駐プロセス、デフォルトは 60 秒ポーリング、環境変数 MONITOR_POLL_INTERVAL で上書き可）

  ```
  python -m kabusys.run_monitoring
  ```

  停止：
  - プロセスを Ctrl+C で止めるか、プロジェクトルートの `data/stop_requested.flag` ファイルを作成するとループを終了します。

  ポーリング間隔の上書き（秒）:

  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- ExecutionEngine（発注エンジン起動）

  ```
  python -m kabusys.run_execution
  ```

  Paper trading（MockBroker を使用し paper DB に書き込む）:

  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  停止：
  - `data/stop_requested.flag` を作成すると実行中のエンジンに停止要求が送られます。
  - 実行中は PID ファイル（デフォルト `data/execution.pid`）を作成します。

- Paper Trading 検証レポート生成

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

  DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI スコア / レジーム判定（ライブラリ API として呼び出す例）

  Python REPL などで DuckDB 接続を渡して呼び出します（OPENAI_API_KEY が必要）:

  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026, 4, 10))
  ```

  同様に regime_detector の `score_regime` を呼んで market_regime テーブルに書き込みます。

---

## ログとファイルの扱い

- ログ: デフォルト `logs/<app_name>.log`（日次ローテート 30 日保持）。環境変数 `LOG_DIR` でディレクトリ指定、`LOG_LEVEL` でレベル指定。
- kill.flag（Kill Switch）: `KILL_FLAG_PATH`（デフォルト `data/kill.flag`）へ理由を書き込むことで ExecutionEngine 停止を要求します。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアします（本番では推奨しません）。
- stop_requested.flag: `data/stop_requested.flag`（起動スクリプトが参照）を作成すると run_monitoring / run_execution のループが終了します。
- PID ファイル: `data/execution.pid`（ExecutionEngine 起動時に使用/作成）。

---

## 注意点 / 運用メモ

- Monitoring は常に "本番" の sqlite_path を使って監視データを書きます（run_monitoring は KABUSYS_ENV に関わらず本番 monitoring DB を使用）。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全に分離します。
- OpenAI を用いる `news_nlp` / `regime_detector` は API のレートやエラーに対してリトライやフェイルセーフロジックを組み込んでいますが、API キー管理・コスト面には注意してください。
- `config/*.yaml` は設定ファイル群（自動生成スクリプト有）。PyYAML がインストールされていない場合は検証ステップでスキップされます。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主要なファイル/モジュールです（抜粋）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成 / CRUD）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （発注監視に関する実装: ファイル内では参照）
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねる
    - alert_manager.py       — （アラート送信機構: LINE 等、実装参照）
  - execution/
    - execution_engine.py    — ExecutionEngine（起動、run_session等）
    - broker_factory.py      — Broker クライアント生成（実ブローカー/Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算（ロット丸め、aggregate cap）
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — IC / 統計サマリー等
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

（実際のリポジトリにはさらに細かい実装ファイルが含まれます）

---

## 開発・拡張のヒント

- DuckDB 接続を渡す設計なので、分析処理（research）は DB を用いたバッチ処理として分離できます。
- Broker の具象実装は Factory パターンで切替可能（Mock と実ブローカーで同一インターフェースを提供することが重要）。
- ログや監視イベントは monitoring_db 経由で永続化されるため、外部ダッシュボード連携や可視化に活用できます。
- AI 周りはレスポンスバリデーションと一貫したクリッピング（±1.0）・リトライ処理を実装済み。モデルやプロンプトを変更する場合はユニットテストを追加してください。

---

## ライセンス / コントリビューション

本プロジェクトのライセンス・貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（ない場合はリポジトリ管理者に確認してください）。

---

必要であれば README にサンプル .env.example を追加したり、requirements.txt / Dockerfile / systemd ユニット定義の例を追記できます。どの情報を追加したいか教えてください。