# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などを含みます。

> 注意: このリポジトリはパッケージ構成のみで、実行環境（J-Quants / OpenAI API キー、必要な DB ドライバ等）の準備が必要です。

## 特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API 経由で株価日足、財務、マーケットカレンダー等を差分取得（ページネーション・レート制御・自動トークンリフレッシュ）
  - DuckDB に冪等保存（ON CONFLICT / UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質
  - 欠損・スパイク・重複・日付不整合のチェック（quality モジュール）
- ニュース収集
  - RSS 取得・前処理・SSRF 対策・トラッキングパラメータ除去・raw_news への保存ロジック
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント → ai_scores へ保存（news_nlp.score_news）
  - マクロニュースの LLM 評価と ETF MA 乖離を組合せた市場レジーム判定（regime_detector.score_regime）
  - OpenAI の JSON Mode を用いた堅牢化（バリデーション・リトライ）
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン、IC（Spearman）、統計サマリ、zscore 正規化
- 監査ログ（Audit）
  - シグナル → 発注 → 約定まで UUID ベースでトレーサブルな監査テーブルと初期化ユーティリティ（init_audit_db / init_audit_schema）
- 設定管理
  - `.env` / 環境変数自動読込と Settings 型（kabusys.config.settings）

設計方針として「バックテストでのルックアヘッドバイアス防止」を強く意識しており、内部処理では date.today()/datetime.today() を不用意に参照しないなどの配慮があります。

---

## 必要条件

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK、v1系想定）
- defusedxml
- （ネットワーク経由の実行には）J-Quants のリフレッシュトークン、OpenAI API キー 等

依存はプロジェクト側で明示されていないため、環境に合わせて必要パッケージをインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを editable install する場合
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数を設定（.env をプロジェクトルートに配置するか OS 環境変数で設定）
   - 自動読み込みは `kabusys.config` がプロジェクトルート（.git または pyproject.toml）を検出した場合に行われます。
   - 自動読込を無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

### 主要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須：データ取得）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu ステーション base URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- PAPER_FILL_MODE: paper trading の fill モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視関連設定
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

簡単な .env の例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下はライブラリの主要機能を呼び出す最小例です。実運用ではログ設定や例外処理、環境構築が必要です。

- DuckDB 接続準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア生成（特定日）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を省略すると環境変数 OPENAI_API_KEY を使用
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 + マクロニュース）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" でインメモリ可
# これで監査テーブル(signal_events, order_requests, executions) が作られる
```

- 研究用ファクター計算例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

- カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

注意点:
- news_nlp / regime_detector は OpenAI API を利用します。API 呼び出しはリトライ・パース例外処理を行いますが、API キーは必須です。
- run_daily_etl 等は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar 等）が前提です。初期スキーマは ETL 実行や別のスキーマ初期化コードで作成してください。
- 多くの関数は外部 API の失敗時に「フェイルセーフ」で処理を継続する設計（スコア 0.0 を返すなど）です。ログを必ず確認してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py              # ニュースセンチメント → ai_scores 書き込み
  - regime_detector.py       # ETF MA + マクロセンチメントで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py        # J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py              # ETL パイプライン（run_daily_etl 等）
  - etl.py                   # ETLResult の再エクスポート
  - quality.py               # 品質チェック（missing, spike, duplicates, date consistency）
  - news_collector.py        # RSS 取得・前処理・raw_news 保存
  - calendar_management.py   # 市場カレンダー管理（is_trading_day など）
  - stats.py                 # zscore_normalize 等の統計ユーティリティ
  - audit.py                 # 監査ログスキーマ・初期化
- research/
  - __init__.py
  - factor_research.py       # Momentum / Value / Volatility 計算
  - feature_exploration.py   # forward returns, IC, rank, factor_summary
- research/... (その他ファイル)
- その他モジュール（execution, monitoring, strategy 等は __all__ に含める想定）

（README 上では代表ファイルを列挙しています。実際のリポジトリを参照してください）

---

## 設計上の重要なポイント（短く）

- ルックアヘッドバイアス対策: 関数は内部で date.today() に依存しないよう設計。target_date を明示的に渡すことを推奨。
- 冪等性: ETL / 保存処理は ON CONFLICT / UPDATE などで冪等に。
- フェイルセーフ: 外部 API 失敗時は代替値（例: 0.0）で処理継続する設計。重要な失敗はログに記録。
- セキュリティ: news_collector は SSRF 対策や XML の安全パーサを利用（defusedxml）、URL 正規化、トラッキング除去。

---

もし README に「インストール可能なパッケージ」「CI」「テスト実行方法」「サンプル .env.example の完全版」などを追加したい場合は、要望を教えてください。必要に応じてサンプルスクリプト（ETL バッチ / 実行ユーティリティ）も作成できます。