KabuSys — 日本株自動売買・データ基盤ライブラリ
================================

概要
----
KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants API からのデータ取得・ETL、ニュース収集と LLM によるニュースセンチメント評価、マーケットカレンダー管理、監査ログ（オーディット）テーブルの初期化、研究用ファクター計算などを一貫して提供します。バックテストやプロダクションのデータパイプライン、戦略研究に使えるユーティリティ群を含みます。

主な特徴
--------
- J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レート制限・リトライ）
- 日次 ETL パイプライン（株価 / 財務 / カレンダーの差分取得・保存・品質チェック）
- ニュース収集（RSS）と前処理、raw_news / news_symbols への冪等保存ロジック
- OpenAI（gpt-4o-mini）を用いたニュース NLP（銘柄別センチメント）と市場レジーム判定（AI と価格指標の組合せ）
- 監査ログ（signal_events / order_requests / executions）テーブルの自動初期化ユーティリティ
- Research 用ファクター計算（モメンタム・バリュー・ボラティリティ）、特徴量探索（forward returns, IC, summary）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

動作要件（代表）
----------------
- Python 3.10+（型アノテーション等を使用）
- ライブラリ例:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / RSS / OpenAI）と、DuckDB（ローカルファイル）への書き込み権限

環境変数 / 設定
----------------
本パッケージは .env/.env.local から設定を自動ロードします（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（README 用まとめ）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live), default=development
- LOG_LEVEL — ログレベル (DEBUG/INFO/...)

セットアップ手順
--------------
1. リポジトリをクローン、またはパッケージをチェックアウト。
2. 仮想環境を作成し有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）:
   - pip install duckdb openai defusedxml
   - もしパッケージをローカルインストールするなら:
     - pip install -e .

4. .env を作成（.env.example を参考に必須キーを設定）。
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます。

使い方（代表的な例）
-------------------

- DuckDB 接続を用意して ETL を実行する（日次 ETL）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

  run_daily_etl はカレンダー、株価、財務の差分取得と品質チェックを順に実行し ETLResult を返します。

- 監査ログ DB / スキーマを初期化する:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査ログに書き込み可能
  ```

- ニュースセンチメント（銘柄別）をスコア化する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数にセットするか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("written:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA + マクロニュース）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- ユーティリティ（ファクター計算、統計）:
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
  # DuckDB の conn と target_date を渡して各種ファクターを取得できます
  ```

注意点 / 設計ポリシー（抜粋）
----------------------------
- Look-ahead バイアス回避: ニュース・AI・研究モジュールは内部で date.today() を参照せず、明示的な target_date を使用して処理します。バックテスト用途に配慮した実装です。
- 冪等性: J-Quants の保存関数やニュース保存、監査スキーマ初期化はなるべく冪等（ON CONFLICT 句など）になるよう設計されています。
- フェイルセーフ: LLM API や外部 API の失敗時は (可能な範囲で) フォールバックし、例外を上位に伝えない（処理継続）箇所があります。ログで失敗を記録します。
- 自動 .env ロード: プロジェクトルートを .git / pyproject.toml を基準に探索して .env/.env.local を読みます。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。

ディレクトリ構成（要約）
----------------------
（src/kabusys を起点に抜粋）

- kabusys/
  - __init__.py                — パッケージ初期化、バージョン定義
  - config.py                  — 環境変数・設定読み込みロジック（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースを LLM でスコア化して ai_scores に書き込む
    - regime_detector.py       — マクロセンチメント + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult の再エクスポート
    - calendar_management.py   — マーケットカレンダー管理と営業日ユーティリティ
    - news_collector.py        — RSS 取得 / 前処理 / 保存ロジック
    - quality.py               — データ品質チェック
    - stats.py                 — 汎用統計ユーティリティ（zscore 等）
    - audit.py                 — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py       — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py   — forward returns / IC / summary / rank
  - ai, data, research 以下にはさらに多くの補助関数や実装があります（上記は主要ファイル）

開発・テストのヒント
--------------------
- テスト・CI で環境変数の自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants API 呼び出しは外部ネットワーク呼び出しを含むため、単体テストでは各モジュールの _call_openai_api や jquants_client._request をモックする設計になっています（コード中にその旨のコメントあり）。
- DuckDB の in-memory モード ":memory:" を使うと一時 DB でのテストが容易です（例: init_audit_db(":memory:")）。

ライセンス / 貢献
-----------------
（このリポジトリにライセンスファイルがあればその内容をここに追記してください）

最後に
------
この README はコードベース（src/kabusys 以下）に含まれる主な機能と利用法をまとめたものです。より詳細な設計仕様は各モジュールの docstring（ファイル先頭）を参照してください。質問や補足の希望があれば教えてください。