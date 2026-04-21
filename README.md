README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのコアライブラリです。  
ポートフォリオ構築、ポジションサイズ計算、リスク調整、モニタリング、Execution エンジン起動、Paper Trading 検証、ニュース NLP（OpenAI）連携などの機能を備え、ローカル実行および本番運用を想定した設計がされています。

主な特徴
--------
- ポートフォリオ構築
  - シグナル選定、等比率／スコア加重の重み計算
  - セクター上限制御、レジーム乗数（bull/neutral/bear）
  - 株数（ロット）算出、総投下額のスケーリング（aggregate cap）
- リサーチ機能
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）計測、統計サマリー
- AI（OpenAI）連携
  - ニュースのセンチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュースを使った市場レジーム判定
- 実行系（Execution）
  - 本番 / ペーパートレード環境の分離（paper_trading モードで MockBroker）
  - RiskManager、OrderManager、Reconciler などの統合
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - SQLite へ監視ログ永続化（monitoring.db）
  - Kill Switch（data/kill.flag）による ExecutionEngine 強制停止
- 運用ツール
  - 対話式 .env 作成ウィザード
  - 設定検証 CLI
  - Paper Trading 検証レポート生成スクリプト
- ロギング
  - 統一的なログ設定（コンソール stdout と日次ローテートファイル出力）

セットアップ手順
----------------
前提:
- Python 3.9+（ソースは型アノテーション等を使用）
- 推奨: 仮想環境（venv）を使用

1. リポジトリをクローン / 取り出す
   - 例: git clone <repo-url>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主な必須/推奨パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML (設定検証で YAML の内容検証を行う場合)
   - （ローカルで編集して使う場合）パッケージをインストール:
     - pip install -e .

4. 環境変数（.env）設定
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成された .env を必ず Git にコミットしないこと（README にも注記）

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合は --strict を付与:
     - python -m kabusys.validate_config --strict

主な環境変数（抜粋）
-------------------
- KABUSYS_ENV: 実行環境（development, paper_trading, live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト localhost）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（テスト用）

使い方
------
1. .env を作成 / 更新
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

3. Execution（取引エンジン）を起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、data/paper_trading.db に記録されます。
   - 起動前に data/stop_requested.flag が存在すると起動をスキップします。

4. Monitoring（監視）を起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60 秒）。
   - Monitoring は常に本番用 sqlite_path（SQLITE_PATH）を使用して監視ログを書き込みます。

5. 停止 / Kill Switch
   - ExecutionEngine を外部から停止させたい場合は data/kill.flag を作成します（KillSwitch が検知して停止）。
   - Monitoring/Execution のスクリプトは data/stop_requested.flag を使って早期終了を検知します。
   - kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START 設定で制御します（本番では 0 を推奨）。

6. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可能）
   - レポートは稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して PASS/FAIL を判定します。

7. AI 関連
   - ニュースの NLP スコア付け:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - conn は DuckDB の接続（duckdb.connect(...)）
     - OPENAI_API_KEY を環境変数で設定するか、api_key 引数で渡します。
   - 市場レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ロギング
-------
- 共通のロギング設定関数: kabusys.utils.logging_setup.setup_logging(app_name="execution")
- デフォルトでは stdout に出力し、logs/<app_name>.log に日次ローテートで出力します（30日分保持）。
- ログディレクトリは環境変数 LOG_DIR で上書き可能。

データベース
----------
- DuckDB: 分析・リサーチ用の主データベース（デフォルト data/kabusys.duckdb）
- SQLite (monitoring.db): 監視ログ・トレードログ用（デフォルト data/monitoring.db）
- Paper Trading 用 SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

注意点
-----
- .env ファイルは決してリポジトリにコミットしないこと（API キーなどの機密情報が含まれる）。
- KABUSYS_ENV=live での実行は実際の発注が発生します。十分な検証と監視設定を行ってください。
- OpenAI の利用は API キーと利用コストに注意してください。API が失敗した場合はフェイルセーフ（スコア 0 等）で継続する設計です。

ディレクトリ構成（抜粋）
------------------------
以下は src/kabusys 内の主なファイルと簡単な説明です。

- __init__.py
  - パッケージ初期化、バージョン定義

- config.py
  - 環境変数の自動ロード（.env / .env.local）と Settings クラス（設定アクセサ）

- config_setup.py
  - .env 対話式作成ウィザード

- validate_config.py
  - 設定検証 CLI（環境変数・config/*.yaml の存在チェックなど）

- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて本番/ペーパー切替）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

- ai/
  - news_nlp.py — ニュースの NLP スコアリング（OpenAI 経由）
  - regime_detector.py — マクロ＋ETF MA による市場レジーム判定

- portfolio/
  - portfolio_builder.py — シグナル選定・重み計算
  - position_sizing.py — 株数計算・スケーリング・ロット丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン, IC, 統計サマリー

- monitoring/
  - monitoring_db.py — SQLite テーブル初期化 + 永続化ヘルパー
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス検査
  - trade_monitor.py — （トレードの滞留・約定異常検出など）※詳細はソース参照
  - risk_monitor.py — ドローダウン/ポジション数の監視（KillSwitch と組合せ）
  - kill_switch.py — data/kill.flag の書き込みロジック
  - monitoring_engine.py — 各 Monitor を束ねる実行ループ
  - alert_manager.py — （LINE 等への通知ラッパー）※詳細はソース参照

- execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等（実行系）

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - その他ユーティリティ群

付録: よく使うコマンド例
-----------------------
- .env 作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- DuckDB 接続（Python REPL から例）:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

サポート / 貢献
---------------
- バグ報告や機能提案は Issue を立ててください。
- 開発に貢献する場合は Pull Request を送ってください。コードスタイル・テストが整備されている場合はそちらに従ってください。

ライセンス
----------
- リポジトリに LICENSE ファイルがある場合はそれを参照してください（ここでは明示されていません）。

以上。README に記載してほしい補足情報（依存関係の正確なリスト、実行上の注意点、CI 設定など）があれば教えてください。必要に応じてサンプル .env テンプレートや systemd / supervisor 用の起動スクリプト例も作成できます。