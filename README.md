# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームのコアライブラリです。  
J-Quants / JPX データを用いた ETL、ニュースの NLP スコアリング、LLM を使った市場レジーム判定、研究用ファクター計算、監査ログスキーマなどを含みます。

バージョン: 0.1.0

---

## 概要

このライブラリは以下の目的を持ちます。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集して raw_news テーブルへ格納し、OpenAI（gpt-4o-mini）で銘柄別 / マクロセンチメントを評価
- ETF（例: 1321）の移動平均乖離とマクロニュースを組み合わせて日次で市場レジーム（bull/neutral/bear）を算出
- 研究用途のファクター（モメンタム / ボラティリティ / バリュー等）計算、将来リターン・IC 計算、統計ユーティリティ
- 発注〜約定に至る監査ログ（audit テーブル群）の初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴として、ルックアヘッドバイアス防止、冪等性（ON CONFLICT DO UPDATE）、外部 API のリトライやレート制御、安全な RSS パース（defusedxml）などが考慮されています。

---

## 機能一覧

主なモジュール・機能：

- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 環境変数アクセスラッパ（settings オブジェクト）
- kabusys.data
  - jquants_client：J-Quants API クライアント（取得 / 保存 / 認証）
  - pipeline：日次 ETL 実行 run_daily_etl 等
  - news_collector：RSS 取得・前処理・raw_news 保存
  - calendar_management：JPX カレンダー管理・営業日判定
  - quality：データ品質チェック
  - audit：監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats：z-score 正規化等ユーティリティ
- kabusys.ai
  - news_nlp.score_news：銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime：マクロセンチメントと ETF MA 乖離から market_regime を作成
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件

- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクト側の pyproject.toml / requirements を参照して下さい）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

   git clone <repo-url>
   cd <repo-root>

2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. インストール

   pip install -e .          # 開発インストール（setup が用意されている前提）
   または
   pip install duckdb openai defusedxml

4. 環境変数設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` と `.env.local` を置けます。
   自動読み込みの優先順位は OS 環境 > .env.local > .env です。
   自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数:

   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - OPENAI_API_KEY (LLM 呼び出しで使用) — OpenAI API キー（score_news / score_regime 等で使用）
   - LINE_CHANNEL_ACCESS_TOKEN（任意）— 通知に使用
   - LINE_USER_ID（任意）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   例 `.env`:

   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG

---

## 使い方（基本例）

以下は Python スクリプト内から主要機能を呼び出す簡単な例です。

- DuckDB 接続を用意して ETL を走らせる

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースの NLP スコアリングを実行（OpenAI API キーが必要）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")

- 市場レジーム判定を実行

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DB を初期化する

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブル群が作成されます

- ファクター計算（研究用途）

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))

注意点:
- score_news / score_regime は OpenAI API キーが必要です（api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定）。
- run_daily_etl 等は内部で J-Quants API を呼びます。J-Quants トークン（JQUANTS_REFRESH_TOKEN）が必要です。
- ETL / API 呼び出しはネットワークや API レート制限により例外が発生する可能性があります。ログを確認してください。

---

## ディレクトリ構成

（主なファイルに限定）

src/kabusys/
- __init__.py
- config.py                       — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py                    — ニュースセンチメントスコアリング
  - regime_detector.py             — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント（取得/保存）
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - etl.py                         — ETL 便利インターフェース
  - news_collector.py              — RSS 収集
  - calendar_management.py         — 市場カレンダー管理
  - quality.py                     — データ品質チェック
  - stats.py                       — 統計ユーティリティ (z-score 等)
  - audit.py                       — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py             — ファクター計算
  - feature_exploration.py         — 将来リターン/IC/統計サマリー

ドキュメント・構成ファイル:
- pyproject.toml / setup.cfg 等（リポジトリルートに存在する想定）
- .env.example（ある場合、環境変数のサンプル）

---

## 動作上の注意 / ヒント

- Python のバージョンは 3.10 以上（型アノテーションで | を使用）。
- .env の自動読み込みはプロジェクトルートを __file__ から探索して行います。テストや別ディレクトリからの実行時に自動読み込みを無効化したい場合は、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- DuckDB のファイルパスは settings.duckdb_path で指定できます（環境変数 DUCKDB_PATH）。
- J-Quants API はレート制限を守るため内部でスロットリングを行います。大量のページネーションや複数同時実行に注意してください。
- OpenAI 呼び出しはリトライ/バックオフを導入していますが、API のコストとレート制限を考慮して運用してください。
- ETL やスコアリング処理はデータ量・ネットワークに依存するためログ出力を有効にして監視することを推奨します。

---

## 貢献 / テスト

- 単体テストや CI のセットアップファイルがある場合は、それらに従ってください。
- モジュール内のネットワーク呼び出しはモック可能な設計になっている箇所（_call_openai_api など）があり、ユニットテストで置き換えて検証できます。

---

README に記載のない詳細な API ドキュメントは各ソースコードの docstring を参照してください。ご不明点があれば使いたい用途（ETL / ニューススコア / レジーム判定 等）を教えてください。利用例やスニペットを追記します。