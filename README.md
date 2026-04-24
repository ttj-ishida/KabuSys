# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリは注文執行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などを含みます。

---

## プロジェクト概要

KabuSys は以下のコンポーネントを備えた自動売買基盤を想定しています。

- ExecutionEngine: 注文発行・リスク管理・リコンシリエーション（本番 / ペーパートレード対応）
- Monitoring: システム状態・注文状況・リスク監視、Kill Switch による安全停止
- Portfolio: 候補選定、重み計算、株数算出（単元株丸め・リスク/上限制御）
- Research: ファクター計算、将来リターン・IC 計算など研究用ユーティリティ
- AI: ニュースのセンチメント評価（OpenAI）と市場レジーム判定
- Tools: Paper Trading の検証レポート生成など補助スクリプト

設計方針の一部:
- データ永続化は DuckDB（分析）と SQLite（監視・履歴）を併用
- .env ベースの設定、対話式ウィザード・検証ツールを提供
- 本番とペーパートレードは DB を分離して安全に運用可能

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードを使用可能）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py: .env の対話式作成/更新ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
- 監視・安全機構
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch
  - kill.flag による ExecutionEngine 停止、stop_requested.flag によるプロセス停止制御
- ポートフォリオ構築
  - 候補選定、スコア重み、等配分、リスク調整（セクターキャップ・レジーム乗数）
  - 株数決定ロジック（risk_based / equal / score）
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン、IC、ファクター統計
- AI（OpenAI 統合）
  - ニュースを LLM で集約して銘柄ごとにセンチメントを算出して ai_scores に格納
  - マクロニュース + ETF MA 乖離で市場レジーム（bull/neutral/bear）判定
- ツール
  - paper_verification_report: ペーパートレード DB からパフォーマンス/安定性指標を出力

---

## 必要な環境 / 前提

- Python 3.9+
- SQLite（標準ライブラリで提供）
- 推奨パッケージ（代表例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証で YAML を使う場合）
- .env による設定管理（.env/.env.local をプロジェクトルートに配置可能）
  - 自動読み込みはデフォルトで有効（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

（validate_config.py を実行すると詳細なチェック結果を確認できます）

---

## セットアップ手順（例）

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   - 代表的なパッケージ例:
     ```
     pip install duckdb psutil openai pyyaml
     ```
   - 開発用にパッケージ列を requirements.txt に用意している場合はそれを使用してください。

3. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - その後、設定検証:
     ```
     python -m kabusys.validate_config
     ```
   - 重要な設定例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     OPENAI_API_KEY=your_openai_key   # AI機能を使う場合
     ```

4. データディレクトリ作成（必要な場合）
   ```
   mkdir -p data logs
   ```

---

## 使い方（起動・主要コマンド例）

- ExecutionEngine を起動
  - 本番・ペーパー切り替えは KABUSYS_ENV による
  - ペーパートレード（MockBrokerClient を使用し data/paper_trading.db に記録）
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 本番
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - 実行時、data/execution.pid に PID を書き込み、data/stop_requested.flag があれば起動/停止制御を行います。

- Monitoring を起動
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- .env 作成ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告を FAIL 扱い
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DBパス指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（プログラム的に呼び出す例）
  - ニュース NLP を実行して ai_scores に書き込む（DuckDB 接続が必要）
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_API_KEY")
    print("written:", n)
    ```
  - レジーム判定（score_regime）も同様に呼び出せます（OPENAI_API_KEY 必須）

- ログ
  - デフォルトで stdout と logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリ）
  - ログレベルは LOG_LEVEL 環境変数で制御

---

## 主要設定・ファイルの説明

- デフォルトのファイルパス
  - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
  - 監視 SQLite: data/monitoring.db（Settings.sqlite_path）
  - ペーパートレード SQLite: data/paper_trading.db（Settings.paper_sqlite_path）
  - PID / Kill flag:
    - execution.pid（Settings.pid_file_path）
    - data/kill.flag（KillSwitch 用）
    - data/stop_requested.flag（run_* スクリプトで監視している停止フラグ）

- 重要な環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - OPENAI_API_KEY（AI 機能使用時）
  - MONITOR_POLL_INTERVAL（監視ループ間隔、秒、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading の MockBroker の振る舞い）
  - LOG_LEVEL（ログレベル）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py               — 環境変数 / Settings 管理（.env 自動ロード機能含む）
- config_setup.py         — .env 対話式ウィザード
- validate_config.py      — 設定検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — SystemMonitor ポーリング起動スクリプト

kabusys/utils/
- logging_setup.py        — ログ設定ユーティリティ
- process_priority.py     — プロセス優先度 / CPU アフィニティユーティリティ

kabusys/execution/
- broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  （ExecutionEngine の主要コンポーネント群）

kabusys/monitoring/
- monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py       — システム状態・データ鮮度チェック
- trade_monitor.py        — 注文滞留・約定異常検出（実装ファイルあり）
- risk_monitor.py         — ドローダウン / ポジション上限チェック
- kill_switch.py          — kill.flag の書き込み / クリア
- monitoring_engine.py    — 監視ループの統括
- alert_manager.py        — アラート送信（実装例：LINE などに接続する想定）

kabusys/portfolio/
- portfolio_builder.py, position_sizing.py, risk_adjustment.py
  （候補選定、重み付け、ポジションサイズ計算、セクター/レジーム処理）

kabusys/research/
- factor_research.py      — Momentum / Volatility / Value 等
- feature_exploration.py  — 将来リターン、IC、統計サマリ

kabusys/ai/
- news_nlp.py             — ニュースセンチメントバッチ処理（OpenAI 使用）
- regime_detector.py      — ETF MA + マクロセンチメントでレジーム判定

kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート

その他:
- logs/                   — ログ出力先（デフォルト）
- data/                   — DB / フラグファイル等の保存先（デフォルト）

---

## 運用上の補足 / 注意点

- .env / シークレット
  - .env は Git にコミットしないでください。config_setup.py も .env を生成しますが、生成後は必ず機密情報を管理してください。
- 本番モード（KABUSYS_ENV=live）は取り扱いに注意
  - validate_config.py は live モード時に追加警告を出します（LINE 通知設定・Kill Switch の自動クリア等）
- Kill Switch
  - RiskMonitor が閾値に達した場合などに kill.flag を書き込み、ExecutionEngine はこのフラグの存在で自動停止します（冪等）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は簡易なマイグレーション（カラム追加）を行いますが、複雑なスキーマ変更は慎重に行ってください。
- AI 呼び出し
  - OpenAI の呼び出しはレート制限や API エラーを考慮して実装されていますが、API キー・課金に注意してください。

---

## 開発・貢献

- コーディング規約、テスト、CI 等はプロジェクトポリシーに従ってください（ここにテストコマンド等を追加することを推奨します）。
- 追加のドキュメント（PortfolioConstruction.md、StrategyModel.md 等）や config/*.yaml のテンプレートを参照すると実装の設計思想が分かります。

---

必要であれば、README に実行例の詳細（各スクリプトのフルオプション説明、環境変数の一覧、よくあるトラブルシュート）を追記します。どの部分を詳しく説明しましょうか？