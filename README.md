README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームの軽量実装です。本リポジトリは以下の主要機能を持ちます。

- 注文・発注エンジン（ExecutionEngine）とそれを監視する Monitoring コンポーネント
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量探索（DuckDB を利用）
- ニュース NLP（OpenAI）を用いた銘柄ごとのセンチメント評価と市場レジーム判定
- 監視ログ・リスク監視・Kill Switch による安全停止
- 開発者向けの設定ウィザード・設定検証・検証レポート出力ツール

設計方針（抜粋）
- 本番 DB（monitoring）とペーパートレード DB を分離可能
- DuckDB を分析用 DB として利用
- OpenAI は外部サービス呼び出し部のみ明確に分離、フェイルセーフ設計
- 自動生成される .env を使った環境設定と起動前検証を提供

主要機能一覧
--------------
- Execution 起動スクリプト: src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
  - プロセス優先度の設定、PID 管理、停止フラグ監視（data/stop_requested.flag）
- Monitoring 起動スクリプト: src/kabusys/run_monitoring.py
  - System / Trade / Risk 各モニタを周期的に実行、kill.flag の作成でエンジン停止を誘発
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を調整（デフォルト 60 秒）
- 設定ウィザード: src/kabusys/config_setup.py
  - 対話式に .env を作成・更新
