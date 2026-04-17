# KabuSys

日本株向けの自動売買 / 研究プラットフォームの一部（モジュール群）。  
本リポジトリには設定管理、監視、ペーパートレード用レポート、ポートフォリオ構築・位置決めロジック、研究用ファクター計算、AI を使ったニュース NLP 等の実装が含まれます。

---

## プロジェクト概要
KabuSys は日本株の自動売買システム（ExecutionEngine 等）と、それを支えるユーティリティ群を提供します。  
主な目的は次のとおりです。

- 設定の対話的作成・検証（.env / config/*.yaml）
- ExecutionEngine と Monitoring の起動スクリプト
- 監視（プロセス生存、データ鮮度、滞留注文、ドローダウン等）と Kill Switch（停止フラグ）の管理
- ペーパートレードの検証レポート生成
- ポートフォリオ構築、ポジションサイズ算出、リスク調整の純関数ライブラリ
- リサーチ用ファクター計算（DuckDB を利用）
- ニュースを LLM（OpenAI）で評価する AI モジュール（news_nlp / regime_detector）

設計上の特徴：
- 環境変数 / .env による設定（config.Settings）
- Paper Trading と Live の DB 分離（paper_trading は専用 SQLite）
- DuckDB を用いたリサーチ計算
- フェイルセーフ（API失敗時のフォールバック、部分失敗の保護等）

---

## 機能一覧
- 設定管理
  - 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- 実行エンジン起動
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV によってペーパートレードを分離）
- 監視プロセス
  - run_monitoring: SystemMonitor のポーリングループを起動
  - MonitoringEngine: System / Trade / Risk モニタを束ねてポーリング（アラート送信のフックあり）
- Kill Switch
  - しきい値超過時に data/kill.flag を書き込み、ExecutionEngine を停止させる仕組み
- ペーパートレード検証レポート
  - tools.paper_verification_report: 稼働率、注文成功率、レイテンシ等の指標を集計して PASS/FAIL 判定
- ポートフォリオ構築（純関数）
  - 候補選定、等分配・スコア分配、セクター制約、レジーム乗数、株数決定（単元考慮、aggregate cap）
- 研究用モジュール
  - factor_research: Momentum, Volatility, Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（Spearman）等
- AI モジュール
  - news_nlp: OpenAI によるニュースセンチメント評価 → ai_scores に書き込み
  - regime_detector: MA とマクロニュースセンチメントを合成して market_regime に保存
- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ（psutil利用）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法や match などを利用しているため）
- SQLite（標準ライブラリ）、DuckDB、psutil 等が必要

推奨インストールパッケージ例:
- duckdb
- psutil
- openai
- pyyaml（validate_config で YAML 検証を行う場合）

例（pip）:
pip install duckdb psutil openai pyyaml

環境変数の初期化
1. 対話式ウィザードで .env を作成:
   python -m kabusys.config_setup
2. 作成後、設定を検証:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development|paper_trading|live（デフォルト: development）
  - paper_trading の場合、MockBroker を使い data/paper_trading.db を使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI 呼び出し用（ai モジュール）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

注:
- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダー参照）。

---

## 使い方（主要コマンド）

1. .env を作成・編集
   python -m kabusys.config_setup
   → 対話式に .env を生成します。

2. 設定検証（起動前に実行推奨）
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict

3. 実行エンジン起動（バックテスト/実運用のエンジン）
   python -m kabusys.run_execution

   特記事項:
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
   - 起動時に data/stop_requested.flag が存在すると起動を行いません。
   - ExecutionEngine は data/execution.pid に PID を書く想定（Settings.pid_file_path で変更可能）。

4. 監視プロセス起動
   python -m kabusys.run_monitoring

   特記事項:
   - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。1 未満や不正値は無視されデフォルトにフォールバックします。
   - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず本番監視 DB を参照）。
   - 停止方法: data/stop_requested.flag を作成すると run_monitoring のループは終了します。KillSwitch は条件により data/kill.flag を書きます。

5. ペーパートレード検証レポート生成
   python -m kabusys.tools.paper_verification_report
   オプション:
   --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   環境変数 PAPER_TRADING_SQLITE_PATH で DB 指定も可能（優先度: --db > 環境変数 > デフォルト）

6. AI / リサーチモジュールのプログラム的利用例
   - ニューススコアリング
     from kabusys.ai.news_nlp import score_news
     score_news(conn, target_date, api_key="...")

   - レジーム判定
     from kabusys.ai.regime_detector import score_regime
     score_regime(duckdb_conn, target_date, api_key="...")

   - ファクター計算
     from kabusys.research import calc_momentum, calc_volatility, calc_value
     calc_momentum(duckdb_conn, date(2026,4,1))

7. Kill Switch / 停止フラグ
   - KillSwitch はリスク条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます。
   - ExecutionEngine 側は起動時に KILL_FLAG_CLEAR_ON_START により自動クリアの挙動を制御できます（本番では 0 推奨）。
   - プロセスを強制停止する際は stop_requested.flag（data/stop_requested.flag）を作成すると run_execution / run_monitoring のループが検知して終了します。

---

## ディレクトリ構成（抜粋）
以下は主要ファイル・ディレクトリの一覧（本リポジトリの一部を抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / .env の読み込みと Settings
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - ai/
      - __init__.py
      - news_nlp.py                — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py         — 市場レジーム判定（MA + LLM）
    - monitoring/
      - monitoring_db.py           — SQLite ベースの監視 DB 層
      - monitoring_engine.py       — 各 Monitor を束ねるエンジン
      - system_monitor.py          — CPU/メモリ/Disk/プロセス/データ鮮度監視
      - trade_monitor.py           — 注文滞留・約定異常監視
      - risk_monitor.py            — ドローダウン・ポジション数監視
      - kill_switch.py             — Kill Switch 実装（flag ファイル書き込み）
      - alert_manager.py           — （アラート送信の抽象インターフェース）
    - portfolio/
      - portfolio_builder.py       — 候補選定・重み計算
      - position_sizing.py         — 株数決定・aggregate cap
      - risk_adjustment.py         — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py         — Momentum/Volatility/Value 等
      - feature_exploration.py     — 将来リターン・IC・統計サマリー等
    - utils/
      - process_priority.py        — プロセス優先度 / CPU affinity 設定
    - execution/                    — Execution 関連（発注・ブローカーファクトリ等）※実装ファイルは省略
    - portfolio/, monitoring/, ai/ 等の内部モジュール

- data/ (ランタイムで使用されることが想定)
  - monitoring.db (デフォルト SQLITE_PATH)
  - kabusys.duckdb (デフォルト DUCKDB_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - execution.pid / stop_requested.flag / kill.flag 等

---

## 追加ノート / 運用上の注意
- paper_trading は本番 DB と完全分離されるよう設計されています。ペーパートレード実行時は PAPER_TRADING_SQLITE_PATH を確認してください。
- run_monitoring は監視 DB（sqlite_path）を使用します。監視は本番 DB を参照する設計のため、環境変数 KABUSYS_ENV に関わらず sqlite_path を使う点に注意してください。
- OpenAI を使う機能（news_nlp / regime_detector）は API キー（OPENAI_API_KEY）が必要です。API レート制限やエラーに対するリトライロジックが実装されていますが、API 利用はコストがかかります。
- validate_config は PyYAML がない場合、config/*.yaml の検証をスキップします（警告を出力）。
- process_priority.set_process_priority は権限やプラットフォームにより動作が制限される場合があります。psutil に依存しています。

---

README に書ききれない詳細な設計・仕様は、各モジュールの docstring / コメントを参照してください。質問があれば具体的なユースケース（例: 実行方法、環境変数の値例、DB スキーマなど）を教えてください。必要に応じて README に追記します。