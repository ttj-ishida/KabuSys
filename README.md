# KabuSys

日本株向けの自動売買システム（KabuSys）のソースコード説明と利用手順書です。  
本リポジトリは取引実行（Execution Engine）、監視（Monitoring）、ポートフォリオ構築、リサーチ用ユーティリティ、AIベースのニュース解析などのコンポーネントで構成されています。

---

## プロジェクト概要

KabuSys は日本株自動売買のための実験／運用フレームワークです。主な目的は次の通りです。

- シグナルからブローカーへ発注し、注文ライフサイクルを管理する ExecutionEngine
- システム稼働状況や注文件数、レイテンシなどを記録・監視する Monitoring
- ポートフォリオ構築（候補選定、重み算出、株数算出）、リスク制御ロジック
- DuckDB を用いたファクター計算・リサーチ機能（ファクター計算、IC 計算等）
- OpenAI を用いたニュースセンチメント分析・市場レジーム判定（AI モジュール）
- Paper Trading 向けの検証ツール（レポート生成、専用 DB など）
- Streamlit ベースの監視ダッシュボード

設計上のポイント：
- DB は SQLite（監視用 / paper_trading 用）と DuckDB（時系列データ・ファクター計算用）を併用
- 設定は環境変数（.env）で管理。Settings クラス経由でアクセス
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離

---

## 主な機能一覧

- Execution
  - 発注（OrderManager）、注文状態管理、リコンシリエーション（Reconciler）
  - Broker クライアントの抽象化（実ブローカー / モック切り替え）
  - RiskManager による発注制約チェック（ポジション上限、利用率など）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク監視、プロセス PID チェック、データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の検出とログ記録
  - KillSwitch：条件に応じて停止フラグを書き込み ExecutionEngine を停止
  - AlertManager：LINE Push による通知（任意）
  - Streamlit ダッシュボード（read-only 接続で監視情報表示）
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - news_nlp：OpenAI（gpt-4o-mini）を使ったニュースセンチメント集計 → ai_scores へ書込み
  - regime_detector：ETF（1321）MA とマクロニュースを合成して市場レジーム判定
- Tools
  - paper_verification_report：Paper Trading DB から各種指標（稼働率、成功率、レイテンシ等）を集計してレポート出力

---

## 必要要件（基本）

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準で Python に同梱）
- ネットワーク接続（OpenAI / LINE API / ブローカー API 利用時）

