# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアモジュール群を含みます。  
主にポートフォリオ構築、発注エンジン、監視、リサーチ、AIによるニュース解析などの機能を提供します。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成される自動売買プラットフォームです。

- ExecutionEngine: ブローカークライアントを通じた発注処理（本番 / ペーパートレード対応）
- Monitoring: システム・発注・リスクの定常監視とアラート、Kill Switch（停止フラグ）
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約など
- Research: DuckDB上の時系列・ファクター計算、IC評価、特徴量探索
- AI モジュール: ニュースのセンチメント集約（OpenAIを利用）、市場レジーム判定
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード・検証ツール、DB 初期化など

設計方針として、可能な箇所は「フェイルセーフ」「ルックアヘッドバイアス回避」「DB分離（paper_trading）」を重視しています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成 / 更新）
  - python -m kabusys.config_setup
- 設定検証ツール（.env / config/*.yaml の検査）
  - python -m kabusys.validate_config
- 実行エンジン起動スクリプト（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視ループ起動スクリプト（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60秒）
- 監視用 DB 初期化 / 永続化（SQLite）
  - monitoring_db: system_status / trade_logs / positions / risk_logs / dashboard の管理
- リスク監視・Kill Switch（drawdown・ポジション上限等）
  - kill.flag を書き込むことで ExecutionEngine を停止
- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- AI（OpenAI）を用いたニュースセンチメント集約・市場レジーム判定
  - kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime
- ポートフォリオ構築ユーティリティ（シンプルで純粋関数）
  - 銘柄選定、等重/スコア重み、ポジションサイズ、セクター制約、レジーム乗数
- リサーチモジュール（DuckDB によるファクター計算・IC評価等）
- ログ設定ユーティリティ（コンソール + 日次ローテーションファイル）

---

## セットアップ手順（開発 / 起動のための基本手順）

前提:
- Python 3.10+（型注釈で | を使用しているため）
- Git（プロジェクトルート検出に用いる）
- 推奨パッケージ: duckdb, psutil, openai, PyYAML

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合:
   - pip install -r requirements.txt

4. 環境変数設定 (.env)
   - 対話的ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI機能を使う場合)
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB: デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（紙トレード用 DB: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）

   注意: .env は Git にコミットしないこと。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる

6. データディレクトリの準備（必要に応じて）
   - デフォルトの SQLite / DuckDB / logs ディレクトリは起動時に自動作成されますが、権限により失敗する場合があります。事前に作成しておくと安全です。

---

## 起動・使い方

- ExecutionEngine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - 動作概要:
    - process priority を "high" にセット（可能なら）
    - DB 接続（KABUSYS_ENV=paper_trading のときは paper_trading DB を使用）
    - BrokerClientFactory によりブローカークライアントを生成（実ブローカー or モック）
    - エンジンはバックグラウンドスレッドで run_session を実行
    - data/stop_requested.flag が存在すると停止シグナルを受け取る
    - PID ファイル: data/execution.pid（設定で変更可）

- Monitoring（監視ループ）起動:
  - python -m kabusys.run_monitoring
  - 動作概要:
    - process priority を "high" にセット
    - monitoring は常に本番 sqlite_path を使用（環境に依存しない）
    - SystemMonitor.check_once を定期実行（デフォルト 60秒）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能
    - data/stop_requested.flag が存在する場合ループ終了

- 止め方・Kill Switch:
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを与えます
  - run_execution と run_monitoring は stop_requested.flag を監視して優雅に終了します

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パス指定可、または --db オプション

- ロギング:
  - ログは stdout に出力され、デフォルトで logs/<app_name>.log に日次ローテーションで出力されます
  - 環境変数 LOG_DIR でログディレクトリを上書き可能
  - LOG_LEVEL 環境変数または .env の LOG_LEVEL でレベル制御

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーション API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI機能使用時）
- KABUSYS_ENV — execution モード（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — MockBrokerClient の約定モード（instant | partial | never | reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1 = 有効、0 = 無効）

---

## 注意事項 / 実運用向けのガイドライン

- 本番環境（KABUSYS_ENV=live）では .env の内容を慎重に管理してください。validate_config は本番における追加チェック（LINE設定等）を行います。
- .env は絶対に VCS にコミットしないでください。
- OpenAI API を使う機能は API 呼び出し失敗時にフェイルセーフ（スコア0.0等）を採る設計ですが、コストやレート制限に注意してください。
- Monitoring は system/process の監視結果を monitoring DB に永続化します。監視データを可視化・アラート連携してください。
- Paper Trading は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。誤操作で本番DBを汚さない設計になっていますが、念のため設定を確認してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数・Settings 管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（AI + ma200）
- monitoring/
  - monitoring_db.py       — SQLite テーブル定義 / 永続層
  - system_monitor.py      — システム状態・データ鮮度監視
  - trade_monitor.py       — （省略）発注ログ監視（存在）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag 管理
  - alert_manager.py       — （存在、アラート送信管理）
  - monitoring_engine.py   — 監視各コンポーネントの束ね
- execution/
  - execution_engine.py    — ExecutionEngine（コア）
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数算出・投下資金スケーリング
  - risk_adjustment.py     — セクター制約・レジーム乗数
- research/
  - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン・IC計算 等
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度・CPU affinity
  - その他ユーティリティ

data/ (ランタイム生成/利用)
- monitoring.db (デフォルト)
- paper_trading.db (ペーパートレード用)
- kill.flag, stop_requested.flag, execution.pid などの制御ファイル

logs/
- execution.log
- monitoring.log
- ...（各アプリ名ごとに日次ローテーション）

config/
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml
  （PyYAML がある場合は validate_config で YAML パース検証を行います）

---

## 開発者向け情報・拡張ポイント

- DuckDB をデータ分析基盤として利用しており、research モジュールは DuckDB 接続を受けて純粋な SQL/Python で計算します。
- AI関係（news_nlp / regime_detector）は OpenAI API を利用します。API 呼び出しまわりはテストしやすいように分離・ラップ実装されています（ユニットテストで差し替え可）。
- モジュールはなるべく副作用を避ける設計（例: portfolio モジュールは DB参照なしの純粋関数群）です。
- 監視やリスク評価は冗長性（dedup / fail-open）を考慮してログ・警告を出すように設計されています。

---

必要であれば、この README をベースに「デプロイ手順」「運用 runbook」「設定ファイルの例（.env.example）」「Docker / systemd サービス定義」なども作成できます。どれを追加しますか？