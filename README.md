# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants）→ DuckDB 保存、ニュース収集・NLP によるセンチメント評価、ファクター計算、監査ログなどを含むモジュール群を提供します。

## 概要

KabuSys は次の目的をもつ内部ライブラリです。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存（ETL）
- RSS ベースのニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini 想定）を用いたニュースセンチメント評価（銘柄別 / マクロ）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用統計ユーティリティ
- 市場カレンダー、データ品質チェック、監査ログ（発注 -> 約定のトレース可能化）
- kabuステーション等実際の発注・監視（パッケージ構成上の別モジュール想定）

設計方針として「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗は局所的にフォールバック）」を重視しています。

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル・品質チェック）
  - J-Quants クライアント（認証・レート制御・リトライ・ページネーション）
- データ基盤
  - DuckDB への保存ユーティリティ（raw_prices / raw_financials / market_calendar など）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 市場カレンダー管理（営業日判定 / next/prev / get_trading_days）
- ニュース & AI
  - RSS 収集（SSRF 対策・トラッキングパラメータ除去・前処理）
  - ニュース NLP: score_news（銘柄別センチメントを ai_scores に保存）
  - レジーム判定: score_regime（ETF 1321 の MA200 とマクロニュースを組み合わせて market_regime に保存）
  - OpenAI 呼び出しは JSON Mode を利用し、エラー時はフェイルセーフで無効化
- 監査ログ
  - init_audit_schema / init_audit_db（signal_events / order_requests / executions 等のテーブルとインデックスを作成）
- 研究用
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
  - 統計ユーティリティ（zscore_normalize）

## 必要条件

- Python 3.10+
- 推奨パッケージ（最小限）
  - duckdb
  - openai
  - defusedxml

（プロジェクト配布に requirements.txt がある場合はそちらを利用してください）

## セットアップ手順

1. リポジトリをチェックアウト / コピーする

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   またはプロジェクトルートに setup/pyproject があれば
   - pip install -e .

4. 環境変数を設定（.env をプロジェクトルートに置くと自動読み込みされます）
   - 自動読み込みは config モジュールで .git または pyproject.toml を基準にプロジェクトルートを探索して .env → .env.local をロードします。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

### 例: .env（必須/任意の主なキー）

必須:
- JQUANTS_REFRESH_TOKEN=あなたのJ-Quantsリフレッシュトークン
- KABU_API_PASSWORD=（kabuステーション API パスワード: 必要な場合）

任意（デフォルト値あり/通知用など）:
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動 .env 読み込みを停止したい場合

OpenAI 用:
- OPENAI_API_KEY=sk-...

LINE 通知:
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...

データベースパス（デフォルトは data/*.duckdb / data/monitoring.db）:
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

監視設定:
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0

その他はソース内の Settings プロパティを参照してください（kabusys/config.py）。

## 使い方（簡単なコード例）

以下は Python スクリプトや REPL からの利用例です。DuckDB 接続は duckdb.connect("path") を使います。

- ETL（日次パイプライン）実行例

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（銘柄別 AI スコア）実行例

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print("wrote", n_written)
```

- 市場レジーム判定実行例

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

- 監査ログ DB 初期化例

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests 等を操作できます
```

- カレンダー操作例

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- OpenAI キーは引数で明示的に渡すか環境変数 OPENAI_API_KEY を設定します。
- 多くの関数は DuckDB 内の特定テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, prices_daily, market_regime など）を前提とします。ETL や schema 初期化が必要です。

## 設定と自動環境読み込み

- config.Settings が主要な設定をラップしています（kabusys/config.py）。
- .env 自動読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 必須環境変数が未設定の場合 Settings のプロパティ（例: jquants_refresh_token）が ValueError を投げます。

## ディレクトリ構成

主要ファイル / モジュール（src/kabusys 以下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         — ニュースの集約と OpenAI による銘柄別センチメント評価（score_news）
  - regime_detector.py  — ETF 1321 MA200 とマクロニュースの LLM 評価を合成して市場レジームを判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（取得・認証・保存）
  - pipeline.py         — ETL パイプライン実装（run_daily_etl 等）
  - etl.py              — ETL 結果型のエクスポート（ETLResult）
  - news_collector.py   — RSS 取得・前処理・raw_news 保存
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - quality.py          — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py            — 汎用統計関数（zscore_normalize 等）
  - audit.py            — 監査ログテーブル初期化（signal_events / order_requests / executions）
- research/
  - __init__.py
  - factor_research.py  — ファクター計算（モメンタム/バリュー/ボラティリティ）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー等

（上記は機能別の概要。実際の schema／テーブル名はソース内の SQL 定義を参照してください。）

## 開発・テストに関するヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に実行されます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env に依存せず明示的に環境変数を注入できます。
- OpenAI 呼び出しは内部で再試行やエラー処理を行いますが、ユニットテストでは _call_openai_api をモックすることで API 依存を切り離してテスト可能です（ソースにその旨の注記あり）。
- DuckDB への executemany に対する制約（バージョン依存）を考慮した実装になっています。ローカルで DuckDB を最新にしてテストしてください。

## 注意事項

- 本ライブラリは実際の発注システム（ライブ取引）と連携する可能性があるため、ライブ環境で使用する場合は十分な検証を行ってください。
- API キーやパスワード等の機密情報は .env 等で管理し、リポジトリにコミットしないでください。
- J-Quants / OpenAI 等の外部 API 利用には利用規約や料金が発生します。事前に確認してください。

---

不明点や追加したい README セクション（例: schema の詳細、CI 設定、具体的なテーブル定義一覧など）があれば教えてください。必要に応じてサンプル .env.example やテーブルスキーマの抜粋も作成します。