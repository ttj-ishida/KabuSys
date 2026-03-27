# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群。  
J-Quants / RSS / OpenAI（LLM）を利用したデータ取得・ETL、ニュースセンチメント評価、ファクター計算、監査ログ（オーディット）等を含むモジュール群です。

- パッケージ名: kabusys
- バージョン: 0.1.0 (src/kabusys/__init__.py)

---

## 概要

KabuSys は以下の用途に向けたユーティリティを提供します。

- J-Quants API と連携した株価・財務・カレンダーの差分 ETL（DuckDB 保存）
- RSS ベースのニュース収集と前処理、ニュース → 銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント算出（銘柄別 / マクロ）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの組合せ）
- ファクター計算（Momentum / Value / Volatility 等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレース）のスキーマ初期化機能

設計方針として「ルックアヘッドバイアス回避」「冪等性」「フォールトトレランス」「外部依存の最小化（研究系は標準 lib のみ）」が取られています。

---

## 機能一覧

主な機能（モジュール単位）

- kabusys.config
  - .env / 環境変数の自動ロード（プロジェクトルート検出）
  - settings オブジェクト（J-Quants トークン、OpenAI、DB パスなど）
- kabusys.data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: fetch / save 関数（rate limit, retry, id_token 管理）
  - news_collector: RSS 取得・前処理・ID 正規化・SSRF 対策
  - calendar_management: 営業日ロジック（is_trading_day / next_trading_day 等）
  - quality: 品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - audit: 監査ログ用 DDL / 初期化（init_audit_db / init_audit_schema）
  - stats: zscore_normalize
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとニュースセンチメント算出・ai_scores への書き込み
  - regime_detector.score_regime: マクロ + MA200 による市場レジーム判定・market_regime への書き込み
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件（依存パッケージ）

最低限必要な主要ライブラリ（バージョンは適宜）:

- Python 3.9+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

その他、標準ライブラリを広く使用。実行環境や CI 用に requirements.txt / pyproject.toml を利用してください。

---

## セットアップ手順

1. リポジトリをクローン・配置
   - 例: git clone ...

2. 仮想環境作成とパッケージインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - pip install -e .   （パッケージを開発モードでインストールする場合）

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml が見つかる場所）に `.env` と `.env.local` を置けます。
   - 自動ロードはデフォルトで有効。テスト等で無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（settings 参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL に必須）
- SLACK_BOT_TOKEN — Slack 通知に使用する場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル
- KABU_API_PASSWORD — kabuステーション API パスワード（注文連携がある場合）

任意／デフォルト:
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（クイックスタート）

以下は Python REPL やスクリプトから呼ぶ最小例です。実行前に環境変数 / .env を正しく設定してください。

1) DuckDB 接続を作成する
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する（市場カレンダー・株価・財務を差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（銘柄別）を算出して ai_scores テーブルへ書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

4) 市場レジームを評価して market_regime テーブルへ書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```
- OpenAI API キーは引数 `api_key` に渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- API 呼び出しやパース失敗はフェイルセーフ（0.0 フォールバック）で処理を継続します。

5) 監査ログ用 DB / スキーマ初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
```

6) カレンダー更新ジョブ（J-Quants から市場カレンダーを取得して保存）
```python
from kabusys.data.calendar_management import calendar_update_job
from datetime import date

saved = calendar_update_job(conn, lookahead_days=90)
print("calendar saved:", saved)
```

---

## 開発者向け情報

- 環境ファイルの自動ロード:
  - 優先度: OS 環境変数 > .env.local > .env
  - 自動ロードはパッケージインポート時に行われます。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - .env のパースはシェル風の export/クォート/コメントを考慮します。

- ログレベル:
  - `LOG_LEVEL` によってログの閾値を設定できます（DEBUG/INFO/...）。
  - `KABUSYS_ENV`: development / paper_trading / live の 3 種をサポートします。無効な値は例外になります。

- OpenAI 呼び出し:
  - news_nlp と regime_detector はいずれも OpenAI Chat Completions（JSON Mode）を使用します。モデルは `gpt-4o-mini` を前提としています。
  - レート制限・リトライ・パース失敗は内部でハンドリングしますが API キーを必ず設定してください（引数または環境変数 OPENAI_API_KEY）。

- J-Quants クライアント:
  - rate limit（120 req/min）を守るための固定間隔スロットリングを実装しています。
  - 401 を受けた場合はリフレッシュトークンを使って id_token を自動更新します。
  - save_* 関数は DuckDB に対して冪等（ON CONFLICT DO UPDATE）で保存します。

- 単体テスト:
  - OpenAI / ネットワーク依存箇所は関数差し替えや patch がしやすく実装されています（例: `_call_openai_api` の差し替えなど）。

---

## 主要ディレクトリ構成

（リポジトリの src/kabusys を起点に抜粋）

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
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - (その他補助モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（補助ユーティリティ等）

各モジュールは責務が分離されており、ETL / データ収集 / AI / 研究ロジック / 監査 が独立して利用できます。

---

## 注意事項・運用上のポイント

- セキュリティ:
  - API キー・トークンは `.env` や環境変数で安全に管理してください。リポジトリにコミットしないでください。
  - news_collector は SSRF・XML Bomb 等を考慮した実装になっていますが、運用時も入力 URL の管理に注意してください。

- ルックアヘッドバイアス回避:
  - 多くの関数は date や target_date を明示的に受け取り、内部で datetime.today() を参照しない設計です。バックテスト用途にも配慮されています。

- DuckDB との互換性:
  - 一部の executemany / 型バインドの扱いで DuckDB のバージョン差異に注意しています（コメント参照）。

---

この README はコードベースの公開仕様を簡潔にまとめたものです。詳細な API ドキュメントや設計資料（DataPlatform.md / StrategyModel.md 等）があれば併せて参照してください。必要であればサンプルワークフロー（ETL cron / Slack 通知連携 / バックテスト利用例）も作成します。