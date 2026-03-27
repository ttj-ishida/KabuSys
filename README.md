# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買の補助ライブラリです。  
J-Quants / kabuステーション / OpenAI（LLM）などと連携し、データ取得（ETL）、データ品質チェック、ニュース NLP による銘柄スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（オーダー・約定トレーサビリティ）などの機能を提供します。

---

## 主な特徴（機能一覧）

- データ ETL
  - J-Quants API から株価（日足）・財務・マーケットカレンダーを差分取得して DuckDB に保存
  - 差分取得、バックフィル、ページネーション、認証トークン自動リフレッシュ、レートリミッティングを実装
- データ品質チェック
  - 欠損値、スパイク（急騰・急落）、重複、日付不整合などの自動検出
- ニュース収集 / NLP
  - RSS からニュースを収集（SSRF 対策・トラッキング除去・前処理）
  - OpenAI（gpt-4o-mini 想定）を用いた銘柄別ニュースセンチメント（ai_scores）算出
  - マクロニュースを用いた市場レジーム判定（bull/neutral/bear）
- リサーチ（ファクター計算）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の SQL と Python）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Z-score 正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブル定義・初期化
  - 発注フローの UUID ベースのトレーサビリティを想定

---

## 動作要件 / 依存関係

- Python 3.10 以上（型ヒントに `X | Y` を利用）
- 必要な主要パッケージ（少なくとも以下をインストールしてください）
  - duckdb
  - openai
  - defusedxml

（プロジェクト固有の追加パッケージは setup / requirements による指定を想定しています）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストールします（例）:

   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトに setup.py / pyproject.toml がある場合:
   pip install -e .
   ```

3. 環境変数を設定します。プロジェクトルートに `.env`（または `.env.local`）を置くと、自動で読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須の環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
   - SLACK_CHANNEL_ID: Slack の通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI を使う場合に必要（関数呼び出しで api_key を渡すことも可能）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=abc...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB 用のデータディレクトリを作成（デフォルトは `data/`）:

   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は代表的な利用例です。各モジュールの関数は DuckDB 接続（duckdb.connect(...) が返す接続オブジェクト）を受け取ります。

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（ai_scores へ書き込み）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数から取得
print(f"scored {count} codes")
```

- 市場レジーム（マクロ + MA200）を評価して保存

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（Research）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査用 DuckDB を作成）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- RSS フィード取得（ニュース収集の一部）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意: 上記は各関数の代表的な呼び出し例です。実運用ではトランザクション管理やエラーハンドリング、ログ設定、API キー管理に注意してください。

---

## 主要モジュールと責務（ディレクトリ構成）

プロジェクトは `src/kabusys` 配下にモジュールが構成されています。主なファイルと説明は以下の通りです。

- src/kabusys/__init__.py
  - パッケージのバージョンと公開サブパッケージ定義

- src/kabusys/config.py
  - .env / 環境変数読み込み、Settings クラス（J-Quants / kabu API / Slack / DB パス / 環境設定など）

- src/kabusys/data/
  - calendar_management.py : 市場カレンダー管理、営業日判定、カレンダー ETL ジョブ
  - etl.py : ETL の公開インターフェース（ETLResult 再エクスポート）
  - pipeline.py : ETL パイプライン（run_daily_etl、各種 run_*_etl）
  - stats.py : 汎用統計ユーティリティ（zscore_normalize 等）
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py : 監査ログ（signal_events / order_requests / executions）と初期化関数
  - jquants_client.py : J-Quants API クライアント（fetch / save / 認証 / レート制御 / リトライ）
  - news_collector.py : RSS 収集、テキスト前処理、保存ロジック（SSRF 対策など）

- src/kabusys/ai/
  - news_nlp.py : ニュースを LLM に渡して銘柄単位のセンチメントスコアを算出し ai_scores に保存
  - regime_detector.py : マクロニュース + ETF MA200 による市場レジーム判定

- src/kabusys/research/
  - factor_research.py : Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py : 将来リターン計算、IC 計算、統計サマリー、ランク関数
  - __init__.py : 研究向け API のエクスポート

- src/kabusys/data/__init__.py
  - data サブモジュールのエクスポート（空のプレースホルダあり）

---

## 動作上の注意 / 設計方針（重要ポイント）

- Look-ahead バイアス対策
  - 多くの処理（ニュースウィンドウ、MA 計算、J-Quants の取得タイムスタンプ保存など）は未来データ参照を避ける設計になっています。
- 冪等性
  - DuckDB への保存は ON CONFLICT DO UPDATE や一意キーによる処理で冪等性を確保します。
- フェイルセーフ
  - LLM / 外部 API の失敗時は例外を上位に投げずフォールバック（0.0 やスキップ）する設計が多く、処理全体が停止しないようになっています（ただし必要に応じて呼び出し元で厳格に扱ってください）。
- テスト容易性
  - API 呼び出し部分（OpenAI / HTTP）は差し替え可能な内部関数やモックポイントを用意しています。

---

## 環境変数まとめ

少なくとも次の環境変数を設定する必要があります（必須）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)

OpenAI を使う機能を利用する場合:

- OPENAI_API_KEY (推奨 / 関数引数で上書き可)

その他オプション:
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|... , デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 （プロジェクトルートの .env 自動ロードを無効化）

---

## ロギング / モニタリング

- 各モジュールは標準 logging を使用しています。運用時は適切にログハンドラやレベルを設定してください。
- ETL と品質チェックの結果は ETLResult や QualityIssue を通じて取得できます。Slack 通知や外部モニタリングに接続することが想定されています（Slack トークンは環境変数で管理）。

---

## 貢献 / 拡張案

- 新しいニュースソース追加（DEFAULT_RSS_SOURCES）
- 追加の品質チェックや自動修正ルール
- 発注実行（kabu API）との連携モジュール（監査ログと紐づけて冪等発注を実装）
- バックテスト用のデータエクスポート / スナップショット取得ツール

---

この README はコードベースの主要機能・使い方の概要を示しています。各モジュールの詳細はソース（src/kabusys 以下の各ファイル）のドキュメント文字列を参照してください。必要であれば、具体的な実行例や運用手順（CI / cron / systemd などでの定期実行方法）について追記できます。