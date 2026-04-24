KabuSys — 日本株自動売買システム（簡易 README）
======================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージ群です。本コードベースは以下の主要機能を持ちます。
- 発注実行エンジン（ExecutionEngine） — 本番/ペーパートレード対応
- 監視コンポーネント（Monitoring） — システム状態・注文・リスク監視、Kill Switch
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量探索、IC 計算など）
- AI モジュール（ニュースのセンチメント評価、レジーム判定） — OpenAI を利用
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）
- ツール群（Paper Trading の検証レポート生成など）

主な特徴
--------
- 本番 / ペーパートレード切替（KABUSYS_ENV 環境変数）
- 設定ウィザード（python -m kabusys.config_setup）で .env を対話式に生成
- validate_config による起動前チェック（--strict オプションあり）
- SQLite（監視用）と DuckDB（分析用）を併用
- モジュール設計でリサーチ / 実行 / 監視が分離
- OpenAI（gpt-4o-mini）によるニュース NLP / レジーム判定を実装（API キー必須）
- 日次ログローテーション（TimedRotatingFileHandler）

セットアップ手順
----------------

1. リポジトリをクローン / ワークツリー配置
   - パッケージが src/kabusys 配下に配置されている想定です。

2. Python 環境準備（例）
   - Python 3.9+ を推奨（コード内 typing/feature に依存）
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - PyYAML を使う場合（validate_config が YAML のパース検証を行う）:
     - pip install pyyaml
   - その他依存関係はプロジェクトの requirements.txt があればそれを使用してください。

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成。
   - 自動ロード:
     - Settings モジュールは、プロジェクトルートに .env/.env.local があれば自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

主な環境変数（代表）
-------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード時の DB）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必須）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

重要な設定の注意点
- PAPER_FILL_MODE（paper_trading における MockBroker の約定挙動）:
  - valid: "instant" | "partial" | "never" | "reject"（デフォルト: "instant"）
- KILL_FLAG_CLEAR_ON_START:
  - 本番環境で 1 にするのは危険。Kill Switch が自動クリアされるため慎重に扱ってください。

使い方（主要スクリプト）
-----------------------

1. 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - strict モード: python -m kabusys.validate_config --strict

3. 実行エンジンを起動（本番または paper_trading）
   - python -m kabusys.run_execution
   - 特記事項:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db にトレードログを保存します（本番 DB と分離）。
     - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
     - 実行中は data/execution.pid に PID を写す設計（設定に依存）。

4. 監視ループを起動
   - python -m kabusys.run_monitoring
   - 特記事項:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）。
     - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用してログを記録します。
     - 停止は data/stop_requested.flag を作成することで行います。

5. Paper Trading 検証レポート生成ツール
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH で別の SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も使用できます。

6. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）が必要です。モジュール関数をプログラムから呼び出して利用します（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）。
   - これらは DuckDB 接続と target_date を受け取り、結果を ai_scores や market_regime テーブルに書き込みます。

ログと監視フラグ
----------------
- ログ:
  - デフォルトログディレクトリ: logs/
  - ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - 日次ローテーション（30日分保存）
  - 環境変数 LOG_DIR、LOG_LEVEL で上書き可能
- フラグファイル / PID:
  - data/stop_requested.flag — 外部からの停止要求（プロジェクト内スクリプトで参照）
  - data/kill.flag — Kill Switch が書き込む停止フラグ（ExecutionEngine 停止用）
  - data/execution.pid — ExecutionEngine の PID（ファイル名は Settings で指定可能）

ディレクトリ構成（主要ファイル）
-----------------------------
（src/kabusys をルートとした概観）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理
  - config_setup.py        — .env 対話式ウィザード（CLI）
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - utils/
    - logging_setup.py     — ログ設定ユーティリティ
    - process_priority.py  — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py     — SQLite 用永続化層（テーブル作成 + CRUD）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py    — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py     —（注文系監視、コード内に参照あり）
    - risk_monitor.py      — ドローダウン / ポジション上限監視
    - kill_switch.py       — kill.flag 管理
    - alert_manager.py     —（アラート送信管理、コード内で参照）
  - execution/             — 発注・ブローカー関連（Engine, OrderManager 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・等重/スコア重み
    - position_sizing.py   — 株数計算・リスク制限
    - risk_adjustment.py   — セクター上限・レジーム乗数
  - research/
    - factor_research.py   — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py          — ニュースを OpenAI でセンチメント評価
    - regime_detector.py   — 市場レジーム判定（MA + マクロ NLP）
  - data/                  — 実行時生成ファイル（logs ではなく data）
    - *.db、stop_requested.flag、kill.flag、execution.pid など

（注意）一部ファイル名やサブモジュールはここで抜粋しています。実装によってはさらに多数のモジュールが存在します。

設計上の留意点
--------------
- Settings は .env の自動ロードを行いますが、テストや特殊な起動時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- paper_trading モードは本番 DB と物理的に分離される設計（PAPER_TRADING_SQLITE_PATH）。
- OpenAI 呼び出しはリトライやエラー処理を持ち、API 失敗時はフェイルセーフ（スコアを 0 で扱う等）になっていますが、APIキーや料金運用には注意してください。
- モニタリング側は kill.flag の存在で ExecutionEngine 停止をトリガーします。kill.flag の自動クリア設定は本番で誤設定すると危険です。

よくある操作例
--------------
- .env を対話式で作る:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- ペーパートレード実行（環境変数を適宜設定）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視開始（デフォルト 60 秒間隔）:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 開発メモ
------------------
- 開発時は LOG_LEVEL=DEBUG を設定すると詳細ログが得られます。
- validate_config は .env の不足や config/*.yaml の存在・パースをチェックします（PyYAML があれば内容検証を行う）。
- DuckDB をデータ分析用に使用しているため、大量データを扱う解析処理は DuckDB 側で完結します。
- テスト時は OpenAI 呼び出し等をモックすることが想定されています（コード中にテストフックあり）。

ライセンスや貢献
----------------
- 本 README には記載されていません。実プロジェクトでは LICENSE ファイル・CONTRIBUTING 指針を合わせて用意してください。

お問い合わせ・変更
-----------------
- この README はコードベースの主要点をまとめたものです。追加で README に載せたい具体的な使い方（例: ExecutionEngine の設定詳細、OrderManager API、BrokerFactory の差し替え方法など）があれば、その項目を指定してください。