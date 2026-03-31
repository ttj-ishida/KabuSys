# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリ。J-Quants / kabuステーション / OpenAI 等を組み合わせて、データ収集（ETL）・品質チェック・ニュース NLP・市場レジーム判定・研究用ファクター計算・監査ログ管理などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（日時は明示的引数で渡す）
- DuckDB を主データストアに利用し、ETL は差分取得＋冪等保存
- 外部 API 呼び出しはリトライ・レート制御・フォールバックを組み込む
- OpenAI 呼び出しは JSON mode を利用して厳密なレスポンスパースを行う

---

## 機能一覧

- 設定管理
  - .env / .env.local から自動読み込み（プロジェクトルート検出）
  - 必須環境変数の明示的チェック（settings オブジェクト）
- データ取得 / ETL（kabusys.data）
  - J-Quants API から株価（OHLCV）、財務、カレンダー等を差分取得（rate limiting / retry / token refresh）
  - ETL メイン: run_daily_etl（市場カレンダー / 株価 / 財務 / 品質チェック）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS）と前処理、raw_news への保存ロジック
  - 監査ログテーブルの初期化 / 管理（signal_events / order_requests / executions）
- AI（kabusys.ai）
  - news_nlp.score_news: ニュースを銘柄ごとにまとめ、OpenAI によりセンチメントスコアを生成し ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースセンチメントを合成して market_regime に書き込み
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 汎用統計ユーティリティ（kabusys.data.stats）

---

## セットアップ手順

前提
- Python 3.10+（型ヒントに Union 型マイナスの表記を使用）
- DuckDB（Python パッケージ）
- OpenAI SDK（openai パッケージ）
- defusedxml（RSS パースの安全化）
- ネットワークアクセス（J-Quants / OpenAI / 各 RSS ソース）

1. リポジトリをチェックアウトし、パッケージをインストール
   ```
   git clone <リポジトリURL>
   cd <repo>
   pip install -e .
   # 依存が明示されていない場合は少なくとも以下をインストールしてください
   pip install duckdb openai defusedxml
   ```

2. 環境変数を設定（.env / .env.local をプロジェクトルートに配置）
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL 認証）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注等）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 投稿先チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
   - オプション
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env 読み込みを無効化
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. （任意）監査ログ用 DB の初期化
   - 監査用に別 DB を作る場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主要な API とサンプル）

基本的に DuckDB の接続を作り、各モジュール関数に接続と日付を渡して実行します。

- 設定の参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 未設定なら ValueError
  print(settings.duckdb_path)
  ```

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI の API キーが必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))  # returns 書き込んだ銘柄数
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究系（ファクター計算等）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize
  from datetime import date

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 監査スキーマの初期化（既存の接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注意点
- OpenAI や J-Quants の呼び出しは外部ネットワークを伴うため、API キー・トークンが正しくセットされている必要があります。
- ETL は差分取得＋バックフィルを行うため、最初のフルロード時は時間がかかることがあります。

---

## 環境変数と設定（まとめ）

主に必要となる環境変数：
- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (ai の実行に必須)
- KABU_API_PASSWORD (発注等に必須)
- SLACK_BOT_TOKEN (通知用)
- SLACK_CHANNEL_ID (通知先)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env 読み込み無効化）

設定値は kabusys.config.settings からアクセスできます。

---

## ディレクトリ構成（主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          — ニュース NLP スコアリング
    - regime_detector.py   — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（fetch & save）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py    — RSS 取得・前処理
    - quality.py           — データ品質チェック
    - stats.py             — 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py             — 監査ログテーブル 初期化 / DB 作成
  - research/
    - __init__.py
    - factor_research.py   — Momentum / Value / Volatility 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - monitoring/ (エクスポート対象に含まれるが詳細実装は省略されている可能性あり)

---

## テスト・デバッグのヒント

- 自動 .env 読み込みを一時的に無効化する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しはテスト時にモック可能（モジュール内の _call_openai_api を patch）
- DuckDB は ":memory:" を指定してインメモリ DB を利用可能
- ログレベルは LOG_LEVEL または settings.log_level で制御

---

## ライセンス・貢献

（ここにはプロジェクトのライセンス表記やコントリビュート方法を記載してください）

---

README に記載が必要な追加情報（実行例スクリプト、CI/テスト手順、依存関係の詳細など）があれば教えてください。必要に応じて README を拡張します。