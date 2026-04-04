# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。ETL、データ品質チェック、ニュース収集／NLP（OpenAI）評価、研究用ファクター計算、監査ログ（トレーサビリティ）など、取引システムと研究環境の共通基盤を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は以下の役割を持つモジュール群で構成されています。

- データ取得・ETL（J-Quants API 経由で株価・財務・カレンダーを取得し DuckDB に格納）
- データ品質チェック（欠損・重複・未来日付・スパイク検出）
- ニュース収集（RSS）とニュース NLP（OpenAI を使った銘柄ごとのセンチメント評価）
- 市場レジーム判定（ETF の移動平均乖離とマクロ記事の LLM センチメントを合成）
- 研究用ユーティリティ（ファクター算出、将来リターン、IC 計算、正規化）
- 監査ログ（シグナル → 発注 → 約定 のトレース可能なスキーマと初期化）

設計方針として「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ」を重視しています。

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）: レート制御・再試行・トークン自動リフレッシュ
- データ品質チェック（kabusys.data.quality）
  - 欠損 / 重複 / スパイク / 日付不整合
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、SSRF 対策、ID 生成（URL 正規化 + SHA256）
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄毎センチメントスコアリング
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）200日 MA 乖離とマクロニュースセンチメントを合成して daily レジームを保存
- 研究（kabusys.research）
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの作成・初期化・監査 DB 初期化関数

---

## セットアップ手順

※プロジェクトは Python パッケージとして利用する想定です。以下はローカル開発環境での手順例です。

1. Python 環境（3.10+ 推奨）を用意する。
2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール：
   - pip install duckdb openai defusedxml
   - （プロジェクト化されている場合は pip install -e . など）
4. 環境変数を用意する（.env をプロジェクトルートに置くことで自動読み込みされます）。
   - 自動読み込みは kabusys.config がプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込みます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

推奨される .env の例:
- .env.example（参考）
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - OPENAI_API_KEY=your_openai_api_key
  - KABU_API_PASSWORD=your_kabu_api_password
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - KABUSYS_ENV=development
  - LOG_LEVEL=INFO

必須（機能を使う場合）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY: OpenAI 呼び出し（ニュース NLP / レジーム判定）用
- KABU_API_PASSWORD: kabuステーション API を使う場合

環境変数の取り扱いは kabusys.config.Settings でラップされています。

---

## 使い方（主要 API とサンプル）

以下は Python からの利用例です。DuckDB 接続には duckdb.connect("path") を使用します。

1) 日次 ETL 実行（株価・財務・カレンダー取得、品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI を使用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print(f"書き込んだ銘柄数: {n_written}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

4) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# conn を使って監査ログ書き込み等を行う
```

5) 研究用ファクター計算（例：モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{ "date":..., "code":..., "mom_1m":..., ...}, ...]
```

注意点:
- すべての「target_date」は内部で datetime.today() を参照しないように設計されています（ルックアヘッドバイアス防止）。
- OpenAI 呼び出しは失敗時にフェイルセーフでスコア 0.0 を採用するなど堅牢に設計されています。
- DuckDB の executemany に空リストを渡さないなど、バージョン互換性に配慮しています。

---

## 設定と環境変数

主な設定は kabusys.config.Settings で取得できます。重要な環境変数：

- JQUANTS_REFRESH_TOKEN（必須 for ETL）
- OPENAI_API_KEY（必須 for AI/NLP）
- KABU_API_PASSWORD（kabuステーション API を使う場合）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH（監視プロセス用）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml）から .env を読み込みます。
- 上書き順序: OS 環境 > .env.local > .env
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールとその役割です（抜粋）。

- kabusys/
  - __init__.py                - パッケージ公開（version 等）
  - config.py                  - 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py              - ニュースの LLM スコアリング
    - regime_detector.py       - 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py   - 市場カレンダーの管理（営業日判定）
    - etl.py                   - ETL インターフェース（ETLResult 再エクスポート）
    - pipeline.py              - ETL パイプライン（run_daily_etl 等）
    - stats.py                 - 統計ユーティリティ（zscore_normalize）
    - quality.py               - データ品質チェック
    - audit.py                 - 監査ログスキーマと初期化
    - jquants_client.py        - J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py        - RSS 取得と前処理
  - research/
    - __init__.py
    - factor_research.py       - ファクター計算（momentum, value, volatility）
    - feature_exploration.py   - 将来リターン・IC・summary 等

フルソースは src/kabusys 以下に格納されています。README で紹介した関数群は各モジュールの公開 API を参照してください。

---

## 依存関係（主な Python パッケージ）

- duckdb
- openai
- defusedxml

（実行環境に応じて他パッケージが必要になる場合があります）

---

## ロギングと運用上の注意

- 設定により LOG_LEVEL を切替可能（環境変数 LOG_LEVEL）。
- ETL・API 呼び出しにおける再試行やバックオフが組み込まれていますが、外部 API（J-Quants・OpenAI）のレート制限に注意してください。
- 監査ログは削除しない前提です。init_audit_db で監査用の DuckDB を初期化できます。
- テスト時や CI で自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 貢献・拡張

- 新しいデータソース（RSS / API）を追加する場合は data/news_collector.py / data/jquants_client.py の設計に合わせて実装してください（冪等性、サイズ制限、SSRF 対策など）。
- OpenAI モデルやプロンプトを調整する場合は ai/news_nlp.py / ai/regime_detector.py の _SYSTEM_PROMPT やモデル名を変更してください。
- 研究モジュールは外部ライブラリに依存しない設計です。大規模分析が必要な場合は別モジュールで pandas 等を使った派生実装を作るのがおすすめです。

---

もし README に追加してほしい内容（例: CI / テスト手順、詳細なスキーマ定義、Dockerfile 例など）があれば教えてください。