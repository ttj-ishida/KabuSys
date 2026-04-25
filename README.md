# KabuSys

日本株自動売買システム（ライブラリ＋起動スクリプト群）

このリポジトリは、戦略・ポートフォリオ構築、発注エンジン、監視・アラート、研究用ファクター計算、AI を使ったニュース NLP などを含む日本株向け自動売買システムのコードベースです。ここに含まれるモジュールは単体でテスト可能な純粋関数群と、エンジン起動用のスクリプト群で構成されています。

---

## プロジェクト概要

- コア機能
  - 発注エンジン（ExecutionEngine 起動スクリプト）
  - 監視ループ（SystemMonitor / MonitoringEngine）
  - リスク監視（ドローダウン・ポジション上限）
  - Kill Switch（フラグファイルで実行系停止）
  - ポートフォリオ構築（候補選定・重み付け・株数算出）
  - 研究用モジュール（ファクター計算・IC 等）
  - ニュース NLP（OpenAI を使って銘柄ごとのセンチメントを算出）
  - Paper Trading 向けツール（検証レポート生成）

- 設定管理
  - .env / .env.local を自動ロード（必要に応じて無効化可能）
  - `Settings` クラスで環境変数をラップ（デフォルトパスや検証を提供）

- 永続化
  - DuckDB（分析用、デフォルト: `data/kabusys.duckdb`）
  - SQLite（監視・取引ログ、デフォルト: `data/monitoring.db`）
  - Paper Trading 用 SQLite（分離された DB。`KABUSYS_ENV=paper_trading` 時使用）

---

## 機能一覧

- 起動 / 管理
  - `python -m kabusys.config_setup` : 対話式 .env 作成ウィザード
  - `python -m kabusys.validate_config` : 設定検証 CLI（--strict オプションあり）
  - `python -m kabusys.run_execution` : ExecutionEngine を起動（実発注 or Mock）
  - `python -m kabusys.run_monitoring` : SystemMonitor のポーリングループを起動
  - `python -m kabusys.tools.paper_verification_report` : Paper Trading 検証レポート出力

- 監視／リスク
  - system_monitor: CPU/memory/disk・データ鮮度・実行プロセス監視
  - trade_monitor: 発注ログ・滞留注文・約定異常検出（trade_logs）
  - risk_monitor: ドローダウン・ポジション数監視（ダッシュボード更新）
  - kill_switch: 条件により `data/kill.flag` を書き込み ExecutionEngine を停止
  - monitoring_engine: 上記を統合して定期実行・通知

- 発注・実行
  - ExecutionEngine（実装は execution パッケージ）
  - BrokerClientFactory による本番 / Mock ブローカー選択
  - Paper Trading 時は `data/paper_trading.db`（または環境変数で上書き）へ記録

- ポートフォリオ構築（pure関数）
  - 候補選定（score ソート）
  - 等配分 / スコア配分ウェイト計算
  - セクター上限適用・レジーム乗数
  - 株数計算（単元数丸め・risk_based / equal / score 配分）

- 研究（DuckDB を利用）
  - モメンタム/ボラティリティ/バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリ

- AI（OpenAI）
  - ニュースをまとめて LLM に投げ、銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ保存
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM 評価を合成）

- ロギング
  - 統一ロギング設定（stdout + 日次ローテートファイル、デフォルト logs/）
  - 環境変数 / 引数でログレベル・ログディレクトリを制御

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須（代表例）:
     - duckdb
     - psutil
     - openai
     - pyyaml (設定ファイル検証を行う場合)
   - 実行例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt がある場合はそれを使用してください（本リポジトリに同梱されていない場合は上記パッケージを参考にしてください）。

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成してください。

4. 主要な環境変数（例・デフォルト）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
   - LOG_LEVEL — デフォルト: INFO
   - OPENAI_API_KEY — AI 機能を使う場合に必要
   - PAPER_FILL_MODE — paper_trading の MockBrokerClient の振る舞い（instant|partial|never|reject）
   - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（0/1）

   補足:
   - .env の自動ロードはデフォルトで有効です（プロジェクトルートが検出できる場合）。
   - 自動ロードを無効にするには環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ
   - `data/`（PID/フラグ/DB を保存）
   - `logs/`（ログファイル。`kabusys.utils.logging_setup.setup_logging` による自動作成）

---

## 使い方

### 設定の作成・検証

- 対話式に .env を作る
  - python -m kabusys.config_setup

- 設定を検証する
  - python -m kabusys.validate_config
  - 警告をエラー扱いにする（--strict）
    - python -m kabusys.validate_config --strict

### ExecutionEngine（発注エンジン）起動

