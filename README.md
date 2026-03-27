# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
市場データの ETL、ニュースの収集・AIによるセンチメント評価、研究用ファクター計算、監査ログ（トレーサビリティ）やカレンダー管理など、アルゴリズム取引に必要な基盤機能を提供します。

---

## 主な特徴（機能一覧）

- 環境変数・設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（無効化可能）
  - 各種 API キー／DB パスなどを Settings オブジェクトから参照可能
- データ取得・ETL
  - J-Quants API からの日足・財務・カレンダーの差分取得（ページネーション対応）
  - レートリミット制御、再試行、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT で更新）
  - 日次 ETL パイプライン（run_daily_etl）
- ニュース収集
  - RSS フィードからの安全な収集（SSRF対策、サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols 連携を想定
- ニュース NLP（OpenAI 経由）
  - 銘柄ごとのニュースをまとめて LLM に送りセンチメントスコアを ai_scores に保存（score_news）
  - マクロ記事を使った市場レジーム判定（1321 の MA200 と LLM を合成して score_regime）
  - OpenAI の JSON Mode を利用した厳格な出力パースとリトライロジック
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials ベース）
  - 将来リターン計算、IC（スピアマン）計算、Z-score 正規化等
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返却）
  - ETL 後の品質サマリ取得が可能
- 監査（Audit / Tracing）
  - signal_events, order_requests, executions テーブル定義および初期化ユーティリティ
  - 監査DB初期化関数（init_audit_db）
- マーケットカレンダー管理
  - JPX カレンダーの差分更新、営業日判定、next/prev_trading_day 等のユーティリティ

---

## セットアップ手順

前提:
- Python 3.9+（typing の新機能を利用するため）を推奨
- DuckDB、OpenAI SDK、defusedxml 等の依存が必要

1. リポジトリをクローン／チェックアウト

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージのインストール（例）

   requirements.txt がある場合はそれを利用してください。無い場合は最低限以下をインストールしてください:

   ```bash
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに合わせて他のパッケージも追加してください）

4. 環境変数設定

   プロジェクトルート（pyproject.toml または .git がある場所）に `.env` または `.env.local` を置くことで settings が自動読み込みします。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

   必要な環境変数（主要なもの）:

   - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD：kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL：（省略可）デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID：通知に使用（必須）
   - OPENAI_API_KEY：OpenAI 呼び出し用（score_news / score_regime で default）
   - DUCKDB_PATH：（省略可）デフォルト: data/kabusys.duckdb
   - SQLITE_PATH：（省略可）デフォルト: data/monitoring.db
   - KABUSYS_ENV：（省略可）development | paper_trading | live（デフォルト development）
   - LOG_LEVEL：（省略可）DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   例 .env（参考）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ初期化（監査DBの例）

   監査用 DB を作成してスキーマ初期化を行う例:

   ```python
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")
   # conn を使って以降の処理を行う
   ```

---

## 使い方（主なユースケース）

以下はコードレベルでの簡単な利用例です。実運用ではログや例外処理、トランザクション管理を適切に行ってください。

1. 日次 ETL を実行して DuckDB にデータを取り込む

   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュースのセンチメントスコアを生成（OpenAI API 必須）

   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   n_written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"{n_written} 銘柄にスコアを書き込みました")
   ```

   score_news は OpenAI API キーを引数 `api_key` で渡すか、環境変数 `OPENAI_API_KEY` を参照します。

3. 市場レジーム判定（MA200 と マクロ記事の LLM スコアを合成）

   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

4. 監査テーブル初期化（既出の init_audit_db、または既存接続に対する init_audit_schema）

   ```python
   from kabusys.data.audit import init_audit_db, init_audit_schema
   import duckdb

   # 1) 独立DBを作る
   conn = init_audit_db("data/audit.duckdb")

   # 2) 既存 DuckDB 接続にスキーマを追加したい場合
   conn2 = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn2, transactional=True)
   ```

5. RSS を取得して記事リストを得る（保存は消費側で実装）

   ```python
   from kabusys.data.news_collector import fetch_rss

   articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
   for a in articles:
       print(a["id"], a["datetime"], a["title"])
   ```

6. J-Quants API を直接使う（ID トークン取得・fetch_*）

   ```python
   from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

   token = get_id_token()  # settings.jquants_refresh_token を使用
   quotes = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
   ```

---

## 重要な設計上の注意点（抜粋）

- Look-ahead バイアス対策:
  - 日付計算やクエリは target_date を厳密に使い、datetime.today() / date.today() の無制限使用を避ける設計。
  - ニュース・レジーム判定・ETL いずれも「その時点で知りうる情報」のみで処理するよう配慮されています。
- フェイルセーフ:
  - OpenAI 呼び出しや外部 API の失敗時は、致命的に停止させずフォールバック値（例: macro_sentiment=0.0）で継続する設計。
- 冪等性:
  - DuckDB への保存は ON CONFLICT / DO UPDATE を使って冪等に行う。
- セキュリティ:
  - News Collector は SSRF 対策、応答サイズ制御、XML パースに defusedxml を使用するなど安全性に配慮。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルと説明です（現状のコードベースに基づく）:

- kabusys/
  - __init__.py: パッケージのバージョン・公開モジュール定義
  - config.py: 環境変数・設定読み込みロジック（.env 自動ロード・Settings）
  - ai/
    - __init__.py
    - news_nlp.py: ニュースセンチメント分析（score_news）
    - regime_detector.py: 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント＋DuckDB保存ロジック
    - pipeline.py: ETL パイプライン（run_daily_etl 他）
    - etl.py: ETLResult 再エクスポート
    - news_collector.py: RSS 取得・前処理ユーティリティ
    - calendar_management.py: マーケットカレンダー管理、営業日ユーティリティ
    - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py: 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py: 監査ログ用スキーマ定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py: モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py: 将来リターン・IC・統計サマリ等

---

## 開発・テスト向けメモ

- 自動 `.env` 読み込みを無効化する:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを行いません（ユニットテストで明示的に環境を制御したい場合に便利）。
- OpenAI 呼び出しやネットワーク依存処理は、モジュール内の `_call_openai_api` や `_urlopen` をモックしてテスト可能なように設計されています。
- DuckDB の executemany に対する注意:
  - 一部の実装（DuckDB 0.10 等）で executemany に空リストを渡すと問題となるため、空のときは呼ばない設計になっています。

---

## ライセンス / 貢献

この README はコードベースのドキュメント生成を目的とした概要です。実運用前にセキュリティ、法令、取引ルール（個人／組織の証券会社利用規約）を必ず確認してください。  
貢献・Issue 作成・改善提案はリポジトリの CONTRIBUTING 方針に従ってください。

---

必要であれば、さらに以下の内容を追記できます:
- .env.example の具体的なテンプレート
- DuckDB のスキーマ（テーブル定義）の初期化スクリプト
- より詳細な API 利用例や CLI ラッパーの使い方
- CI / テスト実行手順

どの追加情報が欲しいか教えてください。