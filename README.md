# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価/財務/カレンダー取得）、ニュース収集・NLP（OpenAI 経由）、ファクター計算、品質チェック、監査ログ（オーダー／約定トレース）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python モジュール群です。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）の自動取得・保存（DuckDB）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント / マクロセンチメント評価（gpt-4o-mini を想定）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- kabuステーション / LINE 通知等の設定置き場（設定管理モジュール）

設計上の特徴:
- DuckDB をデータストアに採用（高速な分析クエリと埋め込み DB）
- Look-ahead bias を避ける設計（関数が内部で date.today() を参照しない等）
- 冪等性を意識した保存（ON CONFLICT / DELETE→INSERT の置換方式）
- API 呼び出しはレート制御・リトライを備える

---

## 機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: fetch/save 関数、トークン自動リフレッシュ、レート制御
- ニュース収集・NLP
  - RSS 取得・正規化・保存（kabusys.data.news_collector）
  - ai ベースのニューススコアリング（kabusys.ai.news_nlp）
  - マクロセンチメントと市場レジーム判定（kabusys.ai.regime_detector）
- データ品質管理
  - 欠損・スパイク・重複・日付不整合チェック（kabusys.data.quality）
- 研究用ツール
  - ファクター計算（momentum/value/volatility）（kabusys.research.factor_research）
  - 将来リターン計算・IC/統計サマリ（kabusys.research.feature_exploration）
  - Z-score 正規化ユーティリティ（kabusys.data.stats）
- 監査ログ（トレーサビリティ）
  - 監査スキーマ初期化 / 専用 DB 作成（kabusys.data.audit）
- 設定管理
  - .env 自動ロード（プロジェクトルート基準）と Settings（kabusys.config）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（typing | union 表記などを利用）
- DuckDB, OpenAI SDK, defusedxml 等の依存あり

1. リポジトリを取得してインストール（開発モード）
   - ソースルートに移動して:
     - pip install -e .
     - もしくは必要な依存を手動でインストール:
       - pip install duckdb openai defusedxml

2. 環境変数 / .env
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）を基に自動で `.env` / `.env.local` を読み込みます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. 必須環境変数（例）
   - J-Quants 用
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OpenAI
     - OPENAI_API_KEY=your_openai_api_key
   - Kabu ステーション（発注連携がある場合）
     - KABU_API_PASSWORD=your_kabu_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # デフォルトあり
   - 任意・運用設定
     - LINE_CHANNEL_ACCESS_TOKEN=
     - LINE_USER_ID=
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KILL_FLAG_CLEAR_ON_START=0
     - CPU_THRESHOLD_PCT=90.0
     - MEMORY_THRESHOLD_PCT=85.0
     - DISK_THRESHOLD_PCT=90.0
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...

   - 参考用 .env の最小例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=./data/kabusys.duckdb
     KABU_API_PASSWORD=foobar
     ```

---

## 使い方（主要ユースケース）

以下は簡単な呼び出し例です。実行前に必要な環境変数を設定してください。

1) DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのセンチメントスコア取得（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} scores")
```

4) 市場レジーム判定（ETF 1321 の MA とマクロセンチメント合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査 DB の初期化（監査用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# init_audit_db はテーブルとインデックスを作成し、UTC タイムゾーンを設定します
```

6) 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

7) データ品質チェック
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- OpenAI 周り（score_news / score_regime）は API キーが必須です。api_key 引数を明示的に渡すこともできます。
- ETL では J-Quants トークン（JQUANTS_REFRESH_TOKEN）を使って id_token を自動取得します。
- 多くの処理は外部 API 呼び出しを伴うため、ネットワークエラーやレート制限を考慮してください。ライブラリはリトライ・バックオフ・レート制御を備えていますが、運用側でも監視を推奨します。

---

## .env の自動ロードについて

- プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を基に `.env` / `.env.local` を自動で読み込みます。
- 読み込み順は: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

---

## ディレクトリ構成（主要ファイル）

(ソースは `src/kabusys` 配下を想定)

- kabusys/
  - __init__.py  -- パッケージ定義
  - config.py    -- 環境変数 / Settings（.env 自動ロード機能含む）
  - ai/
    - __init__.py
    - news_nlp.py         -- ニュースセンチメント（OpenAI を用いる）
    - regime_detector.py  -- マクロ + MA 合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント（fetch/save、rate limiter）
    - pipeline.py         -- ETL パイプライン（run_daily_etl 等）
    - news_collector.py   -- RSS 収集・前処理
    - calendar_management.py -- 市場カレンダー管理（is_trading_day 等）
    - quality.py          -- データ品質チェック
    - stats.py            -- zscore_normalize 等の統計ユーティリティ
    - audit.py            -- 監査スキーマ初期化 / init_audit_db
    - etl.py              -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py  -- Momentum / Value / Volatility 算出
    - feature_exploration.py -- forward returns, IC, factor_summary, rank
  - ai/..., research/... (その他モジュール)
- pyproject.toml / setup.cfg 等（プロジェクトルート）

---

## 運用上の留意点

- Look-ahead bias に注意:
  - 多くの関数は target_date を引数に取り、内部で現在時刻を参照しない設計です。バックテスト用途でも正しい日付管理を行ってください。
- 冪等性:
  - ETL/save 関数は ON CONFLICT / DELETE→INSERT の方式で既存データ保護を行いますが、マルチプロセス運用時は DB ロックやトランザクションに注意してください。
- API レートとリトライ:
  - J-Quants 取得は 120 req/min に合わせた固定間隔スロットリングを行います。OpenAI 呼び出しもリトライロジックがありますが、運用上の割当と制限に留意してください。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査、プライベート IP 拒否）や XML の安全パーサ（defusedxml）を使用していますが、外部ソース運用時は追加の監査を推奨します。

---

## さらに詳しく / 開発

- テスト用に環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、自前の環境設定を注入してテストを行えます。
- OpenAI 呼び出しやネットワーク I/O 部分はユニットテスト時にモック差し替えが想定された設計になっています（例: kabusys.ai.news_nlp._call_openai_api のパッチ等）。

---

質問・使い方の詳細な例が必要でしたら、目的（ETL 実行・OpenAI でのバッチスコア取得・監査 DB 初期化 等）を指定していただければ、より具体的なコード例や運用手順を提示します。