- 本番／paper_trading の切り替えは `KABUSYS_ENV` により制御：
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 専用 DB に記録します（本番 DB と分離）。
- 起動:
  - python -m kabusys.run_execution

- 停止制御:
  - 実行中に `data/stop_requested.flag` を作成するとスレッドループは停止します。
  - Kill Switch による強制停止は `data/kill.flag` が用いられます（KillSwitch によって書き込まれます）。

- PID ファイル:
  - Execution 起動時に `data/execution.pid` を使用／更新する箇所があります（設定による）。

### Monitoring（監視ループ）起動

- 起動:
  - python -m kabusys.run_monitoring

- ポーリング間隔:
  - 環境変数 `MONITOR_POLL_INTERVAL` で秒単位に上書き（デフォルト 60 秒）。
  - 0 以下や不正な値は無視され、デフォルトにフォールバックします。

- 監視が使う DB:
  - Monitoring は KABUSYS_ENV にかかわらず本番 `sqlite_path` を使用します（監視用 DB は分離する運用を想定）。

- 停止制御:
  - `data/stop_requested.flag` を検知すると監視ループは終了します。

### Paper Trading 検証レポート

- レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db で SQLite ファイルパスを指定するか、環境変数 `PAPER_TRADING_SQLITE_PATH` を使う（デフォルト `data/paper_trading.db`）。

### AI 関連（ニュース NLP / レジーム判定）

- 必須: `OPENAI_API_KEY`（パラメータでも渡せます）
- ニューススコア計算:
  - 関数呼び出し例（プログラム内から）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=None)

- 注意:
  - API のレート制限・エラーに対してはリトライやフォールバック（0.0）を行う実装が含まれています。
  - 出力は ai_scores / market_regime 等のテーブルへ永続化されます。

---

## 運用上の注意・フラグ

- 停止フラグ / Kill Switch
  - data/stop_requested.flag: スクリプト側で起動ループを終了させるためのフラグ（手動で作成／削除）
  - data/kill.flag: KillSwitch が書き込む停止指示（ExecutionEngine 側で検知して停止）
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアする（本番では 0 推奨）

- ロギング
  - デフォルトは logs/<app_name>.log（日次ローテート、30 世代保持）
  - stdout とファイルの両方に出力。ログディレクトリ作成に失敗した場合はコンソールのみで継続。

- プロセス優先度
  - run_execution / run_monitoring は起動時にプロセス優先度を `high` に設定しようと試みます（プラットフォーム依存、失敗時は警告）。

---

## 主なファイル・ディレクトリ構成

（src 以下を基準に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env の自動読込と Settings 提供
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — 市場レジーム判定（MA + マクロ NLP）

  - monitoring/
    - monitoring_db.py             — SQLite スキーマ・DB 操作用クラス
    - system_monitor.py            — システム / データ鮮度監視
    - risk_monitor.py              — ドローダウン・ポジション監視
    - trade_monitor.py             — （trade ログ監視）※実装参照（抜粋に未含）
    - kill_switch.py               — kill.flag 書き込みロジック
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン
    - alert_manager.py             — （通知管理）※実装参照（抜粋に未含）

  - execution/
    - execution_engine.py          — 実際の発注エンジン（抜粋に未含）
    - broker_factory.py            — BrokerClientFactory（Mock/Real の選択）
    - order_manager.py             — 発注管理
    - order_repository.py          — DB 経由の注文永続化
    - reconciler.py                — 注文と口座整合
    - risk_manager.py              — 発注前リスク判定

  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数算出・集約キャップ
    - risk_adjustment.py           — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py           — Momentum/Value/Volatility 等
    - feature_exploration.py       — forward returns, IC, summary
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
    - __init__.py

  - utils/
    - logging_setup.py             — ルートロガー設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

- data/    — 実行時に使用する DB / PID / フラグ等（通常は git 管理外）
- logs/    — ログファイル（logs/<app_name>.log）

---

## 例: 最低限の .env (参考)

この .env は config_setup が生成する内容と同等です（例示）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant

---

## よくある質問 / トラブルシューティング

- PyYAML が無いと `validate_config` の YAML 内容検証がスキップされます。設定ファイルのパース検証を行いたい場合は PyYAML をインストールしてください。
- OpenAI を使う機能をローカルで試す場合は `OPENAI_API_KEY` を設定してください。料金・レート制限に注意。
- Paper Trading は本番 DB を触らないように分離されています（`PAPER_TRADING_SQLITE_PATH` を使用）。

---

必要があれば、この README に
- 起動例のログ出力サンプル
- 主要 CLI / API の詳細ドキュメント（関数シグネチャ）
- テストの実行方法
を追加できます。どの情報を追加しますか？