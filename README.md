# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋起動スクリプト群）。

このリポジトリは以下の機能を持つコンポーネントを含みます：取引実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築ルーチン、リサーチ用ファクター計算、AI（LLM）を使ったニュース/レジーム判定、各種ユーティリティと運用用スクリプト。

---

## プロジェクト概要

- 目的：日本株の自動売買を安全に運用するためのエンジンと運用支援ツール群を提供する。
- 設計方針：
  - 本番とペーパートレードを明確に分離（DB・ブローカークライアント等）。
  - ルックアヘッドバイアスを避ける（date.today()等を直接参照しない箇所がある）。
  - フェイルセーフ設計（API失敗時は安全側にフォールバック、ログ・kill switch による運用制御）。
  - テスト容易性のため機能は分割（純粋関数・DB読み書き層・Engine 層など）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine：ブローカーとの注文送信、OrderManager、RiskManager、Reconciler を統合
  - Paper trading モード（KABUSYS_ENV=paper_trading）は MockBrokerClient を使用し、data/paper_trading.db に記録
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・Execution プロセスの監視、データ鮮度チェック
  - TradeMonitor / RiskMonitor：滞留注文、約定異常、ドローダウンやポジション上限の監視
  - KillSwitch：条件を満たしたら data/kill.flag を作成して ExecutionEngine 停止を促す
  - MonitoringEngine：上記をまとめてポーリングし、AlertManager 経由で通知可能
- Portfolio / Research
  - ポートフォリオ候補選定・重み計算（等金額・スコア加重）
  - ポジションサイズ計算（risk_based 等）、セクター制限、レジーム乗数
  - ファクター計算（モメンタム、ボラティリティ、バリュー）、forward returns、IC 計算
- AI（OpenAI）
  - news_nlp: raw_news をまとめて LLM（gpt-4o-mini）に送り、銘柄ごとのセンチメントスコアを ai_scores に保存
  - regime_detector: ETF とマクロニュースを合成して市場レジーム（bull/neutral/bear）を判定・保存
