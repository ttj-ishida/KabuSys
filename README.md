# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュースセンチメント（LLM）・市場レジーム判定・リサーチ用ファクター計算・監査ログ（発注トレーサビリティ）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() / datetime.today() を直接参照しない等）
- DuckDB をデータストアとして前提に設計
- J-Quants / OpenAI 等の外部 API に対して堅牢なリトライ・フェイルセーフ設計
- 冪等性（ETL保存・監査ログの初期化等）

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
- データ収集（J-Quants）
  - 株価日足（OHLCV）取得 / 保存（差分・ページネーション対応）
  - 財務データ取得 / 保存
  - JPX マーケットカレンダー取得 / 保存
  - 上場銘柄情報取得
- ETL パイプライン
  - run_daily_etl による市場カレンダー → 株価 → 財務 → 品質チェックの一括実行
  - 部分的に run_prices_etl / run_financials_etl / run_calendar_etl を個別実行可能
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合（未来日付・非営業日のデータ）などを検出
- ニュース収集・前処理
  - RSS フィード取得（SSRF 対策・gzip/bomb 対策・トラッキング除去）
- ニュース NLP（LLM）
  - 銘柄別ニュース統合センチメント（gpt-4o-mini を想定。JSON Mode）
  - チャンク・バッチ化、リトライ、レスポンスバリデーション
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースセンチメントを合成して daily レジーム判定
  - OpenAI 呼び出しに対する堅牢なエラーハンドリング
- リサーチ用ファクター計算
  - Momentum / Volatility / Value 等の計算関数
  - 将来リターン計算、IC 計算、統計サマリー、Z-score 正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルの DDL と初期化ユーティリティ
  - 発注トレーサビリティを UUID で連鎖保存（冪等キー・ステータス管理）

---

## セットアップ手順

前提
- Python 3.10+ を推奨（typing の | None 等を利用）
- DuckDB（Python パッケージ）、OpenAI SDK、defusedxml 等の依存パッケージが必要

例: pip によるセットアップ
```bash
# 開発インストール（プロジェクトルートで）
pip install -e ".[dev]"  # setup.py/pyproject に extras が定義されている場合
# 明示的に必要なパッケージをインストールする場合
pip install duckdb openai defusedxml
```

環境変数（必須/推奨）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知の Bot Token（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 機能を使う場合は必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment ('development' | 'paper_trading' | 'live'), デフォルト 'development'
- LOG_LEVEL: ログレベル（'DEBUG','INFO',...）

.env ファイル自動読み込み
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）から .env を自動読み込みします。
- 優先順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数を設定: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: .env（最低限）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本例）

以下は主要ユーティリティの呼び出し例です。スクリプトやジョブから利用してください。

設定を確認・DuckDB 接続を作る
```python
from kabusys.config import settings
import duckdb

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))
```

日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメントを計算して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

市場レジームをスコアリングして market_regime テーブルへ書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数か引数で渡す
```

監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

RSS をフェッチ（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

リサーチ用ファクター計算例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
```

品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

OpenAI 呼び出しをテストで差し替える
- news_nlp / regime_detector 内で _call_openai_api を patch してユニットテスト可能です（モジュールの実装に合わせて patch してください）。

---

## 注意点 / 運用上のヒント

- OpenAI による LLM 呼び出しはネットワーク障害や 5xx/429 等を考慮してリトライ設計されていますが、API キー制限やコストに注意してください。
- J-Quants API はレート制限（120 req/min）を守るため内部に RateLimiter を実装していますが、大量の同時実行は避けてください。
- DuckDB の executemany にはバージョン依存の制約があるため、空リストを渡さない等の実装上の配慮があります（コード内で対策済み）。
- 監査ログは削除しない前提です。発注フローのトレーサビリティを確保するため必ず初期化し運用してください。
- .env の自動読み込みはプロジェクトルートの検出に __file__ を起点に探索するため、パッケージ配布後でも期待通りに機能します。CI・テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御できます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                        -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     -- ニュース NLP（銘柄単位センチメント）
    - regime_detector.py              -- 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - etl.py                          -- ETLResult 再エクスポート
    - calendar_management.py          -- マーケットカレンダー管理（営業日判定等）
    - news_collector.py               -- RSS 取得・前処理
    - quality.py                      -- データ品質チェック
    - stats.py                        -- 汎用統計（zscore 等）
    - audit.py                        -- 監査ログ DDL & 初期化
  - research/
    - __init__.py
    - factor_research.py              -- Momentum / Value / Volatility 等
    - feature_exploration.py          -- forward returns / IC / summary / rank
  - research/* (補助モジュール)

（上記は主要ファイルの抜粋です。実際のファイル一覧はソースツリーを参照してください）

---

必要に応じて README を拡張して、実運用向けのジョブ定義（cron / Airflow / Kubernetes CronJob）、監視・アラート設計、Slack 通知のサンプルなどを追加できます。具体的に追加したい項目があれば教えてください。