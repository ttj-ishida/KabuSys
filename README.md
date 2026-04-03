# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（部分実装）。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集・AI を用いたニュースセンチメント評価・市場レジーム判定・ファクター計算・監査ログ（発注/約定トレース）などを提供します。

主な設計方針（抜粋）
- Look-ahead bias を避ける（内部で date.today() を直接参照しない等）
- DuckDB をデータレイヤに採用、ETL は冪等（ON CONFLICT）で保存
- OpenAI（gpt-4o-mini）を使った JSON Mode でのスコアリング（フェイルセーフでフォールバック）
- API 呼び出しはリトライ/バックオフ、レート制限遵守
- 小さなユーティリティ群（統計・ランク変換等）は外部依存を最小化

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須設定は Settings からプロパティとして取得

- データ（data）
  - J-Quants クライアント（fetch / save / token refresh / rate limiting）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - 市場カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, calendar_update_job）
  - ニュース収集（RSS 取得、前処理、SSRF/サイズ制限対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマの初期化 / 専用 DB 初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）

- AI（ai）
  - news_nlp.score_news: ニュースを銘柄ごとに集約し OpenAI でセンチメントを算出して ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）の MA200 偏差とマクロセンチメントを合成して market_regime に記録

- 研究（research）
  - ファクター計算：モメンタム / バリュー / ボラティリティ等（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ、ランク化ユーティリティ

---

## 必要条件（概略）

- Python >= 3.10
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ以外の依存がある場合はプロジェクトのパッケージ定義を参照してください

（実際のインストール用 requirements.txt / pyproject.toml がある場合はそちらを優先してください）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを用意

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt があれば pip install -e . や pip install -r requirements.txt）

4. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml が存在するルート）に `.env` または `.env.local` を配置すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
   - 最低限設定すべき変数（例）:

.env.example:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# LINE（任意）
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

5. DuckDB データベースの準備
   - settings.duckdb_path を使って接続し、必要なスキーマを作成してください（本リポジトリではスキーマ生成ユーティリティがない箇所もあるため、初期テーブルはプロジェクト固有のスクリプトで作成する想定です）
   - 監査ログ専用 DB を初期化する場合:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("path/to/audit.duckdb")

---

## 使い方（基本例）

以下は Python からライブラリを呼ぶ簡単な例です。

- ETL（デイリー）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント算出（特定日）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 19), api_key=None)  # None で環境変数 OPENAI_API_KEY を使用
print(f"written {written} scores")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 19))
```

- ファクター計算（研究用）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, date(2026,3,19))
val = calc_value(conn, date(2026,3,19))
vol = calc_volatility(conn, date(2026,3,19))
```

- 監査ログ DB 初期化（監査テーブル作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続、必要に応じてアプリ側で利用
```

- ニュース RSS 取得（単体ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

---

## 設定項目（settings 経由で取得される代表的な環境変数）

必須（実行する機能に応じて必須）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL で必要）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- KABU_API_PASSWORD: kabu API パスワード（発注等で使用）

任意（デフォルト値あり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH 等の監視設定
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視用閾値）
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

注: Settings の必須プロパティ（例えば jquants_refresh_token）は未設定だと ValueError を送出します。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内の src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント計算・ai_scores 書き込み
    - regime_detector.py            -- マクロ + MA200 合成で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch/save）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETLResult 再エクスポート
    - stats.py                      -- 統計ユーティリティ（zscore_normalize）
    - quality.py                    -- データ品質チェック
    - calendar_management.py        -- 市場カレンダー管理・更新ジョブ
    - news_collector.py             -- RSS 収集・前処理
    - audit.py                      -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py            -- ファクター計算
    - feature_exploration.py        -- 将来リターン / IC / rank / summary

---

## 注意事項・運用上のポイント

- Look-ahead bias 対策が厳密に組み込まれていますが、バックテスト時には必ず ETL データの取得タイミングとバックテストの参照日を分離して運用してください。
- OpenAI 呼び出しは料金が発生します。API キーを扱う際は流用/漏洩に注意してください。
- news_collector は外部 RSS を取得するため、SSRF や大容量レスポンス対策が入っていますが、運用ポリシーに合わせてホワイトリストを検討してください。
- J-Quants API の rate limit（120 req/min）を尊重する実装です。短時間に大量リクエストを行わないでください。
- DuckDB のバージョン差異（executemanyの空リストなど）に注意してお使いください。

---

## 貢献 / 拡張案

- 発注実行層（kabu API との接続）と監査ログの結合（order_requests → executions のワークフロー）
- Web UI / 監視ダッシュボード（LINE 通知連携の強化）
- バックテストフレームワークとの統合
- 追加のニュースソース / フィード管理

---

README の内容はコードコメント・docstring を基にまとめています。より詳細な API 使用例やスキーマ定義、運用手順（デプロイ・監視）はプロジェクトの別途ドキュメントに記載ください。必要であれば README に追記するサンプルコマンドやさらに細かい設定例を作成します。