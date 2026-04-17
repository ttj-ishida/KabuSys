# KabuSys

日本株自動売買システムの一部をまとめたリポジトリ（ライブラリ）。  
この README は与えられたコードベースに基づき、導入・実行方法、主要機能、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ／監視を目的としたモジュール群です。主な機能は以下の通りです:

- ExecutionEngine（発注エンジン）と Execution 用ユーティリティ
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- ニュース NLP を用いた銘柄別センチメント評価（OpenAI API を利用）
- 市場レジーム判定（MA + マクロセンチメントの合成）
- SQLite / DuckDB を使ったデータ永続化・分析
- 開発用ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

設計上の特徴：
- 本番／ペーパートレードを環境変数で切替可能（KABUSYS_ENV）
- OpenAI 呼び出しは失敗時にフォールバック（フェイルセーフ）
- モジュールごとに副作用を抑えた純粋関数や DB 層を分離

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）、対話式ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行 (Execution)
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用して paper DB に記録）
  - Execution 側は PID ファイル・停止フラグ（data/stop_requested.flag / data/kill.flag）で制御
- 監視 (Monitoring)
  - run_monitoring.py: SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔指定）
  - MonitoringEngine により System / Trade / Risk のチェック、アラート、Kill Switch の評価を実行
  - monitoring_db: 監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）
- ポートフォリオ構築
  - 候補選定（select_candidates）、等配分／スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）、セクターキャップ適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
- リサーチ
  - ファクター計算（momentum / value / volatility）、forward returns、IC、統計サマリー
  - DuckDB を使った SQL ベースの計算
- AI（OpenAI）
  - news_nlp.score_news: raw_news を集約して OpenAI に送信、ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF(1321) MA + マクロニュースを LLM で評価し market_regime に保存
- ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを出力

---

## セットアップ手順（ローカル）

前提: Python 3.9+ を想定（duckdb, psutil, openai 等が必要）。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai
   - （任意）YAML 検証を行う場合: pip install PyYAML

   ※ requirements.txt がない場合は上記を目安にインストールしてください。

4. .env の準備（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
     - 対話に従って .env を作成します（.env は機密情報を含むため絶対に Git にコミットしないでください）
   - 作成後、設定検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告もエラー扱いになります

5. データディレクトリ
   - デフォルトの DB パスは data/ 以下を想定しています。必要に応じてディレクトリを作成してください（多くのコードが親ディレクトリを自動作成しますが、念のため）。
   - 例: mkdir -p data

6. OpenAI を利用する場合は API キーを設定
   - 環境変数: OPENAI_API_KEY=your_key
   - もしくは、score_news / score_regime の api_key 引数に直接渡すことも可能

---

## 環境変数（主なもの）

（デフォルト値や説明はコードの Settings / config_setup 定義に基づきます）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード

- 実行環境
  - KABUSYS_ENV (default: development)
    - development / paper_trading / live

- DB 関連
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 SQLite、default: data/paper_trading.db)

- ログ・監視
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, default: INFO)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0|1, default: 0) — 起動時に kill.flag を自動クリアするか（注意: 本番では 0 推奨）

- Monitoring
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）

- PAPER_FILL_MODE (paper_trading の MockBroker 動作)
  - instant | partial | never | reject （default: instant）

- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector などで使用

その他の閾値（CPU, memory, disk 等）は Settings で確認できます（CPU_THRESHOLD_PCT 等）。

---

## 使い方（主なコマンド例）

- .env を作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番・ペーパー共通ランチャー）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag があれば起動をスキップします。
    - 実行中は PID ファイルを書きます（デフォルト data/execution.pid）。stop リクエストは stop_requested.flag を作成して行えます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60）
  - 監視は環境にかかわらず本番 sqlite_path を使い監視テーブルを操作します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で別パス指定可

- AI / リサーチ用関数（プログラム的に利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum(conn, date), calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary など

---

## 停止・Kill Switch の仕組み

- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch.evaluate が条件を満たすとファイルを書き込み、ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 側は起動時にこのフラグを検査し、フラグ存在時は起動しないか実行中に停止処理を行います。
  - KILL_FLAG_CLEAR_ON_START=1 を使うと起動時にフラグを自動でクリアできますが、本番では推奨されません。

- stop_requested.flag
  - run_execution.py / run_monitoring.py が監視している停止フラグファイル（data/stop_requested.flag）。存在すればループを抜けます。

---

## ディレクトリ構成（主要ファイル）

以下はコードベース（src/kabusys）に含まれる主要モジュールと概要です。

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — 環境変数・設定取得ロジック（Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine ランチャー
  - run_monitoring.py — SystemMonitor ポーリングランチャー
  - utils/
    - process_priority.py — プロセス優先度 / CPU アフィニティのヘルパ
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・CRUD（MonitoringDB）
    - system_monitor.py — CPU/memory/disk・データ鮮度・PID チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書込み / 評価
    - monitoring_engine.py — 全モニタを束ねるエンジン
    - alert_manager.py — （アラート送信を担う想定の責務）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・資金配分・丸めロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — Momentum / Value / Volatility ファクター
    - feature_exploration.py — forward returns, IC, summary
    - __init__.py
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書込む
    - regime_detector.py — MA とマクロセンチメントを組み合わせて market_regime を決定
    - __init__.py
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - monitoring_db migration logic（テーブル追加/カラム追加の冪等処理あり）
  - その他（execution 関連モジュール、data/strategy モジュール等は別ファイル群で想定）

---

## 重要な注意事項 / トラブルシューティング

- .env に機密情報（API トークン、パスワード等）を保存する際は絶対に Git にコミットしないでください。
- OpenAI 関連機能を使うには OPENAI_API_KEY を設定する必要があります。未設定だと score_news / score_regime は例外になるかフォールバック動作をします（関数により挙動が異なるためログを確認してください）。
- PyYAML がインストールされていない場合、validate_config は config/*.yaml の内容検証をスキップします（警告出力）。
- psutil によるプロセス優先度設定は権限により失敗する場合があります。失敗時は警告が出て処理を継続します。
- DuckDB / SQLite のファイルパスは環境変数で変更可能です。paper_trading は本番 DB と分離された専用 SQLite を使う設計です（PAPER_TRADING_SQLITE_PATH）。
- monitoring_db の init 関数には既存 DB に対する簡単なマイグレーション（カラム追加）が含まれますが、より大きな変更は別途マイグレーションが必要になる可能性があります。

---

この README はコードベースの抜粋に基づく要約です。実運用や拡張の際は各モジュールの docstring とソースコードを参照してください。質問や補足があれば教えてください。