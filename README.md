# KabuSys — 日本株自動売買システム

このリポジトリは、日本株の自動売買・研究・監視に関するコンポーネント群をまとめた Python パッケージです。  
ここに含まれるコードは、Execution（発注エンジン）、Monitoring（監視）、Research（ファクター計算）、Portfolio（銘柄選定・配分）、AI（ニュース NLP / レジーム判定）などの機能を提供します。

---  

## プロジェクト概要

- 目的: 日本株の自動売買を支える実行・監視・研究用モジュール群を提供。
- 構成:
  - Execution: 発注エンジン、注文管理、ブローカークライアント抽象化（paper_trading モード対応）
  - Monitoring: システム健全性監視、トレードログ監視、リスク監視、Kill Switch
  - Research: DuckDB を使ったファクター計算・特徴量解析
  - Portfolio: 銘柄選定・重み付け・ポジションサイズ計算（純粋関数）
  - AI: ニュースセンチメント（OpenAI）を利用したスコアリング、レジーム判定

---  

## 主な機能一覧

- 環境設定ウィザード（config_setup）で `.env` を対話的に作成
- 設定検証 CLI（validate_config）で起動前の環境・設定ファイルチェック
- ExecutionEngine（run_execution）:
  - KABUSYS_ENV に応じて実行モードを切替（paper_trading は MockBroker による分離 DB）
  - 停止フラグ / PID 管理
  - RiskManager / OrderManager / Reconciler 等の組み立て
- Monitoring（run_monitoring）:
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - MONITOR_POLL_INTERVAL によるポーリング周期制御（デフォルト 60 秒）
  - 監視ログは SQLite（monitoring.db）に永続化、解析用に DuckDB も利用
  - Kill Switch（条件に応じて data/kill.flag を書き込み、Execution を停止）
- Research:
  - モメンタム、ボラティリティ、バリュー系ファクター計算（DuckDB SQL + Python）
  - 将来リターン、IC（Information Coefficient）、統計サマリ
- Portfolio:
  - 候補選定、等配分/スコア配分、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算
- AI:
  - ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア生成）
  - レジーム判定（ETF とマクロニュースを組み合わせたスコアリング）
- ユーティリティ:
  - 統一的なロギング設定（logs/ 日次ローテーション）
  - プロセス優先度 / CPU affinity の簡易設定
  - Paper Trading の検証レポート生成ツール

---  

## セットアップ手順

1. Python のインストール
   - Python 3.9+ を推奨（コードは typing の新しい表記を使用）

2. 依存パッケージのインストール（例）
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config による YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. プロジェクトルートで `.env` を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは `./.env` を手動作成
   - 自動ロード:
     - ランタイム起動時、OS 環境変数 > .env.local > .env の順でロードされます
     - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

4. 主要な環境変数（必須・代表例）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能を利用するなら必須）
   - LOG_LEVEL（デフォルト: INFO）
   - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート用）

5. ディレクトリ作成（必要なら）
   - data/ （DB やフラグファイル）
   - logs/ （ログ出力。setup_logging が自動作成を試みます）

---  

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（data/paper_trading.db）を使用
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中に stop フラグが立つとエンジン停止処理を行う
    - PID ファイルは data/execution.pid（Settings.pid_file_path で変更可能）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 動作:
    - モニタリングは常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を使用して監視情報を残します
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
    - 長期の監視ログは settings.duckdb_path（DuckDB）でも利用します
    - 停止は data/stop_requested.flag を作成するとポーリングループが検出して終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で変更可能）

- AI / レジーム判定・ニューススコアリング
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して利用
  - LLM 呼び出しは外部 API エラーに対してリトライやフォールバック（0.0）を行う設計

---  

## 停止 / Kill Switch / フラグファイル

- stop_requested.flag
  - run_execution と run_monitoring は共にリポジトリ内の data/stop_requested.flag を監視しています。
  - このファイルを作成するとループ中のプロセスは終了処理を行います（安全停止）。

- kill.flag
  - KillSwitch（監視側）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを発行します。
  - 本番環境の設定には KILL_FLAG_CLEAR_ON_START の扱いに注意してください（本番では自動クリアを避けることを推奨）。

---  

## ロギング

- 共通ロギング設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - コンソール（stdout）用 StreamHandler と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保存）を設定します。
  - デフォルトログディレクトリ: logs/
  - LOG_LEVEL / LOG_DIR 環境変数で上書き可能

---  

## 開発者向けノート

- 設定自動ロード
  - 起動時にプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を基準に `.env` と `.env.local` を読み込みます。
  - OS 環境変数は保護され、.env ファイルによる上書きは制御されます。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB
  - 監視情報・注文ログ等は SQLite（デフォルト: data/monitoring.db）に永続化されます。
  - 解析や研究用には DuckDB（デフォルト: data/kabusys.duckdb）を利用します。
  - paper_trading モードは paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離します。

- 依存モジュール
  - PyYAML: config/*.yaml の検証（validate_config）で使用。未インストール時は YAML の検証をスキップします。
  - openai: AI 機能（news_nlp, regime_detector）で使用。API キー必須。
  - psutil: プロセス優先度設定 / システム統計の取得で使用。

---  

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 発注エンジン関連（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py

---  

## よくある操作例

- .env を作って設定の妥当性をチェックする
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 監視プロセス開始（デフォルト 60 秒間隔）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution 起動（paper_trading モード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---  

## 注意事項 / 運用上のヒント

- 本番（KABUSYS_ENV=live）での運用時は .env 内のプレースホルダ・未設定値に注意してください（validate_config が警告／エラーを検出します）。
- kill.flag / stop_requested.flag などのフラグファイルの扱いに注意。特に本番で KILL_FLAG_CLEAR_ON_START=1 を設定すると危険です。
- OpenAI の使用はコストやレイテンシを伴います。AI 機能は API エラー時にフォールバックする設計ですが、運用上の監視を推奨します。
- ログディレクトリの権限やディスク容量に留意してください（logs/、data/ の肥大化）。

---

この README はコードベースの主要な挙動と使い方をまとめたものです。詳細な実装や API 仕様は各モジュール（src/kabusys 以下の各ファイル）を参照してください。必要があれば、README にサンプル .env テンプレートや運用フロー（デプロイ手順、Systemd / Supervisor 用 unit ファイル例）を追記できます。希望があれば作成します。