# KabuSys

日本株向け自動売買システムの一部モジュール群。ポートフォリオ構築、リスク管理、発注エンジン、監視、研究用ファクター計算、ニュースNLP (OpenAI) 等を含みます。

- パッケージ: src/kabusys
- バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買ワークフローを構成するライブラリ群です。主要な関心領域は以下です。

- データ（DuckDB）ベースのファクター計算／研究
- 銘柄選定・配分・株数計算（ポートフォリオ構築）
- ExecutionEngine（ブローカー連携／発注管理）
- 監視・アラート（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- Paper Trading 向け分離された DB と Mock ブローカー
- OpenAI を利用したニュースセンチメント & レジーム判定
- 運用補助ツール（設定ウィザード・設定検証・Paper Trading レポート）

設計上のポイント:

- DB 接続は DuckDB（分析）と SQLite（監視・履歴）を併用
- Paper Trading は本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH）
- 多くの処理は副作用を抑えた純粋関数として実装（研究・ポートフォリオ）
- LLM 呼び出しはリトライ・バリデーション・フェイルセーフを備える

---

## 主な機能一覧

- 環境設定ウィザード: `kabusys.config_setup`
- 設定検証 CLI: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト: `kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` では MockBroker を使用し data/paper_trading.db に記録
- Monitoring 起動スクリプト: `kabusys.run_monitoring`
  - システム・データ鮮度・プロセス状態の定期チェックとログ永続化
- Monitoring サブシステム:
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager
- ポートフォリオ構築:
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究モジュール:
  - ファクター計算（momentum / value / volatility）、特徴量探索、IC 計算、統計サマリ
- AI モジュール:
  - news_nlp.score_news: OpenAI でニュースをスコアリングして ai_scores テーブルに保存
  - regime_detector.score_regime: ma200 + マクロニュースで市場レジーム判定
- 運用ツール:
  - `kabusys.tools.paper_verification_report`：Paper Trading の品質指標レポート生成

---

## セットアップ手順

前提: Python 3.9+（プロジェクトに合わせて適宜調整してください）

1. リポジトリをクローン / 配布パッケージを展開
2. 仮想環境を作成・有効化
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate
3. 依存パッケージをインストール（プロジェクトで requirements.txt がない場合は下記をインストール）
   - pip install duckdb psutil openai
   - PyYAML は設定検証で任意（yaml ファイルの構文チェック）：pip install pyyaml
4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - このウィザードは JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須環境変数を設定する .env を生成します。
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

環境変数の自動ロード:
- プロジェクトルート（.git または pyproject.toml が存在）を起点に `.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効化するには: `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

必須環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な設定（デフォルト値を含む）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI 呼び出しに必要（news_nlp / regime_detector）

---

## 使い方

起動スクリプトはモジュール実行形式で提供されています。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor を単独実行）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）
  - 監視は常に本番の sqlite_path を使用（監視ログは本番DBを参照）

- ExecutionEngine 起動（発注エンジン）
  - KABUSYS_ENV によって実行モードが変わります
    - 本番: KABUSYS_ENV=live
    - Paper Trading（モックブローカー、分離 DB）: KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - Paper Trading の DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` で変更可能
  - 実行中は PID ファイル (data/execution.pid) を出力

停止方法:
- 実行スクリプトはプロジェクトルート `data/stop_requested.flag` の存在を監視しています。ファイルを作成するとループを終了します（run_monitoring / run_execution 共通）。
- Kill Switch: `data/kill.flag` を生成すると ExecutionEngine に停止シグナルを送ります（KillSwitch モジュールで制御）。起動時に自動クリアする挙動は Settings.kill_flag_clear_on_start で制御。

ツール:
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定可能（優先度: --db > 環境変数 > デフォルト）

AI / LLM 機能:
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と target_date を渡してニューススコアを ai_scores テーブルに保存
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB 接続と target_date を渡して market_regime テーブルへ書き込み

研究用 API:
- kabusys.research.calc_momentum(conn, target_date)
- kabusys.research.calc_volatility(conn, target_date)
- kabusys.research.calc_value(conn, target_date)
- kabusys.research.calc_forward_returns(...)
- kabusys.research.calc_ic(...)

ポートフォリオ / 位置サイズ:
- kabusys.portfolio.select_candidates(...)
- kabusys.portfolio.calc_equal_weights(...)
- kabusys.portfolio.calc_score_weights(...)
- kabusys.portfolio.calc_position_sizes(...)
- kabusys.portfolio.apply_sector_cap(...)
- kabusys.portfolio.calc_regime_multiplier(...)

ログ:
- ログ出力は `kabusys.utils.logging_setup.setup_logging` を通じて統一管理されます。
- デフォルトログディレクトリ: `logs/`。ファイル名は `<app_name>.log`（例: execution.log, monitoring.log）
- ローテーション: 日次、30世代保持

---

## ディレクトリ構成

（重要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数/設定管理 (.env 自動ロード)
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py  — Paper Trading 検証レポート
    - ai/
      - news_nlp.py            — ニュースNLP（OpenAI）で ai_scores を更新
      - regime_detector.py     — レジーム判定（ma200 + macro news）
    - monitoring/
      - monitoring_db.py       — SQLite 用永続化層
      - system_monitor.py      — システム・データ鮮度監視
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - trade_monitor.py       — （発注・約定の監視）※実装参照
      - monitoring_engine.py   — 複数モニタを束ねるループ
      - kill_switch.py         — kill.flag 制御
      - alert_manager.py       — （外部通知管理）※実装参照
    - portfolio/
      - portfolio_builder.py   — 候補選定・重み
      - position_sizing.py     — 株数決定・丸め・キャップ
      - risk_adjustment.py     — セクター制限・レジーム乗数
    - research/
      - factor_research.py     — ファクター計算（momentum/value/vol）
      - feature_exploration.py — IC/統計サマリ等
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity
    - data/ （実行時に使用／生成）
      - monitoring.db          — デフォルトの監視 SQLite（SQLITE_PATH）
      - paper_trading.db       — Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）
      - kabusys.duckdb         — DuckDB（DUCKDB_PATH）
      - execution.pid
      - kill.flag / stop_requested.flag

---

## 運用上の注意

- 本番 (KABUSYS_ENV=live) での起動前に `python -m kabusys.validate_config` で必須項目・パス・YAML の妥当性を確認してください。
- `.env` は秘密情報（API トークン等）を含むため、絶対に Git にコミットしないでください。
- OpenAI を使用する機能は API コストとレイテンシを考慮して運用してください。API キーは `OPENAI_API_KEY` に設定します。
- ExecutionEngine は Paper Trading モードであっても本番に近い動作確認ができますが、実際の発注をする `live` 環境では十分なテストと監視（Kill Switch、LINE 通知等）を有効にしてください。
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合はコンソール出力のみで継続します（警告ログが出ます）。

---

## 参考コマンド集

- 仮想環境作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai pyyaml

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution 起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

README は随時更新してください。追加のドキュメント（API 仕様書、設計メモ、運用手順）があればそれらへのリンクをこの README に追記することを推奨します。