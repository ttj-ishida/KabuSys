# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株に特化したデータプラットフォームおよび研究・運用ユーティリティの集合です。主な目的は以下のとおりです。

- J-Quants API を用いた株価／財務／マーケットカレンダーの差分ETL
- RSS ニュース収集と OpenAI を使った銘柄別センチメント（ai_score）算出
- ETF とマクロニュースから市場レジーム（bull/neutral/bear）判定
- ファクター（モメンタム、ボラティリティ、バリュー等）計算と探索ツール
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）を格納する DuckDB スキーマ

設計方針の要点:
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を参照しない）
- DuckDB を中心としたローカルデータ管理（冪等書き込み）
- OpenAI 呼び出しはリトライ・フェイルセーフ実装
- ネットワーク安全（RSS の SSRF 防止・サイズ制限等）

---

## 機能一覧

- data/
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（取得 + DuckDB への保存）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSSの安全取得・前処理・raw_news 保存）
  - 品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI 呼び出しは gpt-4o-mini（JSON Mode）を想定、最大リトライ等のフェイルセーフあり
- research/
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数/.env 管理（自動ロード、必須チェック）
- audit / execution / strategy / monitoring（パッケージ公開名に含まれるが、主要な実装は data/ と ai/ に集中）

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈の `X | None` 等を使用）
- Git リポジトリルートにプロジェクトを配置

例: 仮想環境作成・依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
```

（プロジェクトをパッケージとして使用する場合は `pip install -e .` を想定できますが、ここでは必要ライブラリのみ明示しています。）

環境変数:
- 必須（コード中で _require() によってチェックされるもの）
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD : kabuステーション等の API パスワード（利用箇所に依存）
  - SLACK_BOT_TOKEN : Slack 通知用（必要な場合）
  - SLACK_CHANNEL_ID : Slack 通知先チャンネル
- 任意 / デフォルトあり
  - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL : DEBUG/INFO/...（デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 をセットすると .env 自動ロードを無効化
  - OPENAI_API_KEY : OpenAI 呼び出しに必要（score_news / score_regime は引数でも指定可）
  - DUCKDB_PATH : デフォルト data/kabusys.duckdb
  - SQLITE_PATH : デフォルト data/monitoring.db

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し、`.env` → `.env.local` の順で読み込みます。
- OS 環境変数を上書きしない（`.env.local` は上書き可だが既存の OS 環境変数は保護されます）。
- テスト等で自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

データベース:
- デフォルトで DuckDB ファイルは data/kabusys.duckdb に保存されます（settings.duckdb_path）。
- 監査ログ用に専用 DB を作る場合は kabusys.data.audit.init_audit_db() を使用します。

---

## 使い方（簡易サンプル）

以下は代表的な利用例です。関数の多くは DuckDB 接続（duckdb.connect(...) の戻り値）を受け取ります。

1) DuckDB 接続を作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 監査スキーマ初期化（既存の接続に監査テーブルを追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)  # transactional オプションあり
```

3) 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

4) ニュース NLP スコア生成（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数から取得
print(f"wrote {n_written} ai_scores")
```

5) 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

6) ファクター計算・研究系サンプル
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.data.stats import zscore_normalize

target = date(2026,3,20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# Z スコア正規化例
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

7) RSS 収集（ニュースコレクタ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# 取得後、DB 保存処理は別途実装されている save 系関数等に渡す想定
```

注意点:
- OpenAI 呼び出しには課金・API制限があります。score_news/score_regime は内部でリトライやバッチ処理を行いますが、APIキーの管理は慎重に。
- run_daily_etl 等はネットワークエラーや品質チェックエラーを捕捉しつつ処理を継続する設計です。戻り値の ETLResult で状態を確認してください。

---

## ディレクトリ構成（主要ファイル・モジュール）

以下は src/kabusys 以下の主な構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント算出（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプラインと run_daily_etl 等
    - jquants_client.py       — J-Quants API クライアント + 保存関数
    - news_collector.py       — RSS 収集と前処理
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - quality.py              — データ品質チェック
    - stats.py                — 汎用統計（zscore_normalize）
    - audit.py                — 監査ログスキーマ初期化
    - etl.py                  — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — ファクター群の計算
    - feature_exploration.py  — 将来リターン、IC、統計サマリー
  - ai/、research/、data/ の中にさらに複数の関数群が存在します（上記は代表的なファイル）。

---

## 注意事項 / 実運用上のポイント

- セキュリティ
  - news_collector は SSRF や XML 攻撃対策（_SSRFBlockRedirectHandler、defusedxml、受信サイズ制限）を実装していますが、運用時はネットワーク権限設定等も確認してください。
- 冪等性
  - J-Quants の保存関数（save_*）や監査スキーマは冪等性（ON CONFLICT）を意識した実装になっています。
- ロギング / モード
  - settings.env によって development / paper_trading / live が選べます。ログレベルは LOG_LEVEL で制御。
- テスト性
  - OpenAI 呼び出しや HTTP 操作はモック可能になるよう関数分離されています（例: _call_openai_api の差し替え、_urlopen のモックなど）。
- バックテストとの分離
  - データ取得時に fetched_at を記録し、ルックアヘッドバイアスを防ぐ設計です。バックテスト用途ではデータのタイムスタンプ管理に注意してください。

---

## 参考（環境変数の例）

.env 例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

ご不明点や特定機能の詳細な使用例（例えば ETL のカスタム引数、OpenAI のバッチチューニング、監査スキーマへのレコード追加方法など）が必要であれば、その用途に合わせたサンプルコードを用意します。