# KabuSys

日本株自動売買プラットフォームのコアライブラリ群です。  
このリポジトリはデータ収集（ETL）、データ品質チェック、特徴量計算、ニュース／LLM ベースのセンチメント解析、マーケットレジーム判定、監査ログ用スキーマなどを提供します。

主な設計方針は「ルックアヘッドバイアスを排除」「DuckDB を中心としたローカルデータ管理」「外部 API 呼び出しはリトライ・フェイルセーフで扱う」といった点です。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（jquants_client, data.pipeline）
  - 日次 ETL の統合エントリ（run_daily_etl）
  - レート制限・トークン自動リフレッシュ・リトライ実装
- データ管理
  - DuckDB を用いた永続化（raw_prices / raw_financials / market_calendar 等）
  - 市場カレンダー管理（営業日判定・prev/next/get_trading_days）
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
- データ品質チェック
  - 欠損データ、スパイク、重複、日付整合性チェック（data.quality）
  - チェック結果は QualityIssue オブジェクトで返却
- ニュース収集・前処理
  - RSS 取得（SSRF 対策、URL 正規化、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存ロジック
- AI（LLM）連携
  - ニュースのセンチメント解析（kabusys.ai.news_nlp）
  - マクロニュースと ETF MA 乖離を合成した市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI（gpt-4o-mini）を JSON Mode で利用、リトライ & フォールバック実装
- 研究/ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン・IC 計算・統計サマリ（research.feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats）

---

## セットアップ手順

※以下は開発環境/実行環境の一例です。環境に合わせて調整してください。

1. Python（推奨 3.10+）をインストールします。

2. 仮想環境を作成して有効化（任意だが推奨）:
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストールします（例）:
   ```
   pip install duckdb openai defusedxml
   ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を用意して pip install -r 等で管理してください。

4. 環境変数を設定します。プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   主要な環境変数（最低限必要なもの）:
   - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY：OpenAI API キー（score_news / regime_detector を使う場合必須）
   - KABU_API_PASSWORD：kabuステーション API のパスワード（実行時に必要な場合）
   - DUCKDB_PATH：DuckDB データベースファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH：監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV：environment（development / paper_trading / live）
   - LOG_LEVEL：ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. （任意）データディレクトリ作成:
   ```
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下は Python スクリプト内からライブラリを使う基本例です。すべて DuckDB の接続オブジェクト（duckdb.connect）を渡して操作します。

- 設定参照:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースに対する AI スコアを計算して ai_scores テーブルへ書く:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み件数:", n_written)
```

- 市場レジーム判定を行う:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を用いて監査テーブルに書き込み可能
```

- 研究用ファクター計算:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
```

注意:
- OpenAI を使う関数（score_news, score_regime）は API キーを引数に渡すか環境変数 OPENAI_API_KEY を設定する必要があります。
- DuckDB のスキーマ（必要なテーブル定義）はプロジェクト別に初期化スクリプトを用意する想定です。テスト時は ":memory:" を使えます。
- 多くの外部通信処理はリトライやフォールバック（失敗時はスコア0や空結果）を行う設計です。

---

## 主要モジュールと API（簡易まとめ）

- kabusys.config
  - settings: 環境変数ラッパー（JQUANTS_REFRESH_TOKEN 等）
  - 自動 .env ロード機能あり

- kabusys.data
  - jquants_client: J-Quants API 呼び出し / DuckDB への保存（fetch_* / save_*）
  - pipeline: run_daily_etl、個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - news_collector: RSS 収集・正規化・前処理
  - calendar_management: market_calendar 管理・営業日判定
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

- kabusys.research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize は data.stats から提供

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
    - (その他研究用モジュール)
  - research/
  - monitoring/ (参照あり、詳細実装ファイルはここに含まれる想定)
  - ai/（LLM 関連）

各モジュールは docstring に処理フローと設計方針が詳細に書かれています。実装を読みながら使い方を把握してください。

---

## 注意事項 / 運用上のヒント

- 環境変数は .env / .env.local より OS 環境変数が優先されます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは API エラー時にフォールバック（0.0）する設計ですが、API レート制限・課金には注意してください。
- J-Quants の API レート（120 req/min）を守るため内部に RateLimiter が実装されています。大量の並列リクエストは避けてください。
- DuckDB の executemany に空のリストを与えるとバージョンによってエラーになる点に注意（コード内で空チェックあり）。
- 監査ログのスキーマは冪等（IF NOT EXISTS）で作成されますが、既存データの運用ルールに気をつけてください。

---

README はプロジェクトの導入部として必要最低限の操作例と説明をまとめています。実際に運用する際はユースケースに合わせて schema 初期化スクリプト、マイグレーション、運用用監視（monitoring）やリスク管理ロジックを追加してください。質問や特定機能の詳細ドキュメントが必要であればお知らせください。