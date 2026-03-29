# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
DuckDB をデータストアとして、J‑Quants / RSS / OpenAI（LLM）などを組み合わせてデータ収集（ETL）、品質チェック、ファクター計算、ニュース・センチメント解析、監査ログ（トレーサビリティ）、市場レジーム判定などの機能を提供します。

---

## 主な特徴

- データ取得・ETL
  - J‑Quants API から株価（日足）・財務・JPX カレンダーを差分取得し DuckDB に保存
  - 差分取得とバックフィルによる堅牢な ETL（ページネーション・レート制御・自動トークンリフレッシュ・冪等保存）
- データ品質管理
  - 欠損・重複・スパイク・日付不整合検査の統合チェック（quality モジュール）
- ニュース収集・NLP
  - RSS 収集（SSRF 対策・トラッキング除去・前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（news_nlp）
  - マクロニュース × ETF MA を合成した市場レジーム判定（regime_detector）
- 研究・ファクター計算
  - Momentum / Value / Volatility 系のファクター計算および特徴探索（research モジュール）
  - Z スコア正規化などの統計ユーティリティ
- 監査ログ（オーディット）
  - signal → order_request → execution に至る監査テーブルを DuckDB に冪等初期化してトレーサビリティを保持

---

## 必要条件

- Python 3.10+
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

推奨: 仮想環境（venv / poetry / pipx など）を使用してください。

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発用にパッケージをインストールする場合:
pip install -e .
```

---

## 環境変数 / 設定

パッケージは .env/.env.local（プロジェクトルート）または OS 環境変数から設定を自動読み込みします。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。プロジェクトルートは `.git` または `pyproject.toml` の位置から検出されます。  

主な設定項目（settings で参照）:

- J-Quants
  - `JQUANTS_REFRESH_TOKEN` （必須）
- kabu ステーション API
  - `KABU_API_PASSWORD`（必須）
  - `KABU_API_BASE_URL`（デフォルト: `http://localhost:18080/kabusapi`）
- Slack（通知用）
  - `SLACK_BOT_TOKEN`（必須）
  - `SLACK_CHANNEL_ID`（必須）
- DB パス
  - `DUCKDB_PATH`（デフォルト: `data/kabusys.duckdb`）
  - `SQLITE_PATH`（監視用 DB、デフォルト: `data/monitoring.db`）
- OpenAI
  - `OPENAI_API_KEY`（API 呼び出し時に環境変数で参照）
- 実行モード / ログ
  - `KABUSYS_ENV` = `development` | `paper_trading` | `live`（デフォルト `development`）
  - `LOG_LEVEL` = `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`（デフォルト `INFO`）

必須の環境変数が未設定の場合、settings のプロパティアクセスで `ValueError` が発生します（明示的に確認できます）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンし、仮想環境を作成
2. 依存ライブラリをインストール（上記を参照）
3. プロジェクトルートに `.env`（と必要なら `.env.local`）を用意し、必要なキーを設定
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUS_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```
4. DuckDB ファイルの親ディレクトリがなければ作成されます（init_audit_db 等の関数が作成します）

---

## 使い方（代表的な API）

以下はライブラリの代表的な利用例です。日付には標準 datetime.date を使います。バックテストや運用実行時には Look‑ahead バイアスに注意してください（ライブラリは可能な限り回避措置が組み込まれています）。

- DuckDB 接続と ETL 実行（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア算出（news_nlp）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（regime_detector）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（audit）
```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

conn = init_audit_db(settings.duckdb_path)  # DB ファイルを作成して監査スキーマを初期化
```

- RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url, source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意: fetch_rss は生の NewsArticle を返します。DB への保存や news_symbols との紐付けは別プロセス／ETL の流れで行ってください（パイプライン側での実装を想定）。

---

## 実装上のポイント・挙動

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われ、`.env.local` が `.env` を上書きします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J‑Quants クライアントはレート制御（120 req/min）とリトライ、401 時のトークン自動リフレッシュを備えています。
- OpenAI 呼び出しはリトライ・JSON モード利用・レスポンスバリデーションを行い、失敗時はフェイルセーフでスコアを 0.0 にフォールバックする等の設計です（例外が投げられる場面もありますので呼び出し側での例外ハンドリングを推奨）。
- ETL は各ステップが独立してエラー処理され、1 ステップ失敗でも他は継続します。最終結果は ETLResult で集約されます。
- 日付操作やウィンドウ計算はバックテストで Look‑ahead バイアスを防ぐよう設計されています（内部で datetime.today() を参照しない関数等）。

---

## ディレクトリ構成（抜粋）

（主要ファイル・モジュールを抜粋しています）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント解析（OpenAI）
    - regime_detector.py      — マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J‑Quants API クライアント（取得 + 保存）
    - pipeline.py             — ETL パイプライン
    - etl.py                  — ETLResult 再エクスポート
    - calendar_management.py  — 市場カレンダー管理
    - stats.py                — 統計ユーティリティ（zscore 正規化等）
    - quality.py              — データ品質チェック
    - news_collector.py       — RSS ニュース収集
    - audit.py                — 監査ログ（オーディット）テーブル初期化
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Value/Volatility 等ファクター
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー

---

## 注意事項 / ベストプラクティス

- 本ライブラリは実運用（特に本番の発注・約定処理）を想定した設計を含みます。実際にブローカーへ発注するコードはこのコードベースに含まれていませんが、監査ログ設計は発注フローを追跡できるように作られています。
- OpenAI API や J‑Quants API など外部 API を叩く処理はコストとレート制限に注意して運用してください。
- production（`KABUSYS_ENV=live`）では設定ミスやキーの露出に特に注意してください。秘密情報は安全に管理してください。
- DuckDB のバージョン差異によるバインド挙動（executemany の空リスト等）に注意して実装されていますが、運用環境での DuckDB バージョンを合わせることを推奨します。

---

この README はこのコードベースの概要と代表的な使い方を示すものです。個々の関数やモジュールの詳細はソースコードの docstring を参照してください。必要があれば、実行例（Dockerfile / systemd ジョブ / CI ワークフロー）や .env.example のテンプレート作成も支援できます。