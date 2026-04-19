KabuSys
=======

日本株向けの自動売買／リサーチ基盤の軽量なコードベースです。本リポジトリには以下の主要機能を含みます:

- 実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）
- Paper Trading 用の分離された DB / Mock ブローカー対応
- モニタリング・キルスイッチ（kill flag）による安全停止
- DuckDB を用いたリサーチ／ファクター計算（ファクター群、将来リターン、IC 等）
- ニュース NLP（OpenAI）によるセンチメント評価 / レジーム判定
- ペーパートレード検証レポート生成ツール
- 環境設定ウィザード・設定検証ツール
- ログ出力ユーティリティ、プロセス優先度設定などのユーティリティ群

以下は開発者向けの README（日本語）です。

概要
----
KabuSys はトレーディング実行（発注）とは別に監視・リスク管理・リサーチ機能を備えたモジュール群を提供します。設計方針としては：

- 本番／ペーパーを環境変数（KABUSYS_ENV）で切り替え可能（paper_trading は専用 SQLite DB を使用）
- DuckDB を分析用 DB として利用
- OpenAI を使ったニュース NLP / レジーム判定機能（API キー必須、フォールバックロジックあり）
- 監視は定期ポーリング（MONITOR_POLL_INTERVAL）で system/trade/risk を評価し、条件に応じて kill.flag を書き込むことで実行エンジンを安全に停止させる

主な機能一覧
-------------
- 環境管理
  - .env 自動読み込み（.env.local を含む、OS 環境変数を保護）
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行／監視
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper DB に記録
    - 停止フラグ（data/stop_requested.flag）検出で安全停止
  - Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
    - SystemMonitor（プロセス死活、リソース）、TradeMonitor、RiskMonitor をポーリング
    - MONITOR_POLL_INTERVAL で間隔上書き可能（デフォルト 60 秒）
    - 監視ログは SQLite（monitoring.db）に永続化

- モニタリング DB API
  - monitoring_db.py に CRUD ライクな永続化レイヤ（system_status / trade_logs / positions / risk_logs / dashboard）

- リサーチ / ファクター
  - research モジュール: momentum / volatility / value の計算、将来リターン、IC、統計サマリ等（DuckDB 接続を受け取り SQL で処理）

- ポートフォリオ構築
  - portfolio モジュール: 候補選定、重み計算、単元丸め、セクターキャップ、レジームによる乗数等

- AI 周り
  - ai.news_nlp — raw_news を集約して OpenAI（gpt-4o-mini 想定）で各銘柄のセンチメントをスコア化して ai_scores に保存
  - ai.regime_detector — ETF (1321) の MA200 とマクロニュースの LLM スコアを合成し日次レジーム判定

- ツール
  - tools.paper_verification_report — Paper Trading の検証レポート生成（稼働率・約定率・レイテンシ等）

セットアップ手順
----------------

前提:
- Python 3.9+（typing の一部機能を使用）
- 仮想環境を推奨（venv / pyenv 等）

1. クローンと仮想環境作成
   - git clone <repo>
   - cd <repo>
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt があればそれを使うか、少なくとも次を導入してください:
     - duckdb
     - psutil
     - openai (OpenAI Python SDK)
     - PyYAML (設定検証で YAML パースを行いたい場合)
   例:
     - pip install duckdb psutil openai pyyaml

3. 環境変数 / .env の準備
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数（validate_config で確認される）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他の主要な環境変数（デフォルト値は以下）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading の場合に使用)
     - LOG_LEVEL: INFO（もしくは DEBUG / WARNING / ERROR）
     - OPENAI_API_KEY: OpenAI を利用する際に必須
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定動作）

4. データディレクトリ／ログディレクトリの準備
   - デフォルトでは data/ と logs/ を使用します。自動作成は各処理で試みますが、権限等の問題を避けるため事前に作成しておくことを推奨します。
     - mkdir -p data logs

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

使い方（実行例）
----------------

- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を調整:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使い data/paper_trading.db に記録:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI スコア生成 / レジーム判定（プログラム上の呼び出し）
  - ai.score_news(conn, target_date, api_key=...)  （conn は DuckDB 接続）
  - ai.regime_detector.score_regime(conn, target_date, api_key=...)

運用に関する注意点
------------------
- kill switch / stop flag:
  - 監視が致命的なリスク（ドローダウンやポジション上限）を検出すると data/kill.flag を書き込み、ExecutionEngine を停止させます（実行エンジンは起動時にこのフラグをチェックします）。
  - 監視・実行ループの終了用フラグ: data/stop_requested.flag（運用者がループを終了したい場合に利用）。
- ログ:
  - デフォルトは logs/ 以下に日次ローテートで出力（logs/<app_name>.log）。ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。
- Paper Trading:
  - paper_trading モードは本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
  - PAPER_FILL_MODE によって MockBroker の約定挙動を変更可能（instant / partial / never / reject）。
- OpenAI:
  - OpenAI を利用する機能は OPENAI_API_KEY が必須。API 呼び出しが失敗した場合はフェイルセーフなフォールバック（ゼロスコア等）が実装されていますが、精度は劣化します。
- プロセス優先度:
  - 起動時にプロセス優先度を high に設定しようとします（psutil に依存、権限がない場合は警告）。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 配下の主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読込 / Settings
  - config_setup.py          — .env 対話式ウィザード (python -m kabusys.config_setup)
  - validate_config.py       — 設定検証 CLI (python -m kabusys.validate_config)
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成ツール
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — レジーム判定
  - monitoring/
    - monitoring_db.py       — monitoring DB スキーマ + API
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — （取引関連の監視実装）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各モニタの束ね処理
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — （LINE などへの通知ハンドラ）
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 株数決定 / 単元丸め / aggregate cap
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity
    - __init__.py

（補足）実際のリポジトリでは execution/* や data/ スクリプト等、ここに挙げられていない関連モジュールが存在する可能性があります。

開発・拡張ガイド
----------------
- DuckDB: research モジュールは DuckDB 接続を受け取り SQL を直接実行する設計です。大規模データや解析を行う場合は indexing / パーティショニング等で性能改善してください。
- AI モジュール: API 呼び出し部分はユニットテスト時にモックしやすいよう分離しています（_call_openai_api を patch する等）。
- 設定ファイル（config/*.yaml）: validate_config で存在と YAML パースの検証を行えます。テンプレートは scripts/generate_config.py 等で生成する想定です。
- テスト: 各純粋関数（portfolio/*, research/*, monitoring/* のロジック）は DB に依存しない関数が多く、ユニットテストが書きやすい構造です。

ライセンス / バージョン
-----------------------
パッケージバージョン: src/kabusys/__version__ = 0.1.0

（ライセンス情報はリポジトリルートの LICENSE を参照してください。）

最後に
------
この README はコードベースの主要ポイントをまとめたものです。個々のモジュールには詳細な docstring と設計注記が含まれていますので、実装や拡張の際は該当ファイルを参照してください。問題や質問があれば、どの部分について知りたいかを教えてください。