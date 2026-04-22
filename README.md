KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。  
主な機能は以下のとおりです。

- 注文実行エンジン（ExecutionEngine）／ブローカー抽象化（paper/live 切替）
- 監視サブシステム（System / Trade / Risk モニタ、Kill Switch、アラート）
- ポートフォリオ構築（候補選定・重み計算・セクター上限・ポジションサイジング）
- リサーチ（ファクター計算・特徴量探索、IC 等）
- ニュース NLP を用いたセンチメント評価（OpenAI 経由）
- Paper Trading 用検証レポート生成ツール
- .env ウィザード / 設定検証ツール / ロギングユーティリティ 等の運用支援

主な設計方針
- DB（SQLite / DuckDB）を用いたデータ永続化・分析
- 環境変数経由の設定（.env サポート、.env.local 上書き）
- 本番 / ペーパー（paper_trading）を明確に分離（paper_trading は専用 SQLite）
- OpenAI を使った NLP 機能は API キー必須。失敗時はフェイルセーフで継続

機能一覧
--------
- 実行（run_execution.py）
  - KABUSYS_ENV=paper_trading のとき MockBrokerClient を使用し data/paper_trading.db に記録
  - リスク管理（RiskManager）、注文管理（OrderManager）等の組み立て
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）で安全停止
- 監視（run_monitoring.py）
  - SystemMonitor（CPU/Memory/Disk/プロセス生存）、TradeMonitor、RiskMonitor のポーリング
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視ログは SQLite（settings.sqlite_path）に保存
- 監視 DB（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを提供
- ポートフォリオ（portfolio/*）
  - 候補選定、等重・スコア重み、セクター制限、レジーム乗数、ポジションサイズ計算
- リサーチ（research/*）
  - モメンタム / ボラティリティ / バリュー / 将来リターン / IC / 統計サマリー
  - DuckDB を使った SQL ベースの計算
- AI（ai/*）
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector: ETF とマクロニュースを合成して market_regime を判定
- ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境変数・config/*.yaml の事前検証 CLI
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

セットアップ手順
----------------
前提
- Python 3.9+（型アノテーションや一部ライブラリが必要）
- 推奨パッケージ（プロジェクトの要件に合わせてインストールしてください）:
  - duckdb, psutil, openai, PyYAML（YAML 検証用; 任意）

例（pip）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

初期設定
1. .env を作成（ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動作成

2. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

ディレクトリ・ファイル準備
- data/ ディレクトリ（デフォルト DB / PID / フラグを格納）
  - data/kabusys.duckdb （DuckDB デフォルト）
  - data/monitoring.db   （Monitoring SQLite デフォルト）
  - data/paper_trading.db（paper_trading 用 SQLite）
  - data/execution.pid, data/kill.flag, data/stop_requested.flag など
- logs/ ディレクトリ（ログ出力: logs/<app_name>.log）

重要な環境変数（主なもの）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
- KABU_API_PASSWORD: 必須（kabuステーション API）
- OPENAI_API_KEY: OpenAI を使う機能に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ロギング設定
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）

使い方
------
起動スクリプト
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag が作成されると安全に停止します
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に settings.sqlite_path を使用（環境に依存せず本番 DB パスを用いる設計）

設定関連
- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告もエラー扱い

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH  または 環境変数 PAPER_TRADING_SQLITE_PATH

AI 機能
- OpenAI API キーが必要（OPENAI_API_KEY または関数引数で指定）
- news_nlp.score_news / regime_detector.score_regime といった API を用いて
  ai_scores や market_regime に書き込みます（主にバッチ処理用途）

ログ
- ロギングは共通ユーティリティ kabusys.utils.logging_setup.setup_logging で管理
- デフォルトで stdout（コンソール）と logs/<app_name>.log に日次ローテーションで出力
- ログレベルは LOG_LEVEL で制御

停止・Kill Switch
- KillSwitch は risk/drwaodown 等の条件で data/kill.flag を書き込むことで Execution を停止させます
- 手動停止・運用操作は data/kill.flag を書いたり削除したりして制御できます
- run_execution/run_monitoring は stop_requested.flag（data/stop_requested.flag）を使ったシャットダウンにも対応

ディレクトリ構成（抜粋）
---------------------
- src/kabusys/
  - __init__.py
  - config.py                : 環境変数・Settings
  - config_setup.py          : .env 対話式ウィザード
  - validate_config.py       : 設定検証 CLI
  - run_execution.py         : ExecutionEngine 起動スクリプト
  - run_monitoring.py        : Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py       : 監視 DB スキーマ + ラッパー
    - system_monitor.py
    - trade_monitor.py       : （ファイル内に実装あり）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/               : ExecutionEngine / OrderManager / BrokerFactory / RiskManager 等
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
  - utils/
    - logging_setup.py
    - process_priority.py

（注）一部ファイル名は抜粋しています。詳細はソースツリーを参照してください。

運用上の注意
------------
- 本番環境（KABUSYS_ENV=live）では設定値を慎重に確認してください（validate_config の警告有効推奨）。
- .env は機密情報を含むため Git 管理しないでください。
- OpenAI 利用部分は API 費用・レート制限の影響を受けます。リトライや失敗時のフェイルセーフ実装はありますが、運用時に監視を行ってください。
- paper_trading モードはあくまで検証用で、本番 DB とは完全に分離されます。

補足（開発者向け）
------------------
- ロギング・プロセス優先度設定等はユーティリティ化されており、起動スクリプトから一貫して利用されています
- DuckDB は分析用に使われ、research / ai の多くの関数は DuckDB 接続を受け取る純粋関数として実装されています
- テストしやすさを考慮して外部 API 呼び出し部分は差し替え可能（テスト用パッチ推奨）

問題・貢献
---------
バグ報告や Pull Request はリポジトリの Issue/PR を利用してください。  
設計思想や API 変更はまず Issue にて相談をお願いします。

以上。README の内容で不足している項目や、特定の使い方（例: ExecutionEngine の詳細なパラメータ、OrderManager の API など）を追記希望であれば知らせてください。