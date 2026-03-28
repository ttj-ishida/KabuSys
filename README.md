# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取り込み）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（監査テーブル初期化）など、取引システムの基盤機能を提供します。

## プロジェクト概要
- ETL：J-Quants API から株価（日足）、財務、マーケットカレンダー等を差分取得して DuckDB に保存するパイプライン（冪等・リトライ・レート制御）。
- ニュース収集：RSS フィードを安全に取得して raw_news に保存（SSRF 対策・トラッキング除去・ID ハッシュ化）。
- ニュースNLP：OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント算出（ai_scores へ保存）。
- レジーム判定：ETF（1321）の MA200 とマクロニュースセンチメントを合成して日次の市場レジームを判定・保存。
- 研究用ユーティリティ：モメンタム・バリュー・ボラティリティ等のファクター計算、将来リターン・IC・統計サマリー等。
- 品質チェック：データ品質（欠損・スパイク・重複・日付不整合）検出。
- 監査ログ：シグナル→発注要求→約定までをトレースする監査テーブルの DDL と初期化機能。

設計上の特徴：
- Look-ahead バイアス対策（date を明示的に扱い、date.today()/datetime.today() の無条件参照を避ける等）。
- DuckDB を中心に SQL と最小限の標準ライブラリで実装。
- 外部 API 呼び出しはリトライ・バックオフ・レートリミッタ等の堅牢性を考慮。

## 主な機能一覧
- data/jquants_client.py：J-Quants 取得・保存（fetch / save）・認証管理（トークン自動リフレッシュ・ページネーション対応）
- data/pipeline.py：日次 ETL のエントリポイント run_daily_etl、個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
- data/news_collector.py：RSS 取得・前処理・raw_news への保存
- ai/news_nlp.py：銘柄別ニュースのバッチセンチメントスコア算出（score_news）
- ai/regime_detector.py：ETF MA200 とマクロニュースを用いた市場レジームスコア算出（score_regime）
- research/*.py：ファクター計算（momentum/value/volatility）、特徴量解析（forward returns / IC / summary）
- data/quality.py：データ品質チェック群（run_all_checks 等）
- data/audit.py：監査ログ DDL / init_audit_db / init_audit_schema
- config.py：環境変数管理（.env 自動ロード、必須項目チェック、環境 / ログレベル判定）

## 必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu ステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID : 通知先 Slack チャンネル ID（必須）
- OPENAI_API_KEY : OpenAI 呼び出し用 API キー（score_news / score_regime で必要）
- KABUSYS_ENV : 環境。`development` / `paper_trading` / `live` のいずれか（デフォルト: development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する場合に `1` を設定

config.py はプロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます。優先順位は OS 環境変数 > .env.local > .env です。

## セットアップ手順（例）
1. Python のインストール（推奨: 3.10+）
2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクト配布に pyproject.toml / requirements.txt があればそれに従ってください）
4. プロジェクトルートに .env を作成する（自動ロードを利用する場合）
   - 例: .env
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=CXXXXXXX
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
5. DuckDB の初期スキーマ（監査ログ等）を作成する場合はアプリ側から init_audit_db を呼ぶ（下記 使い方 を参照）

注意:
- OpenAI を利用する機能を使うには OPENAI_API_KEY が必要です。
- J-Quants の API レート制限を守る実装（RateLimiter）が組み込まれていますが、実際の運用では利用ポリシーに従ってください。

## 使い方（コード例）
以下はライブラリをインポートして各種処理を呼ぶ最小例です。実行は Python スクリプト/REPL で行います。

- DuckDB 接続の作成と ETL の実行例
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（settings.duckdb_path は Path オブジェクト）
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら env の OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（専用ファイルに監査テーブルを作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# init_audit_db はテーブルを作成した DuckDB 接続を返す
```

- 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

メモ：
- OpenAI 呼び出しは内部で retry/backoff を実装しています。テスト時には該当モジュールの _call_openai_api をモックして振る舞いを制御できます。
- run_daily_etl は各ステップでエラーハンドリングを行い、ETLResult に詳細を返します。

## .env の自動ロードについて
- config.py はプロジェクトルートにある `.env` と `.env.local` を自動的に読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 自動ロードは .git または pyproject.toml を親ディレクトリに見つけてプロジェクトルートを決定します。見つからない場合はロードをスキップします。

## ディレクトリ構成（主なファイル）
プロジェクトの主要ファイル/モジュール一覧（抜粋）：

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - stats.py
    - quality.py
    - audit.py
    - (その他: pipeline の補助モジュール等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - (strategy/, execution/, monitoring/ はパッケージ公開対象として __all__ にあるが実装は別途)

上記の各モジュールは役割ごとに分割されています。特に data/ 以下は ETL / 保存ロジック・品質チェックを担い、ai/ は OpenAI を使った NLP 処理を提供します。research/ は運用とは切り離した研究用ユーティリティです。

## 運用上の注意・ベストプラクティス
- 本リポジトリは本番（live）環境用の機能を持ちます。実際に発注や実トレードを行う構成では、`KABUSYS_ENV=live` を慎重に管理してください。
- OpenAI / J-Quants の API キーは安全に保管し、アクセス権を最小限にしてください。
- 自動 ETL はデータの差分取得を行いますが、初期ロードや障害復旧時はバックフィルの調整（backfill_days）や start date の指定を行ってください。
- データ品質チェック（data.quality.run_all_checks）を CI / バッチの一部として定期実行することを推奨します。
- テストでは API 呼び出し箇所（jquants_client._request、news_nlp/_call_openai_api、regime_detector/_call_openai_api、news_collector._urlopen など）をモックして外部依存を切り離してください。

---

必要であれば README に以下を追加します：
- 詳細な .env.example（例示）
- テーブルスキーマの簡易説明（raw_prices, raw_financials, raw_news, ai_scores, market_regime 等）
- CI / テスト実行方法（ユニットテストの実行例）
ご希望があれば追記します。