# KabuSys

日本株向けのデータプラットフォーム＆自動売買基盤ライブラリ（モジュール群）。  
ETL（J-Quants → DuckDB）・ニュース収集・LLM を用いたニュース／レジーム解析・因子計算・監査ログなど、アルゴリズムトレーディング研究と運用に必要な主要コンポーネントを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持った Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集とニュース本文の前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別）とマクロセンチメント → 市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ（将来リターン／IC／サマリー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定までの監査テーブル（監査ログ）初期化ユーティリティ
- J-Quants クライアント（レートリミット・リトライ・トークン自動リフレッシュ対応）

設計上の特徴：
- ルックアヘッドバイアス対策（内部で date.today() を不用意に参照しない等）
- DuckDB を中心に SQL を活用した効率的処理
- 冪等的な保存（ON CONFLICT / INSERT ... DO UPDATE）やトランザクション制御
- フェイルセーフ／部分失敗許容（API 失敗時はスキップして継続等）

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価（日次 OHLCV）、財務、マーケットカレンダーを取得（pagination / rate limit 対応）
  - 差分更新、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- ニュース収集
  - RSS 取得（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
  - raw_news/ news_symbols テーブルへの冪等保存サポート
- ニュース NLP（AI）
  - 銘柄ごとのニュースをまとめて LLM に送りセンチメント（ai_scores）を生成（score_news）
  - マクロ記事 + ETF（1321）200日 MA 乖離を合成し市場レジーム（bull/neutral/bear）を判定（score_regime）
  - OpenAI 呼び出しはリトライ・パース保護あり
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー、Zスコア正規化ユーティリティ
- データ品質
  - 欠損・スパイク・重複・日付不整合検出（QualityIssue オブジェクトで集約）
- 監査ログ
  - signal_events / order_requests / executions の DDL とインデックスを初期化するユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env（ルートの .env / .env.local）を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト経由で設定値取得（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）

---

## セットアップ手順

前提
- Python 3.9+（typing の Union | 形式や型アノテーションを利用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

推奨インストール手順（例）

1. 仮想環境作成と有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要ライブラリのインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは requirements.txt を用意している想定です：
   - pip install -r requirements.txt

3. リポジトリルートに .env を作成（下記の「環境変数」参照）

4. DuckDB データディレクトリを作成（settings.duckdb_path デフォルトは data/kabusys.duckdb）
   - mkdir -p data

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- KABU_API_PASSWORD: kabu API パスワード（必要に応じて）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用（必要に応じて）
- DUCKDB_PATH (省略可): DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH (省略可): 監視用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV: development|paper_trading|live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

例 .env ファイル（最小）
```
JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
OPENAI_API_KEY=あなたの_openai_api_key
KABU_API_PASSWORD=（必要なら）
SLACK_BOT_TOKEN=（必要なら）
SLACK_CHANNEL_ID=（必要なら）
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロードの振る舞い
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml が見つかる場所）から `.env`、続けて `.env.local` を自動で読み込みます。
- テスト等で自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（代表的な例）

以降の例は Python スクリプト／REPL で実行する想定です。

共通：settings と DuckDB 接続取得
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄別）をスコア化（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を引数で渡すことも可能（None の場合は OPENAI_API_KEY 環境変数を参照）
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

3) 市場レジーム判定（ETF 1321 の MA200 + マクロセンチメント）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db
# ファイル: data/audit.duckdb を作成してテーブルを初期化
audit_conn = init_audit_db("data/audit.duckdb")
```

5) 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの dict のリスト
```

ログレベルは環境変数 `LOG_LEVEL` で調整します（例: LOG_LEVEL=DEBUG）。

注意点
- OpenAI や J-Quants へアクセスする関数は api_key / refresh_token を引数で注入できるため、テスト時はモック注入が容易です。
- AI 呼び出しはリトライやフォールバック（失敗時は 0.0 など）を備えていますが、API 利用にはコスト・レート制限があるため注意してください。
- DuckDB の executemany にはバージョン差異の注意点がコード内に記載されています（空パラメータでの呼び出し回避等）。

---

## ディレクトリ構成（src/kabusys）

主なファイルと役割：

- kabusys/
  - __init__.py                — パッケージ定義（バージョン）
  - config.py                  — 環境変数 / 設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（銘柄別）処理
    - regime_detector.py       — マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETL の公開型（ETLResult の再エクスポート）
    - news_collector.py        — RSS ニュース収集（SSRF 対策等）
    - calendar_management.py   — 市場カレンダー管理（営業日判定等）
    - quality.py               — データ品質チェック
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査ログ（DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - ai/、data/、research/ が主要な機能ドメインです。

（プロジェクトルート）
- .env / .env.local （環境変数）
- pyproject.toml / setup.cfg / requirements.txt 等（配布用メタ情報、リポジトリに応じて存在）

---

## 開発・運用上の注意

- テスト：AI/API 呼び出し部分はモックしやすい設計（内部 _call_openai_api 等を patch）になっています。ユニットテストでは外部依存をスタブ化してください。
- レート制限：J-Quants には 120 req/min の制約があるため、jquants_client は内部で固定間隔レートリミッタを使用しています。大量取得や並列化には注意してください。
- セキュリティ：
  - news_collector は SSRF 対策・XML 安全処理（defusedxml）・レスポンスサイズ制限を実装しています。
  - .env に秘密情報を置く際はアクセス制御に気をつけてください。
- 運用モード：KABUSYS_ENV は development / paper_trading / live をサポート。is_live/is_paper/is_dev プロパティでモード判定できます。

---

必要であれば README に以下の追加を出力できます：
- 具体的な requirements.txt の推奨内容
- より多くの利用例（ETL スケジューリング例、Slack 通知の使用方法、DuckDB スキーマ定義）
- CI / テストのセットアップ手順

どの追加情報を載せますか？