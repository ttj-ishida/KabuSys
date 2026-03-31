# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
DuckDB を用いたデータプラットフォーム、J-Quants API 経由の ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算や監査ログなど、トレーディングシステムの基礎機能を提供します。

---

## 主な特徴（機能一覧）

- 環境変数／.env 自動読み込みと設定管理（kabusys.config）
- J-Quants API クライアント（差分取得・ページネーション対応・リトライ・レート制御）
  - 株価日足（OHLCV）、財務データ、JPX カレンダー、上場銘柄情報取得
  - DuckDB への冪等保存（ON CONFLICT による上書き）
- ETL パイプライン（data.pipeline）
  - run_daily_etl による市場カレンダー／株価／財務の差分取得と品質チェック
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）およびニュース NLP スコアリング（OpenAI）
  - RSS の SSRF 対策、URL 正規化、記事ID生成、raw_news / news_symbols 管理
  - gpt-4o-mini を用いた JSON Mode での銘柄別センチメント取得（batch 処理、リトライ、バリデーション）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン計算、IC・統計サマリー）
- 監査ログ（audit）：シグナル→発注→約定をトレースするテーブル定義と初期化ユーティリティ
- 汎用統計ユーティリティ（Zスコア正規化等）

---

## 要件（主な依存パッケージ）

- Python 3.10+（型アノテーションに union 表記等を使用）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

（プロジェクトに requirements.txt がある場合はそちらを優先してください）

---

## 環境変数（.env / .env.local）

このプロジェクトは起動時にプロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` / `.env.local` を自動読み込みします。OS 環境変数が優先され、`.env.local` は `.env` を上書きできます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト時に使用）。

主に使用する環境変数例:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネルID（必須）
- DUCKDB_PATH — データ用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例（.env.example）
```
# .env.example
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=xxxx
KABU_API_PASSWORD=xxxx
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - 最低限:
     - pip install duckdb openai defusedxml
   - 開発・配布が用意されていれば:
     - pip install -e .

   （requirements.txt があれば: pip install -r requirements.txt）

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を直接設定してください。
   - 重要なキー: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

4. DuckDB データベース用ディレクトリ作成（必要なら）
   - デフォルトの DUCKDB_PATH は `data/kabusys.duckdb`。親ディレクトリを作成しておくと安全です。

---

## 使い方（主な利用例）

下記は Python から直接利用するサンプルです。logging は必要に応じて設定してください。

- DuckDB 接続の作成（ファイル or :memory:）
```python
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))  # ファイル DB
# または
# conn = duckdb.connect(":memory:")
```

- 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース（AI）スコアリング
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを引数で渡すか、環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# 既存 conn に対してテーブル追加したい場合は init_audit_schema(conn)
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

- ニュース収集（RSS）例
（実装は network / RSS の制約に注意）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
```

---

## 開発・運用時の注意点

- Look-ahead bias の防止:
  - 多くの関数は内部で datetime.today() を直接参照しない設計（target_date 引数を明示的に与えることを推奨）。
  - データ取得やスコア計算は target_date 未満／以前のデータのみを用いるよう配慮されています。

- API キーや外部アクセス:
  - J-Quants / OpenAI の API 呼び出しはリトライ・レート制御・フェイルセーフ（失敗時はスコアを 0.0 にフォールバック等）を備えています。
  - OpenAI 呼び出しは JSON Mode を想定したパース検証を行っていますが、レスポンスの差異（パースエラー）には注意してください。

- テスト:
  - 自動 .env ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（ユニットテスト等で便利）。
  - OpenAI 呼び出し部分は内部関数をモックしやすい設計（_call_openai_api の差し替え等）になっています。

---

## ディレクトリ構成（高レベル）

プロジェクトの主要ファイル／モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（アプリ設定）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの銘柄別センチメントスコア生成（OpenAI）
    - regime_detector.py
      - 市場レジーム判定ロジック（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save 系）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 収集、記事前処理、SSRF 対策
    - calendar_management.py
      - 市場カレンダー管理・営業日判定・calendar_update_job
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ（シグナル・発注・約定）スキーマ定義と初期化
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility / Liquidity 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC (Spearman) 計算、統計サマリー、ランク変換

---

## 付録：よくある操作

- デバッグログを有効にする:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

- OpenAI のレスポンスが安定しない場合は少量のバッチ（_BATCH_SIZE）やリトライ設定を調整してください（news_nlp.py / regime_detector.py の定数）。

---

README は以上です。その他、特定の使い方（例：CI での ETL 実行スクリプト、kabuステーションとの接続例、Slack 通知連携等）のドキュメントが必要であれば、その用途に合わせたサンプルと手順を追加します。どの部分を優先して詳述しましょうか？