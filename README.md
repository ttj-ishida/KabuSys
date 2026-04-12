# KabuSys — README (日本語)

このリポジトリは日本株自動売買システム「KabuSys」のソースコードです。  
以下はコードベースに基づくプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成のまとめです。

注意: README はコードコメント・モジュール実装を元に作成しています。実運用前に必ずテスト環境で動作確認してください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主な責務は次のとおりです：

- 注文生成・管理・ブローカー連携（Execution Engine）
- リコンシリエーション（再起動後の同期）
- ポートフォリオ構築（候補選定・重み付け・株数決定・リスク調整）
- 監視（プロセス監視・データ鮮度・注文滞留・ドローダウン監視）
- 運用用ツール（Paper trading 検証レポート、Streamlit ダッシュボード）
- 研究用ファクター計算・特徴探索（DuckDB を利用）
- AI 機能：ニュースの NLP スコアリング、マクロセンチメントによるレジーム判定（OpenAI 利用）

設計方針の特徴：
- DuckDB + SQLite を組み合わせた分析・監視ストレージ
- 環境変数 / .env による設定
- Paper trading と本番の DB を明確に分離
- 外部 API（ブローカー / OpenAI / LINE）との最小限の結合。API失敗時はフェイルセーフで継続。

---

## 主な機能一覧

- Execution
  - OrderManager / OrderRepository による注文の作成、送信、状態遷移
  - BrokerFactory を介した本番 / Paper Trading 切替（MockBrokerClient）
  - Reconciler による起動時同期（Order / Position の突合）
- Portfolio（ポートフォリオ構築）
  - 候補選定（select_candidates）
  - 等金額・スコア加重配分（calc_equal_weights, calc_score_weights）
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - 株数決定（calc_position_sizes） — lot 単位・リスクベース・各種上限考慮
- Monitoring（監視）
  - SystemMonitor: CPU/MEM/Disk、プロセス PID の存在、価格データ鮮度
  - TradeMonitor: 滞留注文、約定価格の異常検知
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard の永続化
  - KillSwitch: 条件達成時に flag ファイルを書いて ExecutionEngine 停止指示
  - AlertManager: LINE へのプッシュ通知(クールダウン有り)
  - MonitoringEngine: 上記モニタ群を束ねたポーリングループ
  - Streamlit ダッシュボード（簡易 UI）
- Research（研究）
  - ファクター計算: momentum / volatility / value
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - news_nlp.score_news: raw_news から OpenAI を呼び、銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF ma200乖離 + マクロニュース (OpenAI) を用いた日次レジーム判定
- Tools
  - paper_verification_report: Paper Trading の検証レポート（成功率 / レイテンシ / 稼働率 等）

---

## セットアップ手順（開発 / ローカル）

1. Python 環境（3.9+ 推奨）を準備
   - pyenv / venv などを利用して仮想環境を作ることを推奨します。

2. 必要パッケージをインストール
   - 主要な依存（コードから推測）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （実リポジトリに requirements.txt があれば `pip install -r requirements.txt` を使用してください）

3. プロジェクトルートに .env を作成（任意）
   - 自動読み込みはデフォルトで有効。OS 環境変数 > .env.local > .env の順で読み込みされます。
   - 自動ロードを無効にする場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 主要な環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API を使う場合は必須
   - KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")。デフォルトは development。
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）で通知する場合
   - その他（任意で上書き可能）
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (paper_trading の約定モード: instant|partial|never|reject)
     - PID_FILE_PATH (デフォルト: data/execution.pid)
     - KILL_FLAG_PATH (デフォルト: data/kill.flag)
     - MONITOR_POLL_INTERVAL (監視ループ間隔秒、デフォルト 60)

5. データディレクトリ
   - デフォルトの DB 等は `data/` 以下に作成されます。必要に応じて事前にディレクトリやファイルの権限を調整してください。

---

## 使い方（実行例）

- ExecutionEngine を起動（本番/開発）
  - 通常: KABUSYS_ENV によって動作が変わります。
  - 例:
    - 本番モード（live）:
      - export KABUSYS_ENV=live
      - python src/kabusys/run_execution.py
    - Paper trading（API ではなく MockBroker を使い、data/paper_trading.db に記録）:
      - export KABUSYS_ENV=paper_trading
      - python src/kabusys/run_execution.py

- Monitoring のポーリングループ開始
  - python src/kabusys/run_monitoring.py
  - ポーリング間隔を環境変数で変更:
    - export MONITOR_POLL_INTERVAL=30  # 30秒間隔
  - 監視は常に本番の sqlite_path を使用（監視ログは本番 DB を参照する点に注意）

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必要。
  - モジュール API を呼び出して使用:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - 両関数とも DuckDB 接続と target_date を引数に取り、DB に結果を書き込みます。

