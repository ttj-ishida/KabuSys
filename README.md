# KabuSys — 日本株自動売買システム（README）

## プロジェクト概要
KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリです。  
J-Quants API や RSS ニュースを取り込み、DuckDB 上で ETL / 品質チェック / 特徴量計算 / ニュース NLP / 市場レジーム判定を行い、監査ログ（発注・約定トレース）や研究用機能を提供します。  
このリポジトリは、データ収集・前処理・研究（ファクター計算）・AI ベースのニュース評価・監査ログ基盤を備えたバックエンドコンポーネント群を含みます。

## 主な機能
- J-Quants API クライアント
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得と DuckDB への冪等保存
  - トークン自動リフレッシュ、レートリミット遵守、リトライ付き
- ETL パイプライン（run_daily_etl）
  - カレンダー取得 → 株価取得 → 財務取得 → 品質チェック（欠損・重複・スパイク・日付不整合）
- データ品質チェック（quality）
  - 欠損、重複、スパイク、将来日付／非営業日データ検出
- ニュース収集（news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、データ整形、raw_news/ news_symbols への保存想定
- ニュース NLP（ai/news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメント評価（ai_scores へ書込）
  - バッチ・トリム・リトライ・レスポンス検証
- 市場レジーム判定（ai/regime_detector）
  - ETF (1321) の 200日MA乖離 + マクロニュースセンチメントを合成して daily market_regime を算出
- 研究モジュール（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン計算、IC（Spearman）や統計サマリー
- 監査ログ（data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（init_audit_db / init_audit_schema）

---

## 必要条件（推奨）
- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
- 標準ライブラリ：urllib, json, logging, datetime 等

（プロジェクトで利用する OpenAI / J-Quants / Slack などの API キーは環境変数で指定します。詳細は次節）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
4. 環境変数ファイルを作成
   - リポジトリルートに .env を配置すると自動でロードされます（config モジュールが .git または pyproject.toml を探索して自動読込）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主なキー）
config.Settings で参照される主要な環境変数は以下です。必須のものは README内で明記します。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuAPI の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン（通知等）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で利用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行監視用 PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視の閾値
- KABUSYS_ENV — 開発/ペーパー/本番 (development | paper_trading | live)
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要 API と実行例）

下記は Python スクリプト／REPL から簡単に呼び出せる例です。いずれも duckdb を接続して関数を呼びます。

1. DuckDB 接続の作成例
```
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2. 日次 ETL 実行
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3. ニュース NLP（記事のセンチメントスコア算出）
```
from kabusys.ai.news_nlp import score_news
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か api_key 引数で指定
n = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n} codes")
```

4. 市場レジーム判定
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

5. 監査ログ DB 初期化（監査専用 DuckDB を用いる）
```
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成されています
```

6. ETL の個別実行（株価のみ等）
```
from kabusys.data.pipeline import run_prices_etl
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

注意点:
- 各関数は「ルックアヘッドバイアス」を避けるため内部で date.today() を直接参照しない設計です（target_date を明示することが推奨されます）。
- OpenAI 呼び出しにはネットワークリトライやレスポンス検証が組み込まれていますが、API キーの管理やコスト・レート制限に注意してください。
- news_collector は外部 RSS を取得するため SSRF/サイズ制限/圧縮処理などの安全対策を実装しています。

---

## ディレクトリ構成（主なファイル）
（ルートが `src/kabusys` 配下になっている想定の一覧）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動読込機構）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（銘柄ごとのスコア算出）
    - regime_detector.py           — 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch / save）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL ユーティリティの公開
    - news_collector.py            — RSS ニュース収集（SSRF 対策・正規化）
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize 他）
    - calendar_management.py       — 市場カレンダー管理・営業日ロジック
    - audit.py                     — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / ボラ / バリュー等
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー
  - monitoring/ (存在が __all__ に記載されていますが実装が別ファイルにある想定)
  - strategy/ (戦略実装を置く想定)
  - execution/ (発注実装を置く想定)

（上記は主要モジュールの抜粋です。詳細はソースをご参照ください。）

---

## 開発・運用上の留意点
- .env の自動読み込みはプロジェクトルート（.git / pyproject.toml を探索）を基準に行われます。テスト時等は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- DuckDB に対する executemany の振る舞い（バージョン差）に注意してコードが書かれています（空の executemany を避ける等）。
- OpenAI の呼び出しは JSON Mode を使用し、レスポンスの厳密な検証を行っています。API の仕様変更に備えてエラーハンドリングが充実しています。
- 監査ログは削除しない前提（履歴保存）、すべて UTC タイムスタンプで保存します。
- J-Quants API のレート制限（120 req/min）を守るため固定間隔スロットリングを実装しています。

---

## よくある操作（QA）
- .env が読み込まれないと ValueError が上がる箇所があります（必須環境変数未設定）。まず .env を用意してください。
- テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、テスト用環境を明示的に注入してください。
- DuckDB ファイルのデフォルトパスは `data/kabusys.duckdb` です。必要に応じて settings.duckdb_path をオーバーライドしてください。

---

不足しているドキュメントやサンプルスクリプトが必要でしたら、目的（ETL スケジュール設定、news_collector 実行/cron、バックテスト用 DB 初期化 等）を指定していただければ、具体的な例を補足します。