# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（発注・約定）などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下の目的を持つ Python パッケージです。

- J-Quants API を用いた日次データの差分取得（株価・財務・カレンダー）
- ニュース収集（RSS）と LLM（OpenAI）による銘柄別センチメント付与
- 市場レジーム判定（ETF とマクロニュースを統合）
- ファクター計算・特徴量解析（研究用ユーティリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマ（シグナルから約定までのトレーサビリティ）
- 環境設定管理（.env から自動読み込み）

設計上、バックテストでの look-ahead bias を避けるために、日付参照は明示的な引数（target_date）ベースで行われます。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証、ページネーション、保存用ユーティリティ）
  - 市場カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS、SSRF 対策、前処理）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化（監査スキーマの作成・専用 DB 初期化）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp: ニュース記事を LLM に投げて銘柄ごとのスコアを ai_scores テーブルへ挿入
  - regime_detector: ETF（1321）200日 MA 乖離とマクロ記事の LLM 感情を合成して市場レジームを判定
- research/
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config.py
  - .env と環境変数の読み込み（自動ロード）および settings オブジェクト
- audit/
  - 監査スキーマ定義と初期化ユーティリティ

セキュリティ面では RSS の SSRF 対策、defusedxml による XML パース保護、J-Quants/API 呼び出しのリトライ・レート制御などが組み込まれています。

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに | 記法を使用）
- OS によっては `libssl` などのネイティブ依存が必要になる場合あり

1. リポジトリをクローンしてパッケージをインストール（開発用）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 必要な外部パッケージ（例）
   ```
   pip install duckdb openai defusedxml
   ```
   ※プロジェクトで requirements.txt を用意している場合はそれを使ってください。

3. 環境変数の設定
   プロジェクトルートに `.env` ファイルを作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数（一部必須）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector 用）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: environment（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-xxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース初期化（監査ログなど）
   - 監査ログ用 DB を初期化する例は下記の「使い方」を参照。

---

## 使い方（代表的な例）

以下は Python スクリプトまたは REPL から呼び出す例です。基本的に DuckDB 接続を作って関数を呼びます。

共通：settings と DuckDB 接続
```python
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの LLM スコアリング（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されている前提
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（監査テーブルを持つ新しい DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成される
# audit_conn は監査テーブルが作成された接続
```

5) ファクター計算（研究用）
```python
from kabusys.research import calc_momentum, calc_value
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

6) スキーマ初期化 / テーブル作成について
- 本リポジトリにはスキーマ定義（監査スキーマ等）が含まれており、init 関数で作成します。
- raw_prices / raw_financials / market_calendar 等のテーブルは ETL パイプラインまたは別途スキーマ初期化関数で用意してください（実装に応じて）

---

## 注意点 / 運用上のポイント

- Look-ahead bias を避けるため、各関数は内部で date.today() を直接参照せず、明示的に target_date を受け取る設計です。バッチやバックテストでは必ず日付を渡してください。
- OpenAI 呼び出しはリトライやフェイルセーフを備えていますが、API キー（OPENAI_API_KEY）は必須です。API 呼び出し失敗時は安全に 0.0 等にフォールバックする実装が入っています。
- J-Quants API はレートリミットを厳守するよう制御されています。長時間ジョブや並列処理は制限に注意してください。
- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml を基準に検出して実行されます。テストで自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV は development / paper_trading / live のいずれかを設定すること（他の値は ValueError）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP スコアリング（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch/save）
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - etl.py                — ETLResult の再エクスポート
    - news_collector.py     — RSS 収集（SSRF 対策, 前処理）
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - quality.py            — データ品質チェック
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - audit.py              — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility 等
    - feature_exploration.py— Forward returns / IC / summary / rank
  - research/*（ファクター分析用ユーティリティ群）
  - (その他: strategy, execution, monitoring を想定したエントリは __all__ に含まれています)

各モジュールは docstring に設計方針や処理フローが詳細に記載されています。実装の詳細やパラメータは該当ファイルを参照してください。

---

## ライセンス・貢献

（ここにライセンス情報や貢献手順を追加してください）

---

不明点や README に追加してほしい内容（例: 実行スクリプト、CI、テスト手順、具体的なスキーマ DDL 等）があれば教えてください。README を拡張します。