# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、ファクター・リサーチ、監査ログ（発注トレーサビリティ）、市場カレンダー管理など、トレーディング基盤に必要な機能をモジュール化して提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（サンプル）
- 環境変数（主要項目）
- ディレクトリ構成

---

## プロジェクト概要

このライブラリは以下の目的を持ちます。

- J-Quants API から株価・財務・カレンダー情報を差分で取得して DuckDB に保存する ETL パイプライン
- RSS を使ったニュース取得と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI を使ったニュースセンチメント解析（銘柄毎 / マクロなど）
- 市場レジーム判定（ETF の MA とマクロセンチメントの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution まで追跡可能なテーブル群）

設計上の注意点：
- 可能な限りルックアヘッドバイアスを避ける（内部で date.today() を不用意に参照しない等）
- API 呼び出しはリトライ・レート制御を含む堅牢な実装
- DuckDB をデータ格納先に想定（ファイルまたはインメモリ）

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 環境変数アクセサ（settings）
- kabusys.data.jquants_client
  - J-Quants API クライアント（認証・ページネーション・レート制御・保存）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult（実行結果のデータクラス）
- kabusys.data.news_collector
  - RSS 取得・前処理・raw_news への冪等保存支援
  - SSRF 保護や受信サイズ制限など安全対策実装
- kabusys.ai.news_nlp
  - ニュースをまとめて OpenAI に投げ、銘柄毎の ai_score を ai_scores に保存
- kabusys.ai.regime_detector
  - ETF（1321）200日 MA 乖離とマクロセンチメントを組み合わせて market_regime を作成
- kabusys.research
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.quality
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- kabusys.data.calendar_management
  - 市場カレンダーの判定、next/prev trading day、calendar_update_job
- kabusys.data.audit
  - 監査ログテーブル（signal_events / order_requests / executions）の初期化ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の `X | Y` 型注釈を使用）
- DuckDB を利用するためネイティブ環境（通常の pip で動作）

手順概要：

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（例）
   - pip install duckdb openai defusedxml

   （必要に応じて logging 設定や他のユーティリティを追加）

3. 環境変数の準備
   - プロジェクトルートに `.env` を作成すると自動読み込みされます（.env.local で上書き可）。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須: JQUANTS_REFRESH_TOKEN（J-Quants 用リフレッシュトークン）
   - OpenAI を使う場合: OPENAI_API_KEY

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. (任意) DuckDB データベース初期化
   - 監査ログ専用 DB を初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/monitoring.duckdb")
     ```

---

## 使い方（代表的な例）

以下は簡単な Python スニペット例です。実行前に環境変数と DuckDB パスを準備してください。

- ETL（日次実行）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア付け（ai_scores へ書き込み）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key省略時は OPENAI_API_KEY を参照
print("written:", written)
```

- 市場レジーム判定（market_regime へ書き込み）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究用途、DB の prices_daily を参照）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

- 監査ログスキーマ初期化（既存接続）

```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 主要な環境変数

kabusys.config.Settings によって参照される主要キー：

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (kabuステーション API パスワード)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (OpenAI 呼び出しで使用)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知用、空でも動作)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB 等: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を起点）にある `.env` と `.env.local` を自動で読み込みます。既定では OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主なファイル構成:

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
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py
    - calendar_management.py
    - stats.py
    - quality.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファクター・探索用ユーティリティ）
  - (他: strategy, execution, monitoring パッケージが __all__ に含まれますがここには含まれていない場合があります)

重要なテーブル（期待されるスキーマ／用途）
- raw_prices / prices_daily: 株価日足データ（ETL 保存先）
- raw_financials: 財務データ
- market_calendar: JPX カレンダー（祝日・半日・SQ）
- raw_news / news_symbols / ai_scores: ニュース・銘柄関連
- market_regime: 日次の市場レジーム
- signal_events / order_requests / executions: 監査ログ（発注トレーサビリティ）

---

## 運用上の注意

- OpenAI / J-Quants など外部 API のキーは適切に管理してください（不要な公開を避ける）。
- ETL 実行はスケジューラ（cron 等）で夜間に行うことを想定しています。calendar_update_job はカレンダー情報を先に取得します。
- DuckDB のスキーマやテーブルは ETL／audit 初期化関数で作成・更新される前提です。既存データを扱う場合はバックアップを推奨します。
- ニュース収集は外部 URL へアクセスするため、ネットワーク制限や SSRF 対策をソース内で実施していますが、運用環境側でもアクセス制御を検討してください。

---

## おわりに

この README はコードベースから主要機能を要約したものです。詳細な API 仕様や追加のユーティリティは各モジュールの docstring を参照してください。実際の運用／実装時にはテスト・ログ監視・適切な権限管理を忘れずに行ってください。必要があれば README を拡張して CI / デプロイ手順・詳細な設定例などを追加できます。