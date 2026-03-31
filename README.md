# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、ファクター計算、監査ログ（オーディット）など、トレーディングシステムを構成する主要コンポーネントを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（関数内で date.today()/datetime.today() を直接参照しない）
- DuckDB を主要なデータストアとして利用し、SQL と Python を組み合わせて処理
- 外部 API 呼び出しはリトライ・レート制限等の堅牢化を実装
- ETL / 品質チェック / 監査ログは冪等（idempotent）設計

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定／無効化オプションあり）
  - 必須設定の取得ラッパー（settings オブジェクト）

- データ取得（J-Quants クライアント）
  - 日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーの取得
  - レートリミット・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 日次 ETL のエントリ（run_daily_etl）および個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 実行結果を ETLResult で集約（品質チェック・エラー情報含む）

- データ品質チェック
  - 欠損データ・重複・スパイク（急騰／急落）・日付不整合の検出
  - QualityIssue による問題報告（severity: error / warning）

- ニュース収集 / NLP
  - RSS フィード収集（SSRF 対策、URL 正規化、前処理）
  - OpenAI（gpt-4o-mini）の JSON モードを使ったニュースセンチメント分析（score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM 評価を合成）

- リサーチ用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計
  - クロスセクション Z スコア正規化ユーティリティ

- 監査（Audit）ロギング
  - signal_events / order_requests / executions などの監査テーブル定義
  - 監査 DB 初期化ユーティリティ（init_audit_db / init_audit_schema）

---

## 要件（主要パッケージ）

- Python 3.10+
- duckdb
- openai
- defusedxml

（実行環境によっては追加のパッケージや OS ライブラリが必要になる場合があります）

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## 環境変数（主なもの）

このライブラリは環境変数から各種設定を読み取ります。主なキー：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB パス（data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime にも使用）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動読み込みを無効化

設定は .env / .env.local（プロジェクトルート判定: .git または pyproject.toml）から自動で読み込まれます。OS 環境変数が優先され、.env.local は .env を上書きします。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

環境変数はコードから次のように参照できます:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

未設定の必須キーにアクセスすると ValueError が発生します。

---

## セットアップ手順（開発・実行の基本）

1. リポジトリをクローンする（pyproject.toml や .git がプロジェクトルート判定に使われます）
2. 仮想環境作成・有効化
3. 必要パッケージをインストール（上記参照）
4. .env をプロジェクトルートに作成して必須変数を設定（.env.example を参考に）
5. データベース用ディレクトリを作成（例: data/）

例:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
mkdir -p data
# .env を作成して各種トークン等を設定
```

---

## 使い方（代表的な例）

以下は主要な機能の利用例です。各関数は DuckDB 接続を受け取る設計になっています。

- DuckDB 接続と settings の取得:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（J-Quants からデータ取得・品質チェックまで一括）:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を指定しなければ今日（内部で調整）
print(result.to_dict())
```

- 個別 ETL（株価・財務・カレンダー）:
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

d = date(2026, 3, 20)
fetched, saved = run_prices_etl(conn, target_date=d)
```

- ニュースのセンチメントスコア（AI）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数で設定しておくか、api_key 引数に渡す
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"{n_written} 銘柄の AI スコアを ai_scores テーブルへ書き込みました")
```

- 市場レジーム判定（MA200 + マクロニュース）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- ファクター計算（モメンタム／ボラティリティ／バリュー）:
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date

moms = calc_momentum(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
```

- 監査ログ DB 初期化（監査専用 DB を作成）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または既存 conn にスキーマを追加する:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- RSS フィード取得（ニュース収集の低レベルユーティリティ）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
# 返される構造は NewsArticle 型: id, datetime, source, title, content, url
# 取得した記事を raw_news テーブルへ保存する処理はシステムに合わせて実装してください（save 処理は別途）
```

注:
- OpenAI API を使用する関数（score_news / score_regime）は API キーを引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / API 呼び出しはリトライやレート制御が入っていますが、運用スクリプトでは例外処理・ログの監視を行ってください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要モジュールと役割を示します（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースセンチメントの LLM スコアリング（score_news）
    - regime_detector.py
      - ETF 1321 の MA200 と マクロニュースを合成して市場レジームを判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、取得＆DuckDB 保存関数
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, ...）、ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - calendar_management.py
      - 市場カレンダーの管理、営業日判定（is_trading_day / next_trading_day / ...）
    - stats.py
      - zscore_normalize などの統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付整合性）
    - audit.py
      - 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
    - news_collector.py
      - RSS 収集・前処理ユーティリティ（SSRF 対策・URL 正規化等）
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py
      - 将来リターン計算、IC、ファクター統計、ランク変換等

---

## 運用上の注意

- 環境変数は漏洩しないよう管理してください（特に API キーやトークン）。
- DuckDB ファイルは運用環境でのバックアップ・権限管理を検討してください。
- OpenAI 呼び出しにはコストがかかります。バッチサイズや呼び出し頻度を運用に合わせて調整してください。
- ニュース収集の RSS リクエストは外部サイトに対するアクセスとなるため、SSRF 等のセキュリティ対策（本コードにも実装あり）を理解した上で運用することを推奨します。

---

もし README に含めたい追加情報（例: .env.example の具体的なテンプレート、CI / デプロイ手順、ユニットテスト実行方法など）があれば教えてください。必要に応じて追記します。