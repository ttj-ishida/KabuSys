# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買ユーティリティ群です。  
DuckDB をデータストアに用いた ETL、ニュース NLP（LLM を使ったセンチメント）、市場レジーム判定、監査ログ（発注→約定のトレース）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のような目的で設計されたモジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメントスコアリング
- ETF（1321）とマクロニュースの合成による市場レジーム判定（bull / neutral / bear）
- 研究用のファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査（audit）テーブル群によるシグナル→発注→約定のトレーサビリティ

設計上の共通ポリシーとして、バックテスト時のルックアヘッドバイアスを避けるために
内部処理で現在時刻を直接参照しない、API 呼び出しはリトライやフェイルセーフを持つ等が組み込まれています。

---

## 主な機能一覧

- data
  - ETL: 日次 ETL（run_daily_etl）・個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得/保存/認証/ページング/レート制御）
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS、SSRF 対策、正規化）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - news_nlp.score_news: 銘柄別ニュースを LLM に投げて ai_scores を作成
  - regime_detector.score_regime: ETF の MA 乖離とマクロニュースセンチメントを合成して market_regime を作成
- research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算 / IC / 統計サマリ

---

## 必要な環境変数（主なもの）

アプリケーション設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効にできます。

必須（Settings にて _require が使われているもの）:
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD - kabuステーション API パスワード
- SLACK_BOT_TOKEN - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID - Slack 通知先チャンネル ID

OpenAI 関連（AI モジュール使用時）:
- OPENAI_API_KEY - OpenAI API キー（関数に api_key を渡すことも可）

その他（任意／デフォルトあり）:
- KABUSYS_ENV (development / paper_trading / live) - 実行環境（デフォルト `development`）
- LOG_LEVEL (DEBUG/INFO/...) - ログレベル（デフォルト `INFO`）
- KABUS_API_BASE_URL - kabuAPI の base URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH - 監視用 sqlite path（デフォルト `data/monitoring.db`）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 3.10+ の仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install --upgrade pip
   - 必須パッケージ（一例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt がある場合はそれを使用してください（本コードベースには明示の requirements ファイルが含まれていません）。

3. パッケージを editable インストール（開発向け）
   - pip install -e .

4. (任意) .env をプロジェクトルートに作成して必要な環境変数を設定

自動 .env 読み込み:
- パッケージロード時にプロジェクトルート（.git または pyproject.toml を起点）を探索し、`.env`→`.env.local` の順で読み込みます。
- OS 環境変数は上書きされません（`.env.local` は上書き可）。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（簡単な例）

以下は主なユースケースのサンプルコードです。実行は Python スクリプトや対話環境から行います。

- DuckDB 接続例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# conn は DuckDB 接続
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026,3,20))
print(f"scored {written} codes")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- 監査 DB 初期化（監査用 DuckDB ファイルを作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセスできます
```

- research モジュールの利用（例: momentum）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

mom = calc_momentum(conn, date(2026,3,20))
# 結果は dict のリスト: [{'date': ..., 'code': '1301', 'mom_1m': ..., ...}, ...]
```

---

## ディレクトリ構成

主要ファイル/ディレクトリの抜粋（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                  -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py              -- ニュースセンチメント取得（score_news）
    - regime_detector.py       -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py   -- 市場カレンダー管理
    - etl.py                   -- ETL インターフェース
    - pipeline.py              -- ETL パイプライン（run_daily_etl 等）
    - stats.py                 -- 統計ユーティリティ（zscore_normalize）
    - quality.py               -- 品質チェック
    - audit.py                 -- 監査テーブル定義・初期化
    - jquants_client.py        -- J-Quants API クライアント（fetch/save）
    - news_collector.py        -- RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py       -- ファクター計算
    - feature_exploration.py   -- 将来リターン / IC / 統計サマリ
  - research/*、その他 modules...
- pyproject.toml / setup.cfg 等（プロジェクトルートに存在する想定）

（実際のリポジトリでは上記以外にも補助モジュールやテストが含まれる可能性があります）

---

## 実運用・運用上の注意

- OpenAI 呼び出しには料金・レート制限があるため、実行頻度とバッチサイズに注意してください。コード中は再試行とバッチ送信の制御が実装されています。
- J-Quants API はレート制限（120 req/min）があるため、jquants_client ではレートリミッタと再試行ロジックが実装されています。
- DuckDB / ETL のトランザクションは一部関数で BEGIN/COMMIT/ROLLBACK を使って冪等性を保ちますが、呼び出し側でトランザクション管理する場合は注意してください（特に init_audit_schema の transactional オプション等）。
- テストや CI で .env の自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 開発ヒント

- テスト時は jquants_client の HTTP 呼び出しや OpenAI 呼び出しをモックしてください。モジュール内に差し替えポイント（関数ラッパーや client 注入）が用意されています。
- DuckDB はインメモリ(":memory:") やファイルベースの両方が利用できます。テスト用には ":memory:" で素早く初期化できます。
- ニュース RSS の収集では SSRF 防御や gzip の大きさチェック等が実装されています。外部サイトから取得する際は適切なソース管理を行ってください。

---

もし README に追加してほしい内容（例: API レスポンス schema、より詳細な実行例、CI 用設定、パフォーマンスチューニング項目など）があれば教えてください。