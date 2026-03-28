# KabuSys

日本株向けの自動売買・データパイプラインライブラリ。J-Quants / JPX のデータ取得、DuckDB を用いた ETL・品質チェック、ニュースの収集・LLM によるセンチメント評価、研究用ファクター計算、監査ログ用スキーマなどを含むモジュール群を提供します。

主な用途
- 日次の市場データ ETL（株価、財務、マーケットカレンダー）
- ニュース収集と LLM ベースの銘柄センチメント算出
- 市場レジーム判定（MA200 + マクロニュース）
- ファクター作成・評価（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（シグナル→発注→約定のトレース用スキーマ初期化）

---

## 機能一覧（抜粋）

- data/jquants_client.py
  - J-Quants API から日足・財務・マーケットカレンダー等を取得
  - レート制御、リトライ、401 時の自動トークンリフレッシュ、ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data/pipeline.py
  - 日次 ETL（calendar → prices → financials → 品質チェック）
  - 差分更新、バックフィル、ETL 結果の ETLResult オブジェクト返却
- data/news_collector.py
  - RSS フィード取得、前処理、記事IDの冪等化、SSRF 対策、gzip/サイズ制限
- ai/news_nlp.py
  - 複数銘柄の記事をまとめて OpenAI (gpt-4o-mini) に投げ、各銘柄のセンチメントを ai_scores に保存
  - JSON mode を使ったレスポンスバリデーション、リトライ・フォールバック実装
- ai/regime_detector.py
  - ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成し市場レジーム（bull/neutral/bear）を判定・保存
- research/*
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ（forward returns / IC / summary）
- data/quality.py
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）
- data/calendar_management.py
  - market_calendar を使った営業日判定、next/prev_trading_day、get_trading_days 等
- data/audit.py
  - 監査ログ用テーブルとインデックスを初期化する関数（init_audit_schema / init_audit_db）
- data/stats.py
  - z-score 正規化など研究／データ共通の統計ユーティリティ

設計上の特徴
- ルックアヘッドバイアス対策（内部で date.today()/datetime.today() を直接参照しない場所が多い）
- DuckDB を用いた高速な分析・ETL
- LLM 呼び出しは JSON モード・リトライ・フォールバック実装
- RSS 取得時の SSRF・サイズ・XML セキュリティ対策

---

## 前提 / 要件

- Python 3.10+
- 必要な Python パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib, json, datetime などを利用

簡単なインストール例（プロジェクトローカルで）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを editable インストールする場合（プロジェクトルートに pyproject.toml/setup.py があること）
pip install -e .
```

requirements.txt を用意する場合は上記パッケージを列挙してください。

---

## 環境変数 / .env の取り扱い

このパッケージはプロジェクトルート（.git または pyproject.toml を起点）にある `.env` / `.env.local` を自動で読み込みます（OS 環境変数より低優先）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数
- JQUANTS_REFRESH_TOKEN  … J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY         … OpenAI API キー（LLM 評価で使用）
- KABU_API_PASSWORD      … kabuステーション API パスワード（注文連携用）
- KABU_API_BASE_URL      … kabuapi のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        … Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       … Slack 通知先チャンネル ID
- DUCKDB_PATH            … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            … 監視 DB 用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            … 環境 (development | paper_trading | live)（省略時: development）
- LOG_LEVEL              … ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

例 (.env)
```text
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxx...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- `.env.local` は `.env` の上書きに使われます（優先度高）。
- OS 環境変数は .env より優先され、.env ファイルが既存の OS 環境変数を上書きしないよう保護されます。

---

## セットアップ手順（具体例）

1. リポジトリをクローン（あるいはソースを配置）
2. Python 3.10+ 環境を用意
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
4. プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、上記の必須環境変数を設定
5. データベースディレクトリを作成（必要なら）
   - mkdir -p data
6. DuckDB 接続先のパスを設定（`DUCKDB_PATH`）またはデフォルトを使用

---

## 使い方（主要な例）

以下はライブラリ API を利用する基本的な例です。各例は Python スクリプトや REPL で実行できます。

- 共通: settings / DuckDB 接続
```python
import duckdb
from kabusys.config import settings

# DuckDB ファイルに接続
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（例: 今日の ETL）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースのセンチメントをスコア化して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY に設定しておくか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", count)
```

- 市場レジームを判定する（regime テーブルへ書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))
```

- 品質チェックを実行
```python
from kabusys.data.quality import run_all_checks
from datetime import date

issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

- 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# 以降 audit_conn を用いて監査ログに書き込み
```

---

## 重要な実装上の注意点 / 運用メモ

- LLM 呼び出し（OpenAI）は JSON Mode を期待しており、レスポンスパース失敗時はフォールバック（スコア 0.0）する実装になっています。OpenAI API キーの管理とコストに注意してください。
- J-Quants API はレート制限（120 req/min）を守るためモジュール内でスロットリングを行います。大量データ取得時は実行時間に余裕を持ってください。
- ETL は差分・バックフィル方式で動作します。初回ロードや大きな遡及取得は時間がかかります。
- RSS 取得は SSRF、巨大レスポンス、XML 攻撃（defusedxml 使用）等の対策が組み込まれていますが、運用するホスト・ネットワークのポリシーに従ってください。
- DuckDB の executemany による空パラメータセットに関する制約（バージョン依存）を考慮した実装になっています。
- 環境を切り替える際は `KABUSYS_ENV` を指定して（development / paper_trading / live）適切に運用してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ソースは `src/kabusys` 以下にあります。代表的なファイル・モジュール構成：

- src/kabusys/
  - __init__.py
  - config.py                       （環境変数 / 設定管理）
  - ai/
    - __init__.py
    - news_nlp.py                    （ニュース -> LLM -> ai_scores）
    - regime_detector.py             （MA200 + マクロニュース -> market_regime）
  - data/
    - __init__.py
    - jquants_client.py              （J-Quants API client / 保存処理）
    - pipeline.py                    （ETL パイプライン / run_daily_etl 等）
    - etl.py                         （ETLResult の再公開）
    - news_collector.py              （RSS 収集）
    - calendar_management.py         （market_calendar の管理・営業日判定）
    - stats.py                       （zscore_normalize 等）
    - quality.py                     （データ品質チェック）
    - audit.py                       （監査ログスキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py             （momentum/volatility/value）
    - feature_exploration.py         （forward returns / IC / summary）
  - monitoring/ (present in __all__ but omitted in抜粋)
  - strategy/ (戦略層、将来の拡張想定)
  - execution/ (発注/約定連携、証券会社 API 連携想定)

---

必要に応じて README を補足します（例: CI/CD、具体的な ETL スケジュール例、Slack 通知の設定方法、kabu ステーション連携方法など）。ご希望の追加項目があれば教えてください。