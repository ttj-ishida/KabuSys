# KabuSys

日本株自動売買システムのライブラリ/実行スクリプト群です。  
この README はソースツリー（src/kabusys）に基づき、プロジェクトの概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。主な責務は以下のとおりです。

- ExecutionEngine（発注エンジン）: ブローカーとのやり取り、注文管理、リスク管理、約定整合処理等
- Monitoring（監視）: システム稼働確認、注文ログ監視、リスク監視、Kill Switch（停止フラグ）発動
- Portfolio コンポーネント: 候補選定、配分（重み）計算、ポジションサイズ計算、セクター制限・レジーム補正
- Research（研究）: ファクター計算、将来リターン計算、IC・統計サマリー等（DuckDB を用いた分析）
- AI 系: ニュースの NLP スコアリング（OpenAI を利用）・市場レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定、.env ウィザード、設定検証ツール、ペーパートレード検証レポート等
- 永続化: SQLite（監視・ペーパートレード DB）および DuckDB（分析用）

設計方針として、実行スクリプトと内部ロジックを分離し、テスト容易性・冪等性・フェイルセーフ（API障害時のフォールバック）に配慮しています。

---

## 主な機能一覧

- Execution
  - 実際のブローカークライアント / Paper Trading 用 Mock クライアント切替（KABUSYS_ENV）
  - OrderRepository / OrderManager / RiskManager / Reconciler による注文管理
  - ExecutionEngine によるセッション実行（PID ファイル管理、停止フラグ監視）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度/プロセス存在確認
  - TradeMonitor: 注文の滞留・異常約定の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限チェック
  - KillSwitch: 条件に応じた kill.flag 書き込みと ExecutionEngine 停止トリガ
  - AlertManager 経由の通知（LINE 等、トークン未設定時は無効）
- Research / Portfolio
  - ファクター計算（momentum / volatility / value 等）
  - forward returns、IC 計算、統計サマリー
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- AI
  - news_nlp: OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント算出・ai_scores への書き込み
  - regime_detector: ETF（1321）MA200 乖離＋マクロニュースで市場レジーム判定
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト
- ユーティリティ
  - 統一ロギング設定（stdout + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要条件（概要）

- Python 3.9+
- SQLite（Python 標準ライブラリで利用）
- 以下 Python パッケージ（最低限）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config 検証で YAML ファイル検証を行う場合）
- ネットワーク接続（kabuステーション API / OpenAI 等を使う場合）

※ 環境や OS により追加の依存が必要になる場合があります。

---

## セットアップ手順

1. リポジトリをクローン / ソース配置
   - 例: git clone <repo> && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML
   - （必要に応じて他パッケージを追加）

4. .env 初期化（対話ウィザード）
   - python -m kabusys.config_setup
   - これによりプロジェクトルートに `.env` が作成されます（絶対に Git 管理下に commit しないこと）

5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が設定されていることを確認してください。
   - 本番環境 `KABUSYS_ENV=live` の場合は警告が増えます。`--strict` を付けると警告も失敗扱いになります。

---

## 主要な環境変数

主な変数（.env に記載される）:

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能利用時）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（例: INFO）
- LOG_DIR（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険: 0 推奨）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔上書き、秒・デフォルト 60 秒）

---

## 実行方法（使い方）

以下は代表的なコマンド例です。パッケージがインストール済みでプロジェクトルートから実行する前提です。

- ExecutionEngine（エンジン起動）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBroker を利用します。
    - 起動前に data/stop_requested.flag が存在すると起動しません。
    - 実行中は data/execution.pid に PID を書きます（設定で変更可）。
    - 停止は data/stop_requested.flag を作成することで実行エンジンに通知できます（kill.flag とは別）。

