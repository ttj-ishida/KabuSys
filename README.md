# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取得／品質チェック）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログスキーマなどを提供します。

バージョン: 0.1.0

---

## 主要な特徴

- J-Quants API からの差分 ETL（株価日足 / 財務 / 市場カレンダー）を実行して DuckDB に保存
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ニュース収集・前処理（SSRF 対策・トラッキング除去）とニュース NLP（OpenAI）による銘柄別センチメントの算出
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン計算、IC 計算、Zスコア正規化 等）
- 監査ログ（signal_events / order_requests / executions）用の DuckDB スキーマ初期化ユーティリティ
- 設定は環境変数（.env / .env.local の自動読み込みあり）

---

## 主要モジュール（概観）

- kabusys.config: 環境変数 / 設定管理（.env 自動ロード）
- kabusys.data:
  - pipeline, etl: ETL 実行ロジック（run_daily_etl など）
  - jquants_client: J-Quants API クライアント（取得・保存関数）
  - news_collector: RSS 収集・前処理
  - quality: データ品質チェック
  - calendar_management: 市場カレンダー管理（営業日判定など）
  - audit: 監査ログスキーマ初期化
  - stats: 共通統計ユーティリティ（zscore_normalize）
- kabusys.ai:
  - news_nlp: ニュースを LLM で評価して `ai_scores` に書き込む（score_news）
  - regime_detector: ETF の MA とマクロニュースの LLM を合成して market_regime を書き込む（score_regime）
- kabusys.research: ファクター計算 /特徴量探索（momentum, volatility, value, forward returns, IC 等）

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS フィード 等）

プロジェクトの requirements.txt / pyproject.toml がある場合はそちらに従ってください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、パッケージを editable インストール（ソースが src/ 配下の場合）:
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -e ".[dev]"  # または pip install -e .
   ```
   ※ pyproject.toml / extras がある場合は適宜調整してください。

2. 環境変数を設定（.env を使うことを推奨）。自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

3. DuckDB ファイルやディレクトリを作成する（settings のデフォルトは data/kabusys.duckdb など）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH: 実行監視用 PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例 .env（抜粋）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

注意: config.Settings は自動で .env / .env.local をプロジェクトルートから読み込みます（OS 環境変数を上書きしない挙動や .env.local の優先読み込みなどのルールあり）。

---

## 基本的な使い方（コード例）

以下は Python REPL もしくはスクリプトから実行する際の例です。

- DuckDB 接続を得て ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（OpenAI API キーは環境変数か引数で渡す）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を参照
print("scored:", count)
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用の DuckDB を初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 返却された conn を使って監査テーブルにアクセスできます
```

- カレンダー / 営業日ユーティリティ:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
```

---

## よく使う API の説明（簡潔）

- run_daily_etl(conn, target_date, id_token=None, run_quality_checks=True, ...):
  日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）を実行し ETLResult を返す。

- score_news(conn, target_date, api_key=None):
  前日 15:00 JST 〜 当日 08:30 JST のニュースを対象に銘柄ごとの ai_score を生成し ai_scores テーブルへ保存する。戻り値は書き込んだ銘柄数。

- score_regime(conn, target_date, api_key=None):
  ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ書き込む。

- jquants_client.*:
  fetch_* 系で J-Quants API からデータを取得。save_* 系で DuckDB に冪等保存する。

- data.quality.run_all_checks(conn, target_date, reference_date, spike_threshold):
  各種品質チェックを実行して QualityIssue のリストを返す。

- data.audit.init_audit_db(path):
  監査ログ用の DuckDB を初期化して接続を返す。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - pipeline.py
    - etl.py
    - jquants_client.py
    - news_collector.py
    - quality.py
    - calendar_management.py
    - stats.py
    - audit.py
    - etl.py (ETLResult をエクスポートする薄いラッパー)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールは概ね以下の責務で分離されています:
- data/*: データ取得・保存・品質チェック・カレンダー等の Data Platform 機能
- ai/*: OpenAI を使った NLP / レジーム判定
- research/*: ファクター計算 / 統計・IC 計算

---

## テスト・開発時のメモ

- OpenAI 呼び出しはテストでモック可能（各モジュール内の _call_openai_api を patch して差し替えられるよう実装されています）。
- 自動 .env ロードはプロジェクトルートを基準に行われるため、テストで干渉する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB に対する executemany での空リストは一部バージョンで問題になるため、該当コードでは空チェックが入っています（注意点）。

---

## 運用上の注意

- OPENAI_API_KEY や J-Quants のトークンは厳重に管理してください。CI やデプロイ環境では Secret Manager 等を使用することを推奨します。
- run_daily_etl 等は外部 API に依存するため、レート制限やエラー時のリトライ・フェイルセーフ設計（多くの箇所で採用）を理解した上で運用してください。
- market_regime / ai_scores の計算はルックアヘッドバイアス対策（target_date 未満のデータのみ使用）を念頭に置いて実装されています。バックテストなどで利用する際は設計方針を遵守してください。

---

不明点や README に追加したい項目があれば教えてください。必要に応じて実行例や .env.example を追記します。