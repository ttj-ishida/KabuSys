KabuSys
======

日本株向け自動売買・研究基盤の軽量コアライブラリです。Portfolio 構築、ポジションサイズ計算、監視・アラート、Paper Trading 用検証、LLM を使ったニュースセンチメントやレジーム判定などのユーティリティを含みます。

この README はリポジトリ内の主要スクリプト／モジュールの使い方とセットアップ手順、ディレクトリ構成をまとめたものです。

主な特徴
------
- ポートフォリオ構築
  - シグナル選定（スコア順・順位） / 等金額・スコア加重の重み計算
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap）
  - セクター集中制限の適用、レジーム乗数（bull/neutral/bear）
- 研究用ファクター計算・探索
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を入力）
  - 将来リターン、IC（情報係数）や統計サマリー
- 実行（Execution）エンジン（起動スクリプト）
  - 本番 / ペーパートレード切替（KABUSYS_ENV に依存）
  - Paper Trading は mock ブローカー・専用 SQLite DB（data/paper_trading.db）で完全分離
- 監視（Monitoring）
  - システム稼働・データ鮮度・トレードログ・リスク監視
  - Kill Switch（閾値超過で data/kill.flag を書き込み ExecutionEngine を停止）
  - 監視ログは SQLite（data/monitoring.db）に永続化
- LLM 統合（OpenAI）
  - ニュースセンチメント解析（ai/news_nlp.py）
  - マクロニュース + ETF MA を使った市場レジーム判定（ai/regime_detector.py）
  - API 呼び出しはリトライ / フェイルセーフ設計
- 運用ユーティリティ
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 起動前の設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ロギング / プロセス優先度設定ユーティリティ（utils）

必須・主要な環境変数
------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: execution モード
  - development / paper_trading / live（デフォルト: development）
  - KABUSYS_ENV=paper_trading の場合、Execution は mock ブローカー & PAPER_TRADING_SQLITE_PATH を使用
- OPENAI_API_KEY: LLM 機能を使う場合に必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- その他 Settings クラスで参照する項目は src/kabusys/config.py を参照

セットアップ
------
1. Python 環境準備（推奨: v3.10+）
2. 依存ライブラリをインストール（例）
   - duckdb, psutil, openai, PyYAML（任意：config YAML 検証時）
   - 例: pip install duckdb psutil openai PyYAML
   - 実プロジェクトでは requirements.txt / poetry 等で管理してください
3. リポジトリのプロジェクトルートに移動し、.env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 生成した .env を確認・編集してください（.env は決して VCS にコミットしない）
4. 設定検証:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする（CI 等）場合: python -m kabusys.validate_config --strict
5. データディレクトリ作成（例）
   - mkdir -p data logs
   - もしくは setup_logging が起動時に自動作成します

使い方（主要スクリプト）
-----------------
- Execution エンジン起動
  - python -m kabusys.run_execution
  - 動作概要:
    - process priority を high に設定し、設定に応じて本番 DB または paper_trading DB に接続
    - BrokerClientFactory が settings に基づきブローカークライアントを生成（paper_trading は Mock）
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag を監視して安全停止
  - ペーパートレード実行例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 動作概要:
    - システム（CPU/メモリ/ディスク）やデータ鮮度を定期的にチェックして SQLite に記録
    - デフォルトポーリング間隔: 60 秒（環境変数で上書き可）
      - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 監視スクリプトは KABUSYS_ENV に依らず本番 sqlite_path を使用して監視ログを保持

- 設定検証（CLI）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit code 1）

- .env ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

運用メモ / フラグ類
----------------
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution が検出して停止または起動を抑止します
- Kill Switch:
  - KillSwitch は設定した kill_flag_path（Settings.kill_flag_path, デフォルト data/kill.flag）に理由を書き込みます
  - ExecutionEngine はこの kill.flag を見て安全に停止する設計です
  - Settings.kill_flag_clear_on_start=1 にすると起動時に kill.flag を自動で消去（本番では 0 推奨）
- PID ファイル:
  - 実行時に pid を data/execution.pid 等に書きます（設定で変更可）

ログ
---
- setup_logging により stdout と日次ローテートファイル（logs/<app_name>.log）に出力
- 環境変数 LOG_DIR でログ保存先を指定可能
- デフォルトの保持日数は 30 日（TimedRotatingFileHandler）

コード構成（主要ファイル / ディレクトリ）
---------------------------------
以下は src/kabusys 以下の主要なファイルと簡単な説明です。

- src/kabusys/
  - __init__.py                    — パッケージ定義（バージョン情報）
  - config.py                      — 環境変数・設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

- src/kabusys/utils/
  - logging_setup.py               — 一元的なログ設定ユーティリティ
  - process_priority.py            — プロセス優先度 / CPU affinity 設定ユーティリティ

- src/kabusys/portfolio/
  - portfolio_builder.py           — 候補選定・重み計算
  - position_sizing.py             — 株数（ロット）決定ロジック
  - risk_adjustment.py             — セクターキャップ・レジーム乗数

- src/kabusys/monitoring/
  - monitoring_db.py               — SQLite 永続化層（テーブル生成 / ログ書き込み）
  - system_monitor.py              — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py               — （トレードログ監視、滞留注文等 — 実装参照）
  - risk_monitor.py                — ドローダウン / ポジション上限監視
  - kill_switch.py                 — kill.flag 書き込みロジック
  - monitoring_engine.py           — 各 Monitor を束ねるエンジン
  - alert_manager.py               — （アラート送信管理 — 実装参照）

- src/kabusys/execution/
  - execution_engine.py            — 実行エンジン本体（注文管理・リスク管理と結合）
  - broker_factory.py              — ブローカークライアント生成（本番 / mock 切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py
                                   — 実行系の各コンポーネント

- src/kabusys/research/
  - factor_research.py             — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py         — 将来リターン / IC / 統計サマリー
  - __init__.py                    — 便利関数のエクスポート

- src/kabusys/ai/
  - news_nlp.py                    — ニュースを LLM でセンチメント化、ai_scores へ書き込み
  - regime_detector.py             — ETF MA + マクロニュースでレジーム判定
  - __init__.py                    — エクスポート（score_news 等）

- src/kabusys/tools/
  - paper_verification_report.py   — Paper Trading 検証レポート生成スクリプト

- src/kabusys/monitoring/monitoring_db.py — DB スキーマ定義（テーブル・マイグレーション処理含む）

注意事項 / ベストプラクティス
-----------------------
- .env は秘匿情報を含むため絶対にリポジトリにコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では kill_flag_clear_on_start=0 を推奨します。
- OpenAI など外部 API 利用時は API キーのローテーション／レート制限を考慮してください。
- Paper Trading 用 DB は運用実データと分離して管理してください（PAPER_TRADING_SQLITE_PATH）。
- DuckDB は分析用のローカル列指向 DB として設計されています。prices_daily / raw_financials 等のスキーマを事前にロードしてください。
- validate_config.py を CI に組み込むと設定ミスを早期に検出できます。

開発に関して
-----------
- 単体機能は pure function（研究・ポートフォリオの計算など）として設計されている箇所が多く、テストが書きやすい構成です。
- OpenAI 呼び出し部分は API 抽象化・リトライを行っており、ユニットテスト時には _call_openai_api をモックしてください（各モジュールの docstring に記載あり）。

お問い合わせ / 貢献
----------------
- バグ報告や改善提案はリポジトリの Issue にお願いします。
- 大きな設計変更は事前に Issue で相談してください。

---
この README はコードベース（src/kabusys）を元に作成しました。詳細は各モジュールの docstring（ソース内コメント）を参照してください。