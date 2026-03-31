# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。  
DuckDB を用いたデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注/約定トレース）などを含むモジュール群を提供します。

## 主な特徴
- データ ETL
  - J-Quants API から株価（日足）・財務・市場カレンダーを差分取得して DuckDB に保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース NLP
  - RSS 収集 → OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出し ai_scores テーブルに保存
  - API エラー・レート制限に対するリトライ/フォールバック実装
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュース LLM センチメントを合成して日次でレジーム判定
- 監査ログ（Audit）
  - signal → order_request → execution の階層で監査テーブルを初期化・管理（冪等・UTCタイムスタンプ）
- ユーティリティ
  - マーケットカレンダー管理、研究用統計/ファクター計算、Zスコア正規化など

---

## 必要要件
- Python 3.10+
- 主な依存ライブラリ（抜粋）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ

（環境やパッケージ管理方針により requirements.txt / pyproject.toml を参照してください）

---

## インストール
プロジェクトルートで開発インストールする例:

```bash
pip install -e .
# または
pip install duckdb openai defusedxml
```

依存は pyproject.toml / requirements.txt があればそちらを使ってください。

---

## 設定（環境変数）
kabusys は .env / .env.local（プロジェクトルートにある場合）から自動で環境変数を読み込みます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（gpt 呼び出しに使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注関連に必要）
- KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL: "DEBUG" / "INFO" / ...（デフォルト: INFO）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用 Slack 設定
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

.env の例（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
```

設定はコードからも参照できます:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

未設定の必須キーを参照すると ValueError が発生します。

---

## セットアップ手順（簡易）
1. リポジトリをクローンしインストール
2. 必要な環境変数を .env に設定（J-Quants / OpenAI 等）
3. DuckDB ファイルの作成（初期スキーマがある場合はスクリプト等で作成）
4. 監査ログ用 DB を初期化（必要な場合）

監査 DB 初期化例:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 接続が返り、監査テーブルが作成されます
```

---

## 使い方（代表的な例）

- DuckDB 接続を作って ETL を回す（日次処理の例）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア付け（score_news）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（score_regime）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査スキーマ初期化（既存接続へ）:

```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- J-Quants から直接データを取得する（テスト／デバッグ）:

```python
from kabusys.data.jquants_client import fetch_daily_quotes
rows = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,1))
```

注意点:
- OpenAI 呼び出しや J-Quants API 呼び出しには API キーが必須です。
- API 呼び出しはライブラリ側でレート制御・リトライを行いますが、使用者側でも適切な扱いをしてください。
- 本ライブラリはバックテストループ内で Look-ahead を生まないよう設計しています（内部で date.today() を直接使わない等の配慮あり）。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下の主なモジュール）

- kabusys/
  - __init__.py (パッケージ定義, __version__)
  - config.py (環境変数 / 設定)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - calendar_management.py (マーケットカレンダー管理)
    - etl.py (ETL 公開インターフェース)
    - pipeline.py (日次 ETL パイプライン)
    - stats.py (Zスコア等の統計ユーティリティ)
    - quality.py (データ品質チェック)
    - audit.py (監査ログテーブル初期化)
    - jquants_client.py (J-Quants API クライアント & DuckDB 保存)
    - news_collector.py (RSS 収集・前処理・保存)
  - research/
    - __init__.py
    - factor_research.py (Momentum/Value/Volatility 等)
    - feature_exploration.py (forward returns, IC, summary, rank)
  - ai, data, research の他に strategy/ execution/ monitoring パッケージがエクスポート対象として想定されています（パッケージ root の __all__ を参照）。

---

## 注意と運用上のポイント
- 環境変数が未設定の場合、多くの公開 API は ValueError を投げます（設定チェックは明示的）。
- OpenAI（gpt-4o-mini）呼び出し時のレスポンスは JSON mode を期待します。API側の応答不正やパース失敗時はフェイルセーフでスコアに 0 を使うなど適切にフォールバックします。
- J-Quants API はレート制限があるため内部でスロットリング・リトライを実装しています。
- DuckDB の executemany はバージョン差異で空リストが問題になるため、INSERT 前に空チェックを行っています。
- ニュース収集モジュールは SSRF 対策や XML のデフューズ処理、レスポンスサイズ制限を備えています。

---

## 開発 / テスト
- テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い .env 自動読み込みを回避できます。
- OpenAI 呼び出しや外部 API 呼び出しはテスト時にモック（unittest.mock.patch）して差し替えることが想定されています（各モジュール内で呼び出し箇所が分離されています）。

---

この README はコードの主要な使い方と設計方針の概要です。より詳細な設計（StrategyModel.md / DataPlatform.md 等）やスキーマ定義、運用手順はプロジェクト内のドキュメントを参照してください。必要であれば README に追加したい使用例や運用手順を教えてください。