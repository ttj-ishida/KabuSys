# KabuSys

日本株向け自動売買/リサーチ基盤のソースコード群（README の自動生成）。  
この README は与えられたコードベースの主要機能、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買エンジンおよび周辺ツール群です。  
主な役割は以下のとおりです。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- ExecutionEngine による発注管理（本番とペーパートレードを分離）
- 監視コンポーネント（System / Trade / Risk のポーリング、Kill Switch）
- ニュース NLP / レジーム判定（OpenAI を利用）
- 各種 CLI（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針としては、DB 参照と計算の分離、フェイルセーフ（API 失敗時は安全側で継続）、ルックアヘッドバイアス回避（date/time の扱いに注意）などが盛り込まれています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注・オーダー管理・リスク管理・リコンシリエーション）
  - BrokerClientFactory（本番/モックの切替、KABUSYS_ENV に依存）
  - Paper trading は専用 SQLite（data/paper_trading.db）で本番 DB と完全分離

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス存在チェック、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：各 Monitor の統合ポーリング、AlertManager 連携

- Portfolio（純粋関数群）
  - 銘柄選定（select_candidates）、重み計算（等金額・スコア加重）
  - セクター制約適用、レジームに応じた乗数
  - ポジションサイズ計算（単元適合、max ポジション・aggregate cap、cost_buffer）

- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（OpenAI）
  - news_nlp：ニュース記事を集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector：ETF の MA200 乖離とマクロニュース（LLM）を合成して市場レジームを判定

- ツール/CLI
  - config_setup.py：対話式 .env 生成ウィザード
  - validate_config.py：環境変数 / config/*.yaml の検証
  - tools.paper_verification_report：ペーパートレード DB に対する検証レポート生成

---

## セットアップ手順

前提：
- Python 3.9+（コードに型アノテーション等を使用）
- システム上で SQLite は標準で利用可能
- DuckDB を使用（Python パッケージ）

1. リポジトリを取得
   - git clone ...（省略）

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必須（実行・監視・AI を利用する場合）:
     - duckdb
     - psutil
     - openai
   - 任意（設定検証で YAML を検証する場合）:
     - PyYAML
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がなければ上記を個別インストールしてください）

4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 本番環境で警告も失敗にしたい場合: python -m kabusys.validate_config --strict

注意:
- 自動で .env を読み込む仕組みがあり、プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env`, `.env.local` をロードします。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主要なもの）

- KABUSYS_ENV
  - 有効値: development | paper_trading | live
  - paper_trading の場合、MockBrokerClient を使い paper_trading 用 SQLite に記録される
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（"1" にすると起動時に kill.flag を自動クリア。production では 0 推奨）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔を秒で上書き、デフォルト 60）

その他の詳細は `kabusys.config.Settings` を参照してください（デフォルト値や検証ロジックが定義されています）。

---

## 使い方（実行例）

- 監視ループ起動（SystemMonitor 単独のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒に設定できます（例: export MONITOR_POLL_INTERVAL=30）

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH` に記録
  - 起動時に data/stop_requested.flag が存在する場合はエンジンは起動しません
  - 実行中に stop を送りたい場合は data/stop_requested.flag を作成してください（run_execution はこのフラグを監視して停止します）
  - エンジンの PID は data/execution.pid に書かれます

- .env の生成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニュースセンチメント、レジーム判定）
  - OPENAI_API_KEY を設定してから専用関数を呼び出す（ライブラリ経由）
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime（スクリプト化して利用するのが想定）

ログ・フラグ類:
- data/kill.flag : KillSwitch が書き込む停止フラグ（Execution 停止指示）
- data/stop_requested.flag : run_execution / run_monitoring の外部停止制御に使用されるフラグ
- data/execution.pid : 実行中エンジンの PID（SystemMonitor が存在チェック）

注意点:
- set_process_priority()（psutil）で優先度を上げますが権限がない場合は警告が出てスキップされます。
- OpenAI API 呼び出しはネットワークエラー・429・5xx に対してリトライロジックを実装していますが、API キーやネットワークの準備が必要です。

---

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下に配置されています）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py              — .env 対話式ウィザード CLI
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py                — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py         — マクロニュース + ETF MA200 で市場レジーム判定

  - monitoring/
    - monitoring_db.py           — SQLite による監視ログ永続化層（init / CRUD）
    - system_monitor.py          — CPU/メモリ/ディスク/プロセス/Data freshness 監視
    - trade_monitor.py           — 注文滞留・約定異常検出
    - risk_monitor.py            — ドローダウン / ポジション上限監視
    - kill_switch.py             — Kill Switch（flag ファイル操作）
    - monitoring_engine.py       — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py           — （アラート送信のラッパー。ファイルは最後まで提示されていません）

  - execution/
    - broker_factory.py          — ブローカークライアントの生成（本番 / Mock 切替）
    - execution_engine.py        — ExecutionEngine（run_session 等）
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数決定・スケール調整・単元丸め
    - risk_adjustment.py         — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py         — momentum/value/volatility 計算（DuckDB）
    - feature_exploration.py     — 将来リターン・IC・統計サマリ等

  - monitoring/ (上に記載済)
  - tools/
    - paper_verification_report.py — ペーパートレード DB の検証レポート生成
  - utils/
    - process_priority.py        — psutil を用いたプロセス優先度 / CPU affinity 設定ユーティリティ

データ / フラグ（プロジェクトルート配下、デフォルト）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/kill.flag
- data/stop_requested.flag
- data/execution.pid

---

## 開発・運用上の注意

- 本番環境（KABUSYS_ENV=live）では .env の秘密情報（API トークン等）管理に注意してください。`.env` を Git にコミットしてはいけません。
- validate_config.py は運用前の簡易チェックに有用です。--strict モードで警告も失敗扱いにできます。
- AI モジュール（news_nlp, regime_detector）は OpenAI API を利用します。API の利用制限、コスト、レスポンスの妥当性検証を行って運用してください。
- Monitoring 系は SQLite（monitoring.db）にログを記録します。DB のバックアップやディスク容量監視を行ってください。
- Process priority / CPU affinity の設定は OS ごとに挙動や権限が異なります。権限不足時は警告でスキップされます。

---

必要であれば、この README をベースに:
- 具体的なコマンド例集（systemd / supervisor 用のサービス定義）
- requirements.txt / Dockerfile / CI 用のテストシナリオ
- alert_manager の実装に関するドキュメント（LINE 通知等）

を生成できます。どの追加情報が必要か教えてください。