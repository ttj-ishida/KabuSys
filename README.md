# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
市場データのETL、ニュースの収集・NLPスコアリング、ファクター計算、監査ログ・取引監視、AIを用いた市場レジーム判定などを組み合わせて、研究から実運用までを支援します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の用途を想定した Python パッケージです。

- J-Quants API を利用した株価・財務・マーケットカレンダーの差分取得（ETL）
- RSS ベースのニュース収集と前処理（SSRF対策・正規化・冪等保存）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント分析（銘柄別）およびマクロセンチメントを組み合わせた市場レジーム判定
- DuckDB を用いたデータ格納・集計（ETL の保存は冪等）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック、監査ログ（シグナル→注文→約定のトレーサビリティ）
- 設定管理（.env / 環境変数の自動読み込み・保護）

設計上の特徴として、ルックアヘッドバイアス回避のために「現在時刻を暗黙に参照しない」実装方針が徹底されています（各関数は target_date を明示的に受け取ります）。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（無効化可）
  - 必須環境変数のラップ（settings オブジェクト）

- データプラットフォーム（data）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（取得・保存・トークン自動リフレッシュ・レート制御）
  - マーケットカレンダー管理（営業日判定 / next/prev_trading_day）
  - ニュース収集（RSS、URL 正規化、SSRF 対策、前処理）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions テーブル、初期化ユーティリティ）
  - 汎用統計ユーティリティ（zscore 正規化）

- 研究モジュール（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI モジュール（ai）
  - ニュース NLP（銘柄別センチメントを ai_scores に保存する score_news）
  - 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュースセンチメントの組合せで日次判定：score_regime）
  - OpenAI 呼び出しはリトライやJSONモードの考慮あり

---

## 前提 / 必要環境

- Python 3.10+（typing の union 等を利用）
- 必須ライブラリ（例）
  - duckdb
  - openai (OpenAI Python SDK v1 系を想定)
  - defusedxml
- そのほか標準ライブラリを多数使用

インストール例（仮）:
```bash
python -m pip install duckdb openai defusedxml
# またはプロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください
```

---

## 環境変数（主なもの）

KabuSys は .env/.env.local もしくは環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
  - KABU_API_PASSWORD     : kabuステーション API 用パスワード（発注系を使う場合）
  - SLACK_BOT_TOKEN       : Slack 通知を使う場合の Bot トークン
  - SLACK_CHANNEL_ID      : Slack チャンネル ID
- OpenAI
  - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 等で使用）
- 任意 / デフォルトあり
  - KABUSYS_ENV           : "development" | "paper_trading" | "live" （デフォルト: development）
  - LOG_LEVEL             : ログレベル（DEBUG, INFO, ... デフォルト: INFO）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用 SQLite パスなど（デフォルト: data/monitoring.db）

.env の書き方は "KEY=value"、クォートやコメントにも対応します。`.env.local` は OS 環境変数より優先して上書きされます（ただし OS 側のキーは protected されるため意図しない上書きを防止）。

---

## セットアップ手順（簡易）

1. ソースを入手・配置
   - git clone などでプロジェクトを取得

2. Python 環境を準備
   - Python 3.10+ の仮想環境を作成し有効化
   - 必要パッケージをインストール（例: duckdb, openai, defusedxml）

3. 環境変数を設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成
   - 必須トークンを設定する（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABU_API_PASSWORD=your_password
     ```
   - 自動ロードを無効化したい場合:
     ```
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB データベースの準備（初回）
   - デフォルトは `data/kabusys.duckdb`（settings.duckdb_path）
   - 必要に応じて監査DBを初期化:
     ```python
     import duckdb
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db(settings.duckdb_path)  # 監査専用DBを作る場合は別パスを指定
     ```
     または既存の DuckDB 接続に監査スキーマを追加:
     ```python
     conn = duckdb.connect(str(settings.duckdb_path))
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（代表的な例）

※以下は簡単なスニペット例です。実行には適切な環境変数とネットワークアクセス（J-Quants, OpenAI）が必要です。

- DuckDB 接続と settings 利用例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（市場カレンダー・株価・財務・品質チェック）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を明示的に渡す（バイアス防止のため）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別スコアを ai_scores に保存）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定しておく
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written: {n_written}")
```

- 市場レジーム判定（score_regime）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
# market_regime テーブルに結果が書き込まれます
```

- ファクター計算 / 研究系関数:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

- 監査ログ初期化（監査DBを分けて管理する場合の例）:
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_db = Path("data/audit.duckdb")
audit_conn = init_audit_db(audit_db)
# audit_conn で signal_events / order_requests / executions テーブルが作成される
```

- 設定の明示的参照:
```python
from kabusys.config import settings
print(settings.env, settings.log_level, settings.duckdb_path)
```

---

## 開発時の注意 / テストのヒント

- AI 呼び出し（OpenAI）を含む関数は内部で _call_openai_api のようなヘルパーを使っています。ユニットテストではこの関数を patch/mocking して外部APIへの実際の呼び出しを防いでください。
- .env 自動読み込みはプロジェクトルート検出に依存します。テスト実行時に意図しない環境読み込みを避けるため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用できます。
- DuckDB の executemany は空リストを受け付けないバージョン制約（記載あり）に注意。モジュール実装ではこの点に配慮されていますが、直接の呼び出しでは確認してください。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主なモジュールと役割の概観です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env ロード・settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース記事の集約・OpenAI による銘柄別センチメント算出（score_news）
    - regime_detector.py    — ETF(1321)のMA乖離とマクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存・トークン管理・レート制御）
    - pipeline.py          — ETL パイプラインと run_daily_etl など
    - etl.py               — ETL 結果クラスの再エクスポート
    - calendar_management.py — JPX カレンダー管理、営業日判定、calendar_update_job
    - news_collector.py    — RSS 収集、URL 正規化、SSRF 対策
    - quality.py           — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py             — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py             — 監査ログスキーマ定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py   — モメンタム/ボラティリティ/バリュー系ファクター計算
    - feature_exploration.py — 将来リターン計算、IC、rank、factor_summary

（各モジュールは README 内の「機能一覧」やソース内の docstring に詳細な設計方針・挙動が記載されています）

---

## ライセンス・貢献

- ライセンス情報はプロジェクトルートの LICENSE / pyproject.toml を参照してください（ここでは記載がありません）。
- 機能追加やバグ修正は Pull Request を通じて行ってください。外部 API キーや機密情報は決して公開リポジトリに含めないでください。

---

README に記載した操作はコードベースの現状に基づく説明です。実行・運用する際は各 API の利用規約とレート制限、セキュリティ（トークン管理、アクセス制限）に十分注意してください。必要であれば、README に実行スクリプトや cron / job 定義の例（systemd timer / cron / Airflow など）を追加できます。希望があれば追加で作成します。