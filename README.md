# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

## 概要

KabuSys は以下の目的を持つ Python パッケージです。

- J-Quants API からの株価・財務・市場カレンダーの差分 ETL（DuckDB に保存）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析（銘柄ごとの ai_score）
- マクロ＋テクニカル指標を組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）と初期化ユーティリティ

設計上の特徴：
- DuckDB を中心としたローカルデータベース運用
- Look-ahead バイアス対策（日時の扱い、DB クエリ条件等）
- 冪等保存（ON CONFLICT / INSERT ... DO UPDATE）とトランザクション管理
- API 呼び出しに対するリトライ / レート制御 / フェイルセーフ

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数読み込み（.env / .env.local 自動ロード）、設定アクセス（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants からの取得・DuckDB への保存ユーティリティ
  - pipeline: 日次 ETL 実行（run_daily_etl など）と ETLResult
  - news_collector: RSS 収集・前処理・raw_news 保存
  - quality: データ品質チェック（missing / spike / duplicates / date consistency）
  - calendar_management: JPX カレンダー管理・営業日のユーティリティ
  - audit: 監査ログ（signal_events / order_requests / executions）のスキーマ初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM に送信して銘柄別スコアを ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）MA200 乖離とマクロ記事センチメントを合成して market_regime に書き込む
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提：
- Python 3.10 以上（`X | Y` 型注釈などを使用）
- DuckDB, openai, defusedxml 等が必要

例（仮想環境と最低限の依存インストール）:

```bash
git clone <repo-url>
cd <repo-root>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 必要に応じて他の依存を追加（例: requests 等）
# 開発用にパッケージとしてインストールする場合
pip install -e .
```

環境変数（例）。少なくとも以下を設定してください（.env または OS 環境）:

- JQUANTS_REFRESH_TOKEN    # J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY           # OpenAI API キー（score_news / score_regime で利用）
- KABU_API_PASSWORD        # kabuステーション API パスワード（必要時）
- SLACK_BOT_TOKEN          # Slack 通知を使う場合
- SLACK_CHANNEL_ID         # Slack 通知先チャンネル
- DUCKDB_PATH              # デフォルト: data/kabusys.duckdb
- SQLITE_PATH              # 監視用 SQLite（default: data/monitoring.db）
- KABUSYS_ENV              # development | paper_trading | live (default: development)
- LOG_LEVEL                # DEBUG|INFO|... (default: INFO)

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し、.env を自動で読み込みます。
- 読み込み順: OS 環境 > .env.local > .env
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 .env（参考）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な例）

まず settings を使って DB パスや設定を参照できます。

```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニューススコア（ai_scores に書き込む）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを環境変数 OPENAI_API_KEY に設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

市場レジーム判定（market_regime に書き込む）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログ用 DB を初期化（監査スキーマを作成）:

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" でインメモリ可
```

研究用ファクター計算（例: Momentum）:

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ... }, ...]
```

データ品質チェック（全チェック）:

```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None, reference_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

その他：
- jquants_client.get_id_token() / fetch_daily_quotes() / save_daily_quotes() 等を直接利用可能です。
- OpenAI 呼び出しをテストで差し替える際はモジュール内の `_call_openai_api` をモックする設計になっています。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイル構成（抜粋）です：

- src/
  - kabusys/
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
      - calendar_management.py
      - stats.py
      - audit.py
      - audit (関数群)
      - ...
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (コードベースに監視関連モジュールがある想定)
    - strategy/ (戦略・シグナル生成は別ディレクトリ)
    - execution/ (ブローカーインテグレーション)
    - monitoring/ (ログ・メトリクス)

（上記は本リポジトリに含まれるファイル群の主要部分を抜粋したものです。）

---

## 実運用上の注意

- API キーやトークンは厳重に管理してください（.env をバージョン管理に入れないでください）。
- OpenAI の利用はコストが発生します。news_nlp / regime_detector はバッチ単位・チャンク処理を行いますが、運用前に想定コストを確認してください。
- ETL 実行や LLM 呼び出しでは外部 API の障害に対してフェイルセーフ（スコア 0.0 へフォールバック、処理継続）を実装していますが、監査やアラートは別途用意してください（Slack 通知等）。
- DuckDB ファイルはローカルファイルシステムに保存されます。バックアップやアクセス制御を検討してください。

---

## 開発・テスト

- 型注釈や Python 3.10+ 構文を使用しています。ローカル開発環境は Python 3.10 以上を推奨します。
- テストを行う際は、外部 API 呼び出し（OpenAI / J-Quants / RSS）をモックしてください。多くの内部関数がモックしやすいように設計されています（例: _call_openai_api, _urlopen, _get_cached_token 等）。

---

ご不明点や README の改善希望（例: 具体的なコマンド例、追加の使用例、サンプル .env.example の自動生成など）があればお知らせください。