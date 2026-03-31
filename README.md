# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ（KabuSys）。  
J-Quants / DuckDB を用いたデータ ETL、ニュース NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するためのライブラリ群です。主な目的は以下：

- J-Quants API からのデータ取得（株価・財務・JPX カレンダー）
- DuckDB を用いた永続化・ETL パイプライン
- ニュース収集・NLP による銘柄別センチメント算出（OpenAI）
- 市場レジーム判定（ETF + マクロニュースの結合）
- 研究用途のファクター計算・特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）

設計上、ルックアヘッドバイアスを避ける実装や、API 呼び出しのリトライ/バックオフ、冪等保存（ON CONFLICT）など運用を考慮した作りになっています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 各種）
  - ニュース収集（RSS → raw_news）と前処理（SSRF 対策・トラッキングパラメータ除去等）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - マーケットカレンダー管理（営業日判定・next/prev/get_trading_days）
  - 監査ログ（監査テーブル初期化、専用 DuckDB 初期化）
  - 汎用統計ユーティリティ（z-score 正規化 等）
- ai
  - ニュース NLP（銘柄別センチメントを OpenAI で評価 → ai_scores 保存）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースによる LLM スコアを合成）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索（将来リターン計算, IC, 統計サマリー 等）
- config
  - 環境変数 / .env の自動読み込みと Settings オブジェクト提供

---

## 必要な環境・依存

推奨 Python バージョン: 3.10+

主要外部依存（例）:
- duckdb
- openai
- defusedxml

インストールの例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージをローカル開発モードでインストールする場合
pip install -e .
```

（必要に応じて他パッケージを追加してください。requirements.txt はプロジェクトに合わせて用意します。）

---

## 環境変数 / 設定

config.Settings で主要な設定を提供しています。主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / score_regime で利用）
- DUCKDB_PATH — デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)

.env の自動読み込み:
- プロジェクトルート (.git または pyproject.toml を基準) にある `.env` と `.env.local` を自動読み込みします。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意: Settings の必須項目が未設定だと ValueError が発生します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 必要なパッケージをインストール（上記参照）
4. .env を作成（.env.example を用意している場合はそれを参照）
   - 少なくとも JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY を設定
5. DuckDB データベースフォルダを作成（settings.duckdb_path の親ディレクトリは自動作成する処理もありますが確認）

---

## 使い方（サンプル）

基本的に DuckDB 接続を作って関数を呼びます。

- 日次 ETL を実行する例:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別スコア）を計算する例:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数で設定済みなら api_key を省略可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定の例:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する例:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリが無ければ自動作成
# テーブルが作成され、タイムゾーンは UTC に設定されます
```

- J-Quants から直接データ取得する例（テストやスクリプトで）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
```

注意点:
- OpenAI 呼び出しは API 失敗時にフェイルセーフとしてスコア 0 を返す等の保護が入っていますが、API キーは必須です（メソッドで明示的に渡すか環境変数 OPENAI_API_KEY を設定）。
- ETL 実行はログと品質チェックの出力を確認して運用してください。

---

## 開発者向け情報 / 実装上のポイント

- ルックアヘッドバイアス対策として、各スコアリング関数は内部で date.today() を直接参照せず、必ず target_date を引数で与える設計です。
- J-Quants クライアントは固定間隔レートリミットと再試行ロジック（指数バックオフ、401 時のトークンリフレッシュなど）を備えています。
- ニュース収集は SSRF 対策、受信サイズ制限、トラッキングパラメータ除去等の安全対策が実装されています。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）にしています。
- ai モジュールの OpenAI 呼び出し部分はテスト容易性のため内部呼び出しを差し替えられるよう設計されています（ユニットテストでモック可能）。

---

## ディレクトリ構成

（主要ファイルを抜粋、パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / .env 管理（Settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（銘柄別 ai_scores 生成）
    - regime_detector.py         — 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch/save）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult 再エクスポート
    - news_collector.py          — RSS 収集・前処理
    - calendar_management.py     — マーケットカレンダー管理 / 営業日ロジック
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログ（監査スキーマ初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum, value, volatility）
    - feature_exploration.py     — 将来リターン, IC, factor_summary, rank
  - (その他: strategy/, execution/, monitoring/ パッケージ用のエクスポートあり)

各モジュールには詳細な docstring と設計方針が含まれており、読みながら理解しやすい構成です。

---

## 運用上の注意

- 本リポジトリは実際の発注処理（ブローカーとの送信等）を含む設計を想定しています。実運用では paper_trading 環境や十分なテストを行った上で live モードに切り替えてください。
- センシティブな環境変数（API トークン等）は適切に管理し、リポジトリにコミットしないでください。
- OpenAI / J-Quants の API 呼び出しはコストやレート制限に注意してください。

---

もし README のテンプレート（.env.example、requirements.txt、実運用スクリプト）を追加したい場合や、特定モジュール（例: jquants_client）の動作例をより詳しく書いたドキュメントが必要でしたらお知らせください。