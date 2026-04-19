README — KabuSys（日本株自動売買システム）
====================================

概要
----
KabuSys は日本株向けの自動売買（Execution）・監視（Monitoring）・リサーチ（Research）を含む小規模な取引フレームワークです。
設計方針としては「環境分離（本番 / ペーパートレード）」「フェイルセーフ」「外部 API 呼び出しの明示的制御」「DuckDB/SQLite を用いたデータ永続化」を採用しています。

主な特徴
---------
- ExecutionEngine（発注エンジン）: 本番 / ペーパートレードを切替可能。ペーパートレードでは MockBroker を使用し DB を分離。
- Monitoring（監視）: システム状態・データ鮮度・注文/約定の監視とアラート生成。Kill Switch による自動停止機能。
- Portfolio コンポーネント: 候補選定、重み算出、ポジションサイズ計算、セクター上限・レジーム乗数の調整など純粋関数群。
- Research モジュール: DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）や特徴量解析（IC 等）。
- AI モジュール: OpenAI を用いたニュースセンチメント解析（news_nlp）および市場レジーム判定（regime_detector）。
- ユーティリティ: 設定ウィザード .env 作成、設定検証 CLI、ログ設定、プロセス優先度設定など。

前提 / 依存パッケージ
-------------------
主に以下を想定しています（プロジェクトに requirements.txt がある場合はそちらを優先してください）:
- Python 3.10+（PEP 604 の型ヒント（X | Y）を使用）
- duckdb
- psutil
- openai
- sqlite3（標準ライブラリ）
- PyYAML（config/*.yaml の検証に使用、任意）
- その他: logging, pathlib 等は標準ライブラリ

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存ライブラリをインストール
   - pip install duckdb psutil openai pyyaml
   （必要に応じて requirements.txt があれば pip install -r requirements.txt）

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成（.env は Git に絶対にコミットしないでください）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合: python -m kabusys.validate_config --strict

主要な環境変数（代表）
---------------------
（.env に設定する項目の一部）
- JQUANTS_REFRESH_TOKEN : J-Quants API（必須）
- KABU_API_PASSWORD    : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL    : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV          : 実行環境（development / paper_trading / live）
- DUCKDB_PATH          : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH          : 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL, LOG_DIR   : ログ設定
- OPENAI_API_KEY       : OpenAI API キー（AI モジュールで使用）
- PAPER_FILL_MODE      : ペーパートレードの約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1）

主な実行コマンド / 使い方
------------------------

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い: python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - export MONITOR_POLL_INTERVAL=30
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。

- 発注エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
  - 停止: data/stop_requested.flag を作成すると、起動中のループ・スレッドを順次停止します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI モジュール（プログラム的利用例）
  - ニューススコア算出（DuckDB 接続を渡す）:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

ログ・DB・停止フラグについて
----------------------------
- ロギング:
  - kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出しているため、ログは標準出力と logs/<app_name>.log（日次ローテーション、30日保持）へ出力されます。
  - LOG_DIR 環境変数で出力先を変更可能。

- DB:
  - DuckDB: デフォルト data/kabusys.duckdb（リサーチ・AI 等の分析用）
  - SQLite:
    - 監視用: data/monitoring.db（Monitoring 用）
    - ペーパートレード: data/paper_trading.db（paper_trading 環境で使用）

- 停止フラグ・Kill Switch:
  - data/stop_requested.flag: 実行プロセス（run_monitoring, run_execution など）がこのファイルの存在を検知して安全に停止します。
  - data/kill.flag: KillSwitch が条件に応じて書き込み、ExecutionEngine に停止シグナルを送るために使用されます。Settings.kill_flag_clear_on_start により起動時に自動クリアする挙動を制御します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env 自動読み込みロジック、Settings クラス
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py          — ExecutionEngine 起動スクリプト

kabusys/ai/
- news_nlp.py               — ニュース→センチメントスコア（OpenAI）
- regime_detector.py        — 市場レジーム判定（MA + マクロセンチメント合成）
- __init__.py

kabusys/monitoring/
- monitoring_db.py          — SQLite スキーマ初期化・永続化 API
- system_monitor.py         — CPU/メモリ/ディスク/データ鮮度監視
- trade_monitor.py          — （注文関連の監視：コードベース参照）
- risk_monitor.py           — ドローダウン・ポジション上限監視
- kill_switch.py            — kill.flag の作成・管理
- monitoring_engine.py      — 各 Monitor の統合ループ
- alert_manager.py          — （アラート送信ロジック：コードベース参照）

kabusys/execution/
- execution_engine.py       — ExecutionEngine（発注・セッション管理）
- order_manager.py / order_repository.py / reconciler.py / risk_manager.py / broker_factory.py
                             — 発注管理・ブローカー抽象等

kabusys/portfolio/
- portfolio_builder.py      — 候補選定・重み計算
- position_sizing.py        — 発注株数計算（リスクベース等）
- risk_adjustment.py        — セクター上限・レジーム乗数

kabusys/research/
- factor_research.py        — モメンタム/バリュー/ボラティリティ等
- feature_exploration.py    — 将来リターン計算・IC・統計サマリー

kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

kabusys/utils/
- logging_setup.py          — ログ設定ユーティリティ
- process_priority.py       — プロセス優先度 / CPU affinity 設定

開発者向けメモ / 注意点
---------------------
- .env は OS 環境変数を上書きしないように自動読み込みロジックが配慮されています（.env.local は上書き可能）。
- KABUSYS_ENV によって動作モード（development / paper_trading / live）を切替えます。live は本番のため十分注意してください（validate_config が追加チェックを行います）。
- AI 関連の呼び出しは API キーとレート制限・エラー処理を厳重に扱っていますが、API 呼び出しに伴うコストとレイテンシに注意してください。
- データのルックアヘッド（未来データ参照）を避ける設計になっています（target_date の取り扱いがすべて明示的）。

サンプル（よくある操作例）
------------------------
- 初期設定ウィザード → 設定検証 → 監視起動:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.run_monitoring

- ペーパートレード起動（環境変数指定の例）:
  - export KABUSYS_ENV=paper_trading
  - export OPENAI_API_KEY="sk-xxxx"
  - python -m kabusys.run_execution

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
（ここにライセンス情報や貢献方法・コードスタイル規約を記載してください。プロジェクトのポリシーに従って追記をお願いします。）

問い合わせ
----------
実装・運用に関する質問や障害報告はプロジェクトの Issue に登録してください。README の追加改善提案も歓迎します。

以上。README をベースに必要に応じて項目（依存関係の固定バージョン、具体的な DB マイグレーション手順、CI/CD のセットアップ等）を追記してください。