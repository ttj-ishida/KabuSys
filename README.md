# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアモジュールを含みます。取引実行エンジン、監視モジュール、リサーチ／ポートフォリオ構築ロジック、AIベースのニュース解析などが含まれます。

README ではプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤です。主要な責務は次の通りです。

- 市場データ（DuckDB の prices_daily 等）を使ったファクター/特徴量計算・リサーチ
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター・リスク調整）
- ExecutionEngine による発注管理（本番 / ペーパートレードを分離）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- ニュース NLP（OpenAI）を用いたセンチメントスコアリングおよび市場レジーム判定
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート など）

設計上のポイント：
- 設定は .env または環境変数で管理（`kabusys.config`）
- Paper trading と Live は DB を分離（paper_trading は data/paper_trading.db を使用）
- DuckDB を分析用 DB、SQLite を監視・履歴等の永続化に使用

---

## 機能一覧

主な機能（モジュール別）:

- 実行（execution）
  - ExecutionEngine（broker 接続、OrderManager、RiskManager、Reconciler 等）
  - BrokerClientFactory により実ボroker と MockBroker を切り替え（KABUSYS_ENV に応じる）
  - paper_trading 環境では MockBrokerClient と専用 SQLite を使用

- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス監視、データ鮮度チェック
  - TradeMonitor: 発注・約定ログの監視（滞留注文、約定異常など）
  - RiskMonitor: ドローダウン監視、ポジション上限監視、ダッシュボード更新
  - KillSwitch / MonitoringEngine / AlertManager による自動アラート・停止
  - 監視ログは SQLite (data/monitoring.db) に永続化

- ポートフォリオ（portfolio）
  - 銘柄候補選定、等重み／スコア重み計算
  - セクターキャップ適用、レジームに応じた乗数
  - ポジションサイズ（単元株丸め、aggregate cap、リスクベースなど）

- リサーチ（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（ai）
  - news_nlp: OpenAI を使ったニュースセンチメント集計 → ai_scores テーブルへ書込
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して日次レジーム判定

- ユーティリティ（utils）
  - logging_setup: stdout + 日次ローテートログ設定
  - process_priority: プロセス優先度 / CPU affinity の簡易設定
  - config_setup: .env 対話式ウィザード
  - validate_config: .env と config/*.yaml の事前検証

- ツール
  - paper_verification_report: ペーパートレード履歴から PASS/FAIL 判定の検証レポート生成

---

## 必要条件 / 推奨環境

- Python 3.10+（/ 3.11 推奨）
- 必須パッケージ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定検証で YAML 検査を行う場合）
- OS: Linux / macOS / Windows（機能差異は process_priority 等で吸収）

インストール例（仮の requirements がない場合の例）:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil openai PyYAML
```

（実際の requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

---

## セットアップ手順（初期設定）

1. リポジトリをクローンしてチェックアウト
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・依存パッケージインストール（上記参照）

3. .env を作成
   - 対話式ウィザードで作成するのが簡単です:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env を作成（.env.example を参考に）:
     主に必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（任意、例: INFO）

4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も fail にしたければ --strict を付ける
   ```

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 使い方（実行コマンド）

主要な起動スクリプトはモジュールとして実行できます。

- 監視ループ（SystemMonitor をポーリングして監視ログを書き、KillSwitch 評価等を行う）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60）。
  - run_monitoring は data/stop_requested.flag を検知すると終了します。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV にかかわらず）。

- Execution エンジン（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時 / 実行中に data/stop_requested.flag が存在すると起動を停止／実行中止します。
  - 実行中は data/execution.pid に PID を書きます。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定
  - 出力は標準出力に整形レポート（稼働率、成功率、レイテンシ等）

- .env ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- AI スコアリング / レジーム判定（ライブラリ関数として利用）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数で渡す）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

---

## 運用上のポイント

- プロセス優先度:
  - run_monitoring / run_execution は起動時に `set_process_priority("high")` を呼び出して高優先度に設定しようとします（権限不足の場合は警告を出してスキップ）。

- 停止フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution が監視している「実行停止」フラグ
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine 停止を要求（本番での自動停止目的）
  - Settings.kill_flag_clear_on_start を `1` にすると起動時に kill.flag を自動クリアします（本番では `0` 推奨）

- ロギング:
  - デフォルトは stdout と日次ローテーションファイル（logs/<app_name>.log）
  - 環境変数 `LOG_LEVEL` / `LOG_DIR` で調整可能

- DB:
  - DuckDB は分析用で大きなテーブル（prices_daily, raw_financials など）を格納
  - SQLite は監視ログ・トレードログ等の永続化（monitoring.db, paper_trading.db）

- AI/LLM:
  - news_nlp と regime_detector は OpenAI API（モデル: gpt-4o-mini 等）を利用します。API 呼び出しはリトライ・バックオフを備え、失敗時は安全なフォールバック（例: macro_sentiment=0.0）を行います。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル/ディレクトリの構成（src/kabusys 以下）です。実際のリポジトリのトップレベルはプロジェクトルートになります。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — Monitoring のポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト

  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度設定

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — （注文系監視）※実装ファイル参照
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 書込みロジック
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （通知管理）※実装ファイル参照

  - execution/
    - execution_engine.py     — 発注エンジン本体（EngineConfig, run_session 等）
    - broker_factory.py       — ブローカクライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

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

  - monitoring/ (上記)
  - tools/
    - paper_verification_report.py

- data/                      — デフォルト DB ファイル等（自動作成される）
- logs/                      — ログ出力先（設定可能）

---

## よくある質問（FAQ）

Q: 本番用の KABUSYS_ENV の設定は？
- KABUSYS_ENV は development / paper_trading / live のいずれか。live は本番（実際に発注されます）。設定ミスを防ぐため validate_config は live の際に追加警告を出します。

Q: ペーパートレードと本番の DB は分離されていますか？
- はい。paper_trading モードでは `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用し、本番監視 DB（SQLITE_PATH）とは分離されます。

Q: 停止はどうやって行いますか？
- run_monitoring と run_execution は data/stop_requested.flag を検知するとループを抜けます。KillSwitch が重大事象を検出した時は data/kill.flag に理由を書き込み、ExecutionEngine 側で停止処理を行います。

Q: OpenAI の使用に必要な設定は？
- `OPENAI_API_KEY` を環境変数にセットするか、該当関数の引数に API キーを渡してください。モデルはコード内で指定（例: gpt-4o-mini）。

---

## 開発・拡張のヒント

- DuckDB 接続を渡すと多数の research/ai モジュールが SQL と Python を組み合わせてデータを処理します。ローカルで DuckDB に最低限のテストデータを入れてユニットテストを作成すると良いです。
- LLM 呼び出し部分は外部通信であるため、テスト時は `_call_openai_api` のパッチ（モック）を推奨します（コード内にそのための記述あり）。
- logging_setup を各スクリプトの最初に呼ぶことで統一されたログ運用が可能です。

---

必要なら、README に含める具体的な .env サンプルや起動スクリプトのシステムd ユニットファイル例、より詳しいディレクトリツリー（全ファイル列挙）を追加できます。どの情報を追記しましょうか？