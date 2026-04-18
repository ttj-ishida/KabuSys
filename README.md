# KabuSys

日本株向け自動売買システム（ライブラリ + 起動スクリプト群）

このリポジトリは、銘柄選定・ポジションサイジング・発注エンジン・監視・AI補助（ニュースNLP / レジーム判定）などを備えた自動売買システムのコア実装群を含みます。

## 概要
- プロジェクト名: KabuSys
- 目的: 日本株の自動売買ワークフロー（リサーチ → ポートフォリオ構築 → 注文実行 → 監視）をサポートするライブラリと運用用スクリプト群。
- 特長:
  - DuckDB を用いた分析向けデータ処理（prices_daily / raw_financials 等）
  - SQLite を用いた監視・トレードログ（monitoring.db / paper_trading.db）
  - Paper Trading モード（本番 DB と完全分離して動作）
  - OpenAI を利用したニュースセンチメント（ニュースNLP）およびマクロセンチメントによる市場レジーム判定
  - 監視（MonitoringEngine）によりプロセス稼働・データ鮮度・リスク（ドローダウン・ポジション上限）を監視。必要に応じて Kill Switch（data/kill.flag）を発行

## 機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（paper_trading 時は MockBroker と専用 DB を利用）
  - run_monitoring.py: SystemMonitor を定期ポーリングして監視ログを記録
