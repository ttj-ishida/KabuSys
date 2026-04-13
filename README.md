# KabuSys

日本株向け自動売買システムのコードベース README。  
このドキュメントはプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ／監視を行うためのモジュール群です。主な目的は以下のとおりです。

- 戦略に基づく銘柄選定・配分・株数決定（ポートフォリオ構築）
- 注文作成・送信・状態管理（Execution Engine）
- 起動時リコンシリエーション（再起動後の自動復旧）
- モニタリング（システム状態、注文滞留、リスク監視）、アラート通知（LINE）
- 研究向けファクター計算・特徴量解析（DuckDB を利用）
- ニュースセンチメントのAI評価（OpenAI API を利用したニュースNLP）
- 市場レジーム判定（AI + テクニカル指標の複合）
- Paper Trading 用の分離された記録・検証ツール

設計方針の特徴：
- DuckDB / SQLite を利用したデータ層（ローカルDBで完結）
- 環境変数 / .env での設定管理
- フェイルセーフを重視（API失敗時のフォールバック、部分書込みによる保護、冪等性）
- 本番と Paper Trading を明確に分離

---

## 機能一覧（主なコンポーネント）

- config
  - Settings: 環境変数読み込み、自動 .env ロード（.env, .env.local）
- execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager、OrderRepository、Reconciler（起動時リコン）
  - BrokerFactory（本番/モック切替）
  - RiskManager（投資制約・レート制限等）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor：各種監視ロジック
  - MonitoringDB：SQLite による監視ログ永続化（テーブル・マイグレーション含む）
  - KillSwitch：フラグファイルにより ExecutionEngine を停止させる仕組み
  - AlertManager：LINE Push での通知（クールダウン管理）
  - MonitoringEngine：各モニタを束ねたポーリング実行ループ
  - Streamlit ダッシュボード（read-only で監視DBを可視化）
- portfolio
  - 候補選定（select_candidates）、重み計算（equal/score）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- research
  - ファクター計算 (momentum / value / volatility)
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- ai
  - news_nlp: raw_news を集約して OpenAI でセンチメント評価 → ai_scores に格納
  - regime_detector: ma200 乖離 + マクロニュースセンチメントを合成して market_regime に書込
- tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成
- utils
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈や union 演算子 (|) を使用）
- git リポジトリ（.env 自動読み込みはプロジェクトルート検出に .git または pyproject.toml を使用）

推奨パッケージ（最低限）
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)

pip でインストール例:
```
python -m pip install duckdb psutil requests openai streamlit
```

環境変数 / .env
- プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（OS 環境変数が優先）。
- 自動ロードを無効にする場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須（kabuステーション用）
- OPENAI_API_KEY — AI 機能を使う場合は必須
- KABUSYS_ENV — 起動環境: development | paper_trading | live（デフォルト: development）
- PAPER_FILL_MODE — paper_trading 時の約定モード: instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — Paper DB（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視用設定
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager 用

例 `.env`（簡易）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

データベース初期化
- 実行スクリプトは起動時に必要なテーブルを（冪等に）作成します。手動初期化は不要です。

---

## 使い方（起動方法・主要コマンド）

基本的にモジュール単位で起動します。プロジェクトルートから以下を実行できます。

1) ExecutionEngine（発注エンジン）起動
- 通常（本番/開発）:
  ```
  python -m kabusys.run_execution
  ```
- Paper Trading（モックブローカー・分離DBを使用）
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  PaperTrading の場合、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  PAPER_FILL_MODE によってモック約定の挙動を制御できます（instant, partial, never, reject）。

2) Monitoring（監視ループ）起動
```
python -m kabusys.run_monitoring
```
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）。
- Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使います（監視は本番 DB を監視する設計）。
- 起動時に Settings.kill_flag_clear_on_start が True なら kill.flag をクリアします（ExecutionEngine 起動時のクリーンアップ設定）。

3) Streamlit ダッシュボード（監視DBの可視化）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 読み取り専用で DB を開きます。MonitoringEngine を事前に起動してデータを投入してください。

