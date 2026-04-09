# KabuSys

日本株向けのデータプラットフォームと自動売買基盤の実装ライブラリです。  
ETL（J-Quants API 経由）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム推定、ファクター研究、監査ログ（約定トレーサビリティ）など、投資システムに必要な基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計）
- DuckDB を中心としたローカルデータ管理（冪等性を意識した保存）
- 外部 API への呼び出しはリトライ／バックオフ・レートリミットを備える
- フェイルセーフ：API 失敗時は適切にフォールバックして継続する実装

---

## 機能一覧

- 環境設定管理
  - .env の自動読み込み（プロジェクトルート検出）および環境変数ラッパー（kabusys.config.settings）
- Data（データ取得・ETL）
  - J-Quants API クライアント（fetch/save + 認証管理 / レート制御 / リトライ）
  - 日次ETL パイプライン（株価・財務・市場カレンダーの差分取得）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - マーケットカレンダー管理（営業日判定 / next/prev / SQ 日判定）
  - ニュース収集（RSS → raw_news、SSRF/トラッキングパラメータ対策）
  - 監査ログ（signal/order_request/executions テーブル、初期化ユーティリティ）
- AI（ニュース NLP / 市場レジーム判定）
  - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に保存
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime を判定
  - API 呼び出しは JSON mode を利用し、レスポンス検証・リトライを実装
- Research（ファクター計算・特徴量解析）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - z-score 正規化ユーティリティ
- （戦略 / 実行 / 監視層のスケルトンを公開するエントリポイントあり）

---

## 動作環境・前提

- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS ソース, OpenAI API）

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトで pyproject.toml / requirements.txt がある場合はそれを使用してください）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成すると、自動でロードされます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨する基本的な .env キー（例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- OPENAI_API_KEY=sk-...
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_FILL_MODE=instant        # instant|partial|never|reject
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

（設定は kabusys.config.Settings で扱われ、デフォルト値やバリデーションが定義されています）

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL から呼び出す例です。いずれも duckdb の接続オブジェクトを渡して操作します。

- ETL（日次）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（Research）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- 監査ログ（監査 DB の初期化）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は監査用 DuckDB 接続（UTC タイムゾーン設定済）
```

- マーケットカレンダーの判定ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点：
- OpenAI 呼び出しは gpt-4o-mini の JSON mode を利用します。API キーの管理と利用制限に注意してください。
- J-Quants API 呼び出しは ID トークン（refresh token 経由）を使用します。`JQUANTS_REFRESH_TOKEN` を設定してください。

---

## よく使う API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path など

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, id_token=None, ...)

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token(refresh_token=None)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) など（RSS を取得して raw_news へ保存するラッパーを独自に実装可能）

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成（主なファイル）

プロジェクトの主要モジュール構造（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (etl 等から利用するクライアント/ユーティリティ群)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research, ai, data の他に strategy, execution, monitoring パッケージが公開インターフェースとして想定されています（実装はコードベースにより異なります）。

---

## 注意事項 / 運用上のポイント

- 環境変数の自動読み込み：
  - プロジェクトルート（.git または pyproject.toml を検出）から `.env` / `.env.local` を自動ロードします。OS 環境変数が優先され、.env.local は .env を上書きします。
  - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Look-ahead バイアス対策：
  - AI モジュールや ETL は内部で対象日を明示して処理する設計になっており、実行時の現在時刻を直接参照しないよう配慮しています。バックテスト用途では取得タイミングや DB の状態に注意してください。

- API 料金・レート制限：
  - OpenAI / J-Quants は API 利用料やレート制限があります。プロダクション利用時はキー管理・レート制御に十分注意してください（jquants_client は 120 req/min を守る仕組みを持ちます）。

- データベースの互換性：
  - DuckDB のバージョン差異により一部のバインド形式や executemany の扱いに注意（コード内に互換性対策あり）。

---

## 貢献・拡張

- 新しいデータソースを追加する場合：
  - data/news_collector.py の設計に従い、RSS 取得 → 前処理 → raw_news へ保存の流れを踏襲してください。

- 新しいファクター・研究指標：
  - research パッケージに関数を追加し、results をフラット dict のリストで返すように実装してください。z-score 正規化は data.stats.zscore_normalize を利用できます。

- テスト：
  - 外部 API 呼び出しはモック可能な実装になっています（内部 _call_openai_api 等は unittest.mock.patch で差し替え可能）。ユニットテストを作成して堅牢性を担保してください。

---

README は簡潔な導入ドキュメントです。実際の運用や拡張時は、個々のモジュール内の docstring（各ファイル先頭に詳細設計が記載されています）を参照してください。質問や特定の使い方サンプルが必要であれば、対象のユースケース（ETL、AI スコアリング、監査 DB 初期化など）を指定してお知らせください。