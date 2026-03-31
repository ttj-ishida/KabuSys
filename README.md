# KabuSys

日本株向けのデータプラットフォーム兼自動売買（バックテスト / 研究 / 実運用向け）ライブラリ群です。  
DuckDB を中心としたデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（オーダートレース）などの機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの株価（日足）・財務・上場/カレンダー情報の差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）

- ニュース収集・NLP
  - RSS 取得・前処理（SSRF 保護・トラッキングパラメータ削除）
  - OpenAI（gpt-4o-mini）の JSON Mode を用いた銘柄別ニュースセンチメント（score_news）
  - OpenAI 呼び出しのリトライ / フェイルセーフ設計（失敗時はスコア 0 フォールバック）

- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを重み付けして日次レジーム判定（score_regime）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化、統計サマリー

- 監査ログ（トレーサビリティ）
  - シグナル → 発注要求 → 約定 を UUID で辿れる監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）

- 設定管理
  - .env ファイルまたは環境変数からの設定読み込みを自動実行（パッケージルートを自動検出）
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## 前提（依存関係）

主要な依存想定（プロジェクトに合わせて pyproject.toml / requirements.txt を参照してください）:

- Python 3.9+
- duckdb
- openai（OpenAI の公式 SDK）
- defusedxml
- その他標準ライブラリ（urllib, json, datetime 等）

例（最低限のインストール例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# pip install -e . などでパッケージをインストールできる想定
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # もし用意されていれば
   # または最低限:
   pip install duckdb openai defusedxml
   ```

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に自動で `.env` / `.env.local` を読み込みます。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必要なら）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を使う場合

   その他（デフォルトあり）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース初期化（任意）
   - 監査ログ用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn は duckdb の接続オブジェクト
     ```

---

## 使い方（主要な API の例）

- DuckDB 接続の作成
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントをスコアして ai_scores に書き込む（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {written} codes")
  ```

  - OpenAI のキーを引数で渡すことも可能: score_news(conn, date, api_key="sk-...")

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

- ニュース RSS 取得（news_collector.fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

注意点:
- OpenAI 呼び出しはテスト容易性のため関数をモックして置き換えられる設計です（例: unittest.mock.patch で _call_openai_api を差し替え）。
- API 呼び出し中の一時エラーはリトライし、最終的に失敗してもシステムは例外にせずフェイルセーフで継続する実装箇所が多くあります（ニューススコアは失敗時 0.0 にフォールバック等）。

---

## 主要モジュールとディレクトリ構成

ルート: src/kabusys 以下

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（自動 .env 読み込み、Settings オブジェクト）
  - ai/
    - __init__.py (score_news をエクスポート)
    - news_nlp.py — ニュース記事の LLM センチメント集約（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + DuckDB 保存ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - news_collector.py — RSS 収集・前処理
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック
    - audit.py — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/（上記）
  - その他: strategy, execution, monitoring といったパッケージ名が __init__ で公開されています（実装は別ファイル群に依存する想定）。

（上記は主要ファイルの抜粋です。実際のプロジェクトでは tests/, scripts/, docs/ 等が存在する可能性があります。）

簡易ツリー例:
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ news_collector.py
│  ├─ quality.py
│  ├─ stats.py
│  ├─ calendar_management.py
│  └─ audit.py
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
└─ research/__init__.py
```

---

## 開発・テストのヒント

- OpenAI 呼び出し部はモック可能:
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
  テストではこれらを patch して固定レスポンスを返すことで安定したユニットテストが可能です。

- DuckDB を ":memory:" で使えばテスト用の軽量 DB が作れます:
  ```python
  import duckdb
  conn = duckdb.connect(":memory:")
  ```

- .env の自動ロードを無効にするには:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 貢献 / 問い合わせ

バグ報告や機能改善提案は Issue を立ててください。プルリクエスト歓迎です。  
設計思想や外部 API（J-Quants / OpenAI）連携の扱いに関するドキュメントはソース内の docstring を参照してください。

---

README は以上です。追加で「設定ファイルのテンプレート」や「実行スクリプトの例」を入れてほしい等あればお知らせください。