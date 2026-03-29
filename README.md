# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集・AI を用いたニュースセンチメント評価・市場レジーム判定・リサーチ用ファクター計算・監査ログ（トレーサビリティ）など、システム全体の基盤機能を提供します。

---

## 主な機能（抜粋）

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分取得、バックフィル、ページネーション、レートリミット、トークン自動更新、冪等保存（ON CONFLICT）
- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付不整合（未来日／非営業日）を検出
- ニュース収集
  - RSS 取得・前処理・SSRF 防御・トラッキングパラメータ除去・raw_news への冪等保存
- AI（OpenAI）連携
  - ニュースを銘柄ごとにまとめて LLM でセンチメント評価（ai_scores テーブルへ）
  - マクロニュース + ETF（1321）200日 MA乖離を組み合わせた市場レジーム判定（bull/neutral/bear）
  - API 呼び出しはリトライ・バックオフを備えフェイルセーフで動作
- 監査ログ（Audit）
  - signal → order_request → execution の一連の流れを UUID でトレースできるテーブル定義・初期化
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン、IC・統計サマリー、Zスコア正規化

---

## 必要な環境・前提

- Python 3.10+
  - 依存: duckdb, openai, defusedxml （コード内で urllib 等の標準ライブラリも使用）
- DuckDB をデータベースとして使用（デフォルト DB パスは data/kabusys.duckdb）
- OpenAI API キー（AI 機能を使う場合）
- J-Quants リフレッシュトークン（ETL 用）

---

## 環境変数（主要）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。

必須（機能を使う場合）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知等を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID（通知先）
- KABU_API_PASSWORD — kabuステーション API のパスワード（注文機能を使うとき）

OpenAI 関連
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）

その他（デフォルトあり）
- KABU_API_BASE_URL — kabu API の base URL（デフォルト `http://localhost:18080/kabusapi`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト `data/monitoring.db`）
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL — ログレベル: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`

設定値が未設定の場合はモジュールの `kabusys.config.settings` から確認できます。

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUS_API_PASSWORD=passw0rd
KABUSYS_ENV=development
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用）
   - 開発インストール: pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を設定
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

5. データディレクトリを作る（必要に応じて）
   - mkdir -p data

---

## 使い方（サンプル）

以下はライブラリの主な利用例（Python REPL / スクリプト内で実行）。

- 日次 ETL の実行（DuckDB 接続を渡す）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアの作成（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026,3,20), api_key="sk-xxxxx")
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-xxxxx")
```

- 監査ログ DB 初期化（専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーン設定が行われます
```

- リサーチ用ファクター計算（例：モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の dict のリスト
```

注意点:
- AI 呼び出しは外部 API（OpenAI）に対するネットワーク通信を行います。ユニットテスト時は各モジュール内の _call_openai_api をモックする想定です。
- ETL / データ処理は DuckDB のスキーマ（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_calendar 等）を前提としています。スキーマ作成/初期化は別途用意してください（プロジェクトに schema 初期化ユーティリティがあれば利用）。

---

## 開発メモ / 設計方針（要約）

- Look-ahead bias（将来情報の使用）を避ける設計
  - 日付処理は target_date を引数で受け取り、内部で date.today() を参照しない関数が多い
  - prices_daily のクエリは date < target_date 等でルックアヘッドを防止
- API 呼び出しは堅牢化（リトライ・指数バックオフ・フェイルセーフ）
- DuckDB への保存は冪等（ON CONFLICT）で安全に更新
- ニュース収集は SSRF・XML Bomb 対策を実装
- 監査ログは削除せずトレース可能に保存（UUID 連鎖・created_at/updated_at）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを銘柄ごとに集約し OpenAI でセンチメントを算出して ai_scores に書き込む
    - regime_detector.py — ETF(1321) 200日 MA とマクロニュース LLM を合成して市場レジームを判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック含む）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL 用型の再エクスポート（ETLResult）
    - news_collector.py — RSS 収集・前処理・保存
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py — 汎用統計ユーティリティ（Zスコア正規化等）
    - audit.py — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー、ランク関数など

各モジュールはドキュメント文字列に設計方針や処理フロー、例外処理方針などが詳細に記載されています。まずは該当モジュールの docstring を参照してください。

---

## テスト・モックについて

- OpenAI 呼び出し部はテスト時にモックすることを想定しています（各モジュール内で _call_openai_api を分離実装しているため、patch しやすい）。
- news_collector のネットワーク IO はテスト時に _urlopen をモックして置き換えられます。
- J-Quants API は get_id_token / _request レイヤーをモックして ETL のロジックを検証できます。

---

この README はコードベースの主要機能をまとめたものです。より詳細な仕様やスキーマ、運用手順（cron ジョブ、監視・アラート、バックテストでのデータ準備等）は別途ドキュメント（Design/Platform md）を参照してください。必要であれば README に追加する内容（例: example .env.example の具体例、schema 初期化手順、CI/CD 指示など）を教えてください。