# KabuSys

日本株自動売買プラットフォームのライブラリ群（データETL / ニュースNLP / 市場レジーム判定 / 研究用ユーティリティなど）。

バージョン: 0.1.0 (src/kabusys/__init__.py)

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・ニュースセンチメント解析・市場レジーム判定・ファクター計算などを行うためのモジュール群です。主な目的は以下です。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- RSS ニュース収集と OpenAI を用いた銘柄別センチメント算出
- ETF 指標とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算・特徴量探索のための研究ユーティリティ
- ETL/データ品質チェック・監査ログ（監査テーブル初期化ユーティリティ）

設計方針として、ルックアヘッドバイアス防止・冪等性・フォールバックの明示的な扱い・外部API呼出しのリトライ制御等が盛り込まれています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（無効化可）
  - 必要な環境変数のプロパティ経由アクセス（kabusys.config.settings）

- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API からの株価・財務・市場カレンダー取得（ページネーション・レート制御・リトライ）
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
  - ETL 実行結果を ETLResult で集約（品質チェック含む）

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合検出
  - QualityIssue オブジェクトで問題を返す

- ニュース収集 / NLP（kabusys.data.news_collector, kabusys.ai.news_nlp）
  - 安全対策（SSRF 対策、受信サイズ制限、XML パース安全化）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（ai_scores テーブルへ書き込み）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定
  - OpenAI 呼び出しのリトライ・フォールバックロジックあり

- 研究用ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー等
  - クロスセクション正規化ユーティリティ（zscore_normalize）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - init_audit_db() による DuckDB 初期化

---

## セットアップ手順

※ 以下は一般的なセットアップ手順です。プロジェクト配布に requirements.txt / pyproject.toml があればそちらを優先してください。

1. Python バージョン
   - Python 3.10 以上を推奨（typing の | などを使用）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （実際のプロジェクトでは追加パッケージが必要になる可能性があります。pyproject.toml / requirements.txt を確認してください）

4. リポジトリのインストール（編集可能にする）
   - cd <project-root>
   - pip install -e .

5. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置できます（src/kabusys/config.py が自動読み込み）。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須の環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime が使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注系）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先チャンネル ID

その他（任意）:
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例 .env（プロジェクトルート）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（代表的な例）

以下は Python REPL / スクリプトからの利用例です。

- 設定値を参照する
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続を作成して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))  # settings は上で取得
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に保存
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"Scored {count} symbols")
```

- 市場レジーム判定（1321 の MA200 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # requires OPENAI_API_KEY
```

- 監査用 DuckDB 初期化（order / execution テーブルなど）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は監査用 DB の接続
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- 将来リターン・IC 計算（特徴量探索）
```python
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2026,3,20), horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

注意点:
- score_news / score_regime は OpenAI の API 呼び出しを行うため OPENAI_API_KEY が必須です。API 呼び出しはリトライやフォールバックを含みますが、キー未設定時は ValueError を送出します。
- jquants_client は J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）を用いて id_token を取得します。

---

## ディレクトリ構成（主なファイル）

以下はソースツリーのトップレベル（src/kabusys 以下）の簡易一覧です。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースセンチメントの取得・ai_scores 書き込み
    - regime_detector.py               — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETL 結果クラス再エクスポート
    - news_collector.py                — RSS 収集器（SSRF 対策等）
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py           — 市場カレンダー管理（営業日判定等）
    - audit.py                         — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py               — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py           — 将来リターン / IC / 統計サマリー

（上記以外にも strategy / execution / monitoring 等のサブパッケージが __all__ に列挙されていますが、ここに示したのが主要なデータ/AI/研究関連モジュールです）

---

## 注意事項 / 補足

- DB スキーマ
  - audit モジュールには監査テーブルの DDL が含まれており init_audit_db() で初期化できます。
  - raw_prices / raw_financials / raw_news / ai_scores 等のスキーマは本 README のコード断片には一部定義が見当たりません。ETL を実行する前に使用する DuckDB に必要なテーブルスキーマを用意してください（プロジェクトにマイグレーションスクリプトがある場合はそれを使用）。

- セキュリティ
  - news_collector は SSRF 対策・XML の安全パース・受信サイズ制限等を実装していますが、実環境での運用時はさらにネットワークポリシーやアクセス制御を検討してください。

- 自動 .env 読み込み
  - src/kabusys/config.py はプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動読み込みします。テストなどで自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI / J-Quants のリトライ・レート制御
  - OpenAI 呼び出しは API エラーに対してリトライとフェイルセーフ（ゼロスコアフォールバック）を行います。
  - J-Quants クライアントはレートリミット（120 req/min）を守る実装になっています（モジュールレベルの RateLimiter）。

---

もし README に含めたい追加の手順（例えばスキーマ定義ファイル、CI 設定、実行用の systemd / cron 設定例、より詳細なサンプルスクリプトなど）があれば教えてください。必要に応じて追記・整備します。