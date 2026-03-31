# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータプラットフォームと量的リサーチ／自動売買ユーティリティ群を提供するライブラリです。J-Quants API を用いた ETL、DuckDB ベースのデータ保存、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などの機能を含みます。設計上、バックテストでのルックアヘッドバイアスを避ける配慮や API のリトライ／レート制御、フェイルセーフな挙動を重視しています。

---

## 主な機能

- データ取得・ETL
  - J-Quants API による株価（日次 OHLCV）、財務データ、JPX カレンダーの差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL の集約実行（run_daily_etl）と結果の ETLResult 表現

- データ管理・品質
  - market_calendar（営業日管理）、raw_prices/raw_financials などの保存・更新
  - データ品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集・NLP
  - RSS 取得・前処理（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI を使ったニュースセンチメント評価（gpt-4o-mini を想定）
  - 銘柄毎の ai_score を ai_scores テーブルに書き込む処理（score_news）

- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（score_regime）

- リサーチ・ファクター
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC 計算、ファクター統計サマリー、Z スコア正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を中心とした監査テーブル定義・初期化（init_audit_schema / init_audit_db）

- 設定管理
  - .env または環境変数から設定を自動読み込み（project root に .env/.env.local）
  - settings オブジェクト経由でアプリ設定にアクセス可能（例: settings.duckdb_path）

---

## セットアップ

前提: Python 3.9+（型ヒントや一部機能で 3.9 以上を想定）

1. リポジトリをクローン／ダウンロードし、プロジェクトルートへ移動します（pyproject.toml / .git を基準に自動ロードが行われます）。

2. 仮想環境を作成して有効化（任意）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - 最低限必要な依存例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用の追加依存があればプロジェクトの requirements.txt / pyproject.toml を参照してインストールしてください。
   - パッケージを編集可能インストールする場合:
     ```
     pip install -e .
     ```

4. 環境変数（.env）を設定
   - プロジェクトルートに `.env`（および開発用に `.env.local`）を置くと、自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードは無効化可能）。
   - 必須の環境変数（主なもの）:
     - OPENAI_API_KEY — OpenAI API を使う処理（score_news / score_regime）で必要
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - オプション / 既定値あり:
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

5. データディレクトリの準備
   - DUCKDB や監査 DB をファイルで使う場合、親ディレクトリが存在することを確認するかスクリプトで自動作成されます（init_audit_db 等が自動作成）。

---

## 使い方（代表的な例）

以下はライブラリを使う最小例です。実行前に環境変数（特に OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN）を適切に設定してください。

- 設定オブジェクトにアクセスする
```python
from kabusys.config import settings

print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)
```

- DuckDB 接続を開いて日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- OpenAI を使ってニューススコアを生成する（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数に設定されていれば api_key=None で良い
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored count:", n_written)
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- RSS 取得（ニュースコレクタ）を単体で使う
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は duckdb 接続オブジェクト
```

- 研究用ファクター計算（例: momentum）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records))
```

注意点:
- AI を用いる処理は API レート・エラーに対するリトライやフォールバックを備えていますが、実行には OpenAI API の料金が発生します。
- ETL / リサーチ関数は DuckDB 内の特定テーブル（raw_prices, raw_financials, raw_news, market_calendar, news_symbols, ai_scores など）を前提として動作します。最初にスキーマを準備してください（スキーマ初期化関連のユーティリティが別モジュールにある想定）。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py (score_news のエクスポート)
    - news_nlp.py      — ニュース NLP / score_news（OpenAI 呼び出し）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py      — ETL パイプライン (run_daily_etl, run_prices_etl, ...)
    - etl.py           — ETLResult の再エクスポート
    - jquants_client.py — J-Quants API クライアント（fetch/save 関数）
    - news_collector.py — RSS 取得 / 前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py        — データ品質チェック
    - stats.py          — zscore_normalize 等の統計ユーティリティ
    - audit.py          — 監査ログテーブルの DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value 等の計算
    - feature_exploration.py — forward returns, IC, summary, rank
  - research/... (その他リサーチ用ユーティリティ)
  - data/... (その他のデータユーティリティ)

---

## 設計上の注意・ポリシー

- Look-ahead Bias 回避: 多くの関数（score_news, score_regime, ETL 等）は内部で datetime.today()/date.today() を参照せず、target_date を明示的に渡すことを想定しています。バックテスト時は必ず適切な target_date を指定してください。
- 自動環境読み込み: config モジュールはプロジェクトルートの .env/.env.local を自動読み込みします（OS 環境変数 > .env.local > .env の優先順位）。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用フラグ）。
- API リトライ・レート制御: J-Quants クライアント、OpenAI 呼び出しともにリトライや指数バックオフ、レートリミティングが組み込まれています。
- フェイルセーフ: AI API 失敗時はデフォルト値で継続する実装が多く、部分失敗による全体停止を避ける設計です（ログは出力されます）。

---

## 参考 / トラブルシューティング

- DuckDB や OpenAI の接続でエラーになる場合は、まず環境変数（ファイルパスや API キー）を確認してください。
- .env の書式やクォートに関しては config._parse_env_line の実装が詳細に扱います（コメント、エスケープ、シングル/ダブルクォート等）。
- RSS フェッチは SSRF 対策があるため、ローカルホストやプライベート IP への URL は拒否されます。
- テスト時に自動 .env ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

この README はコードベース（src/kabusys 以下）の仕様に基づく概要、セットアップ、使い方をまとめたものです。実運用では各機能の詳細ドキュメント（ETL のパラメータ、DB スキーマ、監査レコードの運用ルールなど）に従ってください。質問や補足の要望があれば教えてください。