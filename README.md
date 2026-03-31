# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB をデータ層に用い、J-Quants や RSS / OpenAI（LLM）を利用したデータ収集、品質チェック、ファクター計算、マーケットレジーム判定、監査ログ等の実装を含みます。

## 特徴（概要）
- データETL（J‑Quants から株価・財務・カレンダーを差分取得して DuckDB に保存）  
- ニュース収集（RSS → raw_news 保存、銘柄紐付け）とニュースNLP（OpenAI による銘柄別センチメント）  
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース LLM を合成）  
- 研究用モジュール（ファクター計算・将来リターン・IC 計算・統計要約）  
- データ品質チェック（欠損、スパイク、重複、日付不整合）  
- 監査ログ（signal → order_request → execution をトレースする監査テーブル）  
- 設定は環境変数 / .env で管理。自動的にプロジェクトルートの .env(.local) を読み込みます（無効化可）。

---

## 機能一覧（主な公開 API）
- 設定
  - `kabusys.config.settings`：環境変数経由の設定アクセス（必須キーは取得時にエラー）
- データ
  - `kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)`：日次 ETL（カレンダー、株価、財務、品質チェック）
  - `kabusys.data.jquants_client.fetch_* / save_*`：J-Quants API クライアントと保存関数
  - `kabusys.data.news_collector.fetch_rss(...)`：RSS 取得・前処理
  - `kabusys.data.quality.run_all_checks(...)`：データ品質チェック
  - `kabusys.data.audit.init_audit_db(path)`：監査ログ DB 初期化（DuckDB）
- AI / NLP
  - `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`：銘柄別ニュースセンチメントを ai_scores に書込
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`：市場レジーム判定を market_regime に書込
- Research（研究用）
  - `kabusys.research.calc_momentum/ calc_volatility/ calc_value`：ファクター計算
  - `kabusys.research.calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`
- ユーティリティ
  - `kabusys.data.stats.zscore_normalize`：Zスコア正規化ユーティリティ

---

## 必要条件 / 依存パッケージ
- Python >= 3.10（型ヒントに | を使用）
- 主なパッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging など）

インストール例（プロジェクト配布方法に応じて調整してください）:
```bash
python -m pip install duckdb openai defusedxml
# またはパッケージ化されているなら
# python -m pip install -e .
```

---

## 環境変数（主な設定）
kabusys は環境変数またはプロジェクトルートの `.env` / `.env.local` から設定を自動読み込みします（OS 環境変数が最優先）。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API エンドポイント（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- OPENAI_API_KEY — OpenAI 呼び出しで使用する API キー（news_nlp / regime_detector で使用）

.env のパースはシェル風の書式（export KEY=val, コメント、引用文字列等）に対応しています。

---

## セットアップ手順（ローカル開発向け）
1. Python と依存パッケージをインストール
   ```bash
   python -m pip install -r requirements.txt
   # requirements.txt がない場合:
   python -m pip install duckdb openai defusedxml
   ```
2. リポジトリのルートに .env を作成（.env.example を参考に）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
3. DuckDB の格納先ディレクトリを準備（自動で作成される箇所もありますが、念のため）
   ```bash
   mkdir -p data
   ```
4. 監査ログ用 DB 初期化（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```
   または、既存の DuckDB 接続に対して `init_audit_schema(conn)` を呼ぶことも可能です。

---

## 基本的な使い方（コード例）

- DuckDB へ接続して日次 ETL を実行する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアを取得してデータベースに書き込む:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数にセットしているか api_key 引数で渡す
count = score_news(conn, target_date=date(2026,3,20))
print(f"scored {count} codes")
```

- 市場レジーム判定を実行:
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DB を初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って監査テーブルへ書き込み／参照
```

注意:
- AI モジュール（news_nlp, regime_detector）は OpenAI の JSON Mode を利用する想定です。API キーは引数で注入可能（テストで差し替えやすい）。
- ETL / AI 呼び出しはネットワーク・API エラーに対して堅牢なリトライやフェイルセーフ設計になっていますが、実行には各種 API キーが必要です。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, 監査テーブル等）は ETL・初期化処理で作成／前提としています。プロジェクト固有のスキーマ初期化ロジック（別途提供される schema 初期化関数等）がある場合はそちらを実行してください。

---

## ディレクトリ構成（主要ファイル）
プロジェクトの主要モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読込と設定ラッパー
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント取得・ai_scores 書込
    - regime_detector.py — マーケットレジーム判定・market_regime 書込
  - data/
    - __init__.py
    - jquants_client.py — J‑Quants API クライアント & DuckDB 保存関数
    - pipeline.py — ETL パイプライン / run_daily_etl 等
    - etl.py — ETLResult エクスポート
    - news_collector.py — RSS 収集・前処理
    - quality.py — データ品質チェック
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等
    - feature_exploration.py — forward returns / IC / summary / rank

各モジュールに詳細なドキュメント（docstring）があり、関数の役割・引数・戻り値が明記されています。開発時はこれら docstring を参照してください。

---

## 運用上の注意点
- 環境（KABUSYS_ENV）は "development", "paper_trading", "live" のいずれかで指定してください（設定検証あり）。
- 自動で .env を読み込む仕組みは、プロジェクトルート（.git or pyproject.toml）を探索して検出されたルートを基準に行います。テスト実行時は自動読み込みを無効化してください（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- OpenAI や J‑Quants の呼び出しはレート制限・コストに注意してください。ローカルでの連続呼び出しやテスト時はモックや少量データでの検証を推奨します。
- データの「ルックアヘッドバイアス」対策が各モジュールに組み込まれています（target_date 未満のデータのみ使用、datetime.today を直接参照しない等）。バックテストや研究用途での利用時はこれらの設計方針を尊重してください。

---

もし README に追加したい動作例（CLI、docker-compose、schema 初期化スクリプト、CI 設定など）があれば、提供するので追記します。