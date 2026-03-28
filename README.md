# KabuSys

日本株向け自動売買・データプラットフォーム用のライブラリ群（プロトタイプ）。  
データ取得（J-Quants）、ETL、ニュースNLP、マーケットレジーム判定、調査用ファクター計算、監査ログ（監査用DuckDBスキーマ）などを提供します。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ Python パッケージです。

- J-Quants API を用いた株価・財務・市場カレンダーの差分取得（レート制御・リトライ・ページネーション対応）
- DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策 / トラッキングパラメータ削除）
- OpenAI を利用したニュースセンチメント（銘柄別）とマクロセンチメントの評価
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントの線形合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー）と特徴量探索ユーティリティ
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）を DuckDB に初期化

設計上のポイント：
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() を不用意に参照しない実装（関数に target_date を明示的に渡す）
- フェイルセーフ設計：外部API失敗時も全体処理を止めずにフォールバックやスキップで継続する箇所が多い

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント + DuckDB に保存するユーティリティ
  - pipeline: 日次 ETL (run_daily_etl) と個別 ETL ジョブ（価格 / 財務 / カレンダー）
  - news_collector: RSS 取得と前処理、raw_news への保存補助
  - quality: データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
  - calendar_management: 市場カレンダーの管理・営業日判定
  - audit: 監査ログスキーマの初期化・監査DBユーティリティ
  - stats: z-score 正規化等の統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを計算して ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) MA200 とマクロセンチメントを合成して market_regime を生成
- research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 環境変数（必須/推奨）

以下の環境変数を設定してください（.env を利用可）。自動ロード機能があり、プロジェクトルートにある `.env` / `.env.local` を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須（Settings._require を通るもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（API 実行モジュールを使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャネルID

OpenAI（AI 機能を使う場合）:
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / ai.regime_detector はこのキーを使用可能）

任意（デフォルトあり）:
- KABUSYS_ENV — 環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
```

---

## セットアップ手順

1. Python 環境を準備（推奨: 3.10+）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - openai
     - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意して pip install -r requirements.txt や pip install -e . を行ってください。

4. 環境変数設定（上記参照）：`.env` をプロジェクトルートに作成するか OS 環境変数に設定
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（代表的な呼び出し例）

以下は Python スクリプトや REPL からの呼び出し例です。すべての関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

1) DuckDB 接続の作成（デフォルトパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（市場カレンダー・株価・財務を差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントを計算して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定しておく（または api_key パラメータで渡す）
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

4) 市場レジーム判定（market_regime テーブルへ書込）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ用 DuckDB の初期化（audit スキーマ作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

6) 研究用ファクター計算の利用例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date":..., "code":..., "mom_1m":..., "ma200_dev":...}, ...]
```

---

## よくある注意点

- OpenAI 呼び出し
  - news_nlp / regime_detector は gpt-4o-mini を想定した JSON Mode を利用しています。API レスポンスが想定外の場合はスコアをスキップしてフォールバックする実装になっています。
  - API キーは関数引数で上書き可能（テストや複数キー運用に便利）。

- J-Quants API
  - rate limit を守るため内部に RateLimiter を実装しています（120 req / min）。
  - 401 が返るとリフレッシュトークンから id_token を取得して再試行します。`JQUANTS_REFRESH_TOKEN` を必ず設定してください。

- ルックアヘッドバイアスへの配慮
  - 多くの関数は target_date を引数に取り、内部で未来データを参照しないように設計されています。バックテストや日次処理では必ず適切な target_date を渡してください。

- 自動環境読み込み
  - パッケージインポート時にプロジェクトルートの .env / .env.local を自動で読み込みます（必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（主要モジュールのみ）の抜粋です（package: src/kabusys）：

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP（score_news）
    - regime_detector.py          — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - etl.py                      — ETLResult のエクスポート
    - news_collector.py           — RSS 収集・前処理
    - quality.py                  — データ品質チェック
    - calendar_management.py      — 市場カレンダー管理（営業日判定等）
    - stats.py                    — zscore_normalize 等
    - audit.py                    — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py          — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py      — calc_forward_returns / calc_ic / factor_summary / rank
  - research/__init__.py

（上のファイル群以外に strategy / execution / monitoring 等のサブパッケージが存在する想定ですが、本リポジトリ内では data / ai / research が主要な提供モジュールです。）

---

## テスト・開発ヒント

- ai モジュールの OpenAI 呼び出しは内部関数をモック可能に設計されています。ユニットテストでは `_call_openai_api` を patch して deterministic なレスポンスを返すことでテストできます。
- news_collector のネットワーク呼び出しは `_urlopen` をモックしてローカルの固定レスポンスを返すとテストしやすいです。
- DuckDB を ":memory:" で接続すればインメモリ DB を使って高速にテストできます（init_audit_db は ":memory:" を受け付けます）。

---

## ライセンス・貢献

本 README はコードベースの説明を目的として作成しています。実運用での注文送信・実口座との接続は慎重に行ってください。貢献や改善提案は Pull Request / Issue を通じてお願いします。

---

必要があれば README にサンプル .env.example、requirements.txt、CI 用テストコマンドなどを追加します。どの情報を優先して追加しますか？