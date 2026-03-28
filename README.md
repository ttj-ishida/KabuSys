# KabuSys

バージョン: 0.1.0

日本株のデータパイプライン、リサーチ、AIによるニュース評価、監査ログ、ETL/カレンダー管理を備えた自動売買支援ライブラリです。DuckDB をデータ層に用い、J-Quants / OpenAI / RSS 等の外部データソースと連携する設計になっています。

---

## 概要

KabuSys は以下の機能群を提供します。

- データ収集（J-Quants 経由の株価・財務・上場情報、RSS ニュース）
- ETL パイプライン（差分取得・冪等保存・品質チェック）
- マーケットカレンダー管理（JPX カレンダーの取得と営業日判定）
- ニュースの NLP（OpenAI を用いた銘柄ごとのニュースセンチメント算出）
- 市場レジーム判定（ETF の MA とマクロニュースを組み合わせたレジーム判定）
- 研究用ファクター群（モメンタム、バリュー、ボラティリティ、特徴量探索）
- 監査ログ（シグナル→発注→約定 をトレースする監査テーブル）
- 各種ユーティリティ（統計正規化、データ品質チェックなど）

設計方針として、バックテストでのルックアヘッドバイアスを避けるため日付参照やデータ取得時の制約に注意が払われています。また外部 API 呼び出しにはリトライ／レート制御が組み込まれており、DB への保存は冪等（ON CONFLICT）となっています。

---

## 主な機能一覧

- kabusys.config
  - .env 自動読み込み（プロジェクトルートの .env / .env.local。無効化可）
  - 必須環境変数の取得ラッパー（ValueError を発生）
  - 環境 (development / paper_trading / live) 判定

- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・ID トークン自動更新）
  - pipeline: 日次 ETL（価格・財務・カレンダーの差分取得・品質チェック）
  - calendar_management: 営業日判定、calendar 更新ジョブ
  - news_collector: RSS 取得・前処理・SSRF 対策・保存ロジック
  - audit: 監査テーブル定義・初期化・DB 作成ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: z-score 正規化等のユーティリティ関数

- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント算出 → ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF MA とマクロニュース（LLM）を合成して market_regime に保存

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

前提
- Python 3.9+（typing の新しい機能を使用）
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）および defusedxml 等

例: pip によるインストール（プロジェクトに requirements.txt がある想定）
```
python -m pip install -r requirements.txt
# または必要な依存を個別に
python -m pip install duckdb openai defusedxml
```

環境変数 / .env の準備（プロジェクトルートに .env を置く）
必須（モジュール設定で _require を呼ぶと失敗します）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id

任意:
- OPENAI_API_KEY=your_openai_api_key
- KABUSYS_ENV=development|paper_trading|live (デフォルト: development)
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)
- DUCKDB_PATH=data/kabusys.duckdb (デフォルト)
- SQLITE_PATH=data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 （自動 .env ロードを無効化）

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=passwd
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

注意:
- パッケージは .env/.env.local をプロジェクトルート（.git または pyproject.toml がある場所）から自動読み込みします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しを行う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。api_key 引数で明示的に渡すこともできます。

---

## 使い方（サンプル）

以下は代表的な使い方の例です。実行前に環境変数（特に認証情報）を設定してください。

1) DuckDB 接続の作成と ETL 実行（日次パイプライン）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト（デフォルト data/kabusys.duckdb）
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))

print(result.to_dict())
```

2) ニュースセンチメントを算出して ai_scores に保存
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数に入っていれば api_key=None で良い
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

3) 市場レジーム判定（regime_detector）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査 DB 初期化（監査ログ専用の DB を作る）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
# テーブルが作成された DuckDB 接続が返る
```

5) RSS フィードを取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:10]:
    print(a["id"], a["datetime"], a["title"])
```

テスト時の差し替えポイント
- OpenAI API 呼び出しは各モジュールで _call_openai_api を wrap しているため、unittest.mock.patch で差し替え可能です（例: kabusys.ai.news_nlp._call_openai_api）。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 配下の主要ファイルと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__）

- src/kabusys/config.py
  - 環境変数管理 (.env 自動ロード、settings オブジェクト)

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py: ニュースを LLM で評価し ai_scores テーブルへ保存
  - regime_detector.py: ETF MA とマクロニュースで市場レジーム判定

- src/kabusys/data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得 & DuckDB への保存）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - etl.py: ETLResult の再エクスポート
  - calendar_management.py: 市場カレンダー管理（営業日判定・更新ジョブ）
  - news_collector.py: RSS 収集・前処理・保存ユーティリティ
  - quality.py: データ品質チェック
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログ用テーブル定義 & 初期化

- src/kabusys/research/
  - __init__.py
  - factor_research.py: モメンタム / バリュー / ボラティリティ 計算
  - feature_exploration.py: 将来リターン・IC・統計サマリー

その他: 各モジュールに詳細な docstring が付与されているため、関数単位での使い方や設計意図を参照できます。

---

## 注意事項 / トラブルシューティング

- 必須環境変数が未設定の場合、settings のプロパティアクセスで ValueError が発生します。README の「セットアップ」で必須変数を設定してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を基準に探します。CI やテストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出しは外部 API のためレート制限・料金が発生します。テストや開発ではモックを使用することを推奨します。
- DuckDB に対する executemany の空リストは一部バージョンで例外になるため、モジュール内で予防処理があります。直接 SQL を書く場合は注意してください。
- news_collector は SSRF 対策や受信サイズ制限、XML デフューズ対策が実装されていますが、不特定の RSS を大量取得する際の運用・法的制約は利用者側で管理してください。

---

## 貢献 / 開発

- コーディング規約やテストはプロジェクトの既存スタイルに従ってください。
- OpenAI や J-Quants 呼び出し部分は外部 API に依存するため、ユニットテストではモックを活用してください（例: unittest.mock.patch）。
- 新しい ETL ジョブや品質チェックを追加する場合は既存の ETLResult / QualityIssue の形式に合わせてください。

---

この README はコードベースの docstring と設計コメントを基に作成しています。詳細な API 使用例は個々のモジュール（docstring）を参照してください。必要であれば README にサンプルスクリプトや運用手順（cron・Kubernetes ジョブ化等）を追記します。