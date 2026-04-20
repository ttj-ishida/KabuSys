# KabuSys

日本株向け自動売買システムの一部を実装した Python パッケージ。  
このリポジトリには、実行エンジン・監視（Monitoring）・ポートフォリオ構築・リサーチ・AI を使ったニュース NLP などのモジュール群が含まれます。

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム取引プラットフォームのコンポーネント群です。本コードベースでは以下を提供します。

- ExecutionEngine（発注実行、paper_trading モード対応）
- Monitoring（システム健全性・注文監視・Kill Switch 等）
- Portfolio 構築（候補選定、重み付け、ポジションサイズ計算）
- Research（ファクター計算、特徴量解析、IC 計算）
- AI 関連（ニュースセンチメント評価、レジーム判定）
- ユーティリティ（設定読み込み、ログ設定、プロセス優先度設定 等）
- CLI 補助（.env ウィザード、設定検証、レポート生成）

設計上の特徴:
- 環境依存設定は .env / 環境変数で管理
- Paper Trading（検証用）は本番 DB と分離
- DuckDB を分析用 DB、SQLite を監視・履歴用 DB に利用
- OpenAI を用いる AI モジュールはキー指定が必須（フェイルセーフあり）

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Broker クライアント抽象化（MockBrokerClient をペーパートレードで利用）
  - リスク管理（Rate limit / ドローダウン等）
- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - Execution プロセス死活監視
  - 注文ログ監視（滞留注文・約定異常など）
  - Kill Switch（条件に応じて data/kill.flag を書き込み）
- Portfolio
  - 候補選定（スコア順）
  - 等重・スコア加重の重み算出
  - ポジションサイズ計算（リスクベース、上限・lot 単位調整、スケーリング）
  - セクター制限、レジーム乗数
- Research
  - モメンタム / バリュー / ボラティリティ等のファクター計算（DuckDB 経由）
  - 将来リターン算出、IC（Information Coefficient）計算
- AI
  - ニュース記事を OpenAI でスコア化して ai_scores に書き込み
  - マクロニュース + ETF MA を使った市場レジーム判定
- CLI/ツール
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 要件 / 依存パッケージ

推奨 Python バージョン: 3.10+ （型注記に | を使用しているため）  

主な依存 (実行に必要なもの):
- duckdb
- psutil
- openai（AI機能を使う場合）
- sqlite3（標準ライブラリ）
- PyYAML（設定ファイル検証を行う場合は任意でインストール）

インストール例:
```
python -m pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt がある場合はそれを使ってください）

---

## 環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境指定:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- DB / ファイルパス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH（監視 / kill flag 関連）

- ログ:
  - LOG_LEVEL（DEBUG/INFO/...）
  - LOG_DIR（ログ出力先ディレクトリ、デフォルト: logs/）

- AI:
  - OPENAI_API_KEY（news_nlp / regime_detector の呼び出しに必要）

- 監視ポーリング間隔:
  - MONITOR_POLL_INTERVAL（run_monitoring で使用、秒。デフォルト 60）

- その他:
  - PAPER_FILL_MODE（paper_trading の約定挙動: instant/partial/never/reject）
  - KILL_FLAG_CLEAR_ON_START（本番で自動クリアするか）

設定ファイルの自動読み込み:
- プロジェクトルートの .env / .env.local は自動で読み込まれます（既存 OS 環境変数は優先）。
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（ローカルでの初期準備）

1. Python 3.10+ を用意
2. 必要パッケージをインストール
   ```
   python -m pip install duckdb psutil openai pyyaml
   ```
3. .env を作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは既存 .env を読み込み、対話形式で編集・保存します。

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   警告も失敗扱いにする場合:
   ```
   python -m kabusys.validate_config --strict
   ```

5. DB ファイル / ディレクトリの準備
   - デフォルトでは data/ 以下に DB を作成します。存在しないディレクトリは自動作成されることがありますが、権限等に注意してください。
   - duckdb や sqlite の初期スキーマは実行時に自動作成 / マイグレーションされます（monitoring 用スキーマ等）。

---

## 使い方（主要スクリプト）

以下はパッケージとして実行する例です。プロジェクトルート（src の親）で実行することを想定します。

- ExecutionEngine を起動（本番 or paper_trading は KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - Paper Trading モード（KABUSYS_ENV=paper_trading）の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録されます。
  - 実行中に data/stop_requested.flag を作成すると、起動中のエンジンは停止シグナルを受け取ります。
  - PID は data/execution.pid（デフォルト）に書き込まれます。

- Monitoring を起動（定期ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（環境にかかわらず production の monitoring DB を利用する設計）。
  - data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスを直接指定する場合:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（プログラムから呼び出す例）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続と target_date（date オブジェクト）を受け取り、DB に結果を書き込みます。
  - OPENAI_API_KEY が必要（引数で渡すことも可）。

---

## ログ / 停止 / Kill Switch

- ログ:
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通して行われます。
  - デフォルトログディレクトリ: logs/
  - 日次ローテーション（30 日保持）

- 停止方法:
  - 監視・実行スクリプトは data/stop_requested.flag の存在を検知して終了します（手動で作成することで安全に停止を要求できます）。
  - Kill Switch: 条件により monitoring が data/kill.flag を書き込むと ExecutionEngine は停止シグナル（外部での確認・操作）として扱えます。
  - execution.pid（デフォルト: data/execution.pid）を参照してプロセス管理を行えます。

---

## 主要ファイル / ディレクトリ構成

（抜粋。src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                — 環境変数・.env の自動読み込み／Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/                — Execution 系（BrokerFactory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - utils/
    - logging_setup.py
    - process_priority.py

プロジェクトルート例:
```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ run_execution.py
│     ├─ run_monitoring.py
│     ├─ ...
├─ data/        # デフォルトの DB/flag/pid を置く場所（実行時に生成）
├─ logs/        # ログ出力先（デフォルト）
└─ pyproject.toml / setup.cfg / .gitignore ...
```

---

## 開発者向け注意事項 / 補足

- DB スキーマは起動時にマイグレーションが走る箇所があります（monitoring_db.init_monitoring_db 等）。既存データとの互換性に注意してください。
- AI 周りは OpenAI SDK の API 仕様変更に左右される可能性があります。テスト時には内部の API 呼び出し関数をモックするよう設計されています（例: unittest.mock.patch）。
- config.py はプロジェクトルート（.git または pyproject.toml）を基準に .env を自動読み込みします。テスト等でこれを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading モードでは実際の発注は行わず、専用の SQLite（デフォルト: data/paper_trading.db）にログを残して検証できます。
- ログ出力は stdout とファイルの両方へ行われるため、cron やサービスマネージャからの実行でも追跡しやすくなっています。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非数）はデフォルト 60 秒にフォールバックします。

---

README は以上です。必要であれば以下を追加で生成します:
- サンプル .env.example
- systemd / Supervisor 用の起動ユニット例
- よくあるトラブルシュート（依存関係・権限・DB ロック 等）

どれを追加しますか？