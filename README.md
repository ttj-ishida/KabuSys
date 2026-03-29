# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants / RSS / OpenAI 等を組み合わせて、データの ETL、品質チェック、ニュース NLP による銘柄スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログの管理などを行います。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を不用意に参照しない）
- DuckDB をデータレイクとして使用、ETL は差分更新かつ冪等保存
- OpenAI の JSON mode を利用した LLM スコアリング（フェイルセーフ設計）
- API 呼び出しはリトライ・レート制御を実装
- テストしやすいように外部依存箇所は差し替え可能（関数単位のモック想定）

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数）とレート制御、認証自動リフレッシュ
  - 市場カレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news 保存、SSRF/サイズ制限等の安全対策）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 監査ログテーブル群（signal_events / order_requests / executions）の初期化ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news）: 銘柄ごとにニュースをまとめて LLM 評価 → ai_scores へ書込
  - 市場レジーム判定（score_regime）: ETF(1321) の MA200 とマクロニュースセンチメントを合成して daily regime を算出
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config
  - 環境変数 / .env ロード・検証（自動的にプロジェクトルートの .env / .env.local を読み込み）
  - Settings オブジェクト経由で型付きアクセス

---

## セットアップ手順

前提
- Python 3.10 以上（型表記に | を使用）
- ネットワーク接続（J-Quants / OpenAI 等）

1. リポジトリをクローン（またはソースを取得）
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （その他ユーティリティは標準ライブラリベース。必要なら requirements.txt を用意して pip install -r で管理してください）
4. パッケージを開発インストール（任意）
   - pip install -e .

.env の準備
- プロジェクトルートに `.env`（必要であれば `.env.local`）を作成してください。config モジュールは自動でプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` を読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678

任意/デフォルト
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  （デフォルト）
- DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development|paper_trading|live  （デフォルト development）
- LOG_LEVEL=INFO

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=XXXXXXXXXXXXXXXXXXXXXXXX
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（主要 API/ユースケース）

以下は Python スクリプトや REPL から利用する簡単な例です。DuckDB 接続は `duckdb.connect(path)` で作成します。

1) 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアリング（OpenAI API 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"ai_scores written: {n_written}")
```

3) 市場レジーム判定（MA200 とマクロニュース統合）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ DB を初期化（監査用の専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが SET されます
```

5) 監査スキーマのみを既存接続に追加
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

6) J-Quants から手動で価格を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")

records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
saved = save_daily_quotes(conn, records)
print(saved)
```

設定値は `kabusys.config.settings` 経由でも参照できます：
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点：
- OpenAI を利用する関数は api_key 引数で上書き可能。省略時は環境変数 `OPENAI_API_KEY` を参照します。
- ETL / 保存処理は冪等化（ON CONFLICT DO UPDATE）されます。
- LLM 呼び出しはリトライやフォールバック(0.0スコア) のロジックを持ち、失敗でプロセス全体が停止しない設計です。

---

## ディレクトリ構成（概要）

プロジェクトは src パッケージ構成になっています。主要モジュールを下記に示します。

- src/kabusys/
  - __init__.py      -- パッケージ初期化、__version__
  - config.py        -- 環境変数/.env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py        -- ニュース NLP（score_news）
    - regime_detector.py -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  -- J-Quants API クライアント（fetch/save 等）
    - pipeline.py        -- ETL パイプライン（run_daily_etl 等）
    - etl.py             -- ETLResult 再エクスポート
    - news_collector.py  -- RSS 収集と正規化
    - calendar_management.py -- 市場カレンダー管理
    - stats.py           -- zscore_normalize 等
    - quality.py         -- データ品質チェック
    - audit.py           -- 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py     -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank

各モジュールは DuckDB 接続を引数に取る設計が多く、データベース接続の管理は呼び出し側が行います。

---

## 運用上の注意・ベストプラクティス

- 環境別に DUCKDB・ログレベル等を切り替えるには `.env.local` を使用（.env より優先して上書きされる）。
- 自動 .env ロードを無効にしたいテスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI のコストやレート制限を考慮して、score_news/score_regime はバッチ実行を想定。リアルタイム呼び出しは設計に注意。
- ETL は差分かつバックフィル（デフォルト 3 日）を行うため、ETL の定期実行（Cron / Scheduler）を推奨。
- 監査ログは削除しない前提（追跡性）。DB サイズ管理（VACUUM やアーカイブ）を検討してください。

---

## 貢献 / テスト

- 外部 API 呼び出し部分（OpenAI / J-Quants / ネットワーク I/O）はモックしやすい設計です。単体テストでは該当関数を patch して振る舞いを制御してください（例: kabusys.ai.news_nlp._call_openai_api の差し替え）。
- DuckDB はインメモリ接続（":memory:"）をサポートするため、テストで使いやすいです。
- Lint / 型チェックを導入する場合は pyproject.toml に設定を追加してください（このリポジトリでは探査位置の基準に .git / pyproject.toml を使用します）。

---

README の内容はコードベースの主要点を抜粋したものです。詳細な API 仕様やデータスキーマ（テーブル定義）はソース内ドキュメント（各モジュールの docstring）を参照してください。必要なら README に追加したい具体的なサンプルワークフロー（cron 例、Docker 化、監視設定など）を教えてください。