- kill.flag 操作
  - KillSwitch は条件に応じて `data/kill.flag` を作成します。ExecutionEngine 側がこのファイルの存在を検出してシャットダウンする設計です。
  - Clear（起動時のクリーンアップ）:
    - KillSwitch.clear() を呼ぶ、あるいは手動でファイル削除: rm data/kill.flag

---

## 動作上の注意点 / 実装上のポイント

- Settings の自動 .env 読み込み
  - プロジェクトルートは .git または pyproject.toml を基準に探索します。見つからない場合は自動ロードをスキップします。
  - OS 側の環境変数は保護され、.env.local の override をさせることが可能です。

- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録して本番データと分離します。

- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び、psutil を使ってプロセス優先度(Windows/HIGH、POSIX の nice 値) を設定しようとします。権限不足時は警告を出してスキップします。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等的にテーブル作成・簡易マイグレーション（列追加）を行います。起動時に自動実行されます。

- OpenAI 呼び出し
  - AI 関連は OpenAI SDK を利用し、429・ネットワーク断・5xx に対して指数バックオフでリトライします。APIキー必須。
  - レスポンス検証、スコアのクリップ、部分書き込み（部分失敗時に既存データを保持）等のフェイルセーフ処理を備えています。

- AlertManager（LINE）
  - token / user_id が未設定の場合は送信をスキップしログのみ出力します。クールダウン機能あり。

---

## コード／ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールと役割の概観です（一部抜粋）。

- src/
  - kabusys/
    - __init__.py                    — パッケージ定義
    - config.py                      — 環境変数 / .env 読み込み / Settings クラス
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
    - portfolio/
      - portfolio_builder.py         — 候補選定 / 等重・スコア重み計算
      - position_sizing.py           — 株数計算・投資上限・スケール調整
      - risk_adjustment.py           — セクターキャップ・レジーム乗数
      - __init__.py
    - monitoring/
      - monitoring_db.py             — SQLite テーブル作成 / MonitoringDB クラス
      - system_monitor.py            — CPU/MEM/Disk / PID / データ鮮度監視
      - trade_monitor.py             — 注文滞留・約定異常監視
      - risk_monitor.py              — ドローダウン / ポジション上限監視
      - monitoring_engine.py         — 監視ループの束ね役
      - kill_switch.py               — kill.flag 書き込みロジック
      - alert_manager.py             — LINE 通知
      - streamlit_dashboard.py       — Streamlit ベースの監視ダッシュボード
      - __init__.py
    - research/
      - factor_research.py           — momentum/value/volatility 計算（DuckDB）
      - feature_exploration.py       — 将来リターン / IC / 統計サマリ
      - __init__.py
    - ai/
      - news_nlp.py                  — ニュース NLP（OpenAI）スコアリング
      - regime_detector.py           — マクロ + MA200 でレジーム判定（OpenAI）
      - __init__.py
    - utils/
      - process_priority.py          — psutil を使った優先度 / CPU affinity ユーティリティ
      - __init__.py
    - execution/                      — 注文実行周り（OrderManager, Reconciler, BrokerFactory など）
      - order_manager.py
      - reconciler.py
      - order_repository.py
      - broker_factory.py
      - broker_api.py
      - order_record.py
      - ...（実装参照）
    - data/                           — データパイプライン / DuckDB 周り（別モジュール）
      - pipeline.py, stats.py 等（コード内参照）

---

## よく使うコマンドまとめ

- 実行（ExecutionEngine）
  - KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py
  - KABUSYS_ENV=live python src/kabusys/run_execution.py

- 監視（Monitoring）
  - python src/kabusys/run_monitoring.py
  - 環境変数で間隔変更: export MONITOR_POLL_INTERVAL=120

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## トラブルシューティング / Tips

- MONITOR_POLL_INTERVAL が 0 または負の値だと無効扱いになり、デフォルト 60 秒が使用されます。
- process_priority の設定は OS と権限に依存します。アクセス拒否時は警告が出て処理は継続します。
- OpenAI 呼び出しは API 制限やネットワーク問題で失敗することがあるため、ログとリトライ挙動を確認してください。失敗時はスコアを 0 にする・部分スキップするなどのフォールバックがあります。
- monitoring の DB スキーマは init_monitoring_db により自動で作成・簡易マイグレーションされます。
- Paper Trading と本番 DB は明示的に分離されるため、paper_trading を使う場合は PAPER_TRADING_SQLITE_PATH を確認してください。

---

この README はコード内のドキュメント文字列・コメントを元に生成しています。実際の運用前に各モジュールの詳細実装や周辺インフラ（ブローカー認証情報、LINE トークン、OpenAI APIキーなど）を確認し、適切なテストを行ってください。必要であれば README により詳しいセットアップ手順（依存パッケージのバージョンや systemd / supervisor 用の起動スクリプト例など）を追加できます。