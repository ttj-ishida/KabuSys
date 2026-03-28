# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
J-Quants からのデータ ETL、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログ構築、マーケットカレンダー管理、及び OpenAI を利用したニュースセンチメント／市場レジーム判定などを提供します。

主な設計方針としては「ルックアヘッドバイアスの排除」「DuckDB によるローカルデータプラットフォーム」「API 呼び出しの頑健なリトライ・レート制御」「冪等性」を重視しています。

---

## 機能一覧

- 環境変数/設定管理（自動 .env 読み込み、保護付き上書き）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得／保存
  - 財務データ取得／保存
  - JPX マーケットカレンダー取得／保存
  - トークン自動リフレッシュ・レート制限・リトライ実装
- ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS、SSRF 対策、トラッキングパラメータ除去、正規化）
- ニュース NLP（OpenAI を利用した銘柄別センチメント、バッチ処理・JSON モード対応）
- 市場レジーム判定（ETF MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ユーティリティ（モメンタム/バリュー/ボラティリティ等のファクター計算、将来リターン、IC 計算、Z スコア正規化）
- 監査ログ（signal / order_request / execution の監査スキーマ作成、初期化、インデックス）
- マーケットカレンダー管理ユーティリティ（営業日判定、next/prev_trading_day 等）

---

## 要件

- Python 3.10 以上（タイプヒントに `|` 演算子を使用）
- 主な Python ライブラリ（プロジェクト依存は setup/pyproject で管理する想定）
  - duckdb
  - openai
  - defusedxml
  - など（HTTP/JSON 標準ライブラリベースの実装が多い）

※ requirements.txt / pyproject.toml がある場合はそれに従ってください。無い場合は少なくとも上記ライブラリをインストールしてください。

---

## 環境変数（主なもの）

以下は本プロジェクトで参照される主要な環境変数です。必須と明示されているものは設定が必要です。

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（jq クライアントで ID トークン取得に使用）

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード

- KABU_API_BASE_URL (省略可)  
  kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン

- SLACK_CHANNEL_ID (必須)  
  Slack チャンネル ID

- DUCKDB_PATH (省略可)  
  DuckDB ファイルパス。デフォルト: data/kabusys.duckdb

- SQLITE_PATH (省略可)  
  監視用 SQLite パス（デフォルト: data/monitoring.db）

- KABUSYS_ENV (省略可)  
  実行環境。許可値: development / paper_trading / live（デフォルト: development）

- LOG_LEVEL (省略可)  
  ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

- OPENAI_API_KEY (必要に応じて)  
  OpenAI を使う関数（news_nlp.score_news, regime_detector.score_regime）を呼ぶ場合に参照されます。関数呼び出し時に api_key を引数で渡すことも可能です。

自動読み込み:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` → `.env.local` の順で自動読み込みします。  
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（pyproject.toml / requirements.txt があればそれを利用）
   ```
   pip install duckdb openai defusedxml
   # または:
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成して必要な変数を設定（.env.example を参考に作成してください）。
   - または CI/実行環境の環境変数として設定。

5. DuckDB／監査 DB の初期化（任意）
   Python REPL やスクリプトから:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # またはメモリ: init_audit_db(":memory:")
   ```

---

## 使い方（代表的な例）

以下は基本的な利用例です。プロダクションではログ・エラーハンドリング・トランザクション管理を適切に追加してください。

- DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別センチメント）を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に入っているか、明示的に api_key を渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written {n_written} ai_scores")
```

- 市場レジームスコアを算出する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- RSS を収集して raw_news に保存する（news_collector には保存関数は含まれていませんが、fetch_rss を使って記事を取得できます）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- 監査テーブルの初期化（既存接続にスキーマを追加）
```python
import duckdb
from kabusys.data.audit import init_audit_schema

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

注意:
- OpenAI を使う関数は api_key 引数でキーを与えるか、環境変数 OPENAI_API_KEY を設定してください。
- ETL・保存処理は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, ai_scores 等）が事前に存在することが前提です。スキーマ作成ユーティリティは別途用意してください（本リポジトリ内に schema 初期化スクリプトがある想定）。

---

## 開発・テスト時の補足

- 自動 .env ロードを無効にする:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  単体テスト等で環境依存を避けたい場合に利用します。

- OpenAI / 外部 API 呼び出しはリトライ・バックオフを備えています。ユニットテストでは該当呼び出しをモックすることを推奨します（コード中に patch しやすい内部関数が用意されています）。

- 多くのモジュールが「datetime.today() / date.today() を直接参照しない」設計になっています。テスト時は日付を明示的に渡して determinism を保ってください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュース NLP（銘柄ごとの ai_score）
    - regime_detector.py            -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得/保存）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETL 結果型の公開
    - quality.py                    -- データ品質チェック
    - stats.py                      -- 統計ユーティリティ（z-score 等）
    - calendar_management.py        -- マーケットカレンダー管理
    - news_collector.py             -- RSS 収集・前処理（SSRF 対策等）
    - audit.py                      -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            -- モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py        -- 将来リターン/IC/統計サマリ等
  - (その他: strategy/, execution/, monitoring/ といった高レイヤーを想定)

---

## 注意事項 / 備考

- DuckDB スキーマ（テーブル定義）はこの README に含まれていません。ETL を動かす前に必要なテーブルを作成してください（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, 監査テーブル等）。
- J-Quants の API レート制限 (120 req/min) に対応した実装が含まれていますが、プロダクションの運用ではさらに運用上の制約（IP レート制限・同時ジョブ数）に注意してください。
- ニュース収集では SSRF 対策や応答サイズ制限、XML パースのセキュリティ対策（defusedxml）を実装しています。外部フィードの信頼性や文字コードに起因する処理は運用に応じて追加検証してください。
- OpenAI（LLM）呼び出しは JSON Mode を利用する想定でレスポンスの厳格な解析・バリデーションをしています。API の挙動変化に備えてエラーハンドリングを確認してください。

---

必要であれば、README にサンプルスキーマ（DDL）、CI 用の起動例、または各モジュールのより詳しい利用例（ETL ワークフロー図、Slack 通知フロー、戦略 → 発注の監査例）を追加で作成します。どの情報が欲しいか教えてください。