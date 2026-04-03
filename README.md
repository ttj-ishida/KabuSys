# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB ベースのデータレイク、J-Quants からの ETL、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算、監査ログなどを備え、研究（research）から実運用（execution / monitoring）までのワークフローをカバーすることを目的としています。

バージョン: 0.1.0

---

## 主な機能

- データ収集・ETL
  - J-Quants API から株価日足・財務データ・JPX カレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL 実行結果を表す ETLResult
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出
  - QualityIssue を収集して呼び出し元が対応可能
- ニュース収集・前処理
  - RSS 取得（SSRF 対策、トラッキングパラメータ削除、受信サイズ制限）
  - raw_news / news_symbols への冪等保存（ID は正規化 URL の SHA-256）
- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコアを ai_scores に書き込む（バッチ、リトライ、JSON モード）
  - マクロ記事を用いた市場レジーム判定（ma200 と LLM センチメントの合成）
- リサーチ用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility など）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー
  - Z-score 正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査スキーマ定義と初期化ユーティリティ
  - order_request_id を冪等キーとして利用
- 設定管理
  - .env / .env.local / OS 環境変数から設定を読み込み（プロジェクトルートを自動検出）
  - セキュアな取り扱いと保護（OS 環境変数の上書き制御）

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成して有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必須パッケージをインストール
   現在のコードベースで使用している外部ライブラリの例:
   - duckdb
   - openai
   - defusedxml
   - （必要に応じて）requests 等

   例:
   ```
   pip install duckdb openai defusedxml
   ```

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意して pip install -e . / pip install -r requirements.txt を行ってください。

4. 環境変数（.env）を用意
   リポジトリルートに `.env` または `.env.local` を配置すると自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   重要な環境変数（例）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=your_openai_api_key

   # kabuステーション（実行系を使う場合）
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # LINE 通知（任意）
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...

   # DB パス（任意、デフォルトあり）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   補足:
   - 読み込み優先順位: OS 環境変数 > .env.local > .env
   - .env のパースはシェル風（export も可）、クォート・コメントを考慮します
   - settings オブジェクトを直接 import して利用できます（kabusys.config.settings）

---

## 基本的な使い方（コード例）

以下は主要なユースケースの最小例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると今日が対象
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア付け（OpenAI が必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み件数: {written}")
  ```

- 市場レジーム判定（ma200 + マクロセンチメント）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算・Z スコア正規化（研究用途）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.stats import zscore_normalize

  records = calc_momentum(conn, date(2026, 3, 20))
  normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
  ```

---

## 設計上の注意点 / ポイント

- Look-ahead バイアス対策
  - 多くの処理は内部で明示的な target_date を受け取り、datetime.today() や date.today() を直接参照しない設計です。バックテスト等では過去日を指定して再現性を確保してください。
- 冪等性
  - ETL・保存処理は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用しています。
- エラー耐性
  - OpenAI / J-Quants 呼び出しはリトライやフォールバック（無効時は中立値を返す等）を備え、単一障害で全処理が停止しないように設計されています。
- セキュリティ
  - RSS 取得で SSRF 防止、XML パースで defusedxml を利用、.env の保護等を考慮しています。

---

## 主要なディレクトリ構成

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（自動 .env ロード）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA200 + マクロLLM）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の再エクスポート
    - calendar_management.py        — 市場カレンダー・営業日判定
    - news_collector.py             — RSS 収集・前処理
    - quality.py                    — データ品質チェック
    - stats.py                      — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログ（監査スキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py        — 将来リターン・IC・統計サマリー
  - ai/、data/、research/ の各モジュールはさらに多くの関数を提供しています（詳細はソース参照）。

ツリー（抜粋）
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ calendar_management.py
│  ├─ news_collector.py
│  ├─ quality.py
│  ├─ stats.py
│  └─ audit.py
└─ research/
   ├─ __init__.py
   ├─ factor_research.py
   └─ feature_exploration.py
```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で必要）
- KABU_API_PASSWORD — kabu API パスワード（kabu 実行系利用時）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 実行プロセス監視設定
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — モニタリング閾値
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動で .env をロードしない（テスト用）

---

## 開発・運用上のヒント

- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境の汚染を避けると便利です。
- OpenAI の呼び出しは外部ネットワークに依存するため、ユニットテストでは _call_openai_api をモックして振る舞いを制御しています（news_nlp, regime_detector 両モジュール）。
- DuckDB のバージョン差異により executemany の挙動（空リスト不可など）があるため、save/insert 周りは空チェックを行っています。
- ETL の run_daily_etl は各ステップを個別に例外ハンドリングして継続する設計です。結果オブジェクト ETLResult から詳細を取得して運用監視に組み込んでください。
- RSS 取得では SSRF 対策や受信サイズ制限が導入されています。外部フィードを追加する場合はサイトの仕様に注意してください。

---

必要であれば README にサンプルの .env.example、CI 用の起動コマンド、または各サブモジュール（etl、news_nlp、jquants_client など）の詳細使い方を追記します。どの部分を詳しく書き足しましょうか？