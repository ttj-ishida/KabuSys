# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買・研究・監視を行うためのコンポーネント群を含みます。  
以下はコードベース（src/kabusys）に基づく README です。

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件 / インストール
- セットアップ手順（.env の作成と検証）
- 使い方（起動コマンド / 環境変数）
- 主要スクリプト / ツールの説明
- ディレクトリ構成
- 運用上の注意・トラブルシュート

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムで、主に次を提供します：

- 注文実行エンジン（ExecutionEngine）とブローカークライアント抽象
- 監視（Monitoring）: システム状態、注文ログ、リスク（ドローダウン・ポジション上限）監視
- ポートフォリオ構築・ポジションサイジングの純関数ライブラリ
- 研究（Research）モジュール：ファクター計算・特徴量解析ユーティリティ
- AI モジュール：ニュースを LLM（OpenAI）でスコアリング、レジーム判定
- 運用ヘルパー：.env ウィザード、設定検証、ペーパートレード検証レポート 等

設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時は安全側で継続）」が組み込まれています。

---

## 主な機能一覧

- Execution
  - 本番/ペーパートレード切替（KABUSYS_ENV）
  - リスク管理（RiskManager）、注文管理（OrderManager）、再和解（Reconciler）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、実行プロセス監視
  - TradeMonitor：注文ステータス/滞留注文/約定異常検出
  - RiskMonitor：ドローダウン / 保有数上限監視、Kill Switch 連携
  - MonitoringEngine：各モニタを束ねるポーリングループ、アラート発行
  - MonitoringDB：SQLite に永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- Portfolio
  - 候補選定・重み計算（等額・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - 株数・単元丸めを考慮した発注サイズ計算
- Research
  - Momentum／Volatility／Value ファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）、統計サマリ
- AI
  - News NLP：OpenAI でニュースを銘柄ごとにスコア化し ai_scores に書込
  - Regime Detector：ETF（1321）の MA とマクロニュースを合成して市場レジームを判定
- ツール
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## 必要条件 / インストール

推奨：Python 3.9+（コードは型ヒントを使用しており、近年の Python での実行を想定）

主要依存ライブラリ（少なくとも次をインストールしてください）:
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- （SQLite は標準ライブラリ）

インストール例（venv 作成後）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ requirements.txt は本リポジトリに含まれていないため、実環境に合わせて追加してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. .env の作成（対話式ウィザード推奨）
   - コマンド:
     ```
     python -m kabusys.config_setup
     ```
   - 対話が終わると `.env` を生成します（Git にコミットしないでください）
4. 作成した設定を検証:
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告も失敗扱いになります
5. 必要に応じてデータディレクトリを作成（.env のデフォルトは data/、logs/）
   ```
   mkdir -p data logs
   ```

---

## 環境変数（主要項目）

（.env で設定。config_setup が主要キーを補助して生成します）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要な任意/設定:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は専用の PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）を使用
- DUCKDB_PATH — 分析用 DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- PAPER_FILL_MODE — ペーパートレードの約定挙動: instant / partial / never / reject（デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

ファイル・フラグ:
- data/kill.flag — Kill Switch（存在すると Execution に停止指示を出す）
- data/stop_requested.flag — run_execution/run_monitoring の外部停止フラグ
- data/execution.pid — Execution 起動時に書き込まれる PID ファイル

---

## 使い方（主要コマンド例）

- .env を作成・編集:
  ```
  python -m kabusys.config_setup
  ```

- 設定の検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（デフォルト・ペーパートレード切替例）:
  - 本番モード:
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - ペーパートレード:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 注意: paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に結果を記録し、本番 DB と分離されます。

- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL によってポーリング間隔を秒で上書きできます（デフォルト 60 秒）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（監視 DB は一貫して本番 DB を想定）

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（コードを通して呼び出す API）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OPENAI_API_KEY を環境変数で渡すか api_key を引数で与えてください

停止・Kill スイッチ:
- Execution を外部から安全に停止するには data/kill.flag を作成します（KillSwitch が検出して Execution を停止）
- run_execution および run_monitoring は data/stop_requested.flag を検知してループを終了します（外部停止要求用）

ログ:
- logs/<app_name>.log に日次ローテーションで出力されます（デフォルト logs/、30日保持）

---

## 主要スクリプト / モジュールの役割（簡易）

- run_execution.py — ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、Engine 起動）
- run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で制御）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — .env / config/*.yaml の検証 CLI
- tools/paper_verification_report.py — ペーパートレード成績・稼働性レポート
- ai/news_nlp.py — raw_news を LLM に投げて銘柄別スコアを ai_scores に書き込むロジック
- ai/regime_detector.py — マクロニュース + 1321 MA で市場レジームを判定して保存
- monitoring/* — MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine, AlertManager（アラート管理は別モジュール）
- portfolio/* — ポートフォリオ構築・リスク調整・ポジションサイジングの純関数群
- research/* — DuckDB を用いたファクター計算・特徴量解析

---

## ディレクトリ構成（抜粋）

（ルート: src/kabusys 以下の主要ファイル／ディレクトリ）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings クラス
  - config_setup.py          — .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — Execution 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (想定)
  - execution/                — ExecutionEngine, OrderManager 等（起動時参照）
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
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                     — 実行時に作成される（data/monitoring.db 等）

---

## 運用上の注意・トラブルシュート

- ログ/データディレクトリ作成失敗:
  - logs/ または data/ の作成が権限不足などで失敗すると、ファイルハンドラが作れずコンソール出力のみになります。書き込み権限を確認してください。
- process priority 設定:
  - set_process_priority() は psutil を使用して優先度を変更します。権限不足で失敗することがあり、その場合は警告ログが出ますが処理は継続します。
- OpenAI / API 呼び出し:
  - OPENAI_API_KEY が未設定だと AI モジュールは例外を投げます（明示的に渡すか環境変数を設定してください）。
  - LLM 呼び出しはリトライ・フェイルセーフが組み込まれていますが、API のレート制限や課金に注意してください。
- データベースの分離:
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使います。監視は常に sqlite_path（監視用 DB）を使用します。
- Kill Switch の扱い:
  - 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にして、起動時に誤って kill.flag を消さないよう推奨します。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対する簡易マイグレーション（カラム追加）を行いますが、本格的なマイグレーションが必要なら別途管理してください。

---

もし README を別フォーマット（Markdown の細分化・バッジ追加・インストール手順を requirements.txt と合わせる等）で出力したい場合や、特定モジュール（AI 周り、Execution の設定ファイルの詳細、監視アラートの統合方法）をもっと詳しく記述してほしい場合は指示してください。