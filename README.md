KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・調査・監視を目的とした Python パッケージ群です。
モジュールは発注エンジン（ExecutionEngine）、監視コンポーネント、
ポートフォリオ構築ロジック、リサーチ用ファクター計算、LLM を使ったニュース解析などで構成されています。

主な特徴
--------
- 実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレードを分離（KABUSYS_ENV により挙動を切替）
  - Broker クライアントの抽象化（Mock を含む）
  - 注文管理・リスク管理・再整合（reconciler）を備える

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス、生データ鮮度の監視
  - TradeMonitor / RiskMonitor: 注文の滞留・約定異常・ドローダウン等の検出
  - KillSwitch / AlertManager による自動停止・アラート発行
  - SQLite（monitoring.db）へ監視ログを永続化

- ポートフォリオ構築（純粋関数）
  - 候補選定、等配分／スコア加重、ポジションサイズ計算、セクターキャップ、レジーム乗数など

- リサーチ（DuckDB ベース）
  - Momentum / Volatility / Value 等ファクター計算
  - 将来リターン、IC（Information Coefficient）、特徴量サマリ等

- AI（OpenAI）連携
  - ニュースのセンチメント評価（news_nlp）
  - マクロ × ETF を使った市場レジーム判定（regime_detector）
  - 大規模言語モデル呼び出しは冗長対策（リトライ・バリデーション）を実装

- ツール類
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report）

前提（推奨）
------------
- Python 3.10+
- SQLite（標準ライブラリで利用可能）
- 推奨パッケージ（後述のインストール手順で導入可能）
  - duckdb, psutil, openai, PyYAML（任意）、その他依存

セットアップ手順
----------------
1. リポジトリをクローン / 展開
   - 例: git clone ...

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 例（最低限）:
     pip install duckdb psutil openai
   - 設定検証で YAML を検査したい場合:
     pip install pyyaml

   （requirements.txt がある場合はそれを利用してください）

4. .env の作成
   - 対話式ウィザードで .env を生成:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成（このプロジェクトでは .env.example は想定されます）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けると警告もエラー扱いになります:
     python -m kabusys.validate_config --strict

環境変数（主要）
----------------
- JQUANTS_REFRESH_TOKEN : J-Quants API トークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABUSYS_ENV           : 実行環境（development | paper_trading | live）
  - paper_trading の場合、ペーパートレード用 DB を使用
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE       : paper_trading 時の約定モード（instant|partial|never|reject）
- OPENAI_API_KEY        : OpenAI 呼び出しに使用する API キー（AI 機能使用時に必須）
- LOG_LEVEL, LOG_DIR 等はログ出力に影響します

主要な起動 / 使い方
--------------------

- 実行エンジン（Execution）
  - 起動:
    python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 起動中に data/stop_requested.flag が存在するとエンジンを停止します（run_execution は定期的にこのフラグを監視します）。
    - 実行時の PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）。

- 監視ループ（Monitoring）
  - 起動:
    python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor を含む監視ループをポーリング実行します。
    - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能。
    - 監視ログは Settings.sqlite_path（デフォルト data/monitoring.db）に保存されます（Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します）。
    - 監視ロジックは KillSwitch を介して必要時に data/kill.flag を書き込み ExecutionEngine に停止シグナルを出します。
    - 監視ループの停止: data/stop_requested.flag を作成すると監視プロセスを終了させることができます。

- Paper Trading 検証レポート
  - レポート生成:
    python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定することも可能です。

- .env ウィザード / 設定検証
  - ウィザード:
    python -m kabusys.config_setup
  - 検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- AI 関連（プログラム的利用）
  - ニューススコアリング（プログラム呼び出し例）:
    from kabusys.ai import score_news
    # DuckDB 接続を渡し、target_date と api_key(または環境変数)を指定
    score_news(conn, date(2026, 4, 1), api_key="sk-...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026, 4, 1), api_key="sk-...")

運用・停止
---------
- 停止フラグ:
  - run_execution / run_monitoring はプロジェクトルート/data/stop_requested.flag（既定）を監視します。ファイルを作成すると安全にループが終了します。
- Kill Switch:
  - 監視側が危険条件を検出した場合、data/kill.flag を書き込み（Settings.kill_flag_path）、ExecutionEngine 側で検出して停止させます。
- ログ:
  - logs/ ディレクトリに日次ローテーションでログが書かれます（utils.logging_setup が設定）。

ディレクトリ構成（要約）
----------------------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算
    - risk_adjustment.py       — セクター制限・レジーム乗数
  - research/
    - factor_research.py       — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py   — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）による銘柄ごとのスコアリング
    - regime_detector.py       — マクロ + ETF による市場レジーム判定
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ定義と簡易永続化 API
    - system_monitor.py        — システム状態・データ鮮度監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - (その他: trade_monitor, alert_manager 等)
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

設計上の注意点 / 運用上の注意
----------------------------
- Paper trading は本番 DB と分離して記録されます（PAPER_TRADING_SQLITE_PATH）。
- AI（OpenAI）呼び出しは API キーが必要。呼び出しはリトライやレスポンス検証を含み、失敗時は安全にフォールバックする設計です（例: スコア未取得時はスキップ）。
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- ログディレクトリ作成に失敗した場合はコンソール出力にフォールバックします。
- process priority / cpu affinity はプラットフォーム依存の制限を考慮して警告レベルで扱います（権限不足時はスキップされます）。
- DuckDB / SQLite のパスやログレベルは Settings を通して容易に変更可能です。

貢献・拡張
----------
- strategy, execution, monitoring の各モジュールは疎結合設計なので、ブローカー実装やリスクルール、アラートチャネルの追加は比較的容易です。
- research モジュールは DuckDB に蓄積したデータを前提としているため、データ投入パイプラインを整備すると有用です。

質問や改善要望があれば、具体的なユースケース（ローカルテスト方法、外部ブローカー接続、AI 呼び出しポリシーなど）を添えてお知らせください。