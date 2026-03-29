# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（部分実装）。  
主に以下の機能群を含みます：データ ETL（J-Quants）、データ品質チェック、ニュース収集と NLP（OpenAI）、市場レジーム判定、ファクター計算・研究ユーティリティ、監査ログ（発注～約定のトレーサビリティ）など。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムや研究プラットフォームの基盤コンポーネント群です。設計上のポイントは次のとおりです。

- Look-ahead bias を避ける（関数は明示的な target_date を受け取り、date.today()/datetime.today() を直接参照しない設計が多い）
- DuckDB をデータストアとして利用（ETL／品質チェック／監査ログなど）
- J-Quants API 経由で株価・財務・市場カレンダーを差分取得
- ニュースは RSS から取得し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを評価
- レジーム判定は ETF（1321）の MA とマクロニュースセンチメントを合成
- 監査ログ（signal_events / order_requests / executions）でシグナルから約定までをトレース

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（取得・保存・認証・レートリミット・リトライ）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS 取得・前処理・保存、SSRF 対策、gzip/サイズ制限）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化（監査テーブル作成、インデックス、init 関数）
  - 統計ユーティリティ（Zスコア正規化）
- ai/
  - news_nlp.score_news：銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores に保存
  - regime_detector.score_regime：ETF MA とマクロニュースを合成して market_regime を書き込み
- research/
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索（forward returns, IC, summary）
- config.py
  - .env 自動読み込み（プロジェクトルート基準）、環境変数取得ラッパー（Settings）

---

## 前提 / 必要環境

- Python 3.10 以上（typing の | 記法・型ヒントを使用しているため）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

（プロジェクトに requirements.txt / pyproject.toml がある想定です。なければ上記を個別に pip install してください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# または: pip install -r requirements.txt
```

---

## 環境変数 / .env

プロジェクトは .env / .env.local から自動で環境変数を読み込みます（読み込み順: OS 環境 > .env.local > .env）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須設定（Settings で必須とされる項目）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 系で使用想定）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID

任意 / デフォルトあり:

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト `development`
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト `INFO`
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化するフラグ（1 を設定）
- KABUSYS_OPENAI_API_KEY はないが、OpenAI 呼び出し関数は `OPENAI_API_KEY` 環境変数を参照するため、API キーを `OPENAI_API_KEY` として設定してください
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）

注意: .env.example をプロジェクトに含めている想定のため、これをコピーして値を埋めてください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 依存パッケージをインストール
4. .env を作成して必要な環境変数を設定
5. DuckDB データベースを準備（ファイルは自動作成されることが多い）

例:
```
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt    # または個別インストール
cp .env.example .env
# .env を編集して各種キーをセット
```

---

## 使い方（主な API と実行例）

以下はいくつかの典型的な利用例です。実行は Python スクリプトまたはバッチジョブで行います。

- DuckDB 接続を作る:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は today）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント集計（ai.news_nlp.score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API key を環境変数 OPENAI_API_KEY に設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"written scores: {n_written}")
```

- 市場レジーム判定（ai.regime_detector.score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)  # api_key None => OPENAI_API_KEY を参照
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成される
```

- その他
  - research モジュールのファクター計算（calc_momentum / calc_value / calc_volatility）
  - data.calendar_management の営業日判定（is_trading_day / next_trading_day / prev_trading_day）
  - data.quality.run_all_checks を用いた品質チェック

---

## 注意点 / 設計上の留意事項

- 多くの関数は明示的な target_date を引数に取ることでルックアヘッドバイアスを防止しています。バックテストや日次バッチ実行時は target_date を適切に設定してください。
- OpenAI API 呼び出しでは JSON Mode（response_format）を使用する前提の実装です。API エラーやパースエラーはフェイルセーフ（多くの場合ゼロやスキップで継続）になっています。
- J-Quants クライアントはレート制限・リトライ・トークン自動リフレッシュを備えていますが、実運用では API 使用量に注意してください。
- news_collector では SSRF 対策、レスポンスサイズ制限、gzip 解凍チェックなどセキュリティ対策が入っています。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあります（コード中で防止済み）。DuckDB のバージョン互換性に注意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ初期化・公開モジュール
- config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント集計（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limiter）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）および ETLResult
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 取得・前処理・保存
  - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
  - quality.py — データ品質チェック
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py — ファクター算出（momentum, value, volatility）
  - feature_exploration.py — forward returns, IC, サマリー等
- ai、data、research の他に strategy / execution / monitoring といったモジュール群が想定されます（パッケージ __all__ に含まれる名前など参照）。

---

## 追加情報 / 開発時のヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。テスト時など自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し箇所は内部で再試行ロジックを持ちます。ユニットテストでは _call_openai_api をモックして戻り値を固定できます（news_nlp._call_openai_api や regime_detector._call_openai_api を patch）。
- DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を関数に渡す設計です。接続のライフサイクル（ファイルの場所、トランザクション管理）を呼び出し元で制御してください。
- ETL の品質チェックは Fail-Fast になっていません。結果（ETLResult）を見て、致命的なissueがあれば運用側でアラート/停止を実施してください。

---

これで README の基本的な要素は網羅しています。必要であれば、実行スクリプト例（systemd タイマー / cron ジョブ / Dockerfile）、より詳細な .env.example、サンプルデータでの動作確認手順、各テーブルのスキーマ（DDL）抜粋などを追加できます。どの情報を優先して追加しましょうか？