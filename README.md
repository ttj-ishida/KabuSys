# KabuSys — README

以下はこのコードベース（KabuSys）の簡易ドキュメントです。日本株向け自動売買システムの各コンポーネント（Execution / Monitoring / Research / AI / Portfolio 等）を含みます。本書はプロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成をまとめたものです。

重要: 本リポジトリは取引処理を伴うため、実運用（live 環境）で実行する前に十分な確認と環境分離（Paper Trading）を行ってください。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（主な設定）
- 使い方（起動 / 停止 / ツール）
- ディレクトリ構成
- 開発・デバッグのヒント

---

## プロジェクト概要

KabuSys は日本株の自動売買フレームワークです。主な責務は次のとおりです。

- 戦略に基づく銘柄選定およびポジションサイズ計算（portfolio）
- 注文の送信・状態管理・再整合（execution）
- システム稼働監視・注文監視・リスク監視およびアラート（monitoring）
- 研究用ファクター計算・特徴量探索（research）
- ニュースを用いた NLP スコアリングやレジーム検出（ai）
- Paper Trading の検証・レポート出力用ツール（tools）

設計方針として、DB（SQLite / DuckDB）を利用した永続化、外部 API（kabuステーション、OpenAI、J-Quants 等）との分離、フェイルセーフな動作を重視しています。

---

## 機能一覧

- Execution
  - Broker クライアントを介した注文作成・送信・同期
  - 再起動時のリコンシリエーション（Reconciler）
  - RiskManager による発注制限（レート制限・最大建玉割合等）
  - Paper Trading モード（MockBrokerClient と専用 SQLite DB を使用）

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセスの生存確認、株価データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常検知
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード集計更新
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）書き込み
  - AlertManager：LINE Push によるアラート送信（オプション）
  - Streamlit ダッシュボード（監視情報の可視化）

- Research / Portfolio
  - momentum / volatility / value ファクター計算（DuckDB）
  - forward returns / IC / 統計サマリー
  - 候補選定、等重・スコア重み付け、セクターキャップ、ポジションサイズ計算

- AI
  - news_nlp: OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング（ai_scores テーブルへ書込）
  - regime_detector: MA200 とマクロニュースセンチメントを組み合わせた市場レジーム判定

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）

---

## セットアップ手順

以下はローカル開発／検証用の一般的な手順です。実運用環境では OS のサービス化やプロセス管理ツール（systemd, supervisord 等）を推奨します。

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   ※ requirements.txt が無い場合は少なくとも次を入れてください:
     - duckdb, psutil, requests, openai, streamlit

4. data ディレクトリを作成（必要に応じて）
   - mkdir -p data

5. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を配置するか、シェルで環境変数を設定します。
   - 自動読み込みはデフォルトで有効（config.py）。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

6. DB 初期化
   - 監視用 SQLite（data/monitoring.db）や Paper Trading 用 DB（data/paper_trading.db）は、run スクリプトで必要なテーブルが自動作成されます（init_monitoring_db）。

---

## 環境変数（主なもの）

Settings クラス（src/kabusys/config.py）で定義されている主要な環境変数：

必須
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（research 等で必要な場合）
- KABU_API_PASSWORD: kabuステーション API 用パスワード

任意 / デフォルトあり
- KABUSYS_ENV: 起動環境。development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: ログレベル（INFO 等）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject、デフォルト: instant）
- PID_FILE_PATH: Execution の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch が書き込むフラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: "1" で起動時に kill.flag をクリア
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

例（.env）
KABUSYS_ENV=development
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...

---

## 使い方（主要コマンド）

 package を PYTHONPATH に含めている前提で、モジュール実行が可能です（あるいはスクリプトを直接実行）。

1. ExecutionEngine を起動（注文エンジン）
   - python -m kabusys.run_execution
   - 動作:
     - Process 優先度を high に設定
     - BrokerClient を生成（KABUSYS_ENV=paper_trading なら MockBroker を使用）
     - Paper Trading 時は PAPER_TRADING_SQLITE_PATH（例: data/paper_trading.db）を使用して本番 DB と分離
     - data/execution.pid に PID を書き、stop フラグ（data/stop_requested.flag）または kill.flag を検知すると停止

2. Monitoring（SystemMonitor 単体ポーリングスクリプト）
   - python -m kabusys.run_monitoring
   - 動作:
     - Process 優先度を high に設定
     - 監視 DB（sqlite_path）へ system_status 等を保存
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（秒、デフォルト 60）
     - data/stop_requested.flag を検知するとループを抜けて終了

3. Streamlit ダッシュボード（監視 UI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ローカルで監視 DB（read-only）を開いて可視化

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで DB パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）
   - レポート出力：稼働率、注文成功率、送信率、P95 レイテンシ など

5. AI 関連
   - ニューススコアリング（programmatically 呼び出し）
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key=...)
   - レジーム判定
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key=...)

6. 停止 / フラグ運用
   - 強制停止（Execution / Monitoring 共通）:
     - data/stop_requested.flag を作成すると run_* スクリプトが検知して終了します（これらは同じ stop flag を参照しています）
   - Kill Switch（自動停止判定）:
     - RiskMonitor → KillSwitch が条件を満たすと data/kill.flag に理由を書き込み Execution に停止シグナルを送ります
   - kill.flag を手動でクリア:
     - 呼び出し側プロセス（Execution 起動時に）または手動で削除してください（Settings.kill_flag_clear_on_start=1 で起動時クリア）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート用 CLI
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - …（注文関連実装）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
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
    - process_priority.py

データファイル（プロジェクトルート）
- data/
  - monitoring.db (デフォルトの監視 DB; Settings.sqlite_path)
  - paper_trading.db (Paper Trading 用 DB)
  - execution.pid
  - stop_requested.flag
  - kill.flag
  - kabusys.duckdb (DuckDB データストア)

---

## 開発・デバッグのヒント

- 環境変数の自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）にある .env / .env.local を自動で読み込みます。
  - テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット。

- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると BrokerClientFactory が MockBrokerClient を生成し、paper_sqlite_path（data/paper_trading.db）へ書き込みます。本番 DB と分離されるため安全に検証できます。

- OpenAI 呼び出しのテスト:
  - news_nlp._call_openai_api や regime_detector._call_openai_api はテスト時に patch して外部 API 呼び出しを抑制できます（unittest.mock.patch）。

- ローカルで DuckDB を使って research 関数を実行する場合は DuckDB ファイル（DUCKDB_PATH）を指定して接続してください。

- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を呼びます。psutil の権限不足などで警告ログが出ることがありますが、それ自体は致命的ではありません。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は既存 DB にないカラム（例: peak_value, latency_ms）を検出して追加する簡易マイグレーションを行います。

---

## 安全上の注意

- live 環境で実行する際は、KABUSYS_ENV=live を設定していることを再確認してください。Paper Trading と live は DB・動作が分離されているものの、実売買を伴うため必ず十分な確認を行ってください。
- API キーやパスワードは .env に平文で置く場合はアクセス制御に注意してください。
- 実行中のプロセスは PID ファイルを参照して stale PID 検出等を行います。PID ファイルの手動編集は推奨されません。

---

README は以上です。必要であれば各モジュール（execution, monitoring, ai, research）ごとの詳細な API ドキュメント、サンプル設定ファイル、systemd ユニット例や Docker-compose による起動手順なども追記できます。どの情報を追加したいか教えてください。