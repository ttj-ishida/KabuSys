README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。
このリポジトリは主に以下の領域をカバーします:

- 実行エンジンの起動スクリプト（ExecutionEngine。発注処理）
- 監視・アラート（System / Trade / Risk のモニタ）
- ポートフォリオ構築・ポジションサイズ計算の純関数群
- 研究用ファクター計算・特徴量解析
- ニュース NLP / レジーム判定（OpenAI を用いた補助機能）
- 各種 CLI ツール（環境設定ウィザード、設定検証、ペーパートレード検証レポート等）

主な特徴
--------
- 実行環境（development / paper_trading / live）に応じた挙動（ペーパートレード時は MockBroker を使用し、DB を分離）
- Monitoring: system/trade/risk を定期ポーリングし、監視ログを SQLite に永続化
- Kill Switch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を安全停止
- DuckDB を用いた時系列・ファクター計算（prices_daily, raw_financials 等を利用）
- ニュースを LLM（OpenAI）でスコアリングし ai_scores テーブルへ保存
- 各種ユーティリティ（プロセス優先度設定、PID / フラグファイル管理、設定ウィザード等）
- ペーパートレード検証用のレポート生成ツール

セットアップ手順
---------------
前提:
- Python 3.9+
- 必要なライブラリ（使用機能により異なる）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config/*.yaml の検証を行う場合)
- ネットワーク経由で実際の発注を行う場合は kabuステーション 等の設定が必要

基本的な導入手順:

1. リポジトリをクローンし、仮想環境を作成・有効化する:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール:
   - pip install -r requirements.txt
     （requirements.txt が無い場合は最低でも duckdb, psutil をインストール）
   - AI 機能を使う場合: pip install openai

3. .env を準備:
   - 対話式ウィザード: python -m kabusys.config_setup
   - あるいは手動で .env を作成し、必須変数を設定:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - など（.env.example を参照）

4. 設定検証（起動前確認）:
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合: python -m kabusys.validate_config --strict

使い方
------

環境設定
- python -m kabusys.config_setup
  対話式に .env を作成・更新します。生成後は python -m kabusys.validate_config で検証してください。

設定検証
- python -m kabusys.validate_config
  .env および config/*.yaml （存在する場合）をチェックします。PyYAML がインストールされていると YAML の構文チェックも行います。

ExecutionEngine（発注エンジン）の起動
- 開発・テスト（ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパートレード時は MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と完全分離されます。
- 本番（live）:
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - 実行時に data/execution.pid に PID が書き込まれ、監視側はこの PID をチェックしてプロセス生存を確認します。
- 補足:
  - 起動時にプロセス優先度を high に設定します（psutil を使用）。
  - 起動前に data/stop_requested.flag が既に存在する場合は起動しません（安全機構）。

Monitoring（監視）プロセスの起動
- python -m kabusys.run_monitoring
  - 監視は定期的に SystemMonitor / TradeMonitor / RiskMonitor を実行し、SQLite（SQLITE_PATH）へログを残します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を参照して記録します。
  - data/stop_requested.flag を置くと監視ループは終了します。

停止・Kill Switch
- Kill Switch: RiskMonitor の評価等で条件が満たされると data/kill.flag に理由を書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine は起動時にこのフラグを確認し、また監視で検出した場合にエンジンを停止します）。
- 手動で停止要求を出す（監視 / エンジン双方の停止）には data/stop_requested.flag を作成します。

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）
  - 出力: 指定期間の稼働率、注文成功率、送信率、レイテンシ等を表示し PASS/FAIL を判定します。

AI 関連
- ニューススコアリング:
  - kabusys.ai.news_nlp.score_news を使用して raw_news から銘柄ごとの ai_score を生成・ai_scores テーブルに保存します。OpenAI API キー（OPENAI_API_KEY）が必要です。
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime を用いて市場レジーム（bull/neutral/bear）を daily に判定し market_regime テーブルへ書き込みます。OpenAI API キーが必要です。
- 注: API 呼び出しはレート制限・ネットワーク障害に対してバックオフ・フォールバック処理が組み込まれていますが、API キーの設定は必須です。

主要な環境変数（抜粋）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 使用頻度高:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db（paper_trading 用）
  - LOG_LEVEL — デフォルト INFO
  - OPENAI_API_KEY — AI 機能を使う場合に必要
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動消去するか（開発用、0/1）
- 自動 .env ロードの無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env の読み込みを抑止できます（テスト向け）。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定読み込みロジック
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト
- tools/
  - paper_verification_report.py  — ペーパートレード検証レポート生成 CLI
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI でセンチメント）
  - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py        — SQLite 用永続化層
  - monitoring_engine.py    — 監視のオーケストレータ
  - system_monitor.py       — システム / データ鮮度監視
  - trade_monitor.py        — 注文滞留・約定異常監視
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — Kill Switch（flag ファイル制御）
  - alert_manager.py        — （アラート送信ロジック、未表示ファイル）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/               — 監視関連（上記）
- utils/
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
- execution/ (参照あり)    — 実行系（OrderManager, Engine など。リポジトリに含まれることを想定）
- data/ (ランタイム用)
  - kill.flag               — Kill Switch が書き込む停止フラグ
  - stop_requested.flag     — 実行・監視の手動停止フラグ
  - execution.pid           — エンジンの PID 書き込み先
  - monitoring.db, paper_trading.db, kabusys.duckdb など

注意点・トラブルシューティング
------------------------------
- DB ファイル / ディレクトリ:
  - デフォルトの data/ 配下に DB を置きます。親ディレクトリが存在しない場合は起動時に自動作成される機能がある箇所もありますが、事前に作成しておくと安全です。
- 権限:
  - プロセス優先度の設定や CPU affinity は権限不足により失敗する場合があり、その場合は警告ログを出すだけで継続します。
- 依存ライブラリ:
  - PyYAML 未インストール時は validate_config の YAML 検証をスキップします（警告）。
  - openai ライブラリは AI 機能専用です。未インストールでもその他機能は動作します。
- LLM 呼び出し:
  - OpenAI 呼び出しはネットワーク・レート制限に配慮してリトライ実装がありますが、APIキー未設定だと例外になる点に注意してください。
- Kill Switch / stop flag:
  - data/kill.flag は本番停止に関わる重要なフラグです。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（validate_config で警告）。

開発・拡張メモ
---------------
- portfolio / position sizing / risk adjustment 等の関数群は副作用のない純関数として設計されているため、単体テストが容易です。
- research モジュールは DuckDB 接続を受け取り SQL と Python の組合せでファクターを計算します。DuckDB に prices_daily, raw_financials 等をロードして動作させます。
- AI モジュールの外部 API 呼び出しは内部でラップされており、テスト時はパッチで置換してモック可能です（例: unittest.mock.patch）。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報や貢献ガイドラインはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

以上が本コードベースの README です。詳細な設計意図や仕様はソース内の docstring / コメントにも記載されていますので、該当ファイルを参照してください。必要であれば README を英語版に翻訳したり、起動フロー図・ER 図を追加することもできます。どの情報を追加したいか教えてください。