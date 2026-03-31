# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群。  
ETL（J-Quants）→ データ品質チェック → 研究（ファクター） → AI（ニュースセンチメント／市場レジーム判定） → 監査ログ（トレーサビリティ）までのワークフローを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のバックテスト／自動売買基盤を構築するためのモジュール群です。主な役割は次の通りです。

- J-Quants API からの株価／財務／カレンダー取得（ETL、ページネーション、再試行、レート制御）
- DuckDB を用いたデータ格納と品質チェック（欠損、重複、スパイク、日付整合性）
- ニュース収集（RSS）とニュースの前処理
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄単位）およびマクロセンチメント→市場レジーム判定
- 研究用ユーティリティ（ファクター算出、将来リターン、IC、Z-score 正規化など）
- 発注/約定フローの監査ログ（監査テーブル初期化・監査DB作成）

設計上の注力点：
- ルックアヘッドバイアス回避（target_date ベースの処理、現在時刻参照を避ける等）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで安全に）
- フェイルセーフ（外部 API 失敗時は可能な限り継続）
- テスト容易性（環境変数自動ロードの無効化フラグ、API 呼び出しの差し替え可能）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API ラッパ（認証、自動リフレッシュ、ページネーション、保存）
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL（prices/financials/calendar）
  - quality: データ品質チェック（欠損、スパイク、重複、日付整合性）
  - calendar_management: JPX カレンダー管理と営業日ユーティリティ
  - news_collector: RSS 取得と前処理（SSRF 対策、サイズ制限、トラッキング削除）
  - audit: 監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - stats: z-score 正規化などの統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント取得 → ai_scores へ書き込み
  - regime_detector.score_regime: ETF（1321）MA とマクロニュース（LLM）を合成して market_regime を書き込み
- research/
  - factor_research: モメンタム／バリュー／ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等
- config: 環境変数読み込み（.env 自動ロード / 必須チェック / 設定ラッパ）

---

## 前提・要件

- Python 3.10+（型アノテーションや Union | None を利用）
- 依存ライブラリ（実行環境に応じて追加）:
  - duckdb
  - openai（OpenAI クライアント）
  - defusedxml
  - その他標準ライブラリのみで多くのロジックを実装

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - または最低限: pip install duckdb openai defusedxml

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local を上書きで読み込み可）。
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env（例）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=your_openai_api_key
    KABU_API_PASSWORD=your_kabu_station_password
    KABU_API_BASE_URL=http://localhost:18080/kabusapi
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C...
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

注意:
- Settings クラスは必須環境変数が未設定だと ValueError を投げます（例: JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY を使用する機能）。
- 環境名は development / paper_trading / live のいずれかにしてください。

---

## 使い方（代表的な API）

基本的に DuckDB の接続（duckdb.connect(...)）を作成して各関数に渡します。

1) 日次 ETL 実行（J-Quants → DuckDB）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # デフォルト path は settings.duckdb_path
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント算出（ai_scores へ書き込み）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print(f"scored {count} codes")
```

3) 市場レジーム判定（market_regime へ書き込み）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

4) 監査ログ DB 初期化（別 DB として使用可能）
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# テーブル群が作成され、UTC タイムゾーンが設定されます
```

5) 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
```

6) カレンダー関連ユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

テスト時のヒント:
- OpenAI 呼び出しやネットワーク依存部分はモック可能（モジュール内の呼び出し関数を patch してください）。
- 自動 .env 読み込みを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                          # 環境変数 / .env ロード
- ai/
  - __init__.py
  - news_nlp.py                       # 銘柄ニュースの LLM スコアリング
  - regime_detector.py                # マクロ + ETF MA による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py                  # J-Quants API クライアント＋DuckDB 保存
  - pipeline.py                        # ETL パイプライン（run_daily_etl 等）
  - quality.py                         # データ品質チェック
  - calendar_management.py             # 市場カレンダー管理／営業日判定
  - news_collector.py                  # RSS 取得・前処理
  - audit.py                           # 監査ログ（DDL・初期化）
  - stats.py                           # zscore_normalize 等
  - etl.py                             # ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py                 # ファクター計算
  - feature_exploration.py             # 将来リターン、IC、summary
- ai/、data/、research/ 以下に各種補助関数と定数がまとまっています。

---

## 設計上の注意点・ベストプラクティス

- Look-ahead バイアス対策として、各処理は target_date ベースで設計されています。コード中で date.today()/datetime.now() を直接参照しない関数が多くあります（テスト／バックテスト用途に適合）。
- J-Quants の API レートリミット（120 req/min）を守るため内部で単純なスロットリングが入っています。
- DB への保存は基本的に冪等（ON CONFLICT）実装。ETL は部分失敗を考慮して構成されています。
- OpenAI 呼び出しは JSON Mode を想定しており、リトライ／フォールバックロジックを備えています。テストでは API 呼び出し箇所をモックして動作確認してください。

---

## 追加情報 / 開発

- ログレベルは環境変数 LOG_LEVEL で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 実運用（ライブ）では KABUSYS_ENV=live を指定して挙動を明確にしてください（settings.is_live 等で判定可能）。
- 監査ログは削除しない前提で設計されています。order_request_id を冪等キーとして二重発注防止に使用できます。

---

もし README に追加したい具体的なコマンド例（Docker、CI、サンプルデータの初期ロード手順）や、より詳しい API 仕様（テーブルスキーマ一覧、SQL サンプル）を希望される場合は教えてください。必要に応じて追記します。