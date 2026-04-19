KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買 / 研究用フレームワークです。  
主な目的は次の通りです：

- 日次のファクター計算・特徴量探索（research）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine による発注（本番 / ペーパートレード切替）
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
- ニュースの NLP によるセンチメント評価 / 市場レジーム判定（OpenAI）
- 運用用のユーティリティ／ツール（設定ウィザード、設定検証、検証レポート）

機能一覧
--------
- 環境設定読み込み / .env ワークフロー（config_setup）
- 起動前設定検証（validate_config）
- ExecutionEngine 起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading DB に記録して本番 DB と分離
- 監視プロセス起動スクリプト（run_monitoring）
  - システム / データ鮮度 / 発注履歴 等をポーリングして監視ログに記録
  - Kill Switch の判断 / kill.flag 書き込みで ExecutionEngine 停止
- 監視 DB 用の永続化層（monitoring_db）と RiskMonitor / TradeMonitor / SystemMonitor
- ポートフォリオ構築ユーティリティ
  - 候補選定（select_candidates）
  - 等配分 / スコア重み付け（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
- Research 用ファクター計算（momentum / volatility / value 等）
- AI モジュール
  - ニュース NLP による銘柄センチメント（ai.news_nlp.score_news、OpenAI 必須）
  - マクロニュース + ETF MA を用いた市場レジーム判定（ai.regime_detector.score_regime、OpenAI 必須）
- 運用ツール
  - ペーパートレード検証レポート生成（tools.paper_verification_report）

セットアップ手順
----------------
1. リポジトリをクローンしてプロジェクトルートへ移動
   - この README はパッケージが src/kabusys 配下にある前提です。

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 最低限の依存例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (validate_config の YAML 検証を使う場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ プロダクションで使う場合は lock ファイルや requirements.txt を用意してください。

4. .env を作成
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - もしくは .env.template/.env.example を手動で編集して作成
   - 主な環境変数（デフォルト等は括弧内）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (http://localhost:18080/kabusapi)
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - KABUSYS_ENV (development | paper_trading | live) — 動作モード
     - LOG_LEVEL (INFO)
     - OPENAI_API_KEY (AI 機能を使う場合)

5. 設定を検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリの作成（必要に応じて）
   - デフォルト DB / ログパスは data/ と logs/ を参照します。自動作成される箇所もありますが確認してください。

使い方
------
起動スクリプト
- ExecutionEngine を起動（バックグラウンド監視プロセス等は別途）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV 環境変数で制御:
    - development: 開発用（発注なし）
    - paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
    - live: 実際の発注を行う（設定に注意）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト: 60 秒）

停止・制御
- stop_requested.flag
  - run_monitoring と run_execution のループはプロジェクトルート/data/stop_requested.flag の存在を検知すると安全に終了します。
- Kill Switch（運用上の強制停止）
  - KillSwitch は data/kill.flag を書くことで ExecutionEngine に停止シグナルを送ります。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 により起動時に kill.flag を自動でクリアする挙動を有効化できます（本番では 0 推奨）。

ログ
- ログは kabusys.utils.logging_setup によって設定されます。
  - デフォルトログディレクトリ: logs/
  - 各アプリ名ごとに日次ローテートされたファイルが生成（例: logs/execution.log, logs/monitoring.log）
  - 環境変数 LOG_DIR / LOG_LEVEL で調整可能

AI 機能
- OpenAI API を使う機能（ニュース NLP / レジーム判定）は OPENAI_API_KEY を要求します。
- 例:
  - ai.news_nlp.score_news(conn, target_date, api_key=...)
  - ai.regime_detector.score_regime(conn, target_date, api_key=...)

ツール
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

主要ファイル / ディレクトリ構成
-----------------------------
プロジェクトの主要なソース配置 (src/kabusys) の抜粋:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 作成ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数算出・スケーリング・lot 単位丸め
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py       — システム状態 / データ鮮度チェック
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - monitoring_engine.py    — 各 Monitor の束ね（ポーリング実行）
    - (その他 TradeMonitor / AlertManager 等)
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

設定関連（要確認）
-----------------
- DB 関連パス（デフォルト）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- 環境モード
  - KABUSYS_ENV:
    - development: 開発（発注制御あり）
    - paper_trading: 模擬発注（MockBroker）で paper DB に記録
    - live: 実際の発注
- ログ・PID・フラグ
  - PID ファイル: data/execution.pid（ExecutionEngine が書き込み）
  - stop フラグ: data/stop_requested.flag（存在で run ループを終了）
  - kill フラグ: data/kill.flag（Kill Switch により書き込まれる）

運用上の注意
-------------
- 本番運用（KABUSYS_ENV=live）の場合、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値などを慎重に設定してください。validate_config は本番向けチェックを含みます。
- OpenAI API を使う処理は外部 API 呼び出しに失敗する可能性があるため、フェイルセーフ（0.0 フォールバック、部分成功保持等）を備えていますが、API キー漏洩やコストには注意してください。
- データベースのパスを共有しないでください。paper_trading は専用 DB に記録することで本番 DB との混同を防止しています。

補足
----
- 各モジュールの docstring / 関数コメントには設計上の注意（ルックアヘッド防止、フェイルセーフ、フォールバック等）が記載されています。挙動を理解した上でカスタマイズしてください。
- 依存パッケージやバージョン、CI/CD 用の設定ファイル（requirements.txt / pyproject.toml など）がある場合はそれに従ってください（この README はソースから読み取れる仕様に基づく概要です）。

問題報告 / 貢献
----------------
バグ報告や機能改善の提案は issue を作成してください。PR は小さな単位で分かりやすく送り、テストやドキュメント更新を含めてください。

---
必要があれば、README に含めるコマンド例（実行サンプル）や environment var の一覧表、よくあるトラブルシューティング（例: DB ファイルが見つからない・OpenAI キー未設定・ログディレクトリ作成失敗）を追加できます。どの内容を詳細化したいか教えてください。