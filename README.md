# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants と連携したデータ ETL、ニュースの NLP スコアリング、ファクタ研究、監査ログ（トレーサビリティ）、マーケットカレンダー管理、及び戦略判定補助（市場レジーム判定）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（冪等）
  - ETL の品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS フィードからニュース収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコアリング（ai_scores への書き込み）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA + マクロセンチメント合成）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー系ファクター計算
  - 将来リターン計算、IC（スピアマン順位相関）、統計サマリー、Zスコア正規化
- カレンダー管理
  - market_calendar を用いた営業日判定・前後営業日検索・カレンダーバックフィル更新
- 監査ログ（audit）
  - signal_events、order_requests、executions テーブルでシグナルから約定までを UUID でトレース可能にするスキーマ定義・初期化
- 安全設計 / テスト配慮
  - ルックアヘッドバイアス対策（datetime.today() を直接参照せず target_date を明示）
  - API 呼び出しのリトライ／フォールバック（Fail-safe）
  - 単体テストで差し替え可能な内部フック（例: OpenAI 呼び出し関数を patch 可能）

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS 取得）

（実際の requirements はプロジェクトの packaging に依存します。pip でプロジェクトの依存をインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトルートへ移動

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - 例: pip install -r requirements.txt
   - または最低限:
     - pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成するか、OS 環境変数として設定します。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DB 初期化（監査ログなど）
   - 監査ログ専用 DB を初期化する例:
     - Python REPL / スクリプト内で:
       from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")
   - DuckDB のファイル親ディレクトリがなければ自動作成されます。

---

## 必要な環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

注意: settings から必須項目は Settings プロパティで _require() によりチェックされます。欠如時は ValueError が発生します。

---

## 使い方（代表例）

以下は主要なモジュールの呼び出し例です。すべての操作は DuckDB 接続（kabusys は DuckDB を内部データ格納に使用）を引数に取ることが多く、target_date を明示してルックアヘッドバイアスを防ぐ設計になっています。

- DuckDB 接続の作成例
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（銘柄別センチメント）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
  written_count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote scores for {written_count} codes")
  ```

- 市場レジームスコアの算出
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（既存 DB に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- RSS フィード取得の簡単な例（news_collector.fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  src = DEFAULT_RSS_SOURCES["yahoo_finance"]
  articles = fetch_rss(src, source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- OpenAI 呼び出しは内部で再試行やフォールバックを行いますが、API キー未設定時は ValueError を投げます。
- 各関数は target_date を受け取ることが多く、バックテストなどで明示的に日時を固定して使用してください（現在時刻参照での自動計算を避ける設計）。

---

## 開発者向けメモ / テストフック

- 自動 env ロード
  - モジュール起動時、プロジェクトルート（.git または pyproject.toml がある親）から .env / .env.local を自動ロードします。
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- OpenAI 呼び出しの差し替え（テスト）
  - news_nlp._call_openai_api、regime_detector._call_openai_api などを unittest.mock.patch で差し替えてモック可能です。
  - ai モジュールの関数は api_key を引数で注入できるものが多く、再現性のあるテストが容易です。

- ルックアヘッド防止
  - 実装は target_date を明示的に受け取り、DB クエリは date < target_date のようにルックアヘッドが発生しない形で設計されています。バックテスト時は必ず過去データのみを使うよう心がけてください。

---

## ディレクトリ構成（主なファイル）

プロジェクトの主要なディレクトリ構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースセンチメント（OpenAI）
    - regime_detector.py         — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch/save）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETL インターフェース再エクスポート
    - news_collector.py          — RSS ニュース収集
    - calendar_management.py     — マーケットカレンダー管理
    - quality.py                 — データ品質チェック
    - stats.py                   — Zスコア等の統計ユーティリティ
    - audit.py                   — 監査ログスキーマと初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py         — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py     — 将来リターン / IC / サマリー
  - research/* その他の研究用ユーティリティ

上記はコードベース（src/kabusys/...）から抜粋した主なファイルです。

---

## 注意事項 / 運用上のポイント

- 本ライブラリには実際の売買発注（ブローカ API 呼び出し）を行うモジュールは含まれていないか、実装箇所に適切な注意書きがあります。運用環境（live）で使用する前に十分な確認を行ってください。
- シークレット（API キー等）は `.env` ファイルに平文で置くのではなく、環境変数やシークレットマネージャの利用を検討してください。
- OpenAI や J-Quants への大量リクエストはコスト／レート上限に注意してください（各クライアントにリトライ・レート制御ロジックを実装済み）。
- DuckDB の executemany は空リストを受け付けないバージョンの扱いに注意（コード内でチェック済み）。

---

もし README に追加したい内容（例: CI、license、より詳細なセットアップ手順や実運用例）があれば教えてください。README をその内容に合わせて拡張します。