# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買 / 取引支援システムの一部コンポーネント群です。戦略の研究・ポートフォリオ構築、実行エンジン、監視、AI を使ったニュース評価などのユーティリティを含みます。

## プロジェクト概要
- 目的: 日本株の自動売買を安全に運用するための基盤機能群（発注エンジン、監視、リスク管理、ポートフォリオ構築、研究用ファクター計算、ニュースNLP 等）。
- 設計方針:
  - 環境変数/.env で設定管理
  - DuckDB（分析）と SQLite（監視・発注ログ）を併用
  - Paper trading（ペーパートレード）と Live（本番）を分離
  - LLM（OpenAI）を利用する機能は API キーで有効化し、失敗時にフェイルセーフで継続

## 主な機能一覧
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、紙上トレード用 DB に記録
  - プロセス優先度設定、PIDファイル管理、停止フラグ対応
- 監視ループ起動スクリプト（run_monitoring）
  - システム状態・データ鮮度・トレード状態・リスク監視のポーリング
  - MONITOR_POLL_INTERVAL によるポーリング間隔の上書き
- 設定ウィザード（config_setup）と設定検証ツール（validate_config）
  - .env の対話的作成/更新
  - 起動前の環境変数 / config YAML の検証
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
  - ペーパートレード DB を解析して稼働率、注文成功率、レイテンシ等を集計
- ポートフォリオ構築モジュール（portfolio）
  - 候補選定、重み計算、ポジションサイズ計算、セクター上限、レジーム乗数
- 研究・特徴量モジュール（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン、IC 計算、統計要約
- AI モジュール（ai）
  - ニュース NLP（news_nlp）: OpenAI で記事をスコアリングし ai_scores に書き込み
  - レジーム判定（regime_detector）: MA200 乖離 + マクロニュースセンチメントで 'bull'/'neutral'/'bear' を算出
- ユーティリティ
  - logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
     （本コードから想定される主要パッケージ: duckdb, psutil, openai, pytest, pyyaml など）
   - 必要に応じて OpenAI SDK, duckdb, psutil をインストールしてください:
     - pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を作成して環境変数を設定してください。
   - 注意: .env をリポジトリにコミットしないこと

5. データディレクトリ
   - デフォルトの DB/ログパス（存在しない場合は自動作成されることが多いですが、権限に注意してください）
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/

## 必須 / 主要な環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境指定:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- ログ:
  - LOG_LEVEL（例: INFO、DEBUG）
  - LOG_DIR（省略時: logs/）
- DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- AI (OpenAI):
  - OPENAI_API_KEY（ai.news_nlp / ai.regime_detector を使う場合必須）
- 監視関連:
  - MONITOR_POLL_INTERVAL（秒。run_monitoring のポーリング間隔を上書き。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア。production では 0 推奨）
- Paper trading 特有:
  - PAPER_FILL_MODE（instant|partial|never|reject、デフォルト instant）

## 使い方（主要なコマンド）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB に記録し Mock ブローカーを使用
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 実行中に data/stop_requested.flag を作成するとエンジンが停止します
    - Kill Switch により data/kill.flag が書き込まれると ExecutionEngine に停止を促します

- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を変更可能（最小 1 秒）
  - 監視は Settings.sqlite_path（本番の監視 DB）を使用（環境に依らず本番パス）

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスの指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（プログラム API）
  - OpenAI API キーを設定してから ai 関数を呼ぶ（例: kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）

## 停止・Kill の取り扱い
- stop_requested.flag (data/stop_requested.flag)
  - run_monitoring / run_execution のループを終了させるためのフラグ（存在すると監視ループ/エンジンが停止）
- kill.flag (Settings.kill_flag_path、デフォルト data/kill.flag)
  - KillSwitch が書き込む。ExecutionEngine は kill.flag を検知して安全に停止する
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動で消去（本番では無効推奨）

## ロギング
- setup_logging により stdout と日次ローテートファイル（logs/<app_name>.log）に出力
- ログレベルは LOG_LEVEL または setup_logging の引数で制御

## ディレクトリ構成（主要ファイル）
（ソースは src/kabusys 以下に配置されています）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動ロード、Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で ai_scores を更新
    - regime_detector.py — 市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite の永続化層（テーブル生成・読み書きユーティリティ）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （トレード監視、ログに基づくチェック）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成/クリア
    - monitoring_engine.py — 各モニターの統合（Polling Engine）
    - alert_manager.py — （通知管理、LINE などに接続する想定）
  - execution/
    - execution_engine.py — 実行エンジンコア
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py ...
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・リスク制限
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - data/ （実行時生成されることが多い）
    - monitoring DB / paper_trading DB / pid / flag ファイル 等
  - utils/
    - logging_setup.py — ログセットアップ
    - process_priority.py — プロセス優先度設定
    - その他ユーティリティ

（上記はリポジトリ内のソースを抜粋した概要です。個別モジュールにはさらに詳細な実装があります。）

## 注意点 / トラブルシューティング
- .env は絶対にリポジトリへコミットしないでください（秘密情報を含みます）。
- ログや DB の保存先ディレクトリに書き込み権限が必要です。特権がない環境ではファイルハンドラの作成に失敗し、コンソール出力のみで動作します。
- OpenAI を使う機能はネットワーク依存かつ API 利用料金が発生します。API キーの管理に注意してください。
- Monitoring は Settings.sqlite_path（監視 DB）を常に使用します。実行エンジンは KABUSYS_ENV に応じて paper_sqlite_path を選択します（本番と分離）。
- DuckDB / SQLite のファイルバージョンや executemany の挙動（空リスト）に注意（コード内で互換性対策済み箇所あり）。

## 開発・テスト
- 単体関数群（portfolio, research など）は副作用がなくメモリ内で完結する設計なのでユニットテストが作りやすくなっています。
- AI 系の関数は API 呼び出し部分をテスト時にモックできるように設計されています（例: _call_openai_api を patch する）。

---

不明点や追加してほしい利用例（例: system_monitor の具体的な使用、ExecutionEngine の起動フラグ詳細など）があれば教えてください。README をさらに詳しく拡張します。