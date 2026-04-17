README
=====

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリは以下を含みます（抜粋）:

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視（Monitoring）コンポーネント（System / Trade / Risk）
- ポートフォリオ構築・ポジション計算ユーティリティ
- リサーチ用ファクター計算・特徴量解析
- AI（OpenAI）を用いたニュースセンチメント / レジーム判定モジュール
- 各種ユーティリティ（設定読み込み、プロセス優先度設定 等）
- CLI 支援ツール（.env ウィザード、設定検証、検証レポート生成）

この README は開発者・運用担当者向けに、セットアップ手順・使い方・主要機能とディレクトリ構成をまとめたドキュメントです。

主な機能
--------
- ExecutionEngine 起動（run_execution.py）
  - 本番（live）・ペーパートレード（paper_trading）モード切替
  - ペーパートレード時は MockBroker を用い、専用 SQLite DB に記録
- Monitoring（run_monitoring.py / monitoring/*）
  - システム状態監視（CPU/Memory/Disk、プロセス生存確認、データ鮮度）
  - 注文滞留・約定異常価格検出
  - ドローダウン・ポジション上限監視と Kill Switch（kill.flag 生成）
  - アラート送信フック（AlertManager 経由）
- ポートフォリオ構築（portfolio/*）
  - 候補選定、等配分 / スコア配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイジング（ロット丸め、利用可能資金に合わせたスケーリング）
- リサーチ（research/*）
  - Momentum / Volatility / Value ファクター計算（DuckDB ベース）
  - 将来リターン、IC（Information Coefficient）、特徴量サマリ
- AI モジュール（ai/*）
  - ニュース NLU による銘柄別センチメント算出（OpenAI 使用）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（OpenAI 使用）
- 設定管理・CLI ツール
  - .env 対話ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
  - Paper Trading 用検証レポート生成（tools/paper_verification_report.py）

セットアップ手順
----------------

1. リポジトリをクローンしてインストール
   - 開発時:
     - git clone ...
     - cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -e ".[dev]"  # requirements を用意している場合

   - 必要な主な依存パッケージ（抜粋）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config/*.yaml の検証を行う場合に推奨）

   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

2. .env を作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意 / 既定値:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時）
     - その他: LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, KILL_FLAG_CLEAR_ON_START など

3. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も failure 扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリ / DB の準備
   - デフォルトでは data/ 以下にファイルを作成します。
   - 必要に応じて .env でパスを変更してください。

使い方
------

起動スクリプト（主にデーモン的に使う）:

- 監視ループの起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 監視は本番 sqlite_path を常に参照します（KABUSYS_ENV に関わらず）。

- 実行エンジンの起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
  - 起動時、data/execution.pid に PID を書きます（プロセス監視と連携します）。
  - data/stop_requested.flag（または .data/kill.flag）等のフラグファイルで停止制御を行う設計です。

ユーティリティ / CLI:

- .env ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ライブラリ API（抜粋）

- AI（ニューススコアリング）
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続
    - target_date: date オブジェクト
    - api_key: OpenAI API キー（省略時は環境変数 OPENAI_API_KEY 参照）
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- ポートフォリオ / ポジション計算
  - kabusys.portfolio.select_candidates(...)
  - kabusys.portfolio.calc_equal_weights(...)
  - kabusys.portfolio.calc_score_weights(...)
  - kabusys.portfolio.calc_position_sizes(...)
  - kabusys.portfolio.apply_sector_cap(...)
  - kabusys.portfolio.calc_regime_multiplier(...)

監視・Kill Switch 概要
--------------------
- Monitoring コンポーネントは MonitoringDB（SQLite）へログを残します（init_monitoring_db がテーブル作成を行います）。
- RiskMonitor がドローダウン・ポジション上限を評価し、必要に応じて KillSwitch が data/kill.flag を書きます。
- ExecutionEngine は kill.flag の存在を検知すると安全に停止するよう設計されています。
- run_monitoring / run_execution は起動直後にプロセス優先度を "high" に設定しようとします（psutil を使用）。

環境変数（主要）
----------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB パス:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用)
- AI:
  - OPENAI_API_KEY（AI 機能利用時）
- 監視 / 制御:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか）
  - PID_FILE_PATH / KILL_FLAG_PATH（Settings 参照）
- ログ:
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み、.env 自動読み込み、Settings クラスを提供
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト

パッケージ群（主要モジュール）
- ai/
  - news_nlp.py          — ニュースセンチメント（OpenAI）
  - regime_detector.py   — 市場レジーム判定（OpenAI + MA）
- monitoring/
  - monitoring_db.py     — SQLite テーブル定義と DB ラッパ
  - system_monitor.py    — システム状態・データ鮮度監視
  - trade_monitor.py     — 注文滞留・約定異常検出
  - risk_monitor.py      — ドローダウン / ポジション上限監視
  - kill_switch.py       — kill.flag 制御
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - alert_manager.py     — （アラート送信を担うフック）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py  — プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/run_*.py, execution/* など（Execution 側の詳細実装は別ファイル群）

注意事項・運用メモ
-----------------
- .env は秘密情報を含むため絶対に Git にコミットしないでください（config_setup も警告あり）。
- KABUSYS_ENV=live 設定時は特に注意して設定を確認してください（validate_config にライブ向けチェックあり）。
- OpenAI を使用する AI 機能は API 呼び出しに対して冪等性・リトライ・フォールバックを考慮して設計されていますが、API キー使用量・コストに注意してください。
- run_monitoring は監視用 DB（monitoring.db）を使用するため、monitoring のログが不要なケースでは DB 設定を調整してください。
- プロセス優先度設定・CPU affinity は OS 権限やプラットフォーム依存で動作しない場合があります（psutil の権限・API の制約）。

問い合わせ / 開発
----------------
- バグ修正や機能追加は Issue / Pull Request を通じて行ってください。
- 主要処理（注文発行・資金計算等）は本番資金を扱うため慎重なレビューが必須です。

以上がこのコードベースの README（日本語）です。必要であれば「起動例」「設定ファイルのサンプル (.env.example)」「詳細な API 参照」などを追記します。どの情報を追加しますか？