# KabuSys

日本株向け自動売買システムの参照実装 / ライブラリ群。

このリポジトリは以下の主要コンポーネントで構成されています：
- 発注・実行エンジン（ExecutionEngine）
- 監視・アラート（Monitoring）
- ポートフォリオ構築（Portfolio）
- 研究・ファクター計算（Research）
- ニュース NLP / レジーム判定（AI）
- ユーティリティ・ツール類（設定ウィザード、検証、検証レポート）

目標は「本番運用に近い設計で安全を重視した自動売買フレームワーク」を提供することです。

---

## 主な機能一覧

- Execution
  - 実際のブローカー／Mock ブローカー（paper_trading）を切り替えて発注実行
  - 発注管理・リスク管理・再整合処理（Reconciler）を組み合わせた ExecutionEngine
  - PID ファイル / stop flag による安全停止制御

- Monitoring
  - システム稼働（CPU/MEM/DISK）、プロセス生存、データ鮮度の定期チェック
  - トレードログ / リスクログ / ダッシュボードの永続化（SQLite）
  - Kill Switch（条件を満たしたら data/kill.flag を書いて Execution を停止）
  - アラート管理フック（LINE などに通知可能）

- Portfolio construction
  - 候補選択、重み計算（等金額・スコア加重）、ポジション数算出（リスクベース）
  - セクター上限・レジームによる投資割合調整

- Research
  - DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（情報係数）等の分析ユーティリティ

- AI（OpenAI）
  - ニュース記事の銘柄ごとセンチメント評価（ai_scores への書き込み）
  - マクロニュース + ETF MA に基づいた市場レジーム判定（'bull' / 'neutral' / 'bear'）
  - API 呼び出しは冪等性・リトライ・フェイルセーフ設計

- ツール
  - .env 対話式セットアップウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）

---

## 動作要件 / 依存

- Python 3.10+
- 必須ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai
- 任意 / 推奨:
  - PyYAML（config 検証で YAML のパースに使用）
- SQLite（標準ライブラリで利用可）

インストール例:
- 仮想環境を作成してから:
  - pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を推奨）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env ファイルの初期作成（対話式）
   - python -m kabusys.config_setup
   - J-Quants トークンや KABU API パスワードなど必須値を入力してください。

   重要環境変数（最低限設定が必要）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主要な設定:
   - KABUSYS_ENV: development | paper_trading | live
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
   - LOG_LEVEL, LOG_DIR, OPENAI_API_KEY（AI 機能利用時）

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば指摘に従い .env などを修正
   - --strict を付けると警告も失敗扱いになる: python -m kabusys.validate_config --strict

6. ディレクトリ作成（必要に応じて）
   - data/ （DB・フラグファイルなど）
   - logs/ （ログ出力用。ログ設定で自動作成も試みるが手動で作るのが確実）

---

## 使い方（実行例）

- ExecutionEngine を起動（デフォルトは Settings に従う）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading 用の DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動前に data/kill.flag が存在すると起動しません（停止フラグ検出）。
  - 実行中に停止させるには data/stop_requested.flag (run_execution/run_monitoring の停止用フラグ) を作成するか、kill.flag を利用します。
  - 実行中の PID は data/execution.pid に書き込まれます。

- Monitoring を起動（システム状態・トレード監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（秒、デフォルト 60）。
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - Monitoring は Settings にかかわらず本番 sqlite_path を使用して監視ログを記録します。

- 設定検証
  - python -m kabusys.validate_config
  - 出力される INFO/WARNING/ERROR を確認

- .env 対話式ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パス指定可能（優先順: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）
  - 出力: 稼働率、注文成功率、レイテンシ、最終判定 PASS/FAIL

- AI 機能（プログラム的に呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続
    - target_date: date オブジェクト（ニュースウィンドウは前日 15:00 JST ～ 当日 08:30 JST）
    - api_key: None の場合は環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要（指定がない場合は例外）

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用、デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- MONITOR_POLL_INTERVAL (run_monitoring でポーリング秒数を指定)
- OPENAI_API_KEY (AI 機能利用時)
- PAPER_FILL_MODE (paper_trading の約定モード: instant | partial | never | reject)
- KILL_FLAG_CLEAR_ON_START (本番での安全のためデフォルト 0。1 にすると起動時に kill.flag を自動クリア)

---

## 停止・安全機構

- stop_requested.flag (data/stop_requested.flag)
  - run_execution / run_monitoring が定期ループを終了するためのファイル。存在するとプロセスはしばらくして安全終了します。

- kill.flag (data/kill.flag)
  - Monitoring の KillSwitch が条件を満たしたときに書き込む。ExecutionEngine は kill.flag を見て停止する設計になっています。

- PID ファイル (data/execution.pid)
  - Execution エンジンの PID を出力（外部監視で利用）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - Settings クラス: .env / 環境変数の読み込み・検証
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - Monitoring 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py        — ニュースの LLM スコアリング
  - regime_detector.py — マクロ + ETF MA によるレジーム判定
- monitoring/
  - monitoring_db.py   — SQLite テーブル定義・永続化層
  - system_monitor.py  — CPU/MEM/DISK・プロセス・データ鮮度監視
  - trade_monitor.py   — （トレード監視ロジック; 実装あり）
  - risk_monitor.py    — ドローダウン・ポジション上限監視
  - kill_switch.py     — Kill Switch ロジック
  - monitoring_engine.py — 各モニタの統合実行
  - alert_manager.py   — アラート送信管理（LINE 等と接続する箇所）
- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py     — 候補選定・重み計算
  - position_sizing.py       — 発注株数計算・上限・丸め
  - risk_adjustment.py       — セクター制限・レジーム倍率
- research/
  - factor_research.py       — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py   — 将来リターン・IC 計算・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- utils/
  - logging_setup.py         — 統一的なログ設定（Console + 日次ローテート）
  - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

データ / 出力（実行時に使用 / 生成）
- data/
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - kill.flag / stop_requested.flag / execution.pid
- logs/
  - execution.log, monitoring.log など（TimedRotatingFileHandler、デフォルト保管 30 日）

---

## 開発上の注意・設計ポイント

- Settings は .env と OS 環境変数を組み合わせて読み込む。プロジェクトルート (.git または pyproject.toml を基準) が検出できない場合は自動ロードをスキップします。
- Monitoring の DB（monitoring.db）は環境にかかわらず本番 sqlite_path を使用します。paper_trading 実行時でも監視は本番 DB に記録されます（意図的設計）。
- ExecutionEngine の paper_trading モードは MockBrokerClient を利用し、本番 DB と完全に分離された paper_trading 用 DB に記録されます。
- AI（OpenAI）呼び出しは冪等性・リトライ・レスポンス検証を重視しています。OPENAI_API_KEY を必ず設定してください。
- ログはデフォルトで logs/ に日次ローテーションで格納されます。ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。

---

## よくあるコマンドまとめ

- .env 対話式作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution

- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

必要であれば README に追加したい内容（例: API の詳細ドキュメント、データベーススキーマ、設計資料へのリンク、運用手順、単体テストの実行方法など）を教えてください。README をさらに展開して運用手順書やデプロイ手順に落とし込むこともできます。