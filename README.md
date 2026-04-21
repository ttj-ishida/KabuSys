# KabuSys

日本株自動売買システム（Prototype）

このリポジトリは、戦略生成・ポートフォリオ構築・発注実行・監視・研究用ユーティリティを含む日本株向け自動売買システムのコードベースです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の主要コンポーネントで構成されます。

- Execution Engine: 発注の実行・注文管理・リスク管理を行うエンジン
- Monitoring: システム状態・注文の監視、Kill Switch による強制停止
- Research: ファクター算出、特徴量探索、IC 等の研究用モジュール
- Portfolio: 候補選定、配分重み計算、ポジションサイジング、リスク調整
- AI モジュール: ニュースを LLM（OpenAI）でスコアリングする NLP、および市場レジーム判定
- Tools: ペーパートレード検証レポート生成などのスクリプト
- Utilities: ロギング設定、プロセス優先度設定などの共通ユーティリティ

設計上のポイント:
- DB は DuckDB（分析）と SQLite（監視／注文履歴）を使用
- Paper Trading（仮想発注）は本番 DB と分離（`data/paper_trading.db`）
- 環境変数は `.env` に記述可能。`config_setup.py` によるウィザードで作成可能
- OpenAI を使う機能は環境変数 `OPENAI_API_KEY` を必要とします

---

## 機能一覧

主な機能（抜粋）:

- run_execution.py
  - Execution Engine の起動スクリプト
  - 実運用（live） / ペーパートレード（paper_trading）に対応
  - プロセス優先度設定、PIDファイル管理、停止フラグ検出

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能
  - 監視は常に本番用の sqlite_path を使用

- monitoring.*
  - system_monitor: CPU/メモリ/DISK、データ鮮度、Execution プロセスの有無監視
  - trade_monitor: 注文の滞留・約定異常などの監視（実装箇所あり）
  - risk_monitor: ドローダウン、ポジション上限監視とダッシュボード更新
  - kill_switch: 条件で `data/kill.flag` を書き込み ExecutionEngine に停止シグナルを送る
  - monitoring_db: SQLite スキーマ初期化と永続化 API

- portfolio.*
  - 候補選定、等金額／スコア加重、セクター上限適用、レジーム乗数
  - ポジションサイズ計算（lot 単位で丸め、利用可能現金に基づくスケーリング）

- research.*
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- ai.news_nlp / ai.regime_detector
  - ニュース記事を LLM でセンチメント評価して ai_scores に書き込み
  - ETF（1321）の MA200 とマクロニュースセンチメントを合成して市場レジーム判定

- tools.paper_verification_report
  - Paper Trading DB を解析して Pass/Fail 判定を含む検証レポートを生成

- utils.logging_setup / utils.process_priority
  - 統一的なロギング設定（コンソール + 日次ローテートファイル）
  - プラットフォーム差分を吸収したプロセス優先度 / CPU affinity 設定

---

## セットアップ手順

推奨 Python バージョン: 3.10 以上（PEP 604 の型記法などを使用）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存ライブラリをインストール
   - 必要な主要依存（例）:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定検証で任意）
   - インストール例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は `pip install -r requirements.txt` を実行してください）

4. .env を作成
   - 推奨: 対話式ウィザードで作成
     - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - 本番環境では `--strict` で警告もエラー扱いにできます

5. データディレクトリの準備
   - デフォルトで使用されるパス（`.env` で上書き可能）
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/
   - 必要に応じてディレクトリを作成（スクリプトが自動作成する場合もあります）

6. OpenAI API を使用する機能を利用する場合:
   - 環境変数 `OPENAI_API_KEY` を設定するか、該当 API 呼び出しにキーを渡してください

---

## 使い方（起動・コマンド例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- Execution Engine 起動（発注実行）
  - python -m kabusys.run_execution
  - paper_trading モードにするには `.env` の KABUSYS_ENV を `paper_trading` に設定します
  - 実行時は `data/stop_requested.flag` や `data/kill.flag` の存在を監視します

- Monitoring 起動（定期監視）
  - MONITOR_POLL_INTERVAL で秒間隔を指定可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は `.env` の sqlite_path を常に本番用に解決します（環境に依存せず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI / レジーム判定 / ニューススコアリング（プログラム経由）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して使用
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）

ログ:
- デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）
- ログレベルは環境変数 `LOG_LEVEL` で設定（例: DEBUG, INFO）

停止・Kill スイッチ:
- `data/kill.flag` を作成すると ExecutionEngine に停止シグナルを送ります（KillSwitch により書き込まれる）
- `data/stop_requested.flag` は起動スクリプトがループ終了のために参照する内部フラグ

重要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live
- OPENAI_API_KEY（AI 機能利用時）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL（monitoring のポーリング秒数）

---

## ディレクトリ構成

主要ファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定の読み込み・ラッパー（Settings）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化 + 永続化 API
    - system_monitor.py      — システム状態・データ鮮度の監視
    - trade_monitor.py       — 注文監視（滞留・約定異常検知 等）
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — Kill Switch（flag 書き込み）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信実装、LINE 等を想定）
  - execution/
    - execution_engine.py    — 発注セッション管理（Engine 実装）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
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
    - news_nlp.py             — ニュースの LLM スコアリング
    - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py        — 共通ロギング設定
    - process_priority.py     — プロセス優先度 / CPU affinity

その他:
- data/         — データファイル（DB、PID、flag 等）を格納する想定ディレクトリ
- logs/         — ログ出力先（デフォルト）

（実際のリポジトリではファイル構成が多少異なる場合があります。上は主要モジュールの一覧です）

---

## 注意事項 / 運用メモ

- 本番運用時は `KABUSYS_ENV=live` として実行し、`.env` の設定は十分にレビューしてください。validate_config の `--strict` を推奨します。
- Paper Trading は本番 DB と分離していますが、念のためパスを確認してください（PAPER_TRADING_SQLITE_PATH / SQLITE_PATH）。
- OpenAI の呼び出しはレート制限やエラーを考慮してリトライ実装がありますが、コストや API 利用制限に留意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります（setup_logging の仕様）。
- PID ファイル / flag ファイルは data/ 配下に保存されます。複数インスタンス起動時の衝突に注意してください。

---

以上がこのコードベースの README です。必要であれば、README にサンプル .env（機密情報は除く）やよくあるトラブルシュート項目、開発フロー（テスト、CI、デプロイ）を追加できます。どの情報を追加しますか？