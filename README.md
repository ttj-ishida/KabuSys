# KabuSys

日本株向けのデータプラットフォーム＋リサーチ／自動売買の共通ライブラリ群です。  
DuckDB をデータレイヤに、J-Quants/API をデータソース、OpenAI（gpt-4o-mini 等）をニュース解析に利用する想定のモジュール群を含みます。

主な用途例:
- J-Quants からの日次ETL（株価・財務・カレンダー）
- ニュースの収集・LLM による銘柄別センチメント付与（ai_score）
- 市場レジーム判定（MA + マクロニュースセンチメント）
- ファクター計算 / 特徴量探索 / IC 計測（研究用途）
- 監査ログ（signal → order → execution の追跡）スキーマ初期化

---

## 主な機能一覧

- 環境変数・設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須設定を取り出すユーティリティ（settings）

- データプラットフォーム（kabusys.data）
  - J-Quants API クライアント（取得・ページネーション・リトライ・レートリミット）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days、夜間更新ジョブ）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS の正規化・SSRF 対策・前処理）
  - 監査ログ用スキーマ初期化（監査テーブル + インデックス / init_audit_db）

- ニュースNLP（kabusys.ai）
  - 銘柄ごとのニュースセンチメント計算（score_news）
  - マクロニュース + ETF MA による市場レジーム判定（score_regime）
  - OpenAI 呼び出しはリトライやフェイルセーフを内蔵

- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - z-score 正規化ユーティリティ（kabusys.data.stats）

---

## 必要条件（推奨）

- Python 3.10+
- パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- J-Quants のリフレッシュトークン（データ取得用）
- OpenAI API キー（ニュース NLP / レジーム判定用）
- ネットワーク接続（J-Quants / RSS / OpenAI）

※ requirements.txt はこのリポジトリに含まれていない想定です。実行環境に合わせて上記パッケージをインストールしてください。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン（src 配置の標準的な Python パッケージ構成を想定）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 必要パッケージをインストール
   - 最小例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発モードでパッケージをインストール（setup.cfg/pyproject.toml がある場合）
     ```
     pip install -e .
     ```

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成すると自動で読み込まれます。
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知設定（オプション）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PAPER_FILL_MODE: paper trading の fill モード（instant|partial|never|reject）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   例の .env（最低限）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データディレクトリ作成
   ```
   mkdir -p data
   ```

---

## 基本的な使い方（コード例）

下記は Python REPL / スクリプトから呼ぶ例です。全て look-ahead bias を避けるため関数に target_date を明示的に渡す設計になっています。

- DuckDB 接続を作って ETL を実行する（日次ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を算出して ai_scores テーブルへ書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定を実行（ETF 1321 の MA200 とマクロニュースを合成）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用の DuckDB を初期化して接続を得る
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- RSS を取得する（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意:
- OpenAI 呼び出し部分は API エラーに対して内部でリトライやフェイルセーフ（スコア=0）を実装していますが、API キーは必須です。
- ETL 実行前に DuckDB スキーマ（raw_prices, raw_financials, market_calendar など）が整備されている必要があります。ETL を最初に実行するときはスキーマを用意するユーティリティを実装／提供してください（本コードベースには schema 初期化の一部（audit 用）は含まれます）。

---

## 主要モジュールと責務

- kabusys.config
  - 環境変数の読み込み・検証・自動ロード処理
- kabusys.data
  - jquants_client.py: J-Quants API とのやり取り（取得 / 保存用関数）
  - pipeline.py / etl.py: 日次ETL の Orchestration と ETLResult
  - calendar_management.py: マーケットカレンダー管理・営業日判定
  - news_collector.py: RSS 取得・前処理・ID 正規化（SSRF 対策あり）
  - quality.py: データ品質チェック（欠損・スパイク・重複・未来日）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログスキーマ定義・初期化
- kabusys.ai
  - news_nlp.py: 銘柄別ニューススコア算出（バッチ・JSON Mode + バリデーション）
  - regime_detector.py: ETF MA とマクロニュース（LLM）を合成した市場レジーム判定
- kabusys.research
  - factor_research.py: momentum / value / volatility などのファクター算出
  - feature_exploration.py: forward returns / IC / rank / summary

---

## ディレクトリ構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py
      calendar_management.py
      news_collector.py
      quality.py
      stats.py
      audit.py
      etl.py
      (その他)
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/...
    research/__init__.py
    (その他モジュール)

※ 上記はリポジトリ内の主要ファイルを抜粋したものです。

---

## 注意点 / 設計上のポイント

- Look-ahead bias 対策が随所に実装されています（関数は target_date を受け取り、future を参照しない設計）。
- OpenAI 呼び出しは JSON Mode（厳密な JSON を期待）で行い、パース失敗時はフェイルセーフでスコア 0 を返す等の堅牢化があります。
- J-Quants クライアントはレートリミット順守（固定間隔スロットリング）・トークン自動リフレッシュ・ページネーション対応・リトライ（指数バックオフ）を備えます。
- news_collector は SSRF・XML Bomb 対策（defusedxml、ホスト検査、応答サイズ制限）を備えています。
- DuckDB 側に保存する際は冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を意識した実装になっています。

---

## よくある運用コマンド例

- ETL バッチを cron / systemd タスクで日次実行する（例: Python スクリプトを呼ぶ）
- news_nlp と regime_detector は ETL 後に別ジョブとして実行し、同日データを用いる（target_date を ETL と合わせる）
- 監査ログ DB は別ファイル（例 data/audit.duckdb）で分離して運用可能

---

## 開発・拡張のヒント

- tests を追加する際は .env の自動ロードを妨げないよう KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用するかテスト用環境変数を注入してください。
- OpenAI 呼び出し部分は内部で _call_openai_api を別ファイルに抽出してモックしやすい構造になっています。ユニットテストではモック注入で外部APIアクセスを避けてください。
- DuckDB のバージョン・SQL の微妙な挙動（executemany の空リスト等）に注意してテストしてください。

---

必要であれば、README に含める実行スクリプト例（CLI 用の entrypoint）や、初期スキーマの作成 SQL、推奨 requirements.txt を作成するサポートもできます。どの部分を詳しく追加したいか教えてください。