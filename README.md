# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュースNLP、市場レジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）、J-Quants クライアントなどを含みます。

現状はライブラリのコア機能を提供する実装が含まれており、実運用環境では外部サービス（J-Quants、OpenAI、kabu API、Slack 等）の設定が必要です。

---

## 主要機能

- データ取得・ETL
  - J-Quants API クライアント（株価日足 / 財務 / 上場情報 / 市場カレンダー）
  - 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - 市場カレンダー管理・営業日判定ユーティリティ
- ニュース収集 / NLP
  - RSS 取得と raw_news テーブルへの保存（SSRF 対策・正規化）
  - OpenAI を用いたニュースセンチメントスコアリング（銘柄別 ai_scores 生成）
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュース LLM スコアの合成による日次レジーム判定
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査（Audit）
  - signal -> order_request -> executions のトレーサビリティを担保する監査スキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型アノテーション・Union 短縮表記等を使用）
- 外部依存（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants, OpenAI, RSS 等）

パッケージは任意のパッケージ管理（pip / Poetry 等）でインストールしてください。

例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# ローカル開発ならパッケージルートで
pip install -e .
```

---

## 環境変数（.env）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動読み込みは、パッケージ内の config モジュールがプロジェクトルート（.git または pyproject.toml を探索）を検出した場合に有効になります。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

主に必要な環境変数例（.env）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxx

# OpenAI (news/regime の呼び出しで使用)
OPENAI_API_KEY=sk-...

# kabu ステーション（発注等）
KABU_API_PASSWORD=your_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（デフォルトは data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

`.env.local` は `.env` より優先して読み込まれます（OS 環境変数がさらに優先）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / パッケージを入手
2. 仮想環境の作成・有効化
3. 必要パッケージをインストール（duckdb, openai, defusedxml など）
4. プロジェクトルートに `.env`（または `.env.local`）を作成して必要な環境変数を設定
5. DuckDB 用のディレクトリを作成（例: data/）
6. 初期スキーマ（監査スキーマ等）の初期化（下記参照）

---

## 使い方（例）

以下は Python REPL やスクリプトでの利用例です。すべての呼び出しは Look-ahead bias（未来データ参照）を避ける実装方針になっています。target_date は明示的に渡すことを推奨します。

- DuckDB 接続を用意:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する（J-Quants トークンは settings.jquants_refresh_token から読み込み）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成（ai_scores へ書き込み）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
```

- 市場レジーム判定（market_regime テーブルへ書き込み）:
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
```

- 監査ログ用 DB を初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または既存接続にスキーマ追加:
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn, transactional=True)
```

- 研究用ファクター計算:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

- データ品質チェック:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意:
- OpenAI 呼び出しを伴う機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を環境変数または関数引数で指定する必要があります。
- J-Quants API 呼び出しではリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必要です。

---

## よく使うエントリ・関数一覧

- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL（カレンダー・株価・財務・品質チェック）
- kabusys.data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl — 個別 ETL ジョブ
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar — J-Quants からの直接取得
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) — ニュース NLP スコアリング
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査スキーマ初期化
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days — 営業日ユーティリティ

---

## ディレクトリ構成（主なファイル）

（ルートが `src/kabusys` となる想定。パッケージ配下の主なモジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込み・設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py — マクロ + ETF MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集・前処理・保存
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/__init__.py, research/__init__.py などで公開 API をまとめています

---

## 注意事項 / 運用上のポイント

- API キー・トークンの取り扱いは慎重に行ってください。コードや公開リポジトリに直接コミットしないでください。
- OpenAI 呼び出しで JSON モードを使う想定の実装がありますが、LLM の応答は不安定になりうるため堅牢なパース・バリデーションが行われています。テスト時はモックを推奨します。
- J-Quants API はレート制限（120 req/min）や 401 リフレッシュなどに対応する実装になっています。運用時は ID トークンや呼び出し間隔に注意してください。
- DuckDB の executemany に関する互換性（空リスト不可など）に配慮した実装があります。DuckDB バージョンに依存する挙動があるため、実行環境のバージョン管理を行ってください。
- 自動環境変数読み込みはプロジェクトルート検出（.git or pyproject.toml）に依存します。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか、明示的に環境変数を設定してください。

---

## テスト・開発

- OpenAI 呼び出し等外部依存はモック化してユニットテストを作成することを推奨します。モジュール内の `_call_openai_api` のような関数はテスト時に差し替え可能に設計されています（unittest.mock.patch 等）。
- ニュース収集では network / XML 攻撃対策（defusedxml・受信サイズ制限・SSRF ブロック）を実装しています。テスト環境では実際の RSS にアクセスせず、ローカルフィードやモックを利用してください。

---

もし README に追加したい運用手順（CI/CD の流れ、具体的な DB スキーマ、Slack 通知の使い方、kabu 発注フロー例など）があれば教えてください。必要に応じてサンプルスクリプトや .env.example の雛形も作成します。