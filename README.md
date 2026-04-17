# KabuSys — README (日本語)

概要
---
KabuSys は日本株向けの自動売買 / 研究用ツール群です。  
主な機能はシグナル生成・ポートフォリオ構築・発注実行・監視・研究（ファクター計算）・AI ベースのニュース評価などを含みます。  
このリポジトリはライブラリとして利用でき、コマンドラインから主要なサービス（ExecutionEngine、Monitoring）やユーティリティ（環境設定ウィザード、設定検証、ペーパートレード検証レポート等）を起動できます。

特徴
---
- ExecutionEngine（実取引 / ペーパートレード切替）
  - KABUSYS_ENV による実運用・ペーパートレードの切替
  - paper_trading 時は MockBrokerClient を使用し DB を分離
- 監視（Monitoring）
  - CPU / メモリ / ディスク，プロセス存在，データ鮮度のポーリング監視
  - 注文滞留・約定異常・ドローダウン・ポジション上限の監視
  - Kill Switch 機能（フラグファイルにより ExecutionEngine を安全に停止）
- ポートフォリオ構築（選定・重み付け・株数計算）
  - 等分配・スコア加重・リスクベース配分
  - セクター集中制限、レジームに応じた乗数
- 研究用ツール
  - DuckDB を利用したファクター計算（Momentum, Volatility, Value）
  - 将来リターン、IC 計算、特徴量サマリー
- AI モジュール
  - OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント（ai_scores）や市場レジーム判定
  - バックオフ・バリデーション・部分書き込み（冪等）を考慮した実装
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証（validate_config）
  - ペーパートレード検証レポート生成ツール

前提・依存
---
- Python 3.10+
- 主なライブラリ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル YAML 検証を行う場合に推奨）
- 環境変数と .env ファイル管理（詳細は下記）

セットアップ手順
---
1. リポジトリをクローンし、仮想環境を作成して依存をインストールしてください。
   例:
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt
   （requirements.txt が無い場合は手動で duckdb, psutil, openai 等をインストール）

2. .env の作成
   - 対話式ウィザードを実行して .env を生成:
     - python -m kabusys.config_setup
   - あるいは .env.example（存在する場合）を参考に .env を手動作成してください。

3. 主要な環境変数（最低限必要）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - デフォルト（自動設定されるもの）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - KABUSYS_ENV: development | paper_trading | live

4.（任意）.env 自動ロード
   - パッケージ読み込み時、プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env → .env.local を自動で読み込みます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（主要コマンド）
---
- 環境ウィザード（.env の生成／更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV で制御:
    - paper_trading: MockBroker を用い data/paper_trading.db に記録（本番 DB と完全分離）
    - live: 実取引（kabuステーション API を使用）
  - 実行中プロセスの PID は data/execution.pid に保存されます
  - 終了を促す外部フラグ: data/stop_requested.flag（このファイルを作ると起動中のループは停止します）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（環境に関わらず同一 DB を参照）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーが必須: 環境変数 OPENAI_API_KEY か関数引数で指定
  - ニューススコア:
    - kabusys.ai.score_news（プログラムから呼び出す API）
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime（DuckDB 接続・date を渡して呼ぶ）

停止・Kill Switch
---
- グローバル停止（run_execution / run_monitoring のループを安全に止める）
  - data/stop_requested.flag を作成する（手動でファイルを作る）
  - スクリプトは定期的にこのファイルをチェックし、検出したらループを終了します。
- Execution 停止のための Kill Switch（自動アラートによる停止）
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine 停止を誘発します
  - 設定（Settings.kill_flag_path）でパスを変更可能
  - 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にして自動クリアを避けることを推奨

設定・設定検証のポイント
---
- 自動ロード順: OS 環境変数 > .env.local > .env
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- ログレベルや DB パスは .env で上書き可能
- validate_config は config/*.yaml の存在と（PyYAML があれば）YAML パースまで確認します

データベース
---
- DuckDB: 分析・研究用（デフォルト data/kabusys.duckdb）
- SQLite: 監視ログ・発注履歴（デフォルト data/monitoring.db）
- Paper trading 用 SQLite（分離）: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
- monitoring_db.init_monitoring_db により DB スキーマが自動で作成・マイグレーションされます

よく使う環境変数（抜粋）
---
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- MONITOR_POLL_INTERVAL (監視ポーリング秒, デフォルト 60)

ディレクトリ構成（主要ファイル）
---
- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / .env 自動ロード / Settings クラス
    - config_setup.py                 — .env 対話式ウィザード
    - validate_config.py              — 起動前設定検証 CLI
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート
    - ai/
      - __init__.py
      - news_nlp.py                   — ニュース NLP（OpenAI）スコアリング
      - regime_detector.py            — 市場レジーム判定（MA + LLM）
    - monitoring/
      - monitoring_db.py              — SQLite 永続化層（schema + クラス）
      - monitoring_engine.py          — 各 Monitor を束ねる
      - system_monitor.py             — CPU/メモリ/ディスク/データ鮮度監視
      - trade_monitor.py              — 注文滞留・約定異常監視
      - risk_monitor.py               — ドローダウン・ポジション上限監視
      - kill_switch.py                — kill.flag 管理
      - alert_manager.py              — （アラート送信管理、実装ファイル）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py           — psutil を用いた優先度 / affinity 設定
      - __init__.py
    - その他: execution/*（注文関連）, data/*（データ管理）等（開発中の実装が含まれる可能性あり）

開発者向けメモ
---
- プロセス優先度設定: 起動直後に set_process_priority("high") が呼ばれます（psutil 権限に依存）。
- Run スクリプトはパッケージモジュールとして起動可能:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- AI 関連は OpenAI SDK のレスポンス形式・エラーコードに依存しており、テスト時は _call_openai_api をモックする設計になっています。
- DB マイグレーションは簡易的に init_monitoring_db 内で実行（ALTER TABLE 追加等）。
- .env の読み込みはプロジェクトルートを .git or pyproject.toml で自動検出するため、パッケージ配布後も動作するよう設計されています。

トラブルシューティング
---
- .env が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルートの検出条件（.git または pyproject.toml）を満たしているか確認
- 実行時に DB ファイルが見つからない:
  - 環境変数 DUCKDB_PATH / SQLITE_PATH を確認
  - validate_config でパス周りの警告を確認
- OpenAI 呼び出しでエラーが出る:
  - OPENAI_API_KEY を設定（.env または OS 環境変数）
  - ネットワーク・レート制限はリトライ実装あり。ログを確認

ライセンス・貢献
---
- この README ではコードの利用手順と概要を示しています。ライセンスやコントリビュートルールはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

最後に
---
まずは .env を作成し（python -m kabusys.config_setup）、設定検証（python -m kabusys.validate_config）を行い、Paper モードで動かす場合は python -m kabusys.run_execution（KABUSYS_ENV=paper_trading） と python -m kabusys.run_monitoring を組み合わせて試してください。必要に応じて OpenAI 関連のキーを設定すれば、ニューススコアやレジーム判定機能が利用可能です。