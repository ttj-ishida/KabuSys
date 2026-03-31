# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などの機能を提供します。

---

## 主要な特徴

- データ取得 / ETL
  - J-Quants API から株価日足・財務・マーケットカレンダーを安全に差分取得して DuckDB に保存
  - レートリミット遵守・リトライ・トークン自動リフレッシュ対応
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合を検出するチェック群
- ニュース NLP / センチメント
  - RSS 収集（SSRF対策・サイズ制限・トラッキング除去）と OpenAI を使った銘柄別センチメント算出
- 市場レジーム判定
  - ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定
- リサーチ機能
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC・統計サマリー
- 監査ログ（Audit）
  - signal → order_request → executions のトレーサビリティを保証する監査スキーマの初期化ユーティリティ
- フェイルセーフ設計
  - API/LLM失敗時はフェイルセーフで継続する設計（ログ出力・部分失敗の保護）

---

## システム要件

- Python 3.10 以上（| 型ヒント等の使用のため）
- 必要な主なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

インストール例（最低限）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはリポジトリに requirements.txt があればそれを使用
# pip install -r requirements.txt
```

---

## 環境変数 / .env

このプロジェクトは .env / 環境変数から設定を読み込みます。パッケージ起点でプロジェクトルート（.git または pyproject.toml）を探索し、自動で `.env` → `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（Settings 参照）:

- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（既定: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（既定: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）
- OPENAI_API_KEY — OpenAI API キー（news/regime モジュールで使用）

例 `.env`（簡易）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（概要）

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   # 他に必要な依存があればプロジェクト側で追加してください
   ```

3. 環境変数を設定（`.env` をプロジェクトルートに作成）
   - 必須のキーを設定（上記参照）

4. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要ユースケース）

以下はライブラリの主要な関数をコマンドラインから簡単に呼ぶ例です。実運用ではスケジューラやワーカーから呼び出します。

- DuckDB 接続と日次 ETL の実行:
```python
python - <<'PY'
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
PY
```

- ニュースセンチメントのスコア付け（特定日）:
```python
python - <<'PY'
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
PY
```

- 市場レジーム判定の実行:
```python
python - <<'PY'
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
PY
```

- 監査ログ用 DB 初期化:
```python
python - <<'PY'
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring.db")
print("audit db initialized")
PY
```

- RSS フェッチ（ニュースコレクタの一部を直接呼ぶ例）:
```python
python - <<'PY'
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
print(len(articles))
PY
```

注意:
- OpenAI を使う処理（news_nlp / regime_detector）は `OPENAI_API_KEY` が必要です。関数呼び出し時に `api_key` 引数で明示することも可能です。
- ETL/保存系は DuckDB のスキーマが前提です。実運用ではスキーマ初期化を行ってから使用してください（プロジェクト内にスキーマ初期化機能がある想定）。

---

## 自動読み込みの挙動

- 環境変数は以下の優先順位で読み込まれます:
  1. OS 環境変数
  2. .env.local
  3. .env
- 自動読み込みを無効化する:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## ディレクトリ構成（src/kabusys ベースの主要ファイル）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM センチメント算出
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理（営業日判定など）
    - etl.py — ETL インターフェース再エクスポート
    - pipeline.py — 日次 ETL パイプライン
    - stats.py — zscore 等の統計ユーティリティ
    - quality.py — データ品質チェック群
    - audit.py — 監査スキーマ作成・初期化
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS 収集と前処理（SSRF対策等）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等ファクター計算
    - feature_exploration.py — forward returns, IC, summary 等
  - (その他) strategy/, execution/, monitoring/ （パッケージ公開用プレースホルダが __all__ に含まれます）

---

## 開発・テストに関するヒント

- テスト中に自動で .env を読み込ませたくない場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する
- OpenAI / external API 呼び出しはモック可能な設計:
  - news_nlp / regime_detector 内部の _call_openai_api はテスト時に patch して差し替えられるよう設計されています
- DuckDB に関する注意:
  - executemany に空リストを渡すと一部バージョンでエラーになることがあるため、コード内で空チェックが行われています

---

必要な内容や追加したいサンプル（例: schema 初期化手順や CI 実行方法）があれば教えてください。README を追記・カスタマイズします。