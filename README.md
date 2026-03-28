# KabuSys — 日本株自動売買基盤（README 日本語）

KabuSys は日本株向けのデータプラットフォーム・リサーチ・監査・AI支援モジュールを含む自動売買基盤のコードベースです。本リポジトリは ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター算出、データ品質チェック、監査ログ（発注→約定トレーサビリティ）などを提供します。

## 主な特徴（機能一覧）
- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPXマーケットカレンダーを差分取得・保存
  - 差分取得・バックフィルロジック、ページネーション、レート制御、トークン自動リフレッシュ
- データ品質管理
  - 欠損・重複・スパイク・日付不整合のチェック（quality モジュール）
- ニュース収集と NLP
  - RSS フィードの収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini） を利用した記事群の銘柄別センチメント付与（ai.news_nlp）
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離 + マクロニュース LLM センチメントの合成（ai.regime_detector）
- 研究用ユーティリティ
  - モメンタム、ボラティリティ、バリューなどファクター計算（research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等
- 監査ログ（Audit）
  - signal → order_request → execution に至る監査スキーマ、冪等性確保、監査DB初期化ユーティリティ
- 設定管理
  - .env または環境変数から自動ロード。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可

## 必要環境 / 依存
（最小限の主なライブラリ）
- Python 3.10+
- duckdb
- openai（OpenAI の新しい SDK を想定）
- defusedxml
- 標準ライブラリ（urllib, json, logging 等）

pip インストール例（プロジェクトの requirements を別途用意している場合はそちらを参照してください）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージ配布用に: pip install -e .
```

## 環境変数（主要）
以下はコード内で参照される主要な環境変数です。プロジェクトルートの `.env` / `.env.local` を使って設定できます（自動ロードあり。CWD ではなくパッケージ位置からプロジェクトルートを探索）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知用途（必要な場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- KABU_API_PASSWORD — kabuステーション API パスワード（発注等を使う場合）

任意（デフォルトあり）:
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env の自動読み込みを無効化
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API を使う処理は環境変数か関数引数で指定可能

例: `.env`（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=yourpassword
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（簡易）
1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 必要ライブラリをインストール（duckdb, openai, defusedxml など）
4. プロジェクトルートに `.env` を作成して環境変数を設定
5. DuckDB 保存先ディレクトリを作成（例: data/）
   ```
   mkdir -p data
   ```
6. （任意）監査DBの初期化は下記コマンド参照

## 使い方（代表的な例）

以下は Python スクリプト / REPL から呼び出す例です。いずれも duckdb に接続して conn を渡します。

- ETL（デイリーパイプライン）を実行する:
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックを順に実行し、ETLResult を返します。

- ニュースセンチメントスコアを取得して ai_scores に書き込む:
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", written)
```
OpenAI API キーは OPENAI_API_KEY 環境変数、または score_news の api_key 引数で渡せます。

- 市場レジーム判定:
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ（監査DB）初期化:
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成されます
```

- 研究用ファクター計算:
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
```

- カレンダー関連ユーティリティ:
```
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
is_trading = is_trading_day(conn, date(2026,3,20))
next_day = next_trading_day(conn, date(2026,3,20))
```

## 自動 .env ロードについて
- モジュール kabusys.config はパッケージのソース位置からプロジェクトルート（.git または pyproject.toml）を探索し、`.env` と `.env.local` を読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env（.env.local が .env を上書き）
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時など）。

## ディレクトリ構成（概要）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント解析（OpenAI）
    - regime_detector.py — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント & DuckDB 保存ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 他）
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 収集（SSRF 対策等）
    - calendar_management.py — 市場カレンダー管理と営業日判定
    - quality.py — データ品質チェック
    - stats.py — 基本統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログ（監査スキーマ定義・初期化）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン, IC, 統計サマリー 等
  - others: strategy, execution, monitoring（パッケージ公開配列に含まれるが本ファイル群の一部は未掲示）

（上記は主要ファイルのみを抜粋した構成です）

## 実運用上の注意 / ベストプラクティス
- OpenAI キーは環境変数か関数引数で安全に渡してください。API 呼び出しはリトライやフォールバックを組んでいるものの、課金やレート制限に注意してください。
- DuckDB ファイルのバックアップやスキーマ管理を運用フローに組み込んでください。
- 本コードは「ルックアヘッドバイアス」を避ける設計方針（関数内で date.today() を直接参照しない等）を採っています。バックテストでは target_date を明示的に指定して使用してください。
- 監査テーブルは削除しない前提の設計です。マイグレーション・メンテナンス時の影響に注意してください。

## トラブルシューティング（よくある問題）
- .env が読み込まれない: KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか、プロジェクトルートの検出に失敗している可能性があります。パッケージ配置と .git / pyproject.toml の有無を確認してください。または明示的に環境変数を export してください。
- J-Quants API の 401 が出る: JQUANTS_REFRESH_TOKEN を確認。jquants_client は 401 時に自動でリフレッシュ処理を行いますが、リフレッシュに失敗する場合はトークンの再発行を検討してください。
- OpenAI 呼び出しで失敗する: API レートや料金上限、モデル名（gpt-4o-mini）を確認。テストでは API 呼び出しをモックすることを推奨します（コードはテスト用の差し替えを想定した設計です）。

---

この README はコードの概観と代表的な利用方法を示しています。詳細な実装仕様や API の挙動は各モジュールの docstring を参照してください。必要であれば README にチュートリアルや運用手順（CI/CD、cron ジョブ、監視）を追加できます。