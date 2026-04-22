# KabuSys

日本株向け自動売買システムのリポジトリ (初期バージョン)。  
本ドキュメントはコードベースの主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめた README.md です。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・モニタリングを目的としたモジュール群です。主な特徴は次のとおりです。

- ExecutionEngine（発注エンジン）：本番 / ペーパートレードでの注文管理・発注制御
- Monitoring（監視）：システム状態、注文状況、リスク（ドローダウン・ポジション数等）を定期チェックし、必要に応じて Kill Switch（停止フラグ）を発動
- Research：DuckDB を使ったファクター計算・特徴量解析ユーティリティ
- Portfolio：候補選定、重み付け、株数計算（単元丸め・リスク制約）
- AI モジュール：OpenAI を用いたニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- ユーティリティ群：設定読み込み (.env), ログ設定、プロセス優先度設定 等
- ツール：Paper Trading 検証レポート生成スクリプト等

設計上の留意点：
- .env / 環境変数で設定を管理（自動ロード機能あり）
- Paper Trading（模擬発注）は本番 DB と分離（data/paper_trading.db 等）
- AI 機能は OpenAI API キーを必要とする（フェイルセーフ実装あり）

---

## 機能一覧（抜粋）

- 設定・起動関連
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config、--strict モードあり）
- 実行 / 発注
  - run_execution.py：ExecutionEngine 起動（KABUSYS_ENV により Paper/Live 切替）
  - BrokerClientFactory を介したブローカークライアント抽象化（Paper は Mock）
  - 発注履歴・ログは SQLite（monitoring.db）へ記録
- 監視
  - run_monitoring.py：SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可）
  - MonitoringEngine：System / Trade / Risk モニタを束ね、Kill Switch 発動やアラート送信
  - MonitoringDB：SQLite に対する永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構築
  - 銘柄選定、等配分 / スコア配分、リスクベースのポジション決定、セクターキャップ、レジーム乗数
- リサーチ
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC 計測、統計サマリー
- AI（LLM）
  - ニュースから銘柄ごとのセンチメントを算出し ai_scores に書き込む
  - マクロニュース + ETF MA を組み合わせて市場レジームを判定
  - OpenAI API の呼び出しはリトライ・バックオフやパース保護を備える
- ツール
  - paper_verification_report：ペーパートレード DB を集計して PASS/FAIL 判定レポートを出力

---

## セットアップ手順

前提：
- Python 3.9+（DuckDB / psutil / openai 等の対応を満たすバージョン）
- SQLite（標準ライブラリに同梱）
- ネットワーク接続（本番ブローカー・OpenAI を利用する場合）

必須パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（設定検証で YAML のパースを行う場合）

インストール例（venv を推奨）:
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install duckdb psutil openai pyyaml
```

設定ファイル（.env）
1. 対話式で .env を作成：
   ```
   python -m kabusys.config_setup
   ```
   - 各キーの説明が表示され、デフォルト / 既存値を参照して編集できます。
2. 作成後、設定を検証：
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告もエラー扱い
   ```

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development) — 有効値: development / paper_trading / live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- PAPER_FILL_MODE（paper_trading の約定動作）: instant | partial | never | reject

自動 .env ロード
- デフォルトでプロジェクトルートの .env/.env.local を自動読み込みします。
- 無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

ログ
- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

DB 初期化
- monitoring に必要なテーブルは MonitoringDB.init_monitoring_db() で作成します。起動スクリプトが自動で呼び出します。

---

## 使い方（起動・主要コマンド例）

1. .env を作成・編集して必要なキーを設定
2. 設定確認
   ```
   python -m kabusys.validate_config
   ```

3. 監視プロセス起動（ポーリング）
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能。デフォルト 60 秒。
   ```
   python -m kabusys.run_monitoring
   ```
   - 実行プロセスはプロセス優先度を High に設定（可能な場合）。
   - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず本番 DB へ記録）。

4. 発注エンジン（Execution）起動
   - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
   ```
   python -m kabusys.run_execution
   ```
   - engine はデーモンスレッドで run_session() を実行し、data/stop_requested.flag を見ることで停止します。
   - 実行時に pid ファイル (data/execution.pid など) を出力します。

5. Kill Switch / 手動停止制御
   - Kill Switch（監視が条件を満たすと書き込む）: data/kill.flag
   - 手動で停止を要求する際は data/stop_requested.flag を作成すると run_execution/run_monitoring のループが終了します。
   - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると Kill Flag を自動クリアします（本番では 0 推奨）。

6. Paper Trading 検証レポート
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で変更可能）
   - レポートは稼働率、注文成功率、送信率、レイテンシ (P95) などを評価して PASS/FAIL を出力します。

7. AI 機能（ニュース NLP / レジーム判定）
   - OPENAI_API_KEY を環境変数に設定してから呼び出します。
   - ニューススコアリング:
     ```
     # 例: Python REPL 内で
     from datetime import date
     import duckdb
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, target_date=date(2026,4,1), api_key=None)  # api_key None の場合は環境変数を使用
     ```
   - レジーム判定（regime_detector.score_regime）も同様に DuckDB 接続と API キーが必要です。

注意点：
- monitoring/run_execution はそれぞれ DB コネクション（SQLite / DuckDB）を作成して使用します。ファイルパスは .env で制御可能です。
- Paper Trading と Live はデータ分離を意識して設定してください。

---

## 主要ファイル / ディレクトリ構成

以下は src/kabusys 配下の主要モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 読み込み / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ（Stream + 日次ローテート）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite ベースの監視 DB 層
    - system_monitor.py      — システム状態 / データ鮮度チェック
    - trade_monitor.py       — （Trade モニタ: 注文滞留・異常検出等）※コード中に参照あり
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねるオーケストレータ
    - kill_switch.py         — フラグファイルによる停止（書き込み/クリア）
    - alert_manager.py       — （アラート送信管理）※コード中に参照あり
  - execution/
    - execution_engine.py    — ExecutionEngine（発注セッション管理）※主要ロジック
    - broker_factory.py      — ブローカークライアント生成（Mock 含む）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定、等/スコア配分
    - position_sizing.py     — 株数決定・資金配分・単元丸め
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Value / Volatility 計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー 等
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄センチメント算出
    - regime_detector.py     — MA + マクロニュースを合成したレジーム判定

注意：一部ファイル（trade_monitor.py, alert_manager.py, execution の内部実装等）はこの抜粋に含まれていない箇所がありますが、上記が主要な構成要素です。

---

## 追加情報 / 運用上の注意

- デフォルトのログ・DB パスはプロジェクト相対の `logs/` や `data/` に配置されます。コンテナやサーバでの運用時はボリュームマウントや適切なパスを .env で指定してください。
- 本番（KABUSYS_ENV=live）での起動前には必ず `python -m kabusys.validate_config` を実行して設定を検証してください。LINE 通知等の設定欠落に関する警告も出ます。
- Kill Switch（自動停止）やリスクイベントのロギングは冪等（同一イベントの短時間重複登録回避）を意識した実装になっていますが、運用ポリシー（通知頻度、アラート受け取り）を事前に決めてください。
- OpenAI API 呼び出しはレート制限 / 5xx / ネットワークエラーを考慮してリトライやバックオフを行いますが、API 利用料・キー漏洩には十分ご注意ください。

---

問題や補足が必要であれば、どの部分の説明をより詳しく書いてほしいか教えてください。README のサンプル .env テンプレートを要望いただければ、例も作成します。