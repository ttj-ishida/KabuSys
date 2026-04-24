KabuSys — 日本株自動売買システム README
====================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のサンプル実装です。本リポジトリは、
- 発注エンジン（ExecutionEngine）
- 監視コンポーネント（Monitoring）
- ポートフォリオ構築・サイズ算出ロジック（portfolio）
- ファクター計算 / リサーチ（research）
- ニュース NLP / レジーム判定（AI を利用）
などを含み、ローカル開発・ペーパートレード・本番運用を想定した構造になっています。

主な設計方針
- 環境変数（.env）で設定管理（自動ロード機能あり）
- Paper trading は本番 DB と完全分離（data/paper_trading.db）
- DuckDB を分析用に利用、SQLite を監視/トレードログ用に利用
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価（任意）
- フェイルセーフ設計（API失敗やデータ不足時は安全側にフォールバック）

機能一覧
--------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用（paper DB に記録）
  - プロセス優先度設定、PID 管理、停止フラグ対応
- 監視ループ起動スクリプト: run_monitoring.py
  - システム状態監視（CPU / メモリ / ディスク）
  - データ鮮度チェック、プロセス死活監視、RiskMonitor と KillSwitch 連携
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能
- 設定ウィザード: config_setup.py
  - 対話式に .env を生成・更新
- 設定検証 CLI: validate_config.py
  - .env と config/*.yaml の整合性チェック（--strict あり）
- Paper Trading 検証レポート: tools/paper_verification_report.py
  - paper_trading DB を解析し Pass/Fail 判定（稼働率、成功率、レイテンシなど）
- ポートフォリオ構築モジュール（pure functions）
  - 候補選定、等配分/スコア配分、リスク調整、株数決定（単元丸め）
- リサーチモジュール（DuckDB ベース）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC 計算、統計サマリー
- AI モジュール
  - news_nlp: ニュース記事を LLM でスコアリングして ai_scores に書込
  - regime_detector: ETF 指標とマクロ記事を統合して市場レジーム判定

セットアップ手順
----------------
前提:
- Python 3.9+（コードは型注釈・新構文を使用）
- 必要パッケージ（最低限）:
  - duckdb, psutil, openai（AI 機能使用時）、PyYAML（validate_config の YAML 検証に任意）
- 推奨: 仮想環境（venv / pipenv / poetry 等）

インストール例（venv + pip）
1. 仮想環境作成・有効化
   $ python -m venv .venv
   $ source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストール（例）
   $ pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式ウィザードを使う:
     $ python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照）

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_CLEAR_ON_START 等

.env 自動ロードについて
- 起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要コマンド）
--------------------
1) 設定作成 / 検証
   - ウィザードで .env 作成:
     $ python -m kabusys.config_setup
   - 設定検証:
     $ python -m kabusys.validate_config
     $ python -m kabusys.validate_config --strict  # 警告も FAIL 扱い

2) 監視ループ起動
   - デフォルトで監視は production sqlite_path（settings.sqlite_path）を使います。
   - ポーリング間隔変更:
     $ MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 停止方法:
     - 監視ループはプロジェクトルート/data/stop_requested.flag の存在を検知して終了します（ファイル作成で停止）。
     - また KeyboardInterrupt（Ctrl+C）でも停止します。

3) 実行エンジン（Execution）起動
   - 通常実行:
     $ python -m kabusys.run_execution
   - Paper trading 実行:
     $ KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     この場合、MockBrokerClient を使い data/paper_trading.db にトレードログを記録します（本番 DB と完全分離）。
   - 停止フラグ:
     - run_execution は data/stop_requested.flag を検知して停止します。
     - KillSwitch（監視側）が判定して data/kill.flag を書き込むと Execution 側で停止や追加処理を行えます（設定に依存）。

4) Paper Trading 検証レポート
   $ python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db。--db でパスを指定可能。

5) AI 関連
   - OpenAI を使う機能（news_nlp, regime_detector 等）は OPENAI_API_KEY が必要です。
   - 直接 Python から呼ぶ場合:
     from kabusys.ai.news_nlp import score_news
     score_news(conn, target_date, api_key="sk-...")
   - API 呼び出しは内部でリトライ／フォールバック処理が組み込まれていますが、API キーの利用制限に注意してください。

運用に関する補足
----------------
- ログ: デフォルト logs/ ディレクトリに日次ローテート形式で出力されます（logs/<app_name>.log）。
- DB マイグレーション: monitoring_db.init_monitoring_db はテーブル/列のチェックと簡易マイグレーションを行います。
- PID / フラグファイル:
  - execution.pid（デフォルト data/execution.pid）に PID を書く設計
  - data/kill.flag: 監視側が書き込む Kill Switch。Execution 側で検知／対応する
  - data/stop_requested.flag: 起動スクリプト（run_monitoring/run_execution）が終了判定に使用
- Paper trading の振る舞い:
  - 環境変数 PAPER_FILL_MODE により MockBrokerClient のフィルモードを制御
    有効値: instant | partial | never | reject
  - PAPER_TRADING_SQLITE_PATH で DB パスを変更可能

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / Settings 管理
  - config_setup.py          -- .env 対話式ウィザード
  - validate_config.py       -- 設定検証 CLI
  - run_execution.py         -- ExecutionEngine 起動スクリプト
  - run_monitoring.py        -- SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       -- 共通ログ設定
    - process_priority.py    -- プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py       -- SQLite の永続化層（テーブル定義・読み書き）
    - system_monitor.py
    - trade_monitor.py       -- （trade 関連の監視ロジック: 滞留注文・約定異常等）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       -- アラート送信（LINE 等は設定次第）
  - execution/               -- ExecutionEngine 関係（ブローカーファクトリ等）
  - portfolio/               -- ポートフォリオ構築（builder / position_sizing / risk_adjustment）
  - research/                -- ファクター計算・特徴量探索
  - ai/
    - news_nlp.py            -- ニュース NLP スコアリング
    - regime_detector.py     -- レジーム判定
  - data/                    -- データ操作（DuckDB 用 pipeline 等）
  - tools/                   -- 各種スクリプト

よくあるトラブルと対処
---------------------
- .env が読み込まれない → プロジェクトルート（.git または pyproject.toml）が見つからない可能性。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を確認/設定、あるいは手動で .env を配置してください。
- OpenAI 関連で JSON パース失敗や 5xx が発生 → 既定でリトライ・フォールバック（0.0 等）します。API キー・レート制限を確認してください。
- DuckDB / SQLite ファイルが無い → デフォルトは data/ 配下。起動時に親ディレクトリがなければ警告が出ますが、多くは自動作成されます。

開発に参加する際のヒント
------------------------
- 各モジュールは可能な限り副作用なし（純関数）や DI（依存注入）を意識して設計されています。ユニットテスト作成がしやすい構成です。
- AI 関連や外部 API 呼び出し部は _call_openai_api 等をパッチ／モックしてテスト可能です。
- DuckDB を使ったリサーチ関数は SQL を直接埋め込んでいるため、小規模データで動作確認すると高速にデバッグできます。

ライセンス / コントリビューション
----------------------------------
本 README に含めるべき特別なライセンス情報や貢献ルールが別途ある場合はプロジェクトルートの該当ファイル（LICENSE / CONTRIBUTING.md）を参照してください。

最後に
------
この README はリポジトリの主要な使い方と設計の概要をまとめたものです。詳細は各モジュールの docstring（ソース内コメント）を参照してください。追加で README の改善点や、特定コマンドの実行例をもっと詳しく掲載してほしい場合は教えてください。