- Monitoring（監視ループ起動）
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL に秒数を設定するとポーリング間隔を上書き（デフォルト 60 秒）
  - 注意:
    - monitoring の DB 接続は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視は常に本番 DB を見る設計）。
    - 停止は data/stop_requested.flag によりループが終了します。

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL 扱い）: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI / 研究系（ライブラリとして利用）
  - OpenAI を使う関数は直接インポートして呼び出します。例:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - DuckDB 接続（duckdb.connect(path)）を渡し、target_date を指定して呼ぶ設計です。
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を使います。

---

## 停止・フラグ関連

- data/stop_requested.flag
  - run_execution/run_monitoring の外部停止フラグ。存在するとループが終了します（run_execution は起動前に存在すれば起動しない）。
- data/kill.flag
  - KillSwitch が発動したときに書き込まれるファイル。ExecutionEngine 側で検出して処理されます。
- KILL_FLAG_CLEAR_ON_START
  - 起動時に kill.flag を自動で消すかの制御（本番で 1 にするのは危険）。

---

## ライブラリ利用例（API 抜粋）

- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- 研究:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- AI:
  - from kabusys.ai import score_news  (内部で OpenAI クライアントを利用)

各関数は docstring に詳細な引数・返り値の仕様があるため、実装箇所を参照してください。

---

## ディレクトリ構成（抜粋）

```
src/
  kabusys/
    __init__.py
    config.py                    # 環境変数/.env 読込ロジック・Settings
    config_setup.py              # .env 対話式ウィザード
    validate_config.py           # 設定検証 CLI
    run_execution.py             # ExecutionEngine 起動スクリプト
    run_monitoring.py            # SystemMonitor ポーリングループ起動スクリプト

    execution/                   # 発注系コンポーネント（Engine, OrderManager 等）
      ...

    monitoring/
      monitoring_db.py           # SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py
      ...

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      factor_research.py
      feature_exploration.py

    ai/
      news_nlp.py                 # ニュース NLP スコアリング (OpenAI)
      regime_detector.py         # 市場レジーム判定 (OpenAI + price)
      __init__.py

    tools/
      paper_verification_report.py

    data/                        # 実行時に使用されるデータ・フラグファイル等（git 管理外推奨）
      *.db, kill.flag, stop_requested.flag, execution.pid, ...

    utils/
      logging_setup.py            # ログ設定ユーティリティ
      process_priority.py         # プロセス優先度・CPU affinity 設定
      ...
```

（上記は主要ファイルのみ抜粋です。詳細はソースツリーを参照してください。）

---

## 注意事項 / 運用上のポイント

- .env は絶対にリポジトリにコミットしないでください（機密情報含む）。
- KABUSYS_ENV の設定により挙動が変わります。paper_trading では本番 DB と完全に分離された専用 SQLite を使うように設計されていますが、設定ミスに注意してください。
- 本番運用時は KILL_FLAG_CLEAR_ON_START=0 を推奨します（誤って Kill Switch を自動クリアすることを避ける）。
- ロギングはデフォルトで stdout と logs/<app>.log（日次ローテート）に出力します。ログディレクトリ作成失敗時はコンソール出力のみになります。
- OpenAI（AI 機能）は料金発生やレイテンシの懸念があるため、充分にテストしてから本番で使ってください。API 呼び出しの失敗や不安定な応答に対するフェイルセーフ（フォールバック）実装がありますが、運用ポリシーを整えてください。
- DuckDB / SQLite のパスやバックアップ方針を運用前に決めておいてください（分析 DB とトランザクション DB の運用分離等）。

---

## 開発・貢献

- コードの追加・修正は PR ベースで行ってください。
- 新しい設定項目を追加する場合は `config_setup.py` と `validate_config.py` の該当箇所を更新してください。
- DB スキーマ変更は `monitoring_db.init_monitoring_db` にマイグレーション処理を追加してください（既存 DB との互換性確保のため）。

---

必要であれば README に「インストール例」「運用チェックリスト」「デバッグ手順（ログの読み方や主要な SQL クエリ）」なども追記できます。どの情報を追加したいか教えてください。