requirements.txt がない場合は上記を pip install してください。例:
```
python -m pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   ※ requirements.txt がない場合は上記の必要ライブラリを個別にインストールしてください。

3. データディレクトリ作成（デフォルト）
   ```
   mkdir -p data
   ```

4. 環境変数 (.env) を準備
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   主要な環境変数例（最低限のものを記載）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要な機能がある場合）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（ライブ運用時）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
   - LINE_CHANNEL_ACCESS_TOKEN: LINE Push 用トークン（アラート送信時）
   - LINE_USER_ID: LINE ユーザ ID（アラート送信時）
   - KABUSYS_ENV: 起動環境（development / paper_trading / live） デフォルト: development
   - PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject） デフォルト: instant
   - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite パス（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

5. DB（初期化）は起動時に自動で作成・マイグレーションされます（監視テーブル等は init_monitoring_db によって）。特別な初期化手順は不要です。

---

## 使い方（起動／主要コマンド）

- ExecutionEngine を起動（実行）
  - 通常実行（デフォルトの SQLite / DuckDB パスを使用）
    ```
    python -m kabusys.run_execution
    ```
  - Paper Trading で起動する場合（環境変数を設定）
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実行中は data/execution.pid に PID が書き込まれます。停止は stop flag（data/stop_requested.flag）を作るか、KillSwitch による data/kill.flag が作成されると停止処理が走ります。

- Monitoring を起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変えたい場合:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は環境にかかわらず（KABUSYS_ENV に依らず）本番の sqlite_path を使用します。

- Streamlit ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - ダッシュボードは DB を read-only モードで開きます。MonitoringEngine がデータを書き込んでいる必要があります。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
  - オプション `--from`, `--to` は YYYY-MM-DD 形式。`--db` を省略すると環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルトを使用します。

- AI モジュール（ニューススコアリング / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - news_nlp.score_news / regime_detector.score_regime を呼び出すと DuckDB 内の raw_news / prices_daily 等を参照して ai_scores / market_regime を更新します。
  - 例（スクリプトから呼ぶ、または管理用 CLI を用意する想定）:
    ```
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    import duckdb, os

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key=os.environ["OPENAI_API_KEY"])
    ```

- 強制停止／フラグ操作
  - 手動で ExecutionEngine を停止したい場合:
    - data/stop_requested.flag を作成すると run_execution の起動ループが検出して停止します（daemon thread 停止）。
    - KillSwitch が評価されると data/kill.flag が書かれ、外部からも停止を促せます。
  - kill.flag の削除・クリアは KillSwitch.clear() または手動削除で行います。

---

## 重要な設定（主な環境変数）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
- KABU_API_PASSWORD: Kabu API パスワード
- OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート送信に必要
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading のモック約定振る舞い（instant/partial/never/reject）

Settings クラス（src/kabusys/config.py）で各値の取得と検証を行っています。必須の値が欠けていると起動時に例外となる箇所があります（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は一部機能で必須）。

---

## ディレクトリ構成（主要ファイル）

```
src/kabusys/
├─ __init__.py
├─ config.py                  # 環境変数 / 設定管理
├─ run_execution.py           # ExecutionEngine 起動スクリプト
├─ run_monitoring.py          # SystemMonitor 起動スクリプト
├─ tools/
│  ├─ __init__.py
│  └─ paper_verification_report.py  # Paper Trading 検証レポート生成
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py             # ニュース NLP スコアリング（OpenAI）
│  └─ regime_detector.py      # 市場レジーム判定（MA + マクロセンチメント）
├─ monitoring/
│  ├─ __init__.py
│  ├─ monitoring_db.py        # SQLite を使った監視ログ永続化層
│  ├─ system_monitor.py       # システム / データ鮮度監視
│  ├─ trade_monitor.py        # 注文滞留・約定異常監視
│  ├─ risk_monitor.py         # ドローダウン・ポジション上限監視
│  ├─ kill_switch.py          # kill.flag 管理
│  ├─ alert_manager.py        # LINE Push 通知
│  ├─ monitoring_engine.py    # 複数監視の統合ポーリング
│  └─ streamlit_dashboard.py  # Streamlit ダッシュボード
├─ execution/
│  ├─ reconciler.py           # 起動時の注文 / ポジションの再同期
│  ├─ order_manager.py        # 発注 API の上位ラッパ
│  └─ ...                     # （その他 OrderRepository 等）
├─ portfolio/
│  ├─ __init__.py
│  ├─ portfolio_builder.py    # 候補選定、重み計算
│  ├─ position_sizing.py      # 株数算出、資金配分・スケーリング
│  └─ risk_adjustment.py      # セクターキャップ、レジーム乗数
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py      # ファクター計算（momentum/volatility/value）
│  └─ feature_exploration.py  # 将来リターン、IC、統計サマリ
└─ utils/
   ├─ __init__.py
   └─ process_priority.py     # プロセス優先度 / CPU affinity 設定ユーティリティ
```

（上記は主要モジュールの抜粋です。execution 以下にブローカー実装や order_repository 等、data モジュールにデータ pipeline / stats 等が存在します。）

---

## 開発・運用上の注意点

- Python バージョンは 3.10 以上が想定（Union 型と新しい構文を使用）。
- DuckDB 用の SQL は 現在のテーブルスキーマに依存するため、データ投入順やスキーマの変更に注意してください。
- OpenAI 呼び出しは費用が発生します。API キーの管理・レート制限に注意してください。news_nlp と regime_detector はリトライ・フェイルセーフの実装あり（失敗時はスコアを 0 相当で続行）。
- Paper Trading は本番 DB と分離しています。KABUSYS_ENV=paper_trading を利用してください。
- 監視は data/stop_requested.flag, data/kill.flag, data/execution.pid 等のフラグ／PID ファイルでプロセス間連携を行います。これらの場所は Settings で上書き可能です。

---

## トラブルシューティング（代表例）

- DB が見つからない / 読み込みエラー:
  - パスが正しいか（デフォルト: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb）確認してください。
- OpenAI 呼び出しが失敗する:
  - OPENAI_API_KEY が設定されているか、料金設定やネットワークを確認してください。
- LINE 通知が送れない:
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が正しいか、LINE Messaging API の設定を確認してください。
- 起動時に環境変数が読み込まれない:
  - 自動 .env ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。自動ロードを無効化している場合は手動で環境変数を設定してください。

---

必要に応じて README を拡張します（例: requirements.txt、.env.example のテンプレート、デプロイ手順、CI 設定など）。特定のセクション（Docker 化、テスト手順、詳細な API ドキュメント等）が必要であれば指示してください。