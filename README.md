# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ。  
ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注/約定トレース）などを提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・研究・自動売買の基盤機能を集約した Python パッケージです。主な目的は次の通りです。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ベースのニュース収集と前処理、LLM（OpenAI）による銘柄別/マクロのセンチメント評価
- 市場レジーム判定（ETF MA と マクロセンチメントの合成）
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析（IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（シグナル → 発注要求 → 約定のトレーサビリティ）
- DuckDB を中心としたローカル DB 操作ユーティリティ群

---

## 機能一覧

- 環境設定管理（.env の自動読込、必須項目チェック）
- J-Quants クライアント（レート制限・リトライ・トークンリフレッシュ対応）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース収集（RSS の正規化、SSRF 対策、前処理）
- ニュース NLP（gpt-4o-mini を用いた銘柄別センチメント score_news）
- マクロセンチメントと ETF MA を合成した市場レジーム判定（score_regime）
- 研究用ファクター計算（calc_momentum, calc_volatility, calc_value 等）
- 統計ユーティリティ（zscore正規化, factor_summary, IC 計算）
- データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
- 監査ログ初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提
- Python 3.10+（型ヒントに `X | None` 形式を使用）
- DuckDB を利用（ローカルファイルまたは :memory:）
- OpenAI の Python SDK（パッケージ名: openai）
- defusedxml（ニュース XML パース用）

推奨インストール手順（例）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml を用意してください）

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` や `.env.local` を置けます。config モジュールは起動時に自動で読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

推奨 `.env`（最小例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- 必須な環境変数は config.Settings が参照し、未設定時は ValueError を出します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
- 自動読み込みを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（簡単な例）

以下は主要なユースケースの最小例です。実際はログ設定やエラーハンドリングを追加してください。

共通: DuckDB 接続と settings の取得
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行（株価・財務・カレンダー・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しないと本日が対象
print(result.to_dict())
```

2) ニュースセンチメントをスコアリング（前日 15:00 JST ～ 当日 08:30 JST 範囲）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

# 明示的に API キーを渡すことも可能。None なら環境変数 OPENAI_API_KEY を参照
written = score_news(conn=conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {written} symbols")
```

3) 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn=conn, target_date=date(2026, 3, 20), api_key=None)
print("score_regime done:", res)
```

4) 監査ログ用の DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # :memory: 可
# テーブルが作成され、UTC タイムゾーンが設定されます
```

5) 研究用関数の利用例（モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
# 結果は [{"date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]
```

ログレベルは環境変数 LOG_LEVEL により調整してください（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

## 主要テーブル（参照されるもの）

コード中で参照される代表的なテーブル（DuckDB 想定）：
- raw_prices / prices_daily
- raw_financials
- market_calendar
- raw_news / news_symbols
- ai_scores
- market_regime
- signal_events / order_requests / executions（監査ログ）

ETL / save_* 関数は多くが ON CONFLICT DO UPDATE を用いて冪等にデータ保存します。

---

## ディレクトリ構成（主なファイル）

以下はパッケージ内部の主要モジュール構成（src/kabusys 以下）です。実際のリポジトリでは tests / docs 等が追加されることを想定します。

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                    — 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 + 保存）
    - pipeline.py                    — ETL パイプライン (run_daily_etl 等)
    - etl.py                         — ETL インターフェース（ETLResult の再エクスポート）
    - news_collector.py              — RSS 取得 + 正規化 + 保存
    - calendar_management.py         — 市場カレンダー・営業日判定
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Value / Volatility 計算
    - feature_exploration.py         — forward returns / IC / summary / rank

---

## 注意事項 / 運用上のポイント

- OpenAI API 呼び出し（news_nlp, regime_detector）は外部 API に依存します。API キーは OPENAI_API_KEY 環境変数か、各関数の api_key 引数で指定してください。
- J-Quants API の認証はリフレッシュトークン（JQUANTS_REFRESH_TOKEN）を用い、モジュール内で id token をキャッシュ・自動リフレッシュします。
- ETL 周りは部分失敗時に既存データを保護する設計（部分的DELETE→INSERT など）になっていますが、本番環境での動作確認・バックアップは必須です。
- DuckDB のバージョン差異により executemany の空リスト取り扱い等で注意が必要です（pipeline モジュール内に考慮があります）。
- ニュース収集は SSRF 対策、コンテンツ長チェック、XML パース安全化（defusedxml）等を行っていますが、追加のセキュリティ要件があれば調整してください。

---

もし README に追加したい内容（例: 実運用のデプロイ手順、CI 設定、より詳しいテーブルスキーマ、サンプル .env.example ファイル）や、特定の機能のドキュメント化希望があれば教えてください。