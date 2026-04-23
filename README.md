# KabuSys

日本株自動売買システムの一部（ライブラリ・運用ユーティリティ群）。  
本リポジトリには監視、発注実行、ポートフォリオ構築、リサーチ、AI（ニュースNLP／レジーム判定）などのコンポーネントが含まれます。

バージョン: 0.1.0

---

## 概要

このプロジェクトは日本株の自動売買を支えるコンポーネント群を提供します。主な役割は以下の通りです。

- ExecutionEngine：発注管理、ブローカーインターフェース、リスク管理、発注の再整合（reconciler）などの実行ロジック
- Monitoring：システム状態・注文状況・リスク（ドローダウン・ポジション数）を定期監視し、必要時に Kill Switch（停止フラグ）やアラートを発動
- Portfolio：銘柄選定・重み付け・ポジションサイズ計算・セクター制約・レジームによる調整
- Research：DuckDB を用いたファクター計算（Momentum / Volatility / Value）や将来リターン、IC 計算
- AI：OpenAI を利用したニュースのセンチメントスコアリング（news_nlp）や市場レジーム判定（regime_detector）
- Tools：ペーパートレード向けの検証レポート生成などのユーティリティ

多くのモジュールは「外部 API による発注を直接行わない」「DuckDB / SQLite によるデータ参照」「環境変数による設定管理」を方針としています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用して paper DB に記録）
  - run_monitoring.py：SystemMonitor のポーリングループを起動（監視用 sqlite を使用）
- 設定管理
  - config_setup.py：対話式 .env 作成ウィザード
  - validate_config.py：.env と config/*.yaml の事前検証
- 監視（monitoring）
  - system_monitor：CPU/メモリ/ディスク・データ鮮度・実行プロセス生存の検査とログ化
  - trade_monitor：注文ログの整合性・滞留注文・約定異常を検出（ソース内に実装あり）
  - risk_monitor：ドローダウンやポジション上限の監視、リスクイベント記録
  - kill_switch：条件により data/kill.flag を書き込んで Execution を停止
  - monitoring_engine：複数モニタを束ねてポーリング、アラートの送出
- ポートフォリオ（portfolio）
  - 銘柄候補選定、等金額・スコア重み付け、リスクベースのポジションサイズ計算、セクター上限適用、レジーム乗数
- リサーチ（research）
  - DuckDB 接続経由でモメンタム／ボラティリティ／バリュー等のファクター計算、将来リターン、IC（スピアマン）計算
- AI（OpenAI）
  - news_nlp.score_news：ニュースを LLM でスコア化して ai_scores テーブルに保存
  - regime_detector.score_regime：ETF の MA とマクロ NLP を合わせて市場レジーム判定を行い DB に保存
- ツール
  - tools.paper_verification_report：ペーパートレードの稼働率や注文成功率等の検証レポート生成

---

## セットアップ手順（開発 / ローカル実行向け）

1. リポジトリをクローン、Python 仮想環境を作成・有効化
   - 例（Unix 系）:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージのインストール（最低限の候補）
   - pip install duckdb psutil openai PyYAML
   - 実際の requirements.txt はプロジェクトに合わせて用意してください。

3. .env の作成
   - 対話式で作る（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成

4. 設定検証
   - python -m kabusys.validate_config
   - 本番相当の厳格チェックを行う場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ（例: data/）やログディレクトリの作成は自動作成されることが多いですが、権限等に不安がある場合は手動で作成してください。

注意:
- OpenAI を使う機能（news_nlp / regime_detector）は OPENAI_API_KEY が必要です。
- ペーパートレード時は本番 SQLite DB と分離され、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）が使用されます。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（設計上の意図）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

推奨 / 主要:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — paper_trading の MockBroker の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)

運用に関するファイル:
- data/kill.flag — kill switch（ExecutionEngine を停止させるために監視側が書き込む）
- data/stop_requested.flag — 起動スクリプト（monitoring/execution）の外部停止フラグ
- data/execution.pid — ExecutionEngine の PID（起動時に書き込まれる）

補足:
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能。ただし 0 以下は無効でデフォルト 60 秒にフォールバックされます。
- Monitoring の DB 初期化は init_monitoring_db() によって冪等に行われます。起動時にテーブルがなければ作成されます。

---

## 使い方（起動と主なコマンド）

- 環境ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - 動作概要:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録
    - 起動前に data/stop_requested.flag がある場合は起動せず終了
    - 実行は別スレッドで行われ、監視フラグ（stop_requested.flag）を見て停止する

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - 動作概要:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）
    - 監視は本番用の SQLITE_PATH を使用（KABUSYS_ENV に依存しない）
    - data/stop_requested.flag を検出でループを終了

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI（ニューススコアリング、レジーム判定）の呼び出し:
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - ※内部で OpenAI API を呼ぶため OPENAI_API_KEY の設定が必要

ログ:
- ログはデフォルトで stdout（コンソール）と logs/<app_name>.log（日次ローテーション、30日保持）へ出力されます。setup_logging() を各起動スクリプトで利用しています。

停止 / Kill:
- 監視による停止（Kill Switch）が発動すると data/kill.flag に理由を書き込みます。Execution 起動時には kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）を制御できます。
- 手動で停止したい場合は data/stop_requested.flag を作成してください（run_execution/run_monitoring はこの flag を検出して安全に終了します）。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要なモジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env の読み込みと Settings クラス
  - config_setup.py           — 対話式 .env 作成ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し、ai_scores への書き込み）
    - regime_detector.py      — 市場レジーム判定（MA + マクロ NLP）
    - __init__.py
  - portfolio/
    - portfolio_builder.py    — 銘柄選定・スコアソート
    - position_sizing.py      — 発注株数決定（risk_based / equal / score）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite 用永続化層（テーブル初期化・読み書き）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文監視（滞留・異常価格等）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の管理
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - utils/
    - logging_setup.py        — 統一的なロギング設定
    - process_priority.py     — プロセス優先度 / CPU affinity 設定

data/、logs/ 等のランタイムファイルはプロジェクトルートに作成されます（.env のパス指定により変更可能）。

---

## 運用上の注意とベストプラクティス

- 本番環境（KABUSYS_ENV=live）では .env や設定値に注意を払い、validate_config の結果を必ず確認してください。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。デフォルト 0 を推奨します。
- Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を参照します。開発で monitoring を動かす際はファイルパスを分離するか注意してください。
- OpenAI を用いる処理は API エラーやレート制限が発生する可能性があるため、ログを確認してバックオフやフォールバックが適切に動作していることを確認してください。
- 重要な DB ファイルや .env ファイルは絶対に Git にコミットしないでください（config_setup でも注意喚起があります）。

---

必要に応じて README にサンプル .env や起動ユースケース（開発と本番の設定差、docker-compose 例、systemd サービス定義など）を追加できます。追加したい内容があれば教えてください。