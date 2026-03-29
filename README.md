# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュースの収集・NLP による銘柄センチメント評価（OpenAI）
- 市場レジーム判定（ETF とマクロニュースの組合せ）
- 研究用ユーティリティ（ファクター計算、IC・将来リターン分析）
- 発注・約定フローの監査ログ用スキーマ管理（監査テーブル初期化）

設計上の特徴：
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しない箇所が多い）
- API 呼び出しに対するリトライとレート制御
- DuckDB を用いたローカル永続化と SQL ベースの高速処理
- フェイルセーフ（API 失敗時はスキップして継続、致命的なクラッシュを最小化）

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（必要に応じて無効化可）
  - settings オブジェクト経由で設定値取得（JQUANTS_REFRESH_TOKEN など）

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl：市場カレンダー / 株価 / 財務 の差分取得と品質チェック
  - 個別ジョブ：run_prices_etl / run_financials_etl / run_calendar_etl

- J-Quants API クライアント（kabusys.data.jquants_client）
  - fetch / save 系関数（daily_quotes, financials, market_calendar）
  - トークン自動リフレッシュ、レートリミット、ページネーション対応

- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、前処理、raw_news への冪等保存（SSRF・XML攻撃対策あり）

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメント評価（ai_scores へ書込）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日移動平均乖離 + マクロニュース LLM スコアを合成して daily market_regime を作成

- 研究用モジュール（kabusys.research）
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）

- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合検出。QualityIssue オブジェクトで集約

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化関数
  - init_audit_db / init_audit_schema を提供

---

## セットアップ手順

下記は一般的なセットアップ例です。実際の依存関係は pyproject.toml / requirements.txt に合わせてください。

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt / pyproject が用意されている場合はそれを使用してください）

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml の上位）に `.env` / `.env.local` を配置できます。
   - 自動読み込みはデフォルトで有効（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化）

必須環境変数（動作に必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN       : Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先のチャンネル ID
- KABU_API_PASSWORD     : kabuステーション API パスワード（発注系を使う場合）
- OPENAI_API_KEY        : OpenAI を使う場合（score_news / score_regime に必要）

任意・デフォルト値あり
- KABUSYS_ENV           : development | paper_trading | live （デフォルト development）
- LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- DUCKDB_PATH           : DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）

サンプル .env
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C1234567890
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単な例）

以下は代表的な機能呼び出し例です。各例では DuckDB の接続オブジェクトを渡しています。

- DuckDB 接続
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（OpenAI が必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```

- 市場レジーム判定（OpenAI が必要）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで監査テーブル群が作成されます
```

- 研究用ファクター計算（例: Momentum）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# 結果は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ... }, ...]
```

- 環境設定の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 必須値。未設定で ValueError が発生
```

注意:
- score_news / score_regime は OpenAI API を呼ぶため、OPENAI_API_KEY を環境変数で設定するか関数引数で渡してください。
- 各関数はルックアヘッドバイアス回避のため target_date を受け取り内部で過去データのみ参照するよう設計されています。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数と settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースの OpenAI スコアリング（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch/save 系）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult 再エクスポート
    - news_collector.py     — RSS 収集・前処理
    - calendar_management.py— 市場カレンダー管理 / 営業日判定
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログスキーマの定義・初期化
  - research/
    - __init__.py
    - factor_research.py    — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py— calc_forward_returns / calc_ic / factor_summary / rank

各モジュールは責務ごとに分離されており、ETL・AI・研究・監査それぞれが独立して呼び出せます。

---

## 補足・注意点

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env/.env.local を読み込みます。テスト時に自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは外部サービス利用のためコストとレート制限に注意してください。retry / backoff ロジックは入っていますが、利用ポリシーに従ってください。
- DuckDB との互換性（executemany の空リストなど）に配慮した実装になっていますが、DuckDB のバージョン差に起因する問題が発生する可能性があります。
- J-Quants API 利用にはリフレッシュトークンが必要です。get_id_token で id_token を取得して内部でキャッシュ・自動更新します。

---

もし README に加えたいサンプルスクリプト、CI 設定、あるいは具体的な導入手順（pyproject.toml / packaging）などがあれば教えてください。それに合わせて README を拡張します。