- 設定検証: src/kabusys/validate_config.py
  - .env と config/*.yaml の妥当性チェック。--strict で警告をエラー扱いに
- Paper Trading 検証レポート: src/kabusys/tools/paper_verification_report.py
  - 運用ログから稼働率・成功率・レイテンシ等を集約して PASS/FAIL 判定を出力
- ポートフォリオ構築モジュール: src/kabusys/portfolio/
  - 候補選定、等重・スコア重み付け、ポジションサイズ計算、セクター上限・レジーム乗数
- リサーチ: src/kabusys/research/
  - ファクター計算（モメンタム・バリュー・ボラティリティ）、将来リターン、IC 計算等
- AI: src/kabusys/ai/
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメントの集約と ai_scores への書き込み
  - regime_detector: ETF MA とマクロニュースで市場レジーム判定
- 監視永続化層: src/kabusys/monitoring/monitoring_db.py
  - SQLite に監視ログ / トレードログ / ポジション / リスクログ / ダッシュボードを保存
- ユーティリティ: src/kabusys/utils/
  - ロギング設定、プロセス優先度/CPU affinity 設定など

セットアップ手順
----------------
以下は一般的なローカルセットアップ手順の例です。プロジェクトに requirements.txt は含まれていませんが、少なくとも以下のパッケージが必要になります: duckdb, psutil, openai, (任意) PyYAML。

1. リポジトリをクローンする
   - git clone <repo_url>
   - cd <repo_root>

2. Python 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai

   追加（YAML 検証を使う場合）:
   - pip install pyyaml

4. .env を作成する
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（例は下に記載）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗としたい場合: python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要なら）
   - mkdir -p data logs

環境変数（主なもの）
--------------------
主要な環境変数のまとめ（必須は明記）:

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境関連
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
    - paper_trading: MockBroker を使い、paper_trading 用 DB に記録
    - live: 本番。注意して設定を行うこと
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

- AI / OpenAI
  - OPENAI_API_KEY — OpenAI 呼び出しに使用

- Monitoring / Execution
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒・デフォルト 60）
  - PID_FILE_PATH — Execution の PID ファイルパス（default: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグファイル（default: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" または "0"。本番での "1" は危険）

- Paper Trading 挙動
  - PAPER_FILL_MODE — ペーパートレード時の約定モード ("instant" | "partial" | "never" | "reject")

例: .env の最小サンプル
-----------------------
以下は .env の一例（実際のシークレットは隠す）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

使い方（起動・各種コマンド）
--------------------------

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告を FAIL 扱いに: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（デフォルト）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード DB に記録され、本番 DB と分離されます

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db path/to/paper_trading.db

- ライブラリ的に使用する関数（プログラム内呼び出し）
  - ポートフォリオ: from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - リサーチ: from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  - AI:
    - from kabusys.ai import score_news  — DuckDB 接続と target_date を渡して実行
    - regime_detector の score_regime を直接呼べます（OpenAI APIキーが必要）
  - 監視 DB ヘルパ: kabusys.monitoring.monitoring_db.MonitoringDB

停止・安全機能
--------------
- kill.flag（Settings.kill_flag_path; デフォルト data/kill.flag）
  - Monitoring の KillSwitch が条件を満たした場合に書き込まれ、ExecutionEngine は起動中に存在を検出して停止します
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START="1" を設定すると自動クリアされます（本番では非推奨）
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring / run_execution 内のループ監視用フラグとして存在。手動で作成すると起動ループを終了させることができます
- PID ファイル: data/execution.pid に PID を書きます

ログ
----
- デフォルトで logs/<app_name>.log に日次ローテーションで出力（30 日保持）
- コンソールは stdout に出力されます
- 環境変数 LOG_DIR でログディレクトリを変更可能

注意事項・運用上のポイント
-----------------------
- KABUSYS_ENV=live の場合は本番運用になります。LINE 通知など本番向け設定を十分に確認してください（validate_config は live 時に追加警告を出します）。
- Monitoring は run_monitoring が使用する sqlite_path（monitoring DB）を本番パスで固定的に使用します（環境にかかわらず設定の sqlite_path を使用）。
- Paper Trading は本番 DB と完全に分離されるように専用 SQLite を使います（PAPER_TRADING_SQLITE_PATH）。
- OpenAI 呼び出しは外部 API に依存します。API キー未設定時は例外を送出する設計の箇所があります（score_news / score_regime など）。
- DuckDB のバージョンや executemany の仕様による制約（空リスト不可など）に注意している箇所があります。

ディレクトリ構成
----------------
以下は主要ファイル・ディレクトリ（src/kabusys 以下）の概要です。

- src/kabusys/
  - __init__.py — パッケージ定義、__version__
  - config.py — 環境変数 / Settings 管理、.env 自動読み込み（.git / pyproject.toml をルートとして探索）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — ニュースの LLM スコアリング（ai_scores）処理
    - regime_detector.py — 市場レジーム判定

  - portfolio/
    - portfolio_builder.py — 候補選定・等重/スコア重み
    - position_sizing.py — 株数計算・スケーリング・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計要約

  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化 + MonitoringDB クラス
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文関連の監視ロジック; 実装あり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 管理
    - monitoring_engine.py — 複数 Monitor の統合実行
    - alert_manager.py — （アラート配信管理; 実装あり）

  - execution/
    - execution_engine.py — ExecutionEngine 本体（発注ループ等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注管理・リポジトリ・ブローカー抽象など

  - data/
    - pipeline.py, stats.py 等 — DuckDB 用のパイプライン・統計ユーティリティ（prices_daily などを扱う）

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力

  - utils/
    - logging_setup.py — ロギング初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

付記（開発者向け）
-----------------
- YAML の内容検証は PyYAML があれば行われます。validate_config は PyYAML 未インストール時は YAML 検証をスキップして警告を出します。
- OpenAI 呼び出しのテストやモックは各モジュールで _call_openai_api をパッチすることで容易に行えます（テスト用フックを想定した設計）。
- DuckDB 接続を渡して純粋関数群（research/portfolio）を呼び出すことで、本番資産には触れずにデータ処理や検証ができます。

お問い合わせ / 貢献
------------------
- バグ報告・改善提案はリポジトリの Issue に投稿してください。
- 大きな変更は PR として送ってください。テストと簡単なドキュメント更新を同時にお願いします。

以上。必要であれば、README に追加するコマンド例や .env の完全テンプレート、起動フロー図などを作成します。どの情報を詳しく掘り下げたいか教えてください。