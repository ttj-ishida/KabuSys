# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
DuckDB をデータストアに、J-Quants / RSS / OpenAI（LLM）を組み合わせてデータ取得・品質管理・ニュース NLP・市場レジーム判定・研究用ファクター計算・監査ログ（発注トレーサビリティ）などを提供します。

## 特徴（機能一覧）
- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーの取得・ページネーション対応
  - レート制限・リトライ・トークン自動更新対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックの一括実行（run_daily_etl）
  - ETL 結果を ETLResult として集約
- データ品質チェック
  - 欠損（OHLC）・重複・スパイク・日付不整合チェック（run_all_checks）
- ニュース収集（RSS）
  - URL 正規化、SSRF/サイズ対策、記事ID生成、raw_news への冪等格納
- ニュース NLP（OpenAI）
  - 銘柄別センチメント集約と ai_scores への保存（score_news）
  - 冪等、チャンク・バッチ処理、リトライ、レスポンスバリデーション
- 市場レジーム判定（AI + 指標）
  - ETF (1321) の 200 日移動平均乖離 + マクロニュース LLM センチメントを合成（score_regime）
- 研究用モジュール（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Z スコア正規化
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 に至る監査テーブル（DuckDB）を定義・初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）／環境変数参照（Settings）

---

## 必要条件
- Python 3.9+（型注釈で | を使用しているため 3.10 を想定しているコードもありますが、3.9+で動作します）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants、OpenAI、RSS ソース 等）

（実際の requirements.txt はプロジェクトに合わせて用意してください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成して依存をインストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb openai defusedxml
3. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` を用意するか、OS 環境変数で設定します。
   - 自動 .env 読み込みは既定で有効。無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
4. DuckDB ファイルの保存先ディレクトリを作成（デフォルト: data/）

---

## 環境変数（主なもの）

必須のもの（実行する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン（jquants_client）
- KABU_API_PASSWORD      — kabuステーション API パスワード（発注モジュール利用時）
- SLACK_BOT_TOKEN        — Slack 通知（存在する場合）
- SLACK_CHANNEL_ID       — Slack 通知先チャンネル

オプション / デフォルト付き:
- KABUSYS_ENV            — development / paper_trading / live（デフォルト development）
- LOG_LEVEL              — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動読み込みを無効化
- OPENAI_API_KEY         — OpenAI 呼び出し（score_news / score_regime など）
- KABU_API_BASE_URL      — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite（デフォルト data/monitoring.db）

.env の例（.env.example を参考に作成してください）:
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡易サンプル）

以下は Python REPL / スクリプトから利用する例です。呼び出し前に環境変数を設定してください。

- DuckDB 接続の作成例
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュース NLP（AI）で銘柄ごとのスコアを生成（score_news）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026,3,20))  # returns 書き込んだ銘柄数

- 市場レジーム判定（score_regime）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))  # DB の market_regime テーブルへ書き込み

- 研究用ファクター計算（例: momentum）
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  mom = calc_momentum(conn, target_date=date(2026,3,20))

- 監査ログ DB を初期化
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # テーブル・インデックスを作成

- J-Quants から直接データを取得
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token がセットされている必要あり
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,1))

注意:
- OpenAI を使う関数は api_key 引数を受け取ります。None の場合は環境変数 OPENAI_API_KEY を使用します。
- date.today() を直接使わないよう設計されている関数が多いため、バックテスト等では target_date を明示的に渡してください。

---

## 自動 .env 読み込みの挙動
- プロジェクトルートはこのパッケージのファイル位置を基準に上方へ探索し、.git または pyproject.toml のあるディレクトリをプロジェクトルートとみなします。
- 読み込み順序: OS 環境変数 > .env.local > .env
- テストや外部環境で自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py — パッケージのエントリ、version
- config.py — 環境変数・設定管理（Settings）

src/kabusys/ai/
- __init__.py — ai パッケージ公開
- news_nlp.py — ニュースを LLM で評価して ai_scores へ書き込む（score_news）
- regime_detector.py — ETF の MA 乖離 + マクロニュース LLM を合成して市場レジーム判定（score_regime）

src/kabusys/data/
- __init__.py
- jquants_client.py — J-Quants API クライアント（取得・保存ロジック・レート制御）
- pipeline.py — 日次 ETL パイプライン（run_daily_etl 等）、ETLResult
- etl.py — ETLResult の再エクスポート
- calendar_management.py — マーケットカレンダー管理・営業日ユーティリティ
- news_collector.py — RSS 取得・前処理・raw_news 保存
- stats.py — 共通統計ユーティリティ（zscore_normalize）
- quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
- audit.py — 監査ログ（シグナル/発注/約定）DDL と初期化ユーティリティ

src/kabusys/research/
- __init__.py — 研究用機能の再エクスポート
- factor_research.py — momentum/value/volatility 等のファクター計算
- feature_exploration.py — 将来リターン計算、IC 計算、統計サマリー、ランク関数

その他:
- 各モジュールは DuckDB 接続を受け取り SQL + Python で処理を行う設計になっています。

---

## 開発・テストに関する注意
- 多くの関数は外部 API（J-Quants / OpenAI / RSS）に依存します。ユニットテストでは API 呼び出し箇所をモック化することを推奨します（コード中にもモック対象として設計されたヘルパー関数があります）。
- DuckDB 側の executemany に空リストを渡せないバージョン差異（DuckDB 0.10 系）を考慮した実装が多くあります。実行環境の DuckDB バージョンに注意してください。

---

README はここまでです。必要であれば以下も提供します:
- 依存関係の具体的な requirements.txt（推奨パッケージ一覧）
- より詳細な実行例（cron / Airflow ジョブ化、Slack 通知連携、kabu ステーション実装例）
- テスト用のモック/フィクスチャ例

どれが必要か教えてください。