# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買のためのライブラリ群です。DuckDB をデータ格納に使い、J-Quants API / RSS / OpenAI（LLM）などを組み合わせてデータ収集、品質チェック、ファクター計算、ニュース NLP、マーケットレジーム判定、監査ログ管理、ETL パイプラインを提供します。

## 主な特徴
- データ取得（J-Quants）と DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 市場カレンダー管理（JPX カレンダー）と営業日ユーティリティ
- ニュース収集・前処理・銘柄紐付け（RSS）
- ニュースの LLM ベースセンチメントスコアリング（gpt-4o-mini を想定）
- 市場レジーム判定（ETF 1321 の MA + マクロニュースセンチメントの合成）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC など）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数 / .env の自動読み込み（プロジェクトルート基準）

---

## 機能一覧（モジュール概要）
- kabusys.config
  - 環境変数読み込み & Settings（J-Quants / kabu API / Slack / DB パス / 環境切替など）
  - 自動 .env ロード（プロジェクトルートにある `.env` / `.env.local`、無効化可）
- kabusys.data
  - jquants_client: J-Quants API クライアント（レートリミット・再試行・トークン管理）
  - pipeline / etl: 差分 ETL / run_daily_etl など
  - news_collector: RSS 収集・前処理（SSRF 対策・サイズ制限）
  - calendar_management: マーケットカレンダー・営業日ユーティリティ
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - audit: 監査ログテーブルの初期化・管理
  - stats: z-score 正規化など
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM でスコア化し ai_scores テーブルへ保存
  - regime_detector.score_regime: MA とマクロニュース LLM を合成して market_regime を保存
- kabusys.research
  - factor_research: momentum / value / volatility 等のファクター
  - feature_exploration: forward returns, IC, 統計サマリー 等

---

## 動作要件
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants, RSS ソース, OpenAI）

（実際のセットアップでは pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone ... (プロジェクトルートに `.git` または `pyproject.toml` があることを想定)

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   あるいはプロジェクトの packaging がある場合:
   - pip install -e .

4. 環境変数の設定
   - 必須（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API のパスワード
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - OPENAI_API_KEY: OpenAI 呼び出し用（score_news / score_regime を使う場合）
   - 任意:
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）

5. .env ファイル
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（ロード順: OS env > .env.local > .env）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。

---

## 使い方（代表的な API とサンプル）

以下は Python REPL / スクリプトでの利用例です。DuckDB 接続には duckdb.connect() を使用します。

- ETL を日次実行（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの LLM スコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にない場合、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み件数:", n_written)
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- RSS を取得して raw_news へ保存（news_collector.fetch_rss の結果を保存する実装はプロジェクトの別関数を想定）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 監査ログ用 DB を初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# これで監査ログ用テーブルが作成されます
```

注意点:
- OpenAI 呼び出し部分は再試行・フェイルセーフが組み込まれています。ユニットテストでは kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api をモックできます。
- J-Quants の API 呼び出しは内部でレートリミットと再試行を処理します。get_id_token / fetch_* 系は id_token キャッシュを使います。

---

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabu API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot Token
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: sqlite/監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: ログレベル（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

設定は `.env` / `.env.local` に書くと自動で読み込まれます（ただし OS 環境変数が優先されます）。

---

## ディレクトリ構成（主要ファイル）
プロジェクトのソースは `src/kabusys` 配下にあります。主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — 市場レジーム判定（MA + LLM）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（fetch/save）
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - etl.py                    — ETLResult 再エクスポート
    - news_collector.py         — RSS 収集・前処理
    - calendar_management.py    — マーケットカレンダー / 営業日ユーティリティ
    - quality.py                — データ品質チェック
    - stats.py                  — z-score など汎用統計
    - audit.py                  — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py        — Momentum / Value / Volatility 等
    - feature_exploration.py    — forward returns, IC, rank, summary

---

## 開発・テスト時のヒント
- OpenAI 呼び出しはネットワークを伴うため、ユニットテストでは _call_openai_api を patch/mocking してレスポンスをシミュレートしてください。
- news_collector は外部 RSS を叩くため、ネットワークアクセスをモックすると安定します。
- DuckDB はインメモリ（":memory:"）で接続できるため、テスト時にファイルを作らずに済みます。
- .env の自動ロードはプロジェクトルートの検出に .git または pyproject.toml を使っているため、テストで意図的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 注意事項（セキュリティ / 実運用）
- API キーやトークンは絶対にソース管理（git）に含めないでください。`.env` を `.gitignore` に入れて管理してください。
- 本ライブラリは発注・実行ログなど重要な操作をサポートします。実運用での発注は十分なリスク管理・テストを行ったうえで行ってください（paper_trading モード推奨）。
- news_collector は SSRF / XML Bomb 等に対する防御機構がありますが、運用環境ではホワイトリスト運用など追加の安全対策を検討してください。

---

この README はリポジトリの概要と基本的な使い方をまとめたものです。詳細な設計意図や仕様（DataPlatform.md / StrategyModel.md などの設計文書）がプロジェクト内にある場合はそちらも参照してください。質問や README の補足希望があれば教えてください。