- 運用ツール
  - config_setup.py: .env の対話式ウィザードでの作成／更新
  - validate_config.py: .env / config/*.yaml の前提チェック CLI
  - tools.paper_verification_report: Paper Trading の検証レポート生成
- ユーティリティ
  - logging_setup: 統一的なログ設定（console + 日次ローテーションファイル）
  - process_priority: プロセス優先度・CPU affinity 設定
  - monitoring_db: SQLite を使った監視ログ永続化層（マイグレーション処理含む）

---

## 前提（推奨）

- Python 3.10+
- ネイティブ依存（OS）: 特に process_priority, psutil を利用するため適切な権限が必要
- 推奨パッケージ（requirements に相当）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証用に任意）
- ネットワーク接続（API を使う場合: J-Quants / kabuステーション / OpenAI 等）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （実際の requirements.txt があればそれを用いて pip install -r requirements.txt）

4. ディレクトリ作成（初回）
   - mkdir -p data logs

5. 環境変数の初期化（.env の作成）
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（下記「重要な環境変数」を参照）

6. 設定検証（任意）
   - python -m kabusys.validate_config
   - 問題がある場合は指示に従って .env / config/*.yaml を修正

7. DB 初期化
   - 実行時スクリプト内で init_monitoring_db() が呼ばれ、必要テーブルが作成されます。通常は起動時に自動で作成されます。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用トークン
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV（development / paper_trading / live） — 実行環境
  - paper_trading: MockBroker を使用し、PAPER_TRADING_SQLITE_PATH を使う
  - live: 本番モード（慎重に）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant | partial | never | reject） — ペーパー注文の成行挙動
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に既存の kill.flag を自動クリアするか（0/1）

注意: .env は絶対にリポジトリにコミットしないでください。

---

## 使い方（起動コマンド例）

- 環境変数をロード済み（.env を読み込む設定が有効）として説明します。

1. ExecutionEngine を起動
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と完全分離）
     - 起動時に data/stop_requested.flag が存在すると起動せず終了
     - execution.pid が data/ に書き込まれる

2. Monitoring を起動
   - python -m kabusys.run_monitoring
   - 挙動:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
     - 監視は settings.sqlite_path（監視 DB）を使用。モニタは常に本番 sqlite_path を使用する点に注意（paper_trading 環境でも同様）
     - stop_requested.flag 検出でループ終了

3. 設定ウィザード（.env の作成）
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として exit(1)

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で DB パスを上書き可能（優先度: --db > 環境変数 > デフォルト）

---

## 運用上のファイル / フラグ

- data/stop_requested.flag
  - 実行スクリプト（run_execution / run_monitoring）が外部からの停止要求を検出するために使用
- data/kill.flag
  - KillSwitch が書き込むフラグ。書かれると ExecutionEngine 側で停止検知のトリガーに利用できる
- data/execution.pid
  - ExecutionEngine の PID を書き込むファイル（プロセス管理用）
- logs/
  - 日次ローテートされるログファイル（例: logs/execution.log, logs/monitoring.log）

---

## 開発者向けメモ

- ロギング
  - 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼ぶことで統一されたログ出力になる
- プロセス優先度
  - 起動直後に set_process_priority("high") を呼んでいる（パーミッションに応じて失敗しても警告で済ます設計）
- DB マイグレーション
  - init_monitoring_db() は必要テーブルを冪等に作成し、既存 DB に対してカラム追加（latency_ms, peak_value）を行う
- LLM 絡み
  - OpenAI 呼び出しはリトライ・バックオフを実装しており、失敗時は安全にフォールバック（スコア 0.0 等）する
  - API キーは OPENAI_API_KEY 環境変数で指定
- Paper trading
  - paper_trading 環境は本番データベースと完全分離されるよう設計（PAPER_TRADING_SQLITE_PATH を使用）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     -- 環境変数/設定読み込みロジック
- config_setup.py               -- .env 対話式ウィザード
- validate_config.py            -- 設定検証 CLI
- run_execution.py              -- ExecutionEngine 起動スクリプト
- run_monitoring.py             -- Monitoring 起動スクリプト

subpackages:
- ai/
  - news_nlp.py                 -- ニュース NLP スコアリング（OpenAI）
  - regime_detector.py          -- レジーム判定（ETF + マクロニュース + LLM）
- monitoring/
  - monitoring_db.py            -- SQLite 永続化層（テーブル作成・読み書き）
  - system_monitor.py           -- CPU/メモリ/データ鮮度監視
  - risk_monitor.py             -- ドローダウン・ポジション数監視
  - trade_monitor.py            -- （滞留注文等の監視 — 実装ファイル群）
  - kill_switch.py              -- Kill Switch 管理
  - monitoring_engine.py        -- 各 Monitor を束ねるエンジン
  - alert_manager.py            -- （アラート送信管理）
- execution/
  - execution_engine.py         -- 実行エンジン本体
  - broker_factory.py           -- ブローカークライアント生成（Mock を含む）
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

（実際のファイル一覧はリポジトリをご確認ください。ここには主要ファイルを抜粋しています）

---

## よくある運用フロー（例）

1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. (Paper) DuckDB / SQLite の配置確認
4. まず Monitoring を起動してシステム稼働・弱点をチェック
   - python -m kabusys.run_monitoring
5. Execution を起動（本番なら十分に注意）
   - python -m kabusys.run_execution
6. 必要に応じて KillSwitch / stop flag を操作して安全停止

---

## トラブルシューティング / 注意事項

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を元に行われます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- run_monitoring は常に settings.sqlite_path（監視 DB）を使用します。paper_trading 環境でも監視 DB が本番と同じになる点に注意してください（設計上の意図）。
- OpenAI 使用時はクォータ・コストに注意。失敗時は安全にフォールバックする設計ですが、期待する性能が得られない場合があります。
- process_priority の設定は OS に依存し、権限不足で失敗する場合があります（警告出力）。

---

この README はコードベースの主要点を簡潔にまとめたものです。細かい API 仕様や設定項目の説明は各ソース（config.py, monitoring/*.py, execution/*.py, ai/*.py, portfolio/*.py）内の docstring / コメントを参照してください。必要であれば、各モジュールごとの詳細ドキュメントを作成します。