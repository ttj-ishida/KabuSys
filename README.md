# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、ファクター計算・リサーチ、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群をまとめたパッケージです。

- J-Quants API からのデータ取得と DuckDB への永続化（差分 ETL、ページネーション、再取得バックフィル、冪等保存）
- ニュース RSS 収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini） を用いたニュース・マクロセンチメント評価（JSON Mode）
- マーケットカレンダー管理（JPX）と営業日判定ユーティリティ
- ファクター計算（モメンタム・バリュー・ボラティリティ 等）とリサーチ補助（将来リターン、IC、統計サマリー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）

設計上の重要点：
- ルックアヘッドバイアス対策（内部で date.today()/datetime.today() を無条件に参照しない設計箇所がある）
- 冪等性・フェイルセーフ（API 失敗時に処理を続行する箇所が多い）
- DuckDB を主な内部 DB として想定

---

## 主な機能一覧

- data.jquants_client: J-Quants からの fetch/save（株価・財務・カレンダー）・認証・レート制御
- data.pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）、ETL 結果クラス
- data.news_collector: RSS 取得・前処理・記事ID生成・SSRF 対策
- data.quality: データ品質チェック（欠損、スパイク、重複、未来日付など）
- data.calendar_management: 営業日判定・next/prev_trading_day・calendar_update_job
- data.audit: 監査ログ（テーブル定義・初期化ユーティリティ）
- data.stats: 汎用統計（zscore 正規化）
- ai.news_nlp: ニュース銘柄ごとのセンチメントを OpenAI でスコア化（score_news）
- ai.regime_detector: ETF（1321）MA200 とマクロニュースを混合して市場レジーム判定（score_regime）
- research: factor 計算（momentum/value/volatility）、feature_exploration（forward returns / IC / summary / rank）
- config: 環境変数読み込み・設定管理（.env 自動ロード・必須チェック）

---

## セットアップ手順（開発 / 利用）

1. Python バージョン
   - 推奨: Python 3.10 以上（パイプライン・型記法に | を利用）

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール（プロジェクトルートで）
   - pip install -e .  # setup.py / pyproject.toml がある前提
   - もしパッケージ化されていない場合は主要依存のみインストール:
     - pip install duckdb openai defusedxml

   必要な主な依存パッケージ:
   - duckdb
   - openai (OpenAI Python SDK)
   - defusedxml
   - （標準ライブラリ以外は適宜追加）

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   最低限設定が必要な環境変数（config.Settings 参照）:
   - JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD      — kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID       — Slack チャンネル ID（必須）

   任意 / デフォルトあり:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に使用、関数の api_key 引数でも指定可能）
   - KABUSYS_ENV — development / paper_trading / live
   - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL

   サンプル .env（README 用例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易サンプル）

以下は主要な使用例です。いずれも Python スクリプト内で利用します。

1) DuckDB 接続と ETL を実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクトを返す
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュースのスコアリング（score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str("/path/to/your.duckdb"))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
print(f"scored {count} symbols")
```

3) 市場レジーム判定（score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成される
```

5) ニュース RSS 収集（単一フィード）
```python
from kabusys.data.news_collector import fetch_rss, preprocess_text

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    text = preprocess_text(a["title"] + " " + a["content"])
    print(a["id"], a["datetime"], text[:200])
```

6) 研究用途のファクター計算
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

---

## 主要 API (抜粋)

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.log_level, ...

- ETL / データ取得
  - kabusys.data.pipeline.run_daily_etl(...)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.pipeline.run_financials_etl(...)
  - kabusys.data.pipeline.run_calendar_etl(...)

- J-Quants クライアント
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.fetch_financial_statements(...)
  - kabusys.data.jquants_client.fetch_market_calendar(...)
  - save_daily_quotes / save_financial_statements / save_market_calendar

- ニュース & AI
  - kabusys.data.news_collector.fetch_rss(...)
  - kabusys.ai.news_nlp.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)

- 研究（Research）
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.data.stats.zscore_normalize

- 品質チェック
  - kabusys.data.quality.run_all_checks(...)

- 監査ログ
  - kabusys.data.audit.init_audit_db(...)
  - kabusys.data.audit.init_audit_schema(...)

---

## ディレクトリ構成（主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースセンチメント（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch/save）
    - pipeline.py                — ETL パイプライン / ETLResult
    - etl.py                     — ETL 再エクスポート（ETLResult）
    - news_collector.py          — RSS 取得 / 前処理
    - calendar_management.py     — 市場カレンダー管理 / 営業日ユーティリティ
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログスキーマ初期化
    - stats.py                   — 統計ユーティリティ（zscore）
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算
    - feature_exploration.py     — 将来リターン / IC / summary / rank
  - ai/, data/, research/ のほか、strategy/ execution/ monitoring/（__all__ に定義）は公開 API の対象だが、今回のコードベースでは一部モジュールに実装があります。

---

## 注意事項 / 運用上のポイント

- OpenAI API を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とします。関数呼び出し時に api_key 引数で渡すか環境変数に設定してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定すると自動ロードを無効化できます。
- DuckDB をファイルで使用する際は Path の親ディレクトリを事前に作成するか、関数（init_audit_db 等）が自動生成することを利用してください。
- J-Quants API のレート制御や HTTP リトライ、401 リフレッシュロジックは jquants_client に実装されています。大量リクエスト時はレート上限に注意してください。
- ニュース収集では SSRF 防止（プライベート IP チェック、リダイレクト検査）や受信サイズ上限等の安全対策が組み込まれていますが、実運用ではさらに監視・例外処理を追加してください。
- ETL / AI 周りは外部 API に依存するため、実行環境でのネットワーク・認証情報の管理に注意を払ってください。

---

## 貢献 / 開発

- コントリビューション、バグレポート、改善提案はこのリポジトリに対して行ってください（Issue / PR）。
- ユニットテストやモックを用いた API 呼び出しの差し替えを想定した実装（例えば _call_openai_api の差し替え）になっています。テスト容易性を保つため、外部通信はテスト時にモックしてください。

---

README はこのリポジトリに含まれる機能の要約と最小限の導入・利用ガイドを示しています。実際の利用時は各モジュールのドキュメント（関数の docstring）を参照して詳細な引数・返り値・例外処理を確認してください。