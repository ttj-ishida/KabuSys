# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。  
J-Quants / RSS / OpenAI 等を組み合わせ、データ収集（ETL）→ 品質チェック → AI によるニュース評価 → ファクター算出 → 監査ログ生成までのワークフローを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とする Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（ETL）
- RSS ニュース収集と LLM による銘柄別ニュースセンチメント算出
- マーケットレジーム判定（ETF の MA とマクロニュースの LLM 評価の合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化
- データ品質チェック、カレンダ管理、ニュース収集の堅牢な実装

設計方針としては、Look-ahead bias を避けるため「内部で現在時刻を参照しない」等の注意が組み込まれており、DuckDB を主要なローカルデータストアとして利用します。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント: 株価日足、財務データ、マーケットカレンダー、上場銘柄情報
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 差分取得（最終取得日からの差分 + バックフィル）

- ETL パイプライン
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック を一括実行
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl

- データ品質チェック
  - 欠損（OHLC）検出、重複検出、スパイク検出、日付整合性チェック
  - QualityIssue オブジェクトで問題を収集

- ニュース収集 & NLP
  - RSS を安全に収集（SSRF 対策、サイズ制限、トラッキングパラメータ削除）
  - news_nlp.score_news: OpenAI（gpt-4o-mini 等）で銘柄別センチメントを算出・保存
  - マクロニュースからのセンチメント -> regime_detector.score_regime により市場レジーム判定

- 研究用ユーティリティ
  - ファクター算出: calc_momentum / calc_value / calc_volatility
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - 監査用スキーマ定義・初期化（signal_events / order_requests / executions）
  - init_audit_db / init_audit_schema により DuckDB を準備

- 設定管理
  - 環境変数 / .env 自動ロード（プロジェクトルートの .git か pyproject.toml を検索）
  - settings オブジェクトから各種設定を取得

---

## セットアップ手順（開発環境）

前提:
- Python 3.10 以上（PEP 604 の型 | を使用しているため）
- Git 等でリポジトリルートがあると .env 自動読み込みが有効になる

1. 仮想環境を作成して有効化（任意）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 必要パッケージをインストール（最小セット）
   ```
   pip install duckdb openai defusedxml
   ```
   プロジェクトに requirements.txt や pyproject.toml がある場合はそちらを使用してください:
   ```
   pip install -e .
   ```

3. 環境変数設定
   - リポジトリルートに `.env`（および必要に応じて `.env.local`）を配置します。
   - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます（テスト用途等）。

必要な主要環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（fetch系 API に必要）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注関連）
- OPENAI_API_KEY: OpenAI API を使う機能（news_nlp / regime_detector）

任意:
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/...）

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- 自動読み込み順: OS 環境 > .env.local > .env
- プロジェクトルートは __file__ の親ディレクトリを上って `.git` または `pyproject.toml` を探すことで決定します。

---

## 使い方（主要な利用例）

以下は Python スクリプト / REPL からの呼び出し例です。

- DuckDB 接続の準備（デフォルトパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースのセンチメント算出（OpenAI API キー必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("scored:", count)
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を利用
```

- 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成されます
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentums = calc_momentum(conn, date(2026,3,20))
values = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
```

- カレンダー／営業日ユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, get_trading_days, next_trading_day

d = date(2026,3,20)
print(is_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
print(next_trading_day(conn, d))
```

注意点:
- OpenAI を使う関数は api_key を引数で注入可能（テスト容易性のため）。None を渡すと環境変数 OPENAI_API_KEY を参照します。
- 各関数は Look-ahead bias を避けるため target_date を明示して呼び出すことを想定しています（内部で date.today() を参照しない設計が多い）。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数 / .env 自動ロード / settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM ベーススコアリング（score_news）
  - regime_detector.py — マーケットレジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得/保存/認証/レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — マーケットカレンダー & 営業日判定
  - news_collector.py — RSS 収集と前処理
  - quality.py — データ品質チェック
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank

各ファイルにはモジュール内ドキュメント（docstring）とログ出力が整備されています。

---

## 開発 / 運用上の注意

- Python バージョン: 3.10 以上を推奨
- DuckDB をデータストアとして利用するため、DB パス（DUCKDB_PATH）のディレクトリは事前に作成するか、モジュールから作成するコードを用意してください（audit.init_audit_db は親ディレクトリ作成あり）。
- OpenAI 利用時は API レートや費用に注意してください。news_nlp と regime_detector はリトライやフェイルセーフ（失敗時は 0.0 にフォールバック）を備えていますが、予期せぬコストがかかる可能性があります。
- .env 自動読み込みはプロジェクトルートの検出に .git または pyproject.toml を利用します。パッケージ配布後や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にして手動で設定する運用を検討してください。
- kabu 系（実際の発注）を統合する場合、必ず paper_trading モード等で十分な検証を行ってください（KABUSYS_ENV による切替を想定）。

---

もし README のフォーマット（より詳細な例、API リファレンス、コマンドラインツール化など）の追加や、各モジュールごとの詳細な説明（関数引数一覧や戻り値の詳細）を希望する場合は、その範囲を指定してください。