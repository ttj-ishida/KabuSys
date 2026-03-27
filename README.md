# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）→ ETL → 品質チェック → 研究用ファクター計算 → ニュースNLP / レジーム判定 → 監査ログ（発注/約定トレーサビリティ）までをカバーするモジュール群を提供します。

---

## 概要

KabuSys は日本株の自動売買システムや研究プラットフォーム向けの共通ユーティリティ群です。主に以下を目的としています。

- J-Quants API 経由での株価・財務・市場カレンダーの取得と DuckDB への保存（ETL）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究向けファクター（モメンタム、バリュー、ボラティリティ等）の計算と統計ユーティリティ
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメント算出（AI モジュール）
- ETF とマクロセンチメントを組み合わせた市場レジーム判定
- 発注・約定を追跡する監査テーブルの初期化ユーティリティ
- 環境変数 / .env の自動読み込みと設定ラッパー

設計上のポイント:
- ルックアヘッドバイアスの回避（内部で date.today() などを無秩序に参照しない）
- DuckDB をデータ層に採用（軽量かつ SQL ベース）
- API 呼び出しはリトライ / バックオフ・レートリミット対応
- 冪等性を重視した DB 書き込み（ON CONFLICT 等）

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants からの株価日足、財務諸表、上場情報、マーケットカレンダー取得
  - 差分更新、バックフィル、保存（冪等）
  - 日次 ETL パイプライン（run_daily_etl）

- データ品質チェック
  - 欠損値検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトで結果を収集

- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー系のファクター計算
  - 将来リターン計算、IC（ランク相関）、ファクター統計サマリ
  - Zスコア正規化

- ニュース収集 & NLP（OpenAI）
  - RSS フィード取得（SSRF 対策、gzip/サイズ検査付き）
  - 銘柄ごとの記事集約 → GPT 系モデルでセンチメントスコア化（JSON mode）
  - 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュースセンチメントの合成）

- 監査ログ（発注/約定トレーサビリティ）
  - signal_events / order_requests / executions テーブルとインデックス定義
  - 初期化ユーティリティ（init_audit_schema / init_audit_db）

- 設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - settings オブジェクト経由で必須設定を取得

---

## 必要条件

- Python 3.10 以上（型ヒントで `X | Y` 構文を使用しているため）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ

実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード）
   - 例:
     - git clone ...
     - cd <repo_root>
     - pip install -e .

   あるいは必要なパッケージを pip で個別にインストールしてください:
   - pip install duckdb openai defusedxml

2. Python バージョン確認:
   - python --version  # 3.10+

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数（利用する機能に応じて）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabu ステーション API のパスワード（発注周り）
     - SLACK_BOT_TOKEN        — Slack 通知（必要なら）
     - SLACK_CHANNEL_ID       — Slack チャンネル ID（必要なら）
     - OPENAI_API_KEY         — OpenAI を使う機能を実行する場合
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live)  デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|...) デフォルト: INFO
     - KABU_API_BASE_URL デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH / SQLITE_PATH （データベース保存先）

   - .env の自動読み込みは以下の優先順:
     - OS 環境変数 > .env.local > .env

4. DuckDB ファイル置き場の作成
   - settings.duckdb_path に基づき親ディレクトリが自動作成されますが、必要に応じて手動作成してください。

---

## .env 例 (.env.example)

例として最低限必要なキーを示します（実運用前に適切な値で作成してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（クイックスタート）

以下は主な処理を呼び出す最小例です。実行前に必ず必要な環境変数を設定してください。

- DuckDB 接続を作成して日次 ETL を実行する例:

```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュースセンチメント算出（OpenAI API が必要）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {written} scores")
```

- 市場レジーム判定（ETF 1321 + マクロセンチメント）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```

- 設定値を取得する（必須項目は未設定時に例外が発生します）:

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 未設定なら ValueError
```

---

## 主要モジュールとディレクトリ構成

リポジトリは src/kabusys 配下をパッケージとして想定しています。主要ファイル・ディレクトリは以下です：

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動ロード、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの銘柄別センチメント算出（OpenAI）
    - regime_detector.py  — ETF + マクロセンチメントで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult 再エクスポート
    - calendar_management.py — マーケットカレンダー管理 / 営業日判定
    - news_collector.py   — RSS 収集・前処理（SSRF 対策等）
    - quality.py          — データ品質チェック
    - stats.py            — 統計ユーティリティ（zscore_normalize 等）
    - audit.py            — 監査テーブル DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - その他: strategy, execution, monitoring といったサブパッケージが想定されるエントリポイント（__all__ に定義）

---

## 開発・テストに関する補足

- 自動 .env 読み込みを無効化する:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます（テスト時に便利）。

- OpenAI / J-Quants 呼び出しは外部 API を使用するため、ユニットテストではモック推奨です。コード内でも _call_openai_api 等の差し替えポイントが用意されています。

- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、実装側で空チェックを行っています。開発時は duckdb バージョン互換性に注意してください。

---

## 貢献

バグ報告・機能要望は issue を作成してください。Pull Request の際はテストと簡単な説明を添えてください。

---

必要であれば README に実行例の追加、CI / テスト手順、開発環境設定（pre-commit / linters）などの追記も可能です。どの情報を優先して拡張しますか？