- 設定関連 CLI
  - config_setup.py: .env を対話式で生成・更新するウィザード
  - validate_config.py: .env や config/*.yaml の起動前チェック（--strict オプションあり）
- モジュール（抜粋）
  - kabusys.portfolio: 銘柄選定・重み計算・ポジションサイズ計算・セクター制限・レジーム乗数
  - kabusys.research: ファクター計算（Momentum / Volatility / Value）や特徴量解析ユーティリティ
  - kabusys.ai: news_nlp（ニュースセンチメント） / regime_detector（市場レジーム判定）
  - kabusys.monitoring: SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / MonitoringDB
  - kabusys.utils: logging_setup（統一ログ設定）/ process_priority（優先度設定）
  - tools: paper_verification_report（Paper Trading の検証レポート生成）
- DB スキーマ（監視用）
  - system_status, trade_logs, positions, risk_logs, dashboard（init_monitoring_db にて作成・マイグレーション実行）

## セットアップ手順（開発・運用向けの概要）
前提:
- Python 3.10 以上を推奨（型注釈に | 記法などを使用）
- SQLite は標準ライブラリで利用可能
- システムにより追加パッケージが必要（下記）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   代表的な依存（プロジェクトに requirements.txt が無い場合の例）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config YAML 検証が必要な場合）
   例:
   - pip install duckdb psutil openai PyYAML

3. .env の準備
   - 対話式に .env を作る:
     - python -m kabusys.config_setup
   - または手動で作成し、下記の環境変数を設定する（必須／任意を参照）

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

5. ログディレクトリの作成（通常は自動で作成されますが手動でも）
   - mkdir -p logs
   - デフォルトログディレクトリは `logs/`。環境変数 LOG_DIR で変更可能。

必須となる主な環境変数（.env に設定）
- JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）

主なオプション / 運用用環境変数
- KABUSYS_ENV : 実行環境（development / paper_trading / live）[default: development]
  - paper_trading: MockBroker を使用し、専用 DB (data/paper_trading.db) に記録
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : Paper Trading 時の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE : paper_trading 時の約定動作（instant|partial|never|reject）
- LOG_LEVEL / LOG_DIR
- OPENAI_API_KEY : OpenAI を使う機能（ニュースNLP / レジーム判定）で必要
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START : ExecutionEngine 起動時に kill.flag を自動でクリアするか（0/1）

※ .env の自動ロード
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます。
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

## 使い方（主要なコマンド）
- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- 実行エンジン起動（銘柄選定 → 注文実行を行う）
  - 本番/開発共通:
    - python -m kabusys.run_execution
  - Paper Trading（環境変数 KABUSYS_ENV=paper_trading を設定）
    - python -m kabusys.run_execution  （Settings.is_paper により paper_trading 用 DB と MockBroker を使用）

  起動時の挙動:
  - プロセス優先度を high に設定し、PID ファイル（data/execution.pid）を使用
  - 停止フラグ（data/stop_requested.flag）や kill.flag（data/kill.flag）を検知すると安全終了

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL=30
  - 監視は monitoring.db（sqlite）に記録し、duckdb も併用
  - 停止フラグ読み取り: data/stop_requested.flag

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - ニューススコア:
    - kabusys.ai.score_news をエントリポイントから呼び出して使用（スクリプトはモジュールを通して呼ぶ想定）
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime を使用
  - 注意: API 呼び出しはリトライやフェイルセーフが組み込まれているが、APIキーの管理は注意して行ってください。

## 運用上の重要ポイント
- Paper Trading は本番 DB と完全に分離します（paper_trading 用 SQLite を使用）。本番 DB を誤って上書きしないよう KABUSYS_ENV を正しく設定してください。
- Kill Switch:
  - RiskMonitor / KillSwitch により致命的リスク（大きなドローダウン、ポジション上限超過）を検出した場合に `data/kill.flag` を書き込んで ExecutionEngine に停止シグナルを送れます。
  - ExecutionEngine 側は起動時に kill.flag の自動クリア挙動を制御可能（KILL_FLAG_CLEAR_ON_START）。
- ログ:
  - ロギングは統一的に setup_logging を使用。標準出力と日次ローテートファイル出力（logs/<app_name>.log）に出力します。
- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を呼びます（psutil が必要）。設定に失敗しても警告に留まります。

## 主要ファイル・ディレクトリ構成
（src/kabusys 以下、重要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / Settings 管理（自動 .env ロード機能あり）
    - config_setup.py               — .env 対話式ウィザード
    - validate_config.py            — 起動前検証 CLI
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — Monitoring ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading レポート生成ツール
    - ai/
      - news_nlp.py                 — ニュースセンチメント（OpenAI 依存）
      - regime_detector.py          — 市場レジーム判定（OpenAI 依存）
    - research/
      - factor_research.py          — モメンタム等のファクター計算（DuckDB）
      - feature_exploration.py      — 将来リターン・IC・統計サマリー
    - portfolio/
      - portfolio_builder.py        — 候補抽出・重み計算
      - position_sizing.py          — 株数算出ロジック（lot/aggregate cap 等）
      - risk_adjustment.py          — セクターキャップ・レジーム乗数
    - monitoring/
      - monitoring_db.py            — SQLite スキーマ初期化・永続化層
      - system_monitor.py           — システム状態・データ鮮度監視
      - risk_monitor.py             — ドローダウン・ポジション数監視
      - kill_switch.py              — kill.flag 書込みロジック
      - monitoring_engine.py        — 各モニタを束ねるランナー
      - trade_monitor.py            — (トレード監視関連)
    - utils/
      - logging_setup.py            — ログ設定ユーティリティ
      - process_priority.py         — 優先度 / CPU affinity ユーティリティ
    - data/                          — 実行時に作成される可能性のあるファイル（例: data/*.db, *.pid, kill.flag）
- config/
  - system_config.yaml, data_config.yaml, ... （テンプレート・運用用設定ファイル群。validate_config で確認）

## 開発時のヒント
- DuckDB 接続を利用する reseach / ai モジュールは prices_daily / raw_financials / raw_news 等のテーブルを想定しています。分析用データは事前にロードしてください。
- テスト時は OPENAI 呼び出し関数をモックすることを推奨（モジュール内で明確に差し替え可能な関数を使用しています）。
- config_setup.py で生成される .env は絶対に VCS にコミットしないでください（トークン等の機密情報を含むため）。

---

この README はコードベースから主要な使い方・構成情報を抽出してまとめたものです。実際の運用にあたっては、プロジェクト付属の運用手順書（もしあれば）や config/*.yaml の内容を必ず確認してください。必要であれば README を運用ドキュメント向けに追記・展開します。