4) Paper Trading 検証レポート生成ツール
```
python -m kabusys.tools.paper_verification_report
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
- 主要チェック: 稼働率、注文成功率、送信率、P95 レイテンシ等。閾値はコード内で定義されています。

5) AI 機能（ニューススコア / レジーム判定）
- OpenAI API キー（OPENAI_API_KEY）を設定した上で、モジュールを呼び出します（スケジュールやジョブから呼び出す想定）。
- 例: news_nlp.score_news(conn, target_date, api_key=...)
- API 呼び出しはレート制限やネットワークエラーに対しリトライとフォールバックを実装しています。APIキー未設定時は例外となる箇所があります。

その他設定
- プロセス優先度: 起動スクリプトは最初に set_process_priority("high") を呼びます（psutil を利用）。権限不足や未対応 OS では警告のみ。

Kill Switch（Execution 停止）
- kill_switch は RiskMonitor の判定結果（ドローダウン超過等）により data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります。KillSwitch は冪等で既存の flag を上書きしません。

---

## 重要な挙動・注意点

- 環境分離: Paper Trading モードは DB を明確に分離（PAPER_TRADING_SQLITE_PATH）し、本番 DB を汚しません。
- .env 読み込み優先度: OS 環境 > .env.local > .env。自動読み込みを停止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- DuckDB/SQLite: 研究処理やファクター計算は DuckDB を利用（大規模データ処理向け）。監視ログは SQLite。
- AI モジュール: OpenAI API 呼び出し部分はリトライ・入力トリミング・出力バリデーションを実装済み。ただし料金やレートに注意。
- ローカル時刻依存回避: AI/レジーム判定などの処理は基本的に datetime.today()/date.today() を直接参照しないように設計（ルックアヘッドバイアス対策）。
- マイグレーション: monitoring_db.init_monitoring_db は既存 DB のカラム追加（マイグレーション）を行います（例: latency_ms, peak_value の追加）。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — Settings / .env の自動読み込みロジック
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/execution/
  - order_manager.py — 注文作成・送信ロジック（OrderManager）
  - reconciler.py — 起動時の注文/ポジションの突合（自動復旧）
  - その他（broker_api, order_repository などが存在する前提）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル定義／CRUD（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 注文滞留・約定異常価格監視
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 複数モニタを束ねる実行エンジン
  - streamlit_dashboard.py — Streamlit による監視ダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・スコアソート
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - position_sizing.py — 株数算出・aggregate cap・単元丸め

- src/kabusys/research/
  - factor_research.py — momentum/value/volatility 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC計算・統計サマリー

- src/kabusys/ai/
  - news_nlp.py — ニュース記事の集約と OpenAI でのセンチメント評価
  - regime_detector.py — MA200 とマクロニュースの混合で日次レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading DB から検証レポートを生成

- src/kabusys/utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

- data/
  - デフォルトの DB ファイル置き場（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb）

---

## 開発・運用時のヒント

- ローカルで Paper Trading を試す際は KABUSYS_ENV=paper_trading を使い、本番データを汚さないようにしてください。
- OpenAI を用いる機能は API コスト・レートに注意。ログにレートやエラーが残るため運用監視を推奨します。
- LINE 通知は channel token と user id が未設定でも動作しますが、通知は送信されません。テスト時は環境変数を空にしておくことで通知を抑止できます。
- Streamlit ダッシュボードは読み取り専用モード（URI に ?mode=ro を付与）で起動しているため、運用環境でも安全に表示できます。
- プロセス優先度変更には十分な権限が必要な場合があります。権限不足時は警告ログが出ますが処理は継続します。

---

この README はコードベース内の主要モジュールを元にまとめています。追加の使い方や運用手順（デプロイ、systemd ユニット、ログローテーション、バックアップ等）は運用環境に合わせて追記してください。必要であれば、各モジュールの具体的な API / 関数仕様や実際の起動例（systemd / supervisor 設定例）も作成します。ご希望があれば教えてください。