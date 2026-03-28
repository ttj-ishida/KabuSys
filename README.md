# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
J-Quants / kabuステーション / Slack / OpenAI を組み合わせ、データETL、ニュースNLP、ファクター計算、監査ログ、マーケットカレンダー管理などを提供します。

---

目次
- プロジェクト概要
- 主な機能
- 動作要件
- セットアップ手順
- 環境変数 / .env
- 使い方（簡易サンプル）
  - ETL（日次パイプライン）
  - ニュース NLP（銘柄センチメント）
  - 市場レジーム判定
  - 監査DB初期化
- ディレクトリ構成
- よくあるトラブルシューティング

---

## プロジェクト概要

KabuSys は、日本株に特化したデータパイプラインとリサーチ / 自動売買補助のためのライブラリ群です。  
主に以下の役割を持ちます。

- J-Quants API を使った株価・財務・上場情報・マーケットカレンダーの差分取得（ETL）
- raw_news の収集とニュースの前処理・NLP（OpenAI を利用したセンチメント評価）
- ファクター（モメンタム / バリュー / ボラティリティ等）の計算と正規化ユーティリティ
- マーケットカレンダーの管理（営業日判定 / next/prev）
- 監査ログ（シグナル→発注→約定）テーブルの初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、ルックアヘッドバイアスを避けるために date.today()/datetime.today() を不注意に参照しない実装方針が採られています。

---

## 主な機能

- ETL / run_daily_etl: 市場カレンダー、株価日足、財務データを差分更新して DuckDB に保存
- jquants_client: J-Quants API への安全なリクエスト（レート制御・リトライ・トークンリフレッシュ）
- news_collector: RSS からのニュース収集（SSRF対策、トラッキング除去、冪等保存）
- news_nlp: OpenAI を用いた銘柄別ニュースセンチメント（バッチ処理・検証ロジック）
- regime_detector: ETF(1321) の MA200 乖離 と マクロニュースセンチメントを合成して市場レジーム判定
- research.*: ファクター計算（momentum / value / volatility）や特徴量探索ユーティリティ
- data.quality: 品質チェック（欠損・スパイク・重複・日付不整合）
- data.audit: 監査ログテーブルの作成・初期化（冪等、UTC タイムスタンプ）

---

## 動作要件

- Python 3.10 以上（PEP 604 の型記法や最新の型ヒントを利用）
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API, OpenAI API, RSS フィード
- DuckDB ファイル（デフォルト: data/kabusys.duckdb）

※ 実際の環境では requirements.txt を用意して pip install -r で管理してください。ここでは主要依存のみ示しています。

---

## セットアップ手順

1. リポジトリをクローン（例）
   - git clone <リポジトリURL>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. インストール（開発モード推奨）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - pip install -e .  （プロジェクトがパッケージ化されている場合）
4. データ格納ディレクトリ作成（必要に応じて）
   - mkdir -p data
5. 環境変数を設定（下記参照）

---

## 環境変数 / .env

パッケージの起動時にプロジェクトルート（.git または pyproject.toml 所在）を起点に自動で `.env` / `.env.local` を読み込みます（OS 環境 > .env.local > .env の優先順）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（Settings により参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（売買連携時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI 呼び出しに必要（news_nlp / regime_detector）

オプション:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値は任意）

サンプル .env（README 用例、実運用では秘密を漏らさないこと）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡易サンプル）

以下は簡単な Python REPL / スクリプト例です。実行前に環境変数を設定してください。

共通準備:
```python
import duckdb
from kabusys.config import settings

# DuckDB に接続（デフォルトパスを使用）
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL 実行（市場カレンダー→株価→財務→品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

2) ニュース NLP（ある日付の銘柄別センチメントを ai_scores に書き込む）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# 日付は ETL と同様にバックテストバイアスを避けるため外部から与える
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込み銘柄数: {written}")
```

3) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれます
```

4) 監査DB（監査テーブル）初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査用 DB を別ファイルで用意することを推奨
audit_conn = init_audit_db(settings.duckdb_path)
# または init_audit_db("data/audit.duckdb")
```

5) リサーチ／ファクター計算の例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

t = date(2026, 3, 20)
mom = calc_momentum(conn, t)
val = calc_value(conn, t)
vol = calc_volatility(conn, t)
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

注: OpenAI 呼び出しを行う関数（score_news, score_regime）は API キーが必要です。api_key 引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。未設定の場合 ValueError が発生します。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ公開
  - config.py — 環境変数 / .env 読込と Settings オブジェクト
  - ai/
    - news_nlp.py — ニュースのセンチメントスコアリング（OpenAI）
    - regime_detector.py — マクロセンチメント + MA200 を合成した市場レジーム判定
  - data/
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETL の公開インターフェース（ETLResult の再エクスポート）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py — RSS 収集（SSRF 対策・トラッキング除去・保存）
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック
    - audit.py — 監査ログテーブル定義・初期化ユーティリティ
  - research/
    - factor_research.py — モメンタム / バリュー / ボラティリティ等の計算
    - feature_exploration.py — 将来リターン, IC, statistics（rank, factor_summary 等）
  - monitoring/ (監視・アラート関連モジュールがここに入る想定)
  - execution/, strategy/ など（自動売買関連の実装想定）

（上記はリポジトリに含まれる主要モジュールの一覧と役割説明です）

---

## よくあるトラブルシューティング

- ValueError: 環境変数が設定されていません
  - settings が必須環境変数（例: JQUANTS_REFRESH_TOKEN）を参照するときに発生します。`.env` に設定するか OS 環境変数で設定してください。
- OpenAI 関連の呼び出し失敗
  - API キーが無い、または通信エラーが起きています。OPENAI_API_KEY を設定し、ネットワーク経路・プロキシ設定を確認してください。
  - rate limit / 5xx はライブラリ内でリトライしますが、最大リトライで失敗した場合は関数が 0 を返す／警告を出します（例: マクロセンチメントは 0 にフォールバック）。
- J-Quants API エラー（401）
  - jquants_client は 401 受信時にリフレッシュトークンで ID トークンを再取得して自動リトライします。リフレッシュトークン JQUANTS_REFRESH_TOKEN を確認してください。
- DuckDB 関連
  - executemany に空リストを渡すとバージョン依存でエラーになるため、空チェックを行ってください（内部コードは既に対応しています）。
- RSS 取得で SSRF/プライベートアドレス拒否
  - news_collector は安全性のためプライベートアドレスや非 http(s) を拒否します。社内の RSS を使う場合は監査の上で許可設定を検討してください。

---

必要に応じて README に追記します。たとえば CI/infrastructure、開発用テストの実行方法、具体的な .env.example ファイル、requirements.txt の内容などを提供できます。どの情報を優先して追加しますか？