KabuSys
=======

日本株自動売買システムの Python 実装（ライブラリ＋起動スクリプト）。  
このリポジトリは、戦略・ポートフォリオ構築、実行エンジン、監視・アラート、AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

主要な特徴
---------
- 自動発注用 ExecutionEngine（本番 / ペーパートレード切替）
- 監視コンポーネント（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター上限）
- リサーチ用モジュール（ファクター計算、特徴量解析、IC 計算）
- ニュースを LLM でスコアリングする AI モジュール（OpenAI を利用）
- SQLite / DuckDB を用いた永続化・分析基盤
- 起動前チェック・対話的 .env ウィザード（config_setup / validate_config）
- ペーパートレード検証レポート生成ツール

要件
----
- Python 3.9+（ソースは型ヒント・標準ライブラリで書かれているため 3.9 以上を推奨）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に YAML のパースを行いたい場合）
- 標準ライブラリ: sqlite3 等

インストール例
--------------
仮想環境を作成して必要なパッケージを入れる例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# 必要に応じてその他のパッケージを追加
```

環境変数 / .env
----------------
このプロジェクトは .env を読み込んで設定を決定します（自動ロード機能あり）。プロジェクトルートに .env を置いてください。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（必須・主要）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか ("0" または "1")

簡易 .env サンプル
------------------
（config_setup ウィザードで対話的に作成できます）

JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

起動前チェック / .env ウィザード
--------------------------------
- 対話式ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証スクリプト
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗と扱う

データベースとログ
------------------
- デフォルトのファイル配置:
  - DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db
- ログ:
  - デフォルトログディレクトリ: logs/
  - 各アプリケーション名でファイルに出力（execution.log, monitoring.log など）
- 監視 DB 初期化:
  - 起動スクリプトは monitoring 用のテーブルを冪等に作成します（init_monitoring_db）

停止 / Kill Switch
------------------
- 手動停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループを安全に停止します
- Kill Switch:
  - data/kill.flag を KillSwitch が書き込むと ExecutionEngine 側で停止シグナルとして扱われます
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動的にクリアします（本番では注意）

実行方法
--------
主な起動スクリプト:

- 監視ループ起動（SystemMonitor をポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に settings.sqlite_path（本番用の monitoring DB）を使用します

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB とは分離）
  - 起動時に data/execution.pid を作成し、stop flag を検知すると安全停止します

ユーティリティ / ツール
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易的な稼働率・注文成功率・レイテンシのサマリと PASS/FAIL 判定を出力します

AI 関連（ニュース NLP / レジーム判定）
- ニュース NLP（銘柄ごとに LLM でセンチメントを算出）
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（ai 用テーブル: raw_news, news_symbols, ai_scores）を渡して実行
- レジーム判定
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF (1321) の MA200 とマクロニュースの LLM スコアを合成して daily regime を判定・保存

注意点 / 実装上のポイント
-----------------------
- run_monitoring は KABUSYS_ENV にかかわらず monitoring 用 sqlite_path（デフォルト data/monitoring.db）を使います。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB（デフォルト data/paper_trading.db）を使い、本番 DB と分離されます。
- ロギングは kabusys.utils.logging_setup.setup_logging() で統一的に設定されます（コンソール + 日次ローテーションファイル）。
- プロセス優先度設定や CPU affinity は psutil 経由で行います（権限や OS によってスキップされることがあります）。
- AI 呼び出しは OpenAI クライアントを使用。API エラーやレート制限はリトライ戦略を持ち、失敗してもシステム全体を停止させない設計です。
- DuckDB / SQLite の書き込みはトランザクション（BEGIN / COMMIT / ROLLBACK）で扱います。DuckDB の executemany の振る舞い（空リスト不可など）に注意して実装されています。

ディレクトリ構成（主要ファイル）
------------------------------
以下は主なファイル・モジュールの一覧と簡単な説明（src/kabusys 以下）:

- __init__.py
  - パッケージ定義（__version__ 等）

- config.py
  - Settings クラス（環境変数の取得、検証、パス解決）
- config_setup.py
  - .env 対話ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 起動前の設定検証 CLI（python -m kabusys.validate_config）

- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- monitoring/
  - monitoring_db.py : SQLite 用永続化層（テーブル定義・読み書き）
  - system_monitor.py : システム状態・データ鮮度チェック
  - trade_monitor.py  : 発注関連の監視（滞留注文、約定異常等）※実装ファイルあり
  - risk_monitor.py   : ドローダウン・ポジション上限監視
  - kill_switch.py    : kill.flag 操作ロジック
  - monitoring_engine.py : 各 Monitor を束ねる実行ループ
  - alert_manager.py  : アラート送信（LINE 等）※実装ファイルあり

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - Execution のコアロジック（発注、ポジション管理、リスクチェック）

- portfolio/
  - portfolio_builder.py : 候補選定・重み付け
  - position_sizing.py   : 発注株数計算、リスク・上限考慮
  - risk_adjustment.py   : セクターキャップ・レジーム乗数

- research/
  - factor_research.py : ファクター計算（momentum / volatility / value）
  - feature_exploration.py : 将来リターン計算、IC、統計サマリ
  - __init__.py : 公開 API（zscore_normalize 等を re-export）

- ai/
  - news_nlp.py : ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py : ETF MA200 とマクロニュースを合成してレジームを判定

- data/ (実行時に利用される想定ディレクトリ)
  - monitoring.db (デフォルト)
  - paper_trading.db
  - kabusys.duckdb
  - kill.flag / stop_requested.flag / execution.pid （制御ファイル）

- logs/
  - execution.log, monitoring.log など（起動時に自動作成）

サンプルコマンド一覧
-------------------
- .env を作る（対話ウィザード）
  - python -m kabusys.config_setup
- 設定を検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視ループを起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジンを起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート（例）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Python から AI 関数を呼ぶ（例）
  - from kabusys.ai import score_news
    score_news(duckdb_conn, date(2026, 4, 10), api_key="sk-...")

開発メモ / 拡張ポイント
---------------------
- strategy / execution のロジックはモジュール化されているため、BrokerClient の差し替えやポジション単位の lot_size 拡張などが容易に行えます。
- DuckDB を使った分析パイプラインは research モジュールで再利用できます。
- AI モジュールは OpenAI の仕様変更に影響されるため、テスト時は API 呼び出し関数をモックして検証してください（コード内にモックしやすい設計があります）。

問い合わせ / コントリビュート
----------------------------
- README にない詳細な仕様はソース中の docstring / コメントに記載しています。まずは各モジュールの docstring を確認してください。
- バグ修正・機能追加は PR を歓迎します。設計方針やトランザクション方針・フェイルセーフ動作に沿うよう配慮してください。

以上が本リポジトリの概要と利用ガイドです。必要に応じて README の補足（依存関係 pin、セットアップスクリプト、Dockerfile 例など）を追加できます。希望があれば追記します。