# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL・ニュース収集・LLM を用いたニュースセンチメント・市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、投資システムのバックエンド処理を中心に実装しています。

## プロジェクト概要
- パッケージ名: `kabusys`
- 目的: J-Quants 等から株価・財務・カレンダー・ニュースを取得し、DuckDB に格納・品質管理。ニュースを LLM でスコアリングし、リサーチ／戦略層へ利用できる形で提供する。
- 設計方針:
  - ルックアヘッドバイアス対策（date/timestamp の参照やクエリでの排他条件）
  - 冪等性（DB 保存は ON CONFLICT / UPSERT を活用）
  - フェイルセーフ（API 失敗時に処理を継続する）
  - 外部依存は最小限（標準ライブラリ + 必要ライブラリ）

## 主な機能一覧
- データ取得 / ETL
  - J-Quants API クライアント（株価、財務、上場銘柄、マーケットカレンダー）
  - 差分 ETL / 日次 ETL パイプライン（`run_daily_etl`）
- データ品質管理
  - 欠損・重複・スパイク・日付不整合チェック（`data.quality`）
- ニュース関連
  - RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去）
  - ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコアリング: `ai.news_nlp.score_news`）
- AI / レジーム判定
  - マクロニュース＋ETF（1321）の MA200 乖離を組み合わせた市場レジーム判定（`ai.regime_detector.score_regime`）
- リサーチ支援
  - ファクター計算（モメンタム / バリュー / ボラティリティなど）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - シグナル → 発注 → 約定までを追跡する監査用スキーマの初期化 / DB 作成（`data.audit`）
- 環境変数・設定管理（`config.Settings`）

## 必要条件
- Python 3.10 以上（型ヒントで `|` union を使用）
- 推奨パッケージ（最低限の例）
  - duckdb
  - openai
  - defusedxml

例（簡易）:
pip install duckdb openai defusedxml

（実際は requirements.txt / pyproject.toml をプロジェクトに合わせて用意してください）

## セットアップ手順
1. リポジトリをクローン
   - git clone <repo-url>

2. 開発環境にインストール（ソースツリーが `src/` レイアウトのため）
   - python -m pip install -e .

   または依存を個別にインストール:
   - python -m pip install duckdb openai defusedxml

3. 環境変数の準備
   - ルートに `.env` / `.env.local` を配置すると自動で読み込まれます（`config` モジュールがプロジェクトルートを .git または pyproject.toml を基準に探索して読み込みます）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN = (J-Quants リフレッシュトークン) — 必須
   - OPENAI_API_KEY = (OpenAI API キー) — ai モジュール利用時に必須
   - KABU_API_PASSWORD, KABU_API_BASE_URL — kabu ステーション API 関連
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - KABUSYS_ENV = development | paper_trading | live
   - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL

4. DuckDB 用ディレクトリ作成（必要なら）
   - mkdir -p data

## 使い方（コード例）
以下は最小限の使い方例です。実運用では例外処理やログ設定、監視を追加してください。

- ETL（日次パイプライン）を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定していれば api_key は省略可能
n_written = score_news(conn, target_date=date(2026,3,20))
print("scored:", n_written)
```

- 市場レジームスコア計算（1321 の MA200 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

conn = init_audit_db(settings.duckdb_path)  # transactional=True 相当の初期化処理が行われます
```

- 設定の利用例
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

## 実装上の注意点（簡単なガイド）
- AI系（news_nlp / regime_detector）は OpenAI の JSON mode（gpt-4o-mini など）を利用します。API エラーやパースエラー時はフォールバック値（0.0 等）を使う実装です。
- ETL/保存処理は冪等（ON CONFLICT / DO UPDATE）で実行されます。既存データの更新を前提としています。
- 日付・時間の取扱い:
  - raw_news.datetime は UTC naive で保存される想定。
  - audit モジュールはタイムゾーンを UTC に設定します（SET TimeZone='UTC'）。
- テスト時に環境変数自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## ディレクトリ構成（主要ファイル）
(リポジトリの src/kabusys 以下を抜粋)

- src/kabusys/
  - __init__.py
  - config.py                         -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     -- ニュースを銘柄ごとにスコアリング（OpenAI）
    - regime_detector.py              -- マクロ + ETF MA200 で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント & DuckDB 保存
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - etl.py                          -- ETLResult の再エクスポート
    - news_collector.py               -- RSS 取得・前処理・保存
    - calendar_management.py          -- 市場カレンダー管理、営業日判定
    - quality.py                      -- データ品質チェック
    - stats.py                        -- 汎用統計（Zスコア正規化等）
    - audit.py                         -- 監査ログスキーマの定義・初期化
  - research/
    - __init__.py
    - factor_research.py              -- モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py          -- 将来リターン・IC・統計サマリ等

各モジュールはドキュメンテーション文字列で詳しい動作・設計方針が記載されています。関数単位での利用方法や引数の意味は各ファイル先頭の docstring を参照してください。

## ロギング / 実行時設定
- 環境変数 `LOG_LEVEL` でログレベルを指定できます（デフォルト: INFO）。
- `KABUSYS_ENV` により挙動（開発/ペーパー/本番）を切り替えることができます。値は `development`, `paper_trading`, `live` のいずれか。

## テストとモック
- OpenAI 呼び出しやネットワーク I/O 部分はテスト時に差し替え可能な設計（内部 `_call_openai_api` を patch する等）になっています。
- news_collector の URL 開放・リダイレクト処理等は `_urlopen` をモックできます。

---

必要があれば、README に含めるコマンド例（Docker / CI / 詳細な環境変数一覧 / サンプル .env.example）や、API の入出力スキーマ（DB テーブル定義抜粋）を追加で作成します。どの情報を追記しますか？