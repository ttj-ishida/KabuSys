# KabuSys

日本株向け自動売買システム（パッケージ版）  
このリポジトリは、戦略・ポートフォリオ構築・注文実行・監視・リサーチ・AI補助（ニュースNLP / レジーム判定）を含むモジュール群で構成されています。

## 概要
KabuSys は次を目的としたモジュール化された自動売買フレームワークです。

- データの蓄積・分析（DuckDB / prices_daily など）
- ファクター算出 / 特徴量解析（research）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 注文執行（ExecutionEngine、ブローカークライアント分離）
- 監視（System / Trade / Risk モニタ、Kill Switch）
- Paper Trading 用検証レポートの生成
- ニュースを使った AI スコアリング（OpenAI を利用）

設計方針として、DB 書き込み・IO と計算部分を明確に分離し、ユニットテストや運用の容易さを重視しています。

---

## 主な機能一覧
- 環境設定ウィザード（.env 生成）: kabusys.config_setup
- 設定検証 CLI（環境変数、config/*.yaml 等）: kabusys.validate_config
- 実行エンジン起動スクリプト（本番 / ペーパートレード切替）: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用 DB に記録
- 監視ループ起動スクリプト（SystemMonitor）: run_monitoring.py
  - 環境に関わらず監視用 sqlite_path（本番 DB）を使います
- Monitoring DB（SQLite）ラッパー: monitoring/monitoring_db.py
- Risk / System / Trade モニタ、Kill Switch、アラート連携
- ポートフォリオ構築ユーティリティ（候補抽出・重み付け・単元丸め）: portfolio/
- リサーチ（ファクター計算、IC, forward returns 等）: research/
- AI モジュール:
  - news_nlp: ニュースを OpenAI に投げて銘柄ごとのセンチメントスコアを生成
  - regime_detector: マクロ記事 + ETF MA200 乖離で市場レジーム判定
- ツール: ペーパートレード検証レポート生成: tools/paper_verification_report.py

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - (リポジトリに requirements.txt がある場合)
     - pip install -r requirements.txt
   - ない場合は代表的な依存を個別にインストール:
     - pip install duckdb psutil openai pyyaml

   ※ 実行環境により追加パッケージが必要になる場合があります（例: broker client 実装依存）。

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成（.env は絶対に Git にコミットしないでください）。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 厳密チェック: python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要に応じて）
   - デフォルト DB/ログパス:
     - data/kabusys.duckdb
     - data/monitoring.db
     - data/paper_trading.db (paper_trading 用)
     - logs/（ログファイル格納）
   - これらは自動で作成されることが多いですが、パーミッションなどに注意してください。

---

## 環境変数（主なもの）
多くの設定は .env / 環境変数から読み込まれます。主なキーとデフォルト:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合に必要)
- KABUSYS_ENV (development | paper_trading | live) — default: development
  - paper_trading: 実際のブローカー呼び出しを Mock に切替
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading 用: instant | partial | never | reject) — default: instant
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
- LOG_DIR (ログ格納ディレクトリ) — default: logs
- KILL_FLAG_CLEAR_ON_START (0/1) — 本番では 0 推奨
- PID_FILE_PATH, KILL_FLAG_PATH, その他各種パス（Settings 参照）

一部モジュールは環境変数の値を厳密に検査します。config_setup で生成した .env の内容を必ず validate_config で確認してください。

---

## 使い方（主要 CLI / スクリプト）

- 環境設定ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存
    - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録
    - live: 実際のブローカークライアントを使用（KABU API 等の設定が必要）

- 監視ループ起動（SystemMonitor、リスク判定・Kill Switch 等）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（デフォルト 60）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）
  - news_nlp.score_news / regime_detector.score_regime を呼び出して使用

---

## 運用上の注意
- Kill Switch（data/kill.flag）
  - RiskMonitor 等が条件を満たすと KillSwitch が kill.flag を書き込み、ExecutionEngine に停止を促します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 に設定すると自動クリアされますが、本番では危険なため 0 を推奨します。

- ロギング
  - kabusys.utils.logging_setup.setup_logging によりコンソール出力と logs/<app_name>.log へ日次ローテーションで出力します。
  - LOG_DIR は環境変数で変更可能です。

- DB
  - monitoring 用は SQLite（Settings.sqlite_path）
  - 分析は DuckDB（Settings.duckdb_path）
  - paper_trading モードでは paper_trading 用 SQLite を使用して本番 DB と分離します

- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び出しプロセス優先度を上げようとします（OS 権限による失敗は警告でスキップされます）。

---

## ディレクトリ構成（主要ファイル）
（パッケージルート: src/kabusys 以下）

- __init__.py
- config.py — 環境変数読み込み / Settings クラス（.env 自動ロードロジック含む）
- config_setup.py — 対話式 .env ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py

- monitoring/
  - monitoring_db.py
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

- utils/
  - logging_setup.py
  - process_priority.py

- tools/
  - paper_verification_report.py

- data/ (推奨データディレクトリ)
  - monitoring.db (デフォルト)
  - kabusys.duckdb
  - paper_trading.db
  - kill.flag / stop_requested.flag / *.pid など

- logs/
  - execution.log, monitoring.log, ... （日次ローテート）

---

## 開発・拡張のヒント
- 単体関数（portfolio/*, research/*）は DB に依存しない純粋関数として設計されているためユニットテストが容易です。
- AI モジュールは OpenAI のレスポンス不安定性を考慮し、リトライやフォールバック（スコア 0）を実装しています。API 呼び出しの差し替え（モック）を行えばテスト可能です。
- Monitoring / Kill Switch は冪等操作を意識しており、部分失敗時のデータ保護（範囲限定の DELETE → INSERT 等）に配慮しています。

---

必要であれば README に「デプロイ手順（systemd ユニット / Dockerfile / docker-compose）」や「API / DB スキーマ詳細」「主要クラスのシーケンス図」などを追加できます。どの情報を追記したいか教えてください。