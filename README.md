KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的としたモジュール群です。  
主な責務は以下の通りです。

- ExecutionEngine（発注エンジン）: ブローカーと連携して注文の管理・実行を行う
- Monitoring（監視）: システム状態・注文ログ・リスク指標を監視し、Kill Switch を発動する
- Research（ファクター計算）: DuckDB 上の時系列データからファクターを算出する
- Portfolio（銘柄選定・ポジションサイズ計算）: 候補選定・ウェイト・株数決定の純関数群
- AI（ニュース NLP / レジーム判定）: OpenAI を用いてニュースセンチメントや市場レジームを評価
- Tools（ユーティリティ）: ペーパートレード検証レポート等のスクリプト

主な特徴 / 機能一覧
-----------------
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV に応じて Paper/Live 切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動
- 環境設定支援
  - config_setup.py — 対話式に .env を生成 / 更新
  - validate_config.py — .env と config/*.yaml を検証する CLI
- データベース
  - DuckDB（分析用, デフォルト data/kabusys.duckdb）
  - SQLite（監視 / 発注ログ, デフォルト data/monitoring.db）
  - Paper trading 用 SQLite（KABUSYS_ENV=paper_trading のとき分離, data/paper_trading.db）
- 監視 / リスク管理
  - SystemMonitor: CPU / メモリ / ディスク使用率、データ鮮度、プロセス死活を記録
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウン、ポジション上限を監視
  - KillSwitch: 条件に応じて data/kill.flag を作成し ExecutionEngine を停止させる
- 分析 / 研究
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - IC 計算、将来リターン計算、特徴量サマリー
- AI 統合（OpenAI）
  - ニュースを LLM で評価し ai_scores テーブルを更新
  - レジーム判定（ETF マクロ指標 + LLM）
  - OpenAI の利用は OPENAI_API_KEY を設定する必要があります
- ペーパートレード検証
  - tools.paper_verification_report: 指定期間の稼働率・成功率・レイテンシ等をレポート化

セットアップ手順
----------------
1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な依存（手動インストール例）:
     - pip install duckdb psutil openai
     - （YAML 検証や一部ツールに PyYAML が必要: pip install pyyaml）
4. 必要ディレクトリ作成（ログ / DB 保存先等）
   - mkdir -p data logs
5. 環境変数の設定
   - 対話式ウィザードで .env を生成（推奨）
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照）
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（任意で上書き）
     - LOG_LEVEL（例: INFO）
   - 自動ロードはデフォルトで .env / .env.local から行われます。無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方
------
基本的な起動例（プロジェクトルートで実行）:

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
    - 起動時に data/stop_requested.flag が存在する場合は起動を行いません
    - 実行中に data/stop_requested.flag が作成されるとエンジンは停止を受け付けます
    - PID ファイルは data/execution.pid（デフォルト）に保存されます

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを残します

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード（警告をエラーとして扱う）:
    - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で別パス指定可能。

- AI 機能（プログラム的に呼び出す）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=...) など
  - OPENAI_API_KEY が必要（引数または環境変数で指定）

ログ
---
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。
- ログレベルは LOG_LEVEL 環境変数または logging_setup.setup_logging の引数で制御できます。
- ログ出力先ディレクトリは LOG_DIR 環境変数で変更可能。

注意事項 / 実運用のポイント
-------------------------
- KABUSYS_ENV を "live" に設定する際は特に注意してください（validate_config は警告を出します）。
- Kill Switch（data/kill.flag）は実行中の ExecutionEngine に安全に停止指示を出すための仕組みです。自動クリア設定（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。
- Monitoring は監視ログを常に本番 sqlite_path に書きます（監視は本番 DB を参照）。
- Paper trading と Live は DB を分離しておくことを推奨します（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を使う処理は外部 API 呼び出しを伴うため、ネットワークエラーやレート制限への対処（リトライ、バックオフ）が組み込まれていますが、API キーの管理とコストには注意してください。

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 以下の主要なファイル/ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - run_execution.py                    — ExecutionEngine 起動スクリプト
  - run_monitoring.py                   — SystemMonitor 起動スクリプト
  - config.py                           — 環境変数/設定読み込みユーティリティ
  - config_setup.py                     — .env 対話式ウィザード
  - validate_config.py                  — 設定検証 CLI
  - tools/
    - paper_verification_report.py      — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py              — 候補選定・ウェイト算出
    - position_sizing.py                — 株数決定・投資制限ロジック
    - risk_adjustment.py                — セクター制限・レジーム乗数
  - research/
    - factor_research.py                — ファクター計算（momentum/value/vol）
    - feature_exploration.py            — IC / 将来リターン / 統計
  - ai/
    - news_nlp.py                       — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py                — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py                  — 監視用 SQLite テーブル定義 + DB ラッパ
    - system_monitor.py                 — システム状態・データ鮮度監視
    - risk_monitor.py                   — ドローダウン・ポジション上限監視
    - kill_switch.py                    — Kill Switch 実装
    - monitoring_engine.py              — 各 Monitor の統合ポーリング
  - utils/
    - logging_setup.py                  — ログセットアップ共通処理
    - process_priority.py               — プロセス優先度 / CPU affinity
  - （その他: execution/*.py, data/*.py などエンジン側コンポーネント）

よく使う環境変数（抜粋）
-----------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- KABUSYS_ENV — "development" | "paper_trading" | "live"
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパー取引用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（例: INFO）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject）

その他 / 開発向けヒント
---------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup で注意書きあり）。
- DuckDB を用いることで分析処理は高速に実行できます。research モジュールは DuckDB 接続を受け取って計算します。
- テスト・ローカル実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効にできます。

問い合わせ / 貢献
-----------------
本リポジトリに変更を加える際は、まずユニットテストや validate_config を実行して設定やマイグレーションの影響を確認してください。README に記載のない動作やエラーが出る場合は、該当モジュールの docstring とログを参照してください。

---  
以上。必要であれば各コマンドのより詳細な使用例や運用手順（systemd 用ユニットファイル、Docker 化、CI 設定例など）を追加で作成します。どの部分を重点的にドキュメント化したいか教えてください。