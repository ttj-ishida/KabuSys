# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。J-Quants / JPX / RSS / OpenAI を組み合わせてデータ収集・品質チェック・ファクター計算・ニュース感情スコアリング・マーケットレジーム判定・監査ログを提供します。

主な設計方針:
- ルックアヘッドバイアス防止（日時参照やクエリ条件に配慮）
- DuckDB をデータ格納に使用、ETL は冪等的に実行
- 外部API呼び出しはリトライ・レート制限を備えフェイルセーフ化
- OpenAI を用いたニュースNLP/レジーム判定をサポート（JSON Mode）

---

## 機能一覧
- データETL
  - J-Quants から株価日足、財務データ、上場情報、マーケットカレンダーを差分取得・保存（jquants_client / pipeline）
  - 日次 ETL エントリポイント: run_daily_etl
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合チェック（data.quality）
- ニュース収集・前処理
  - RSS 取得、URL 正規化、テキスト前処理、raw_news への保存（news_collector）
  - SSRF / XML Bomb 等の防御を実装
- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコア算出と ai_scores への保存（ai.news_nlp.score_news）
  - マクロニュースを用いた市場レジーム判定（ai.regime_detector.score_regime）
- リサーチ / ファクター
  - Momentum / Value / Volatility 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC/ランキング/統計サマリ（research.feature_exploration）
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions 等の監査テーブル作成・初期化（data.audit）
  - init_audit_db / init_audit_schema による初期化
- ユーティリティ
  - Zスコア正規化、マーケットカレンダー操作（next_trading_day 等）、各種 helpers（data.stats / calendar_management）

---

## 必要条件
- Python 3.10 以上（型ヒントで | を使用）
- 主な Python パッケージ:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）

（プロジェクト固有の追加依存がある場合は requirements.txt を用意してください）

---

## 環境変数 (主なもの)
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールの呼び出しで使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: デフォルト DuckDB パス（data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 用（data/monitoring.db）
- KABUSYS_ENV: environment ("development", "paper_trading", "live")
- LOG_LEVEL: ログレベル ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

設定は .env / .env.local または OS 環境変数から読み込まれます（config.Settings）。

---

## インストール例
1. リポジトリをチェックアウト
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール

例:
- pip を使う場合:
  - pip install "duckdb" "openai" "defusedxml"

プロジェクトを開発モードで使う場合:
- pip install -e .

（実プロジェクトでは requirements.txt / pyproject.toml に依存を定義してください）

---

## セットアップ手順（最小構成）
1. 環境変数の用意
   - .env をプロジェクトルートに作成（.env.example を参考）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を利用する場合は OPENAI_API_KEY を設定

2. DuckDB データベース初期化（監査 DB の例）
   - Python REPL やスクリプト内で:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - あるいは既存の DuckDB 接続に対して init_audit_schema を呼ぶことも可能:
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)

3. 初回 ETL 実行（J-Quants トークンが必要）
   - Python:
     import duckdb
     from kabusys.data.pipeline import run_daily_etl
     from datetime import date
     conn = duckdb.connect("data/kabusys.duckdb")
     result = run_daily_etl(conn, target_date=date(2026,3,20))
     print(result.to_dict())

4. ニュース・NLP / レジーム判定
   - score_news / score_regime は OpenAI API キーが必要:
     from kabusys.ai.news_nlp import score_news
     from kabusys.ai.regime_detector import score_regime
     score_count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
     status = score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

---

## 使い方（主要 API 例）

- 日次 ETL を実行する:
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())

- ニュースセンチメントを計算して ai_scores に書き込む:
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う

- マーケットレジームを算出:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査DBを初期化:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- ファクター計算（例: モメンタム）:
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026,3,20))

- z-score 正規化:
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "ma200_dev"])

注: 各関数は docstring に使用上の注意（例えばルックアヘッド回避や例外の取り扱い）を記載しています。実行前にログレベルや環境を確認してください。

---

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py (パッケージのエクスポート)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースセンチメント算出、score_news)
    - regime_detector.py (マクロ+MA200 による市場レジーム判定、score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、取得/保存ユーティリティ)
    - pipeline.py (ETL パイプライン、run_daily_etl 他)
    - quality.py (データ品質チェック)
    - news_collector.py (RSS 収集・前処理)
    - calendar_management.py (マーケットカレンダー操作)
    - audit.py (監査ログテーブル定義・初期化)
    - stats.py (zscore_normalize 等)
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py (momentum/value/volatility 等)
    - feature_exploration.py (forward returns、IC、rank、summary)
  - research/*: リサーチ向けユーティリティ群

各ファイルは docstring で詳細な処理フローや設計方針を記載しています。API ごとの挙動（例: リトライ条件、フォールバック値、DBの前提スキーマ）を参照してください。

---

## 開発者向けメモ
- 自動で .env をロードする挙動:
  - プロジェクトルート (.git または pyproject.toml を探索) が見つかると .env → .env.local の順で自動読み込みを行います。
  - テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Look-ahead バイアス対策:
  - 多くの関数は target_date を受け取り、内部で datetime.today() を参照しない設計です。バックテストや逐次処理では target_date 指定に注意してください。
- 冪等性:
  - ETL の保存関数は ON CONFLICT DO UPDATE を使い冪等化してあります。
- テスト:
  - OpenAI / HTTP 呼出しはモック可能な設計（内部 _call_openai_api / _urlopen を差し替えられる）です。

---

以上が README.md の要旨です。必要ならばサンプル .env.example や requirements.txt、簡易運用スクリプト（cron 用 wrapper）も追加できます。どの部分を詳細化したいか教えてください。