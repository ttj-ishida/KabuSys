# KabuSys

日本株向けの自動売買／データ基盤ライブラリセットです。  
J-Quants / RSS / OpenAI を中心にデータ収集・ETL・品質チェック・特徴量計算・ニュースNLP・市場レジーム判定・監査ログ（トレーサビリティ）を提供します。

## 主な特徴
- データETL（J-Quants 経由）
  - 株価（日足）、財務データ、JPX カレンダーを差分取得・冪等保存
  - ページネーション・レート制御・トークン自動リフレッシュ対応
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出と QualityIssue レポート
- ニュース収集・前処理
  - RSS 取得、URL 正規化、SSRF 対策、前処理
- ニュースNLP（OpenAI）
  - 銘柄単位のニュースセンチメントを ai_scores に書き込む（gpt-4o-mini）
  - バッチ処理、JSON Mode、リトライ・バックオフ実装
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離 + マクロニュース LLM による判定（bull/neutral/bear）
- 研究用モジュール
  - モメンタム、バリュー、ボラティリティ等のファクター計算、将来リターン、IC、統計サマリ
- 監査ログ（audit）
  - signal → order_request → execution の階層で冪等・トレーサビリティを保証する監査スキーマ
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）、環境変数で主要設定を管理

---

## セットアップ

前提
- Python 3.10 以上（type union (`X | Y`) を使用）
- DuckDB を利用します（pip パッケージ `duckdb`）
- OpenAI API を利用する場合は `openai`、RSS の XML 安全パースに `defusedxml` 等

例: 必要なパッケージ（プロジェクトに requirements.txt があればそちらを利用してください）
```
pip install duckdb openai defusedxml
```

設定ファイル（.env）
- プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector で使用）
  - KABU_API_PASSWORD: kabuステーション API パスワード
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用途の sqlite DB（デフォルト: data/monitoring.db）
  - PID_FILE_PATH / KILL_FLAG_PATH 等の監視設定
  - KABUSYS_ENV: 開発/ペーパートレード/ライブの切替 (`development`, `paper_trading`, `live`)
  - LOG_LEVEL: ログレベル（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）

例: `.env`（最小）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な操作例）

まず DuckDB 接続と設定を用意します:

```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)
```

日次 ETL の実行（市場カレンダー・株価・財務の差分取得と品質チェック）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

ニュースセンチメントスコア（ai_scores）作成:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは OPENAI_API_KEY 環境変数、または api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

市場レジーム判定（market_regime テーブル書き込み）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログ（監査DB）初期化:
```python
from kabusys.data.audit import init_audit_db
db = init_audit_db("data/audit.duckdb")  # ":memory:" も可能
# 返り値は初期化済みの duckdb 接続
```

設定の参照:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

注意事項:
- AI 関連機能は OpenAI API 呼び出しを行うため、API キーと通信環境が必要です。API 呼び出しはリトライやフェイルセーフが組み込まれており、失敗時は 0 やスキップで続行する実装です。
- ETL / 研究モジュールは DuckDB 内のテーブル構造（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, prices_daily など）を前提としています。実行前にスキーマ準備が必要です（ETL は save_* 関数で ON CONFLICT を使用した冪等保存を行います）。

---

## ディレクトリ構成（主要ファイル）

概略: src/kabusys 以下

- __init__.py
  - パッケージエクスポート（data, strategy, execution, monitoring）
- config.py
  - 環境変数管理・.env 自動読み込み・Settings クラス
- ai/
  - __init__.py (news_nlp のエクスポート)
  - news_nlp.py: ニュースセンチメント解析（score_news）
  - regime_detector.py: 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（fetch_* / save_*）
  - pipeline.py: ETL パイプライン（run_daily_etl 他）
  - etl.py: ETLResult の公開
  - stats.py: 統計ユーティリティ（zscore_normalize）
  - quality.py: データ品質チェック（check_missing_data, check_spike, ...）
  - news_collector.py: RSS 取得・前処理（fetch_rss 等）
  - calendar_management.py: 市場カレンダー管理（is_trading_day, next_trading_day, calendar_update_job）
  - audit.py: 監査スキーマ初期化（init_audit_schema, init_audit_db）
- research/
  - __init__.py
  - factor_research.py: calc_momentum, calc_value, calc_volatility
  - feature_exploration.py: calc_forward_returns, calc_ic, factor_summary, rank

（上記は抜粋です。実装内にさらに詳細な関数・ユーティリティが含まれます。）

---

## 開発上のヒント / 注意点
- 自動 .env 読み込みは project root (.git or pyproject.toml) を基準に行います。テストなどで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API 呼び出しや DB 書き込みは冪等性を重視していますが、初期スキーマの作成や監査DB 初期化は明示的に行ってください（例: init_audit_db）。
- LLM 呼び出しは外部 API へのアクセスを伴うため、コストとレート制限に注意してください。news_nlp / regime_detector はリトライとバックオフを実装していますが、プロダクション運用時はバッチ化や費用対策を検討してください。
- DuckDB に保存される日付／タイムスタンプは設計上 UTC を意識して扱われます。news_collector では RSS の日時を UTC naive に変換して保存しています。

---

この README はコードベースの主要機能と使い方の概略を示しています。より詳細な API 仕様やスキーマ、運用手順（デプロイ、監視、ジョブスケジューリング等）は別ドキュメント（Design/Platform 文書）を参照してください。必要であれば README を環境別（開発/ステージング/本番）に分けた手順や具体的な SQL スキーマ定義の抜粋も作成します。