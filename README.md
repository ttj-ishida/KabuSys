# KabuSys

日本株向け自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、発注エンジン（ExecutionEngine）、監視サブシステム、ポートフォリオ構築・リスク管理ロジック、リサーチ / ファクター計算、LLM を使ったニュース NLP 等を含むモジュール群で構成されています。

---

## プロジェクト概要

- 発注ロジック（ExecutionEngine）と、それを補助する OrderManager / RiskManager / Reconciler 等を提供します。
- 監視サブシステムは SystemMonitor / TradeMonitor / RiskMonitor を組み合わせ、監視ログを SQLite に永続化し、閾値超過時に kill.flag を書き込んで発注エンジン停止をトリガーできます。
- リサーチモジュールは DuckDB を使ってファクター計算（モメンタム・ボラティリティ・バリュー等）を行います。
- ai.* モジュールは OpenAI API を使ってニュースセンチメントや市場レジーム判定を行い、DuckDB 上のテーブルへ書き込みます（API キーが必要）。
- utils に共通ユーティリティ（ログ設定、プロセス優先度設定など）。
- 設定管理用に .env ウィザード（config_setup）・検証ツール（validate_config）を提供します。

---

## 主な機能一覧

- Execution
  - ExecutionEngine による発注セッション管理
  - BrokerClientFactory による実運用 / ペーパートレード切替
  - リスク管理（最大ポジション比率、利用率、ドローダウン等）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、Execution プロセス検出）
  - TradeMonitor（滞留注文・約定異常等の検出）
  - RiskMonitor（ドローダウン・ポジション上限の監視）
  - KillSwitch（kill.flag による安全停止）
  - MonitoringEngine（複数 Monitor のポーリング、アラート送信）
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC（Information Coefficient）等の解析ユーティリティ
- Portfolio
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム調整
- AI
  - news_nlp: OpenAI を用いたニュースセンチメントの銘柄別スコア化（ai_scores への書き込み）
  - regime_detector: ETF MA とマクロニュースを組み合わせた日次レジーム判定
- ツール
  - config_setup: .env を対話式に生成・更新
  - validate_config: .env / config/*.yaml の事前検証
  - tools.paper_verification_report: ペーパートレード検証レポート生成

---

## セットアップ手順（開発/ローカル向け）

1. Python 仮想環境を作成・有効化
   - 例（Unix/macOS）:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
2. 依存ライブラリをインストール
   - requirements.txt が無い場合は主な依存をインストールしてください:
     ```
     pip install duckdb psutil openai pyyaml
     ```
   - openai / duckdb / psutil はそれぞれ AI 呼び出し・DB・プロセス管理で必要です。PyYAML は validate_config の YAML 検証で利用します（任意）。

3. プロジェクトルートで .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成（次節に環境変数一覧とデフォルト値を記載）。

4. 設定の事前検証（推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告を FAIL 扱いにする
   ```

5. 必要なディレクトリを作成（ログ・データ）
   ```
   mkdir -p data logs
   ```

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

主要（省略時はデフォルトを使用）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時のみ適用、デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールを使う場合）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch の flag ファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" でクリア。デフォルト: "0"）

自動 env の読み込み:
- プロジェクトルートが .git または pyproject.toml を含む場合、起動時に `.env`（次に `.env.local`）が自動的に読み込まれます。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（起動コマンド例）

- ExecutionEngine を起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは data/paper_trading.db に分離して記録されます。
  - 起動時にプロセス優先度を "high" に設定します。
  - 停止は data/stop_requested.flag を作成するか、kill.flag によりエンジンに停止シグナルを送ることができます。

- Monitoring を起動（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
  - 停止フラグ: data/stop_requested.flag を作成すると監視ループが終了します。

- .env の作成（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで SQLite ファイルを指定できます（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）。

- AI 機能（プログラム内で）
  - ニュース NLP（銘柄別スコア付け）:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
  - レジーム判定:
    from kabusys.ai import score_regime
    score_regime(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")

  どちらも OPENAI_API_KEY が必要（引数で渡すことも可能）。

---

## 停止 / Kill フラグの挙動

- data/kill.flag
  - KillSwitch が条件を満たすと理由文を書き込みます（存在すれば再書き込みしない）。
  - ExecutionEngine は起動時および実行中に kill.flag の存在を確認し、存在すれば安全停止します（paper_trading でも同様）。
  - KILL_FLAG_CLEAR_ON_START=1 に設定すると ExecutionEngine 起動時に自動で kill.flag を削除します（本番では推奨されません）。

- data/stop_requested.flag
  - run_execution / run_monitoring の起動スクリプトはこのフラグの存在を監視し、見つかるとループを終了します（手動で安全に停止するときに使用）。

---

## ログ

- 共通の logging 設定ユーティリティがあり、ログは標準出力（stdout）と日次ローテーションのファイル出力（logs/<app_name>.log）に出力されます。
- デフォルトログディレクトリ: logs/
- 環境変数 LOG_LEVEL / LOG_DIR で挙動を変更可能。

---

## ディレクトリ構成（主要ファイル）

概略ツリー（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証ツール
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py        — ログの統一設定
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - execution/
    - broker_factory.py       — ブローカークライアント生成
    - execution_engine.py     — ExecutionEngine
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...                     — （発注系の詳細実装）
  - monitoring/
    - monitoring_db.py        — SQLite 操作用ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - research/
    - factor_research.py      — ファクター計算
    - feature_exploration.py  — IC・統計解析等
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — レジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py
  - data/                     — 実行時に作成される想定（DB / flag / pid 等）
  - logs/                     — ログファイル出力先（デフォルト）

---

## 注意事項 / 運用上のヒント

- 本番運用（KABUSYS_ENV=live）の場合は、LINE 通知や kill flag 等の設定を慎重に行ってください。validate_config は本番向けの追加警告を出します。
- Paper trading モードは本番 DB と完全に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。実稼働と同じ DB を参照しないよう注意してください。
- OpenAI を用いる機能は API コストとレイテンシを伴います。API キーは漏洩しないよう管理し、rate limit / 再試行挙動を考慮してください。
- ログディレクトリの作成に失敗した場合はファイルハンドラが無効化され、コンソールのみの出力になります。権限やパスを確認してください。
- process_priority の変更は OS 権限に依存します（非 root ユーザーではアクセス拒否となる場合がありますが、警告ログを出して継続します）。

---

この README はコードベースの主要機能と運用の概要を示しています。詳細な設計やアルゴリズム（PortfolioConstruction.md / StrategyModel.md 等の参照）が別ドキュメントにある想定のため、そちらも合わせて参照してください。質問や追加で欲しいドキュメント（例: systemd ユニット例やデプロイ手順）があれば教えてください。