# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
J-Quants や RSS ニュース、OpenAI（LLM）を組み合わせてデータ収集・品質チェック・NLP によるセンチメント評価、リサーチ用のファクター計算、監査ログの管理、さらに発注（kabuステーション）連携を想定したコンポーネントを提供します。

主な用途
- 日次 ETL（株価・財務・市場カレンダー）の差分取得と保存（DuckDB）
- ニュースの収集と銘柄別センチメント評価（OpenAI）
- マクロセンチメントと MA を組み合わせた市場レジーム判定
- ファクター計算 / 将来リターン / IC 等のリサーチ用ユーティリティ
- 監査ログ（シグナル → 発注 → 約定）用スキーマ初期化と管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 機能一覧

- data/
  - ETL パイプライン（jquants_client 経由で J-Quants API からデータ取得）
  - market_calendar 管理・営業日判定
  - news_collector（RSS 取得・前処理・SSRF 対策）
  - quality（データ品質チェック）
  - audit（監査ログスキーマの初期化・監査用 DB ユーティリティ）
  - stats（Zスコア正規化 等）
- ai/
  - news_nlp: ニュース記事を LLM で銘柄別にスコア化して ai_scores に保存
  - regime_detector: ETF（1321）の 200 日 MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
- research/
  - factor 計算（momentum / value / volatility）
  - feature_exploration（forward returns, IC, 統計サマリー 等）
- config.py
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と Settings API（環境変数経由設定）

---

## 前提・準備

- Python 3.10+（typing の `|` や forward annotations を使用）
- 推奨パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API、RSS、OpenAI）

requirements.txt が無い場合は最低限以下をインストールしてください:
pip install duckdb openai defusedxml

---

## 環境変数（主なもの）

必須（実行する機能によって必要）:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（ETL）
- SLACK_BOT_TOKEN : Slack 通知を利用する場合
- SLACK_CHANNEL_ID : Slack チャンネル ID
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注連携で使用）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）

任意（デフォルトあり）:
- KABUSYS_ENV : "development" | "paper_trading" | "live"（デフォルト "development"）
- LOG_LEVEL : ロギングレベル（デフォルト "INFO"）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト `data/monitoring.db`）

自動ロード:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env.example）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## セットアップ手順（例）

1. リポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール
   pip install duckdb openai defusedxml
   （他に要求パッケージがあれば適宜追加）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. データディレクトリを作成（必要に応じて）
   mkdir -p data

---

## 使い方（コード例）

以降は Python REPL やスクリプト内で利用します。基本的に DuckDB 接続オブジェクト（duckdb.connect）を渡して操作します。

- 共通: settings の利用（環境変数読み取り）
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB に接続:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー / 株価 / 財務 / 品質チェック）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア付け（ai_scores テーブルへ書き込む）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（regime を market_regime テーブルへ書き込み）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB / スキーマの初期化:
```python
from kabusys.data.audit import init_audit_db

# ":memory:" でインメモリ DB も可能
audit_conn = init_audit_db("data/audit.duckdb")
```

- RSS を取得して raw_news に保存する（news_collector を利用するコードの呼び出しは用途に応じて実装してください）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

注意点:
- すべてのモジュールは「ルックアヘッドバイアス」を避ける設計（内部で date.today() を勝手に参照しない等）になっています。target_date を明示的に渡して使ってください。
- OpenAI / J-Quants API 呼び出しは外部サービス依存で、API キーやレート制限、コストに注意してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py (alias)
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - etl.py
  - (その他 data.* モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

主要役割:
- ai/* : LLM を使ったスコアリング（ニュースセンチメント、マクロセンチメント）と市場レジーム判定
- data/jquants_client.py : J-Quants API の取得・保存ロジック（rate limiting, retry, id_token refresh）
- data/pipeline.py : ETL の上位実装（run_daily_etl 等）
- data/news_collector.py : RSS 収集と前処理（SSRF / XML 攻撃対策を含む）
- research/* : ファクター計算や評価指標（IC 等）

---

## 開発 / テスト上のヒント

- 環境変数の自動ロードは .env / .env.local をプロジェクトルートから自動検出して読み込みます。ユニットテストなどでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- OpenAI 呼び出し部分は内部で関数を分離しているため unittest.mock.patch で容易に差し替え可能です（_call_openai_api をモックする等）。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、呼び出し側で空判定が行われています。テストで挙動を再現する際は注意してください。

---

## ライセンス・貢献

この README はコードベースの簡易説明です。ライセンスや貢献ルールはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

README に記載した使い方はライブラリの公開 API を抜粋したものです。実運用ではロギング設定、エラー監視、API レート・コスト対策、機密情報の保護（Vault や CI の secret 管理）を必ず行ってください。