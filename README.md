# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
J-Quants API からのデータ取得・ETL、ニュース収集と LLM によるニュースセンチメント、マーケットカレンダー管理、リサーチ（ファクター計算）および監査ログ（オーダー／約定トレーサビリティ）などの機能を提供します。

## 主な特徴
- J-Quants API との堅牢な連携（レート制限遵守、リトライ、トークン自動リフレッシュ）
- DuckDB を用いた ETL パイプライン（差分取得、冪等保存、品質チェック）
- RSS ベースのニュース収集と記事前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄ごとの ai_score、マーケットレジーム判定）
- マーケットカレンダー管理と営業日ユーティリティ（フォールバックロジックあり）
- 監査ログ用スキーマ（signal / order_request / execution）と初期化ユーティリティ
- 研究用途のファクター計算・特徴量探索ユーティリティ（外部依存を最小化）

## 機能一覧（抜粋）
- data/
  - jquants_client: J-Quants からのデータ取得・保存（raw_prices, raw_financials, market_calendar, listed info 等）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースをまとめて LLM に送信し ai_scores に書き込む
  - regime_detector.score_regime: ma200 とマクロニュースの LLM センチメントを合成して market_regime に書き込む
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

## 前提・依存
- Python 3.10+
- 主なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース、OpenAI API）

必要な依存はプロジェクトの requirements.txt / pyproject.toml に合わせてインストールしてください。開発環境の最低要件は Python 3.10 を想定しています。

## セットアップ手順（簡易）
1. リポジトリをチェックアウト
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - またはプロジェクトの requirements / pyproject に沿って pip install -e .
4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を用意することで自動読み込みされます（config モジュールが自動で読み込み）。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

### 必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- SLACK_BOT_TOKEN: Slack 通知用トークン（必要なら）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル
- KABU_API_PASSWORD: kabuステーション API を使う場合のパスワード
- OPENAI_API_KEY: OpenAI を使う機能（score_news / score_regime）を利用する場合に必要

オプション:
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
```

## 使い方（代表的な例）

- DuckDB 接続を作って日次 ETL を実行する例
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"wrote {n_written} ai_scores")
```

- 市場レジームを判定して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用の DuckDB を初期化する（order / execution 用スキーマ）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルへ書き込み／検索が可能
```

- 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- カレンダー関連ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- LLM 呼び出し（OpenAI）は API キーが必要です。api_key 引数を使って注入するか、環境変数 OPENAI_API_KEY を設定してください。
- モジュールは「ルックアヘッドバイアス防止」のため、内部で date.today()/datetime.today() を不用意に参照しない設計になっています。バックテスト等では target_date を明示的に渡してください。
- ETL の実行中に品質チェックでの問題が検出されても処理は継続し、結果オブジェクトに issues / errors が収集されます。呼び出し元で判断してください。

## ディレクトリ構成（主要ファイル）
```
src/
  kabusys/
    __init__.py
    config.py                     # .env / 環境設定読み込み
    ai/
      __init__.py
      news_nlp.py                 # ニュース→ai_scores（LLM）
      regime_detector.py          # ma200 + マクロニュースで市場レジーム判定
    data/
      __init__.py
      jquants_client.py           # J-Quants API クライアント + 保存ユーティリティ
      pipeline.py                 # 日次 ETL パイプライン（run_daily_etl 等）
      etl.py                      # ETLResult 再エクスポート
      news_collector.py           # RSS 取得・正規化・raw_news 保存
      calendar_management.py      # 市場カレンダー／営業日ユーティリティ
      quality.py                  # データ品質チェック
      stats.py                    # zscore_normalize 等
      audit.py                    # 監査ログスキーマ初期化
    research/
      __init__.py
      factor_research.py          # モメンタム/ボラティリティ/バリュー等
      feature_exploration.py      # 将来リターン / IC / summary / rank
```

## データベース（期待される主なテーブル）
- raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / market_regime  
- audit 用: signal_events / order_requests / executions

（テーブル定義は各モジュールの実装に基づいて作成されます。init_audit_schema / ETL の保存関数により作成・更新されます。）

## テスト・デバッグ
- OpenAI / J-Quants API 呼び出しは外部依存があるため、ユニットテストでは各種内部呼び出しをモックする設計になっています（モジュール内の _call_openai_api 等）。
- 自動環境ファイル読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

詳細な内部設計や処理フローは各モジュールの docstring / コメントに記載されています。必要な操作や拡張点があれば、そのファイルを参照してください。README の補足やサンプルスクリプトが必要であれば教えてください。