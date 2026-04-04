# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（order/signal/execution）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・カレンダーの差分取得と DuckDB への冪等保存
- RSS ニュース収集と OpenAI を用いた銘柄／マクロのセンチメント評価
- 日次 ETL パイプライン（品質チェック含む）
- 市場レジーム判定（ETF MA と LLM センチメントの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ用テーブル初期化（信頼できるトレーサビリティ）

設計上の主要な方針：
- ルックアヘッドバイアスを避ける（内部で date.today() を使わない箇所が多い）
- DuckDB を中心にローカルで完結する ETL / 研究ワークフロー
- OpenAI（gpt-4o-mini）との連携は冗長なリトライとフォールバックを備える
- 各種処理はフェイルセーフで部分失敗を許容し他処理を継続する

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - カレンダー管理（is_trading_day, next_trading_day, calendar_update_job）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news：銘柄ごとのセンチメント）
  - 市場レジーム判定（score_regime：ETF MA とマクロセンチメントの合成）
- research/
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（forward returns, IC, factor summary, rank）
- config
  - 環境変数読み込み・管理（自動的に .env, .env.local をロード）
  - settings オブジェクトで簡単に設定取得

---

## セットアップ手順

前提
- Python 3.10 以上

1. リポジトリをクローン（省略）

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。上記は主要依存のみの例です。）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

5. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で未指定時に参照）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必要に応じて）
   - KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用（任意）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 sqlite パス（デフォルト data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, その他監視関連設定（オプション）
   - LOG_LEVEL, KABUSYS_ENV（development, paper_trading, live）

   settings クラスでデフォルト値やバリデーションが見えますので、必要に応じて参照してください。

---

## 使い方（代表的な例）

以下は Python インタラクティブやスクリプトから呼び出す例です。

1) DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2）ニュースをスコアリング（銘柄別 ai_scores へ書き込み）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数に設定されていれば api_key は省略可能
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

3）市場レジームを判定して DB に保存
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4）監査ログ用 DB を初期化する
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn を使って監査テーブルにアクセスできます
```

5）カレンダー更新ジョブを単独で実行
```python
import duckdb
from datetime import date
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved", saved)
```

注意点：
- score_news / score_regime は OpenAI API を呼びます。api_key を関数引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- run_daily_etl は J-Quants の id_token を内部で取得するため JQUANTS_REFRESH_TOKEN が必要です。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）が事前に用意されていることを想定しています。ETL の save_* は ON CONFLICT DO UPDATE を使うため冪等に保存できます。

---

## 重要な実装・設計メモ

- 環境変数の自動ロード
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を起点に `.env` → `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env > .env.local（.env.local は override=True のため .env を上書き）
  - 自動読み込み停止: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- LLM 呼び出し
  - OpenAI の JSON Mode を利用して厳密な JSON を期待する実装（パース失敗時はフォールバック処理あり）
  - レート・再試行ロジックを備えていて、致命的な失敗時はスキップして続行する設計（フェイルセーフ）

- J-Quants クライアント
  - 固定間隔レートリミッタ（120req/min）
  - 401 時はトークン自動リフレッシュ
  - ページネーション対応、指数バックオフによるリトライ

- データ品質チェック
  - ETL 後に run_all_checks を実行して欠損 / スパイク / 重複 / 日付不整合を検出
  - QualityIssue で詳細を収集し、呼び出し側が重大度に応じた対処を行える

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     -- ニュースセンチメント（銘柄別）
    - regime_detector.py              -- マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント（fetch/save）
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - etl.py                          -- ETL 再エクスポート（ETLResult）
    - calendar_management.py          -- 市場カレンダー管理
    - news_collector.py               -- RSS ニュース収集
    - quality.py                      -- データ品質チェック
    - stats.py                        -- 統計ユーティリティ（zscore_normalize）
    - audit.py                        -- 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py              -- モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py          -- forward returns / IC / summary

---

## 開発者向け・テスト時のヒント

- テストで環境変数の自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分は内部で `_call_openai_api` をラップしているため、unit test ではこれを patch して外部 API をモックできます（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- news_collector のネットワーク処理は `_urlopen` をモックすることでネットアクセスを防げます。
- DuckDB を :memory: で使うとテストが軽くなります（init_audit_db(":memory:") など）。

---

## ライセンス / 貢献

（このテンプレートではライセンス情報は含めていません。実プロジェクトでは LICENSE ファイルを追加してください。）

---

README に記載されている API や設定について不明点があれば、どの機能の詳細が必要か教えてください。使用例やスキーマ（期待する DuckDB テーブル定義）の追加も可能です。