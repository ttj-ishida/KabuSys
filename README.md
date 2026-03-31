# KabuSys

日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。  
J-Quants / RSS / OpenAI 等を組み合わせてデータ取得（ETL）、データ品質チェック、ニュースのAIセンチメント評価、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）機能を提供します。

---

## 概要（Project overview）

KabuSys は日本株のバックテスト／リサーチ／自動売買システムの基盤となるコンポーネント群を集めた Python パッケージです。主な役割は：

- J-Quants API を用いた株価・財務・カレンダー等の差分取得と DuckDB への保存（ETL）
- ニュース収集（RSS）とニュースごとの AI センチメント評価（OpenAI）
- マクロセンチメントとテクニカル指標を組み合わせた市場レジーム判定
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution の追跡のためのテーブル初期化）

設計方針として、Look-ahead bias を避けるため関数は内部で現在日時を参照しないことが強く意識されています（呼び出し側から target_date を渡す）。

---

## 機能一覧（Features）

- ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- J-Quants API クライアント（認証/トークンリフレッシュ、ページネーション、レートリミット、保存関数）
- ニュース収集（RSS）と前処理（URL正規化、SSRF対策、サイズ制限）
- OpenAI を使ったニュース（銘柄別）センチメント評価（score_news）
- マクロセンチメント＋MA乖離による市場レジーム判定（score_regime）
- ファクター計算（calc_momentum / calc_value / calc_volatility）
- 特徴量解析ユーティリティ（forward returns / IC / rank / summary）
- データ品質チェック（missing/spike/duplicates/date consistency）
- 監査ログ用スキーマ作成・初期化（init_audit_schema / init_audit_db）
- 環境変数管理（.env 自動読み込み、Settings クラス）

---

## 必要条件（Requirements）

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / RSS / OpenAI にアクセスする場合）

README 内のコード例は duckdb を使った接続を前提とします。

推奨のインストール例（仮想環境を使う）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください。）

---

## セットアップ手順（Setup）

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成して依存をインストール

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt    # 無ければ必要なパッケージを個別にインストール
   ```

3. 環境変数設定

   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（優先順: OS環境変数 > .env.local > .env）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用）。

   必須の環境変数（少なくとも以下を設定してください）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション等を使う場合のパスワード
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知先
   - OPENAI_API_KEY: OpenAI を使う場合（score_news / score_regime 等）
   - （任意）DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - （任意）SQLITE_PATH: 監視系 sqlite ファイル（デフォルト: data/monitoring.db）
   - （任意）KABUSYS_ENV: development / paper_trading / live
   - （任意）LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   .env の例:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベースディレクトリ作成（必要なら）

   デフォルトの DUCKDB_PATH は `data/kabusys.duckdb` なのでディレクトリを作成しておきます。

   ```bash
   mkdir -p data
   ```

---

## 使い方（Usage）

下記は代表的な利用例です。すべて Python スクリプト内で行います。

- DuckDB 接続の作成例：

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を走らせる（run_daily_etl）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースの AI センチメントを付与（score_news）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは env か api_key 引数で渡せる
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

- マーケットレジーム判定（score_regime）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB の初期化（init_audit_db / init_audit_schema）

```python
from kabusys.data.audit import init_audit_db, init_audit_schema

# 新規に監査専用ファイルを作る場合
audit_conn = init_audit_db("data/audit.duckdb")

# 既存接続に監査スキーマを追加する場合
init_audit_schema(conn, transactional=True)
```

- ファクター計算（研究用途）

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

- データ品質チェックの実行

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点：
- OpenAI 呼び出しは API レート・課金が発生します。`api_key` を明示的に渡して呼び出すか、環境変数 OPENAI_API_KEY を設定してください。関数は api_key 引数を受け取るため、テスト時にはモック注入が可能です。
- 各種 ETL / 保存関数は冪等性（ON CONFLICT DO UPDATE 等）を意識して実装されています。

---

## 環境変数の自動読み込み挙動（重要）

- プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出します（config._find_project_root）。
- 自動読み込みはデフォルトで有効。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- .env のパースはシェル風の簡易パーサ（コメント、export プレフィックス、クォート、エスケープ等を考慮）を行います。

---

## 開発 / テスト時のヒント

- テストで環境変数の自動ロードを無効にしたい場合：
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI の呼び出し部分は内部で `_call_openai_api` を使用しているため、ユニットテストでは該当関数をモックすることで外部通信を防げます（例: unittest.mock.patch）。
- RSS フェッチでは SSRF 対策（ホストのプライベート判定、リダイレクトチェック）、最大受信サイズ制限、gzip 解凍後もサイズ確認など安全対策が施されています。

---

## ディレクトリ構成（Directory structure）

以下は本パッケージの主要なファイルと説明です（src/kabusys 以下）:

- __init__.py
  - パッケージメタ（バージョン等）
- config.py
  - 環境変数読み込みと Settings クラス（アプリ設定）
- ai/
  - __init__.py
  - news_nlp.py
    - 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に書き込む（score_news）
  - regime_detector.py
    - ETF(1321) の MA 乖離とマクロニュースの LLM センチメントを合成して market_regime を書き込む（score_regime）
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（fetch / save / 認証 / rate limit / retry）
  - pipeline.py
    - ETL パイプライン（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
    - ETLResult データクラス
  - etl.py
    - ETLResult の再エクスポート
  - news_collector.py
    - RSS 取得・前処理・raw_news への保存ロジック
  - calendar_management.py
    - 市場カレンダー管理、営業日判定ユーティリティ
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py
    - 監査ログテーブル DDL / 初期化ロジック
- research/
  - __init__.py
  - factor_research.py
    - モメンタム/ボラティリティ/バリューの計算
  - feature_exploration.py
    - 将来リターン計算、IC、ランク、統計サマリー

（上記以外に strategy / execution / monitoring 等のモジュールが別リポジトリや今後の実装に含まれる想定です。）

---

## ライセンス / 貢献

この README はコードベースのドキュメント生成を目的として作成しています。実運用や商用利用の際は各 API（J-Quants / OpenAI 等）の利用規約、API キー管理、料金体系、法令順守等を必ず確認してください。

貢献・ Issue・PR はリポジトリの手順に従ってください。

---

何か特定の部分（例: ETL の詳細な実行例、.env.example の自動生成、CI 用の設定、テストケースの書き方）を README に追加したい場合は教えてください。必要に応じて例やテンプレートを追記します。