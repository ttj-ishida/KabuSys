# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（軽量プロトタイプ）。  
DuckDB を利用したデータプラットフォーム、J-Quants / RSS / OpenAI を組み合わせたデータ取得・NLP スコアリング・市場レジーム判定・リサーチ用ファクタ処理などのユーティリティを含みます。

主な目的は「データ取得 → 品質チェック → 特徴量（ファクター）計算 → シグナル生成 → 監査ログ」を一貫して扱える基盤を提供することです。

---

## 機能一覧（概要）

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出：.git / pyproject.toml）
  - 必須設定の取得ヘルパー
- データ取得 / ETL（J-Quants API）
  - 日次株価（OHLCV）・財務データ・JPX カレンダー取得（ページネーション対応、レート制限・リトライ）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック（QualityIssue を返す）
- ニュース収集・NLP（RSS → raw_news）
  - RSS フィード取得（SSRF 対策、gzip 制御、トラッキングパラメータ除去）
  - ニュースの前処理・ID 化・DB への冪等保存（news_collector）
- OpenAI を使った NLP スコアリング
  - 銘柄ごとのニュースセンチメント算出（news_nlp.score_news）
  - マクロセンチメントと ETF MA を合成した市場レジーム判定（ai.regime_detector.score_regime）
- 研究 (research)
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等
- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
- ユーティリティ
  - 統計ユーティリティ（zscore_normalize 等）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, calendar_update_job）

---

## 必要な環境変数

主要な環境変数（README に含める主要なもの）:

- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL      : kabu API のベース URL（省略時 "http://localhost:18080/kabusapi"）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot Token（必須）
- SLACK_CHANNEL_ID       : Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH            : DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（省略時 data/monitoring.db）
- KABUSYS_ENV            : 環境 ("development" | "paper_trading" | "live")（省略時 development）
- LOG_LEVEL              : ログレベル ("DEBUG" | "INFO" | ... )（省略時 INFO）
- OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector などで使用可能）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する場合に "1" を設定

注意: パッケージ起動時にプロジェクトルートが検出できる (src/kabusys/config._find_project_root) と .env / .env.local を自動で読み込みます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. Python 3.9+ を用意（コードは型注釈に Py3.10+ の書き方が含まれますが、3.9 以降で動作する設計を想定しています）。
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必須ライブラリをインストール（プロジェクトで requirements.txt が無ければ以下を参考に）
   - pip install duckdb openai defusedxml
   - その他必要に応じて（例: requests 等）。実行環境や拡張機能に応じて追加してください。
4. ソースをインストール（開発モード）
   - pip install -e .
     （pyproject.toml / setup がある場合。ない場合はパッケージディレクトリを PYTHONPATH に含めるか、プロジェクトルートから実行してください）
5. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動読み込みされます。
   - .env.example を参照して必須値（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD など）を設定してください。
6. DuckDB / 監査DB 初期化
   - 監査ログ専用 DB を作る場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit_duckdb.duckdb")

---

## 使い方（例）

下記は代表的なユースケースの簡単なコード例です。適宜 logging の設定や例外処理を追加してください。

- DuckDB に接続して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("/path/to/data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアして ai_scores テーブルへ書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定を行う

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
```

- 監査ログスキーマを初期化する（既存 DuckDB 接続へ）

```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- 研究モジュールでファクターを計算する

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
```

- 設定オブジェクトの利用

```python
from kabusys.config import settings
print(settings.duckdb_path)       # Path オブジェクト
print(settings.is_live)
```

---

## よく使う API のまとめ

- kabusys.config.settings — 環境設定を取得
- kabusys.data.pipeline.run_daily_etl — 日次 ETL のメインエントリ
- kabusys.data.jquants_client.* — J-Quants からの fetch / save 関数群
- kabusys.data.news_collector.fetch_rss — RSS 取得ユーティリティ
- kabusys.ai.news_nlp.score_news — ニュースに基づく銘柄ごとの AI スコア生成
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定（MA + マクロセンチメント）
- kabusys.data.audit.init_audit_schema / init_audit_db — 監査ログ初期化
- kabusys.research.* — ファクター計算 / 研究系ユーティリティ

---

## ディレクトリ構成（主なファイル）

（パッケージルート: src/kabusys）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント算出（OpenAI 呼び出し、バッチ処理・検証・DuckDB 書込）
  - regime_detector.py     — マクロセンチメント + ETF MA で市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETLResult の再エクスポート
  - news_collector.py      — RSS 収集・正規化・保存
  - calendar_management.py — 市場カレンダー・営業日判定・calendar_update_job
  - quality.py             — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py               — zscore_normalize 等の統計ユーティリティ
  - audit.py               — 監査ログテーブル定義と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py     — Momentum / Value / Volatility の計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー等

---

## 運用上の注意 / 設計上のポイント

- Look-ahead バイアス対策
  - module 内では date.today() / datetime.today() を不用意に参照しない設計（target_date を明示して処理）
  - データ取得・スコアリングは target_date 未満のデータのみを参照する等の制約を守る
- 冪等性
  - DB 保存は ON CONFLICT DO UPDATE / INSERT ... ON CONFLICT を用いて冪等に設計
- フェイルセーフ
  - 外部 API（OpenAI / J-Quants）の一時失敗はリトライやフォールバック（ゼロスコア）で処理を継続
- セキュリティ
  - RSS 取得に SSRF 対策、defusedxml を利用した XML パース、レスポンスサイズチェックなどを実施
- レート制限
  - J-Quants API 呼び出しは固定間隔の RateLimiter を用いて規定レートを遵守

---

## 開発 / テストについて

- 自動 .env 読み込みはプロジェクトルートを基準に行われます。テスト時に自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants などの外部 API 呼び出しはユニットテストではモック可能なように実装されています（内部呼び出し関数を patch して差し替えられます）。
- DuckDB を用いるためローカルでのテスト実行が容易です（:memory: も使用可能）。

---

必要に応じて、README にサンプル .env.example、requirements.txt、起動スクリプト（cron / systemd / GitHub Actions 用）などを追加すると運用が楽になります。追加で含めてほしい内容（例えば .env のテンプレートや具体的な SQL スキーマなど）があれば教えてください。