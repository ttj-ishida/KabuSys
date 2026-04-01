# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータパイプライン、研究（ファクター算出・特徴量解析）、AI を用いたニュース NLP、監査ログ・発注監視などを含む日本株自動売買支援ライブラリです。DuckDB を中心としたローカルデータベースと J-Quants / OpenAI / kabu API 等を連携して、ETL、品質チェック、シグナル生成・追跡、AI スコアリングを行うためのユーティリティ群を提供します。

主な設計方針:
- ルックアヘッドバイアス回避（内部で datetime.today() を盲目的に参照しない設計）
- 冪等性（DB 保存は ON CONFLICT / UPSERT を多用）
- フェイルセーフ（API エラー時のフォールバック・ロギング）
- テスト可能性を高めるため API 呼び出しの差替えを想定

---

## 機能一覧

- データ取得・ETL（J-Quants API 経由）
  - 株価日足（OHLCV）取得 & 保存（raw_prices）
  - 財務データ取得 & 保存（raw_financials）
  - JPX マーケットカレンダー取得 & 保存（market_calendar）
  - 差分取得 / バックフィル / ページネーション対応
  - 品質チェック（欠損、重複、スパイク、日付不整合）

- ニュース収集・NLP
  - RSS からのニュース収集（SSRF 対策・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いたニュース・センチメントスコアリング（ai_score）
  - マクロニュースを使った市場レジーム判定（bull/neutral/bear）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター算出
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - Z-score 正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化
  - 監査 DB 初期化ユーティリティ（DuckDB）

- 外部統合
  - J-Quants クライアント（認証・リトライ・レートリミット）
  - OpenAI クライアント利用（JSON Mode）を前提としたラッパー呼び出し

---

## セットアップ手順

以下は一般的な開発環境でのセットアップ手順の例です。プロジェクトルート（pyproject.toml / .git がある場所）から実行してください。

1. リポジトリをクローンしワークディレクトリへ移動
   - 例: git clone ... && cd kabusys

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 本リポジトリに pyproject.toml / requirements がある想定です:
     - pip install -e .
     - または pip install -r requirements.txt

   ※ 本リポジトリのサンプルコードでは duckdb, openai, defusedxml などを使用しています。適宜インストールしてください:
   - pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を作成することで自動的に読み込まれます（デフォルトで自動ロード）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注・約定連携を行う場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

その他の設定（デフォルトが設定されているもの）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

---

## 使い方（主要ユースケース）

以下はライブラリの主要な利用例です。実際はアプリケーション側でこれらを呼び出す形になります。

1) DuckDB に接続して日次 ETL を実行する

Python スクリプト例:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース・センチメント（銘柄別）を取得して ai_scores テーブルに書き込む

必要: OPENAI_API_KEY を環境変数に設定

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

3) マクロニュース + ETF MA を使った市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ（audit DB）を初期化する

```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn を使って監査テーブルにアクセス可能
```

5) RSS フィードを取得する（ニュース収集の一部）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss(
    url="https://news.yahoo.co.jp/rss/categories/business.xml",
    source="yahoo_finance"
)
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

※ OpenAI 呼び出しや J-Quants API 呼び出しはネットワーク・課金を伴います。テスト時はモックで関数（例: kabusys.ai.news_nlp._call_openai_api）を差し替えてください。

---

## 主要モジュールの説明（抜粋）

- kabusys.config
  - .env / 環境変数読込み、settings オブジェクト経由で設定を提供
  - 自動 .env ロード（プロジェクトルート検出） / KABUSYS_DISABLE_AUTO_ENV_LOAD

- kabusys.data.jquants_client
  - J-Quants API の認証・取得・保存（rate limiting / retry / token refresh 含む）
  - save_* 系は DuckDB へ冪等保存を行う

- kabusys.data.pipeline
  - run_daily_etl: カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック の一括実行
  - ETLResult で結果を表現

- kabusys.data.quality
  - 欠損、重複、スパイク、日付不整合を検出し QualityIssue のリストを返す

- kabusys.ai.news_nlp, kabusys.ai.regime_detector
  - OpenAI を用いたニュースセンチメント評価・市場レジーム判定（JSON Mode を利用）
  - リトライ、レスポンスバリデーション、フェイルセーフ設計

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
  - バックテストやファクターリサーチ向け

- kabusys.data.audit
  - signal_events / order_requests / executions の DDL を定義・初期化するユーティリティ

---

## ディレクトリ構成

（ src/kabusys 配下の主要ファイル）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - stats.py
  - quality.py
  - calendar_management.py
  - news_collector.py
  - audit.py
  - other helper modules...
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
  - other research utilities...

---

## 注意事項 / ベストプラクティス

- OpenAI / J-Quants キーは機密情報なので .env に保存する場合は適切に管理してください。
- 自動ロードを無効にしたいテスト・CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のパス（settings.duckdb_path）はバックアップ・バージョン管理を考慮して保存場所を決めてください。
- ニュースの収集・AI 呼び出しは API レートやコストに影響します。バッチ化やレート制御を施してください。
- news_collector は SSRF / XML Bomb に対策していますが、信頼できない RSS を扱う場合は監視・制限を強化してください。
- 本ライブラリの関数は多くが DB 接続（duckdb.DuckDBPyConnection）を受け取ります。テスト時は :memory: 接続やモックを活用してください。

---

問題報告・貢献
- バグや改善提案は Issue を作成してください。プルリクエスト歓迎します。

--- 

作成者 / 貢献者向けメモ: README は実コードを参照して必要に応じて補完してください（依存関係や実行スクリプト等の追加ドキュメント化を推奨）。