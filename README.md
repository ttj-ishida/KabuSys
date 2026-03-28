# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（部分実装）。  
本リポジトリはデータ収集（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、監査ログ（発注／約定トレーサビリティ）などのユーティリティ群を提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（date.today() を直接参照しない等）
- DuckDB を中核ストレージとして利用（ローカル ETL / 研究用途向け）
- API 呼び出しは堅牢なリトライ・レート制御を備える
- ETL / 保存は冪等に設計（ON CONFLICT / 排他制御）
- AI 呼び出しは JSON Mode を利用しレスポンスを厳格に検証

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 動作要件
- 環境変数
- セットアップ手順
- 使い方（主なユースケース）
- ディレクトリ構成
- 注意事項 / トラブルシューティング

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインと研究・自動売買に必要な基盤機能を提供する Python パッケージです。主に次の領域をカバーします。

- J-Quants API を用いた株価・財務・カレンダーの差分取得（レート制御・トークンリフレッシュ付き）
- ETL（差分取得 → 保存 → 品質チェック）の一括実行
- ニュース収集（RSS）とニュース NLP（OpenAI）による銘柄センチメント算出
- 市場レジーム判定（ETF MA とマクロニュースの LLM スコアを合成）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- 監査ログ DB（signal → order_request → execution のトレース用テーブル・初期化）

---

## 機能一覧

- data/
  - jquants_client: J-Quants API からのデータ取得・DuckDB への保存（raw_prices / raw_financials / market_calendar など）
  - pipeline: 日次 ETL の実行（run_daily_etl、個別ジョブ run_prices_etl 等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - news_collector: RSS 取得、前処理、raw_news への保存（SSRF / Gzip / XML セキュリティ対応）
  - audit: 監査ログ用テーブル作成・初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約して LLM でスコア化、ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF 200日MA乖離とマクロニュース LLM を合成して market_regime に書込
- research/
  - factor_research: momentum / volatility / value のファクター算出
  - feature_exploration: forward returns, IC（スピアマン）計算、統計サマリ
- config: 環境変数読み込みと Settings（.env 自動ロード・必須 env チェック）
- その他: news_collector の安全対策、J-Quants のレートリミッタ、OpenAI 呼び出しのリトライ等

---

## 動作要件

- Python 3.10 以上（型注釈で | 演算子を使用しているため）
- 必須 Python パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - openai
  - defusedxml

必要に応じて他の標準ライブラリ外パッケージが追加される可能性があります（logging 等は標準）。

---

## 環境変数

主に config.Settings で参照される環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注モジュール等が使う想定）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで参照）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）を検出し、.env → .env.local の順に自動ロードします。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env の書式パースはシェル風の記述（コメント、export 形式、クォート、エスケープ）に対応しています。

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   以下は最小例です。プロジェクトに requirements.txt などがあればそちらを利用してください。
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定
   プロジェクトルートに .env を作成する例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```
   - .env.local を使用してローカル上書きも可能（自動ロード順: .env → .env.local）。

---

## 使い方（簡易ガイド）

以下は代表的な利用例です。DuckDB 接続は kabusys.settings.duckdb_path を使うのが簡単です。

- DuckDB 接続例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl

# conn は上で作成した DuckDB 接続
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース NLP（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))  # 前日15:00JST〜当日08:30JSTの窓で処理
print(f"書き込み銘柄数: {written}")
```
- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査用 DuckDB を作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- ファクター計算（研究用）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- カレンダー操作
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_td = is_trading_day(conn, date(2026, 3, 20))
next_td = next_trading_day(conn, date(2026, 3, 20))
```

ログレベルは環境変数 LOG_LEVEL で制御できます。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定読み込み（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュースを銘柄ごとに集約して LLM でスコア化
    - regime_detector.py             -- ETF MA と マクロニュース LLM を合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント＆DuckDB 保存関数
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - etl.py                         -- ETL インターフェース再エクスポート
    - news_collector.py              -- RSS 収集・前処理・保管（SSRF / Gzip 対策等）
    - calendar_management.py         -- 市場カレンダー管理 / 営業日判定
    - quality.py                     -- データ品質チェック群
    - audit.py                       -- 監査ログ用テーブル定義・初期化
    - stats.py                       -- zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py             -- Momentum/Value/Volatility ファクター計算
    - feature_exploration.py         -- 将来リターン, IC, 統計サマリ
  - research/ のユーティリティや他モジュール
- src/kabusys/__init__.py

（上記はソースに含まれる主要モジュールの抜粋です）

---

## 注意事項 / トラブルシューティング

- OpenAI / J-Quants の API キーが未設定だと該当機能は ValueError を投げます。環境変数または各関数の api_key / id_token 引数で明示的に渡してください。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）から行います。テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany に空リストを渡すとエラーになるバージョンがあります（コード内でチェック済み）。もし意図しないエラーが出る場合は duckdb のバージョンを確認してください。
- news_collector は RSS の取得で SSRF 対策や受信サイズ制限を実施しています。内部ネットワークへアクセスしようとするとエラーになります。
- J-Quants API はレート制限（120 req/min）を守る必要があります。クライアントは固定間隔スロットリングを実装していますが、並列化時は注意してください。
- DuckDB 時刻はタイムゾーン扱いに注意（audit.init_audit_schema は TimeZone を UTC に設定します）。

---

もし README に追加したい具体的な使用シナリオ（例: バックテスト連携、kabu ステーションへの発注フロー、Slack 通知の実装例など）があれば、その用途に合わせたサンプルや詳細手順を追記します。どの部分を詳しく知りたいか教えてください。