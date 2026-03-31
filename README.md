# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数（.env 例）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株市場向けに設計されたデータプラットフォーム兼リサーチ/トレーディング基盤ライブラリ群です。
- 主に DuckDB を用いたローカル DB、J-Quants API 経由のデータ取り込み、RSS ニュース収集と OpenAI を用いた NLP 評価、研究用ファクター計算、発注・約定の監査ログ機能などを備えます。
- バックテスト用のルックアヘッドバイアス対策や、API 呼び出しの堅牢なリトライ・レート制御、ETL の品質チェック等が実装設計に反映されています。

---

機能一覧
- 設定管理
  - .env の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（kabusys.config.settings）
- データ ETL（kabusys.data.pipeline）
  - J-Quants からの株価（日足）・財務・マーケットカレンダーの差分取得・保存
  - 日次 ETL の統合エントリ（run_daily_etl）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、SSRF・サイズ制限・トラッキングパラメータ除去、冪等保存
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリング（ai_scores へ保存）
  - バッチ・トリミング・リトライ・レスポンス検証実装
- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュース（LLM センチメント）を重み合成して市場レジームを判定
- 研究用（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman rank）計算、統計サマリー
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の監査テーブル定義・初期化
  - 監査 DB の初期化ユーティリティ（init_audit_db / init_audit_schema）
- 共通ユーティリティ
  - 統計ユーティリティ（zscore 正規化）
  - カレンダー管理（営業日判定・次/前営業日取得）

---

セットアップ手順（開発・実行環境）
前提
- Python 3.10 以上（型アノテーションの union 演算子 '|' を使用）
- Git（プロジェクトルート検出に使用）

例（仮想環境の作成とパッケージインストール）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml

   ※ 実行環境によっては追加パッケージが必要になることがあります（例: requests 等）。プロジェクト配布時に requirements.txt があればそちらを使用してください。

3. 環境変数設定
   - プロジェクトルートに .env を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数は下記「環境変数」セクション参照。

4. DuckDB ファイル作成 / スキーマ初期化
   - ETL を実行する前に利用する DuckDB に必要なテーブルを作成してください（本 README では DDL の自動作成ユーティリティは提供していません。init_audit_schema は監査テーブルを作成します）。
   - 監査用 DB 初期化例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

使い方（主要な API の例）

共通: 設定参照・DB 接続
- settings を使って既定パスを取得:
  from kabusys.config import settings
  db_path = settings.duckdb_path

- DuckDB 接続:
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

ETL（日次パイプライン）
- 日次 ETL を実行して J-Quants から差分取得と品質チェックを実行:
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  import duckdb

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

ニュース NLP スコアリング（OpenAI 必須）
- raw_news / news_symbols が DB に入っている前提:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か api_key 引数で指定

市場レジーム判定（OpenAI 必須）
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

監査テーブル初期化
  from kabusys.data.audit import init_audit_db, init_audit_schema
  conn = init_audit_db("data/audit.duckdb")  # DuckDB ファイルと監査スキーマを作成

研究用ファクター計算
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  records = calc_momentum(conn, target_date=date(2026,3,20))

ログレベル・環境
- settings.log_level で LOG_LEVEL 環境変数（DEBUG/INFO/WARNING/ERROR/CRITICAL）を検証します。
- settings.env で KABUSYS_ENV（development / paper_trading / live）を検証します。

エラーハンドリング
- AI 呼び出しや外部 API はリトライやフォールバック（失敗時は 0.0 等）を備えていますが、呼び出し側でも例外に備えてください。

---

環境変数（.env 例）
以下は本ライブラリが参照する主要な環境変数の例です。プロジェクトルートに .env を置くと自動で読み込まれます（.env.local をさらに優先して読み込み）。

必須（最低限プロダクション用途で必要）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- SLACK_BOT_TOKEN=xxx
- SLACK_CHANNEL_ID=C01234567

その他（デフォルトあり / 任意）:
- KABU_API_PASSWORD=secret  # kabuステーション API パスワード
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb  # settings.duckdb_path のデフォルト
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development / paper_trading / live
- LOG_LEVEL=INFO

自動 env ロードを無効化する（テスト等）:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡易 .env.example
- JQUANTS_REFRESH_TOKEN=
- OPENAI_API_KEY=
- SLACK_BOT_TOKEN=
- SLACK_CHANNEL_ID=
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

注意: settings は必須項目が未設定の場合 ValueError を送出します。

---

ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py                          # 環境設定・.env 自動ロード
- ai/
  - __init__.py
  - news_nlp.py                      # ニュース NPL スコアリング（score_news）
  - regime_detector.py               # 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                # J-Quants API クライアント & DuckDB 保存
  - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
  - etl.py                           # ETLResult 再エクスポート
  - calendar_management.py           # マーケットカレンダー管理
  - news_collector.py                # RSS ニュース収集
  - stats.py                         # 統計ユーティリティ（zscore_normalize）
  - quality.py                       # データ品質チェック
  - audit.py                         # 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py               # Momentum / Value / Volatility 等
  - feature_exploration.py           # 将来リターン / IC / summary / rank
- research/（その他モジュール）
- その他（strategy / execution / monitoring） が __all__ に含まれる想定

---

開発上の注意
- Look-ahead バイアス防止: 多くの関数は datetime.today() や date.today() を直接参照せず、呼び出し側が target_date を明示する設計です。バックテスト時は注意して利用してください。
- DuckDB に対する executemany に空リストを渡すとエラーになるバージョンがあるため、該当箇所は空チェック済みです（pipeline/news_nlp 等）。
- OpenAI の JSON Mode を前提にレスポンス解析を行っています。API の挙動が変わるとパース処理に影響が出る可能性があります。
- ニュース収集では SSRF 対策・レスポンスサイズ制限・XML の defusedxml 処理を実装していますが、運用時は RSS ソースを慎重に選んでください。

---

貢献・ライセンス
- 本リポジトリに対する変更は Pull Request を通じて行ってください。ユニットテスト・ドキュメントの追加を歓迎します。
- ライセンスはプロジェクト配布物の LICENSE を参照してください（本コードスニペットにはライセンス情報が含まれていません）。

---

問い合わせ
- 不具合・質問は issue を立てるか、プロジェクトの管理者に連絡してください。

以上。