# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants API からのデータ取得（ETL）、ニュース収集・NLP（OpenAI）によるセンチメント評価、マーケットカレンダー管理、研究用ファクター計算、監査ログ（オーダー・約定トレース）など、トレーディングシステムに必要な主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPXカレンダー取得（ページネーション・リトライ・レート制御）
  - DuckDB への冪等保存（ON CONFLICT / upsert）
- ETL パイプライン
  - 差分更新・バックフィル、品質チェック（欠損・スパイク・重複・日付整合性）
  - 日次 ETL の統合エントリポイント（run_daily_etl）
- ニュース収集・NLP（OpenAI）
  - RSS からニュース収集（SSRF / Gzip / トラッキングパラメータ除去対策）
  - ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント算出（score_news）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（score_regime）
- 監査ログ（Audit）
  - signal → order_request → execution のトレースが可能なテーブル定義・初期化ユーティリティ
- 研究用モジュール
  - ファクター計算（モメンタム・バリュー・ボラティリティ）、将来リターン計算、IC（Information Coefficient）、統計サマリ、Z-score 正規化
- カレンダー管理
  - JPX カレンダー同期、営業日判定 / 前後営業日計算、get_trading_days など
- 設定管理
  - .env / .env.local / OS 環境変数を自動で読み込む（プロジェクトルート検出）  
    必要に応じて自動ロードを無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（抜粋）
  - duckdb
  - openai (v1 系 API client を想定：OpenAI クラスを利用)
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS, OpenAI）

実際の依存関係はプロジェクトの setup / pyproject に合わせてください。最低限以下をインストールしておくと動作検証できます:

pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

---

## 環境変数

主に以下を設定する必要があります（用途別に抜粋）。

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション（発注系）
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- OpenAI
  - OPENAI_API_KEY (score_news / score_regime を使う際に必要)
- Slack 通知（モジュールが使用する場合）
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- システム設定
  - KABUSYS_ENV (development | paper_trading | live) - デフォルト: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) - デフォルト: INFO
  - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
  - SQLITE_PATH: デフォルト `data/monitoring.db`

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- OS 環境変数が優先されます。`.env.local` は上書き（override）されます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env）:
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=CXXXXXXX
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを利用）

4. パッケージを編集可能モードでインストール（任意）
   pip install -e .

5. 環境変数を設定
   - .env/.env.local をプロジェクトルートに配置するか、OS 環境変数として設定する。
   - 必須変数（JQUANTS_REFRESH_TOKEN 等）を必ず設定してください。

6. DuckDB 初期化（監査ログ等を使う場合）
   Python REPL / スクリプトで:
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的なサンプル）

以下は最小限の利用例です。実行は Python スクリプト内で行ってください。

- DuckDB 接続を開いて日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアを算出して ai_scores テーブルへ保存
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scored:", count)
```

- 市場レジーム（マクロ + ETF MA）を判定して market_regime テーブルへ保存
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- RSS フィード取得（ニュース収集ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- 監査ログスキーマを初期化（オートメーション / 発注系の監査用）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

注意:
- 上記サンプルの多くは OpenAI API、J-Quants API、あるいは DB に既存のテーブルが必要です。実行前に該当環境・テーブルの準備を行ってください。
- API キーは関数引数で明示的に渡すか、環境変数 OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN を利用します。

---

## ディレクトリ構成（概要）

プロジェクトの主要モジュールツリー（src/kabusys 配下の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数・設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント & score_news
    - regime_detector.py            -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント + 保存関数
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETLResult 再エクスポート
    - news_collector.py             -- RSS 収集
    - quality.py                    -- データ品質チェック
    - stats.py                      -- 共通統計ユーティリティ（zscore_normalize）
    - calendar_management.py        -- マーケットカレンダー管理
    - audit.py                      -- 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py            -- ファクター計算
    - feature_exploration.py        -- 将来リターン / IC / サマリー
  - ai/, data/, research/ の各モジュールは相互参照がありますが、外部サーバーへの書き込み（発注等）は戦略・実行モジュールで制御してください。

---

## 設計上の注意点 / 重要事項

- Look-ahead バイアス防止:
  - 多くのモジュール（ETL / ニュース窓 / レジーム判定 等）は datetime.today() / date.today() を内部ロジックで直接参照しないよう設計されています。外部から target_date を渡すことでバックテスト等での漏れを防止します。
- フェイルセーフ:
  - OpenAI / 外部 API の一時エラー時は（多くの箇所で）フォールバック（スコア 0.0 やスキップ）して処理を継続します。重大なエラーは上位へ伝播しますが、部分失敗時の保護（既存データの保護）を意識した実装になっています。
- 冪等性:
  - J-Quants の保存関数や監査ログの初期化は冪等性を意識して実装されています（ON CONFLICT / upsert や UUID の冪等キー）。
- セキュリティ:
  - news_collector は SSRF / Gzip bomb / XML Bomb 対策を施していますが、運用環境では追加のネットワーク制限や検査を行ってください。

---

## 貢献 / 開発

- バグ報告や改善要望は Issue を立ててください。
- 開発ルール: type hints の維持、Look-ahead バイアスの回避、DB 書き込みは冪等化、テストの追加を重視してください。

---

この README はコードベースの公開インターフェースと主要な使い方をまとめた簡易ドキュメントです。詳細は各モジュールの docstring（src/kabusys/ 以下）を参照してください。