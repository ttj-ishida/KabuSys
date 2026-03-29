# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ KabuSys の README（日本語）。

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（ETL）・品質チェック・特徴量生成・ニュースNLP・市場レジーム判定・監査ログ管理などを備えた内部ライブラリ群です。  
主に以下用途を想定しています：

- J-Quants API からの株価・財務・カレンダー等の差分ETL
- DuckDB を用いたローカルデータプラットフォーム
- RSS ニュース収集と OpenAI を使った銘柄ごとのニュースセンチメント評価
- ETFベース移動平均やマクロセンチメントを組み合わせた市場レジーム判定
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量探索
- ETL のデータ品質チェック
- 発注システム向け監査ログ（信頼できるトレーサビリティ）テーブルの初期化

設計方針としては、ルックアヘッドバイアスを防ぐこと（日時参照の扱いに注意）、DuckDB + SQL ベースでの効率的処理、外部API呼び出し時の堅牢なリトライ／フェイルセーフ設計が重視されています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 設定アクセス用 `kabusys.config.settings`
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（`kabusys.data.jquants_client`）：認証・ページネーション・レート制御・保存ロジック
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合チェック
- 市場カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、calendar_update_job
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、正規化、SSRF対策、raw_news への冪等保存
- ニュース NLP / レジーム判定（kabusys.ai）
  - score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して `ai_scores` に保存
  - score_regime: ETF(1321) の 200 日 MA 乖離とマクロニュースの LLM スコアを合成して市場レジームを判定・保存
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算 / IC / 統計サマリー
  - z-score 正規化ユーティリティ（kabusys.data.stats）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions などのテーブル DDL と初期化ヘルパー（冪等）
- ユーティリティ
  - RSS パーサー、URL 正規化、OpenAI 呼び出しの保護的実装、J-Quants クライアントのレートリミッタ等

---

## セットアップ手順（開発環境）

以下は最小セットの手順・依存の例です。プロジェクトに pyproject.toml / requirements.txt があればそちらを優先してください。

1. Python 環境を用意（推奨: 3.9+）

2. 仮想環境作成・有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 必要パッケージをインストール（最小）
   - pip install duckdb openai defusedxml

   （プロジェクトにパッケージ配布設定があれば `pip install -e .` を使って開発インストールしてください）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に `.env` / `.env.local` を自動ロードします（自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要環境変数（最低限設定が必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime を使う場合必須）
     - KABU_API_PASSWORD — kabu API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN — Slack 通知連携（必要なら）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必要なら）
     - KABUSYS_ENV — 環境（development / paper_trading / live。デフォルト: development）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - DUCKDB_PATH — DuckDB DB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（必要に応じて）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - .env のサンプルがプロジェクトにある場合は `.env.example` を参考に `.env` を作成してください（config._require により必須値がチェックされます）。

---

## 使い方（主要な例）

下記は最小限の利用例です。DuckDB 接続オブジェクトを渡して各 API を呼び出します。

- DuckDB 接続例

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイル DB。":memory:" も可
```

- ETL（日次パイプライン）実行

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しないと今日が対象（内部で営業日調整あり）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 個別 ETL（株価のみ等）

```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
print(f"fetched={fetched}, saved={saved}")
```

- ニューススコアリング（OpenAI API が必要）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# env OPENAI_API_KEY を設定しておけば api_key 引数は不要
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（発注監査用）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ファイルを作成して DDL を適用
```

- 設定参照

```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
# 必須項目に未設定の場合、アクセス時に ValueError が出ます
```

注意点：
- OpenAI 呼び出しはモデル gpt-4o-mini を想定し JSON mode を利用します。API 失敗時はフェイルセーフ（スコアを 0.0 にフォールバック）する実装になっています。
- DuckDB 側テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime, market_calendar など）は事前に作成しておくか、ETL あるいはスキーマ初期化ロジックを用いて準備してください（プロジェクトにはスキーマ初期化ユーティリティが含まれている場合があります）。

---

## ディレクトリ構成（主要モジュール）

以下はコードベース（src/kabusys）内の主要ファイル・モジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースNLP（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch / save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py              — RSS ニュース収集
    - quality.py                     — データ品質チェック
    - calendar_management.py         — 市場カレンダー管理
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算
    - feature_exploration.py         — 将来リターン / IC / summary / rank
  - (その他)
    - strategy / execution / monitoring  — __init__ に名前はあるが実装は別ディレクトリまたは今後の実装想定

---

## 開発者向けメモ / 注意点

- 環境変数自動ロード:
  - `kabusys.config` はプロジェクトルートを .git / pyproject.toml から探索し、`.env` と `.env.local` を自動で読み込みます。テスト時など自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany の仕様に注意（空リストバインド不可など）。pipeline や ai モジュールはその点を考慮した実装になっています。
- OpenAI 呼び出しは内部でリトライ・エラーハンドリングを行いますが、API キー未設定時は ValueError を投げます。
- J-Quants API のレート制限（120 req/min）を遵守する実装が含まれています（固定間隔スロットリング）。ID トークンの自動リフレッシュも実装されています。
- news_collector は SSRF / XML-Bomb / GZIP 圧縮対策などを実装済みです。RSS のサイズ上限やトラッキングパラメータ除去なども行います。
- 監査ログスキーマは冪等で適用可能（init_audit_schema / init_audit_db）。

---

## ライセンス / 貢献

（ここにプロジェクトのライセンスや貢献方法を記載してください。例: MIT, コントリビュートガイド等）

---

以上。README の補足や具体的なサンプル（テーブルスキーマ、.env.example、requirements.txt、運用スクリプトなど）が必要であれば、用途に合わせて追記します。