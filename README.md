# KabuSys

日本株向け自動売買・データプラットフォーム（KabuSys）の簡易 README。  
このリポジトリはデータ収集（J-Quants）、品質チェック、特徴量算出、AI によるニュースセンチメント評価、
市場レジーム判定、監査ログ管理などを含むコンポーネント群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。主な目的は次の通りです。

- J-Quants API からのデータ ETL（株価日足、財務、マーケットカレンダー）
- RSS ベースのニュース収集と NL 評価（OpenAI を用いたセンチメント）
- AI による市場レジーム判定（ETF の MA とマクロニュースを統合）
- ファクター算出・研究用ユーティリティ（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル〜約定のトレーサビリティ）用スキーマ初期化・管理
- DuckDB を中心としたローカル DB 操作ユーティリティ

設計上の特徴:
- ルックアヘッドバイアスに配慮（date.today()/datetime.today() を不用意に使わない）
- DuckDB + SQL を活用した効率的データ処理
- 冪等な保存（ON CONFLICT / INSERT/UPDATE）
- OpenAI 呼び出しに対するリトライ / フェイルセーフ実装
- SSRF / XML Bomb 等に配慮した安全なニュース収集

---

## 機能一覧（抜粋）

- 環境設定読み込み: 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可）
- data:
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（取得・保存関数）
  - market calendar 管理・営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - データ品質チェック（missing_data / spike / duplicates / date_consistency）
  - audit（監査ログ）スキーマ初期化（init_audit_schema / init_audit_db）
  - news_collector: RSS 収集・正規化・保存支援
  - stats: zscore_normalize
- ai:
  - news_nlp.score_news: ニュースを銘柄別に集約して OpenAI でセンチメント評価、ai_scores に書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースで市場レジームを判定・market_regime に書き込み
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要要件（想定）

最低限の Python 環境（3.9+ 推奨）と以下のライブラリが必要です（コード中で使用）:

- duckdb
- openai
- defusedxml

実際のプロジェクトでは requirements.txt / pyproject.toml に依存関係を定義して使用してください。

---

## 環境変数

主に次の環境変数を期待します（必須／任意は下記参照）。

必須（Settings._require を通して参照されるもの）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API パスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

OpenAI:
- OPENAI_API_KEY : OpenAI クライアント（ai.score_news / regime で使用）

オプション:
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると自動 .env ロードを無効化

自動 .env ロード:
- パッケージ内 config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から `.env`、`.env.local` を順に読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` の値を上書きします。
- テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: 簡単な .env（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存ライブラリをインストール（requirements.txt がある前提）
   ```
   pip install -r requirements.txt
   ```
   直接インストールする場合の例:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定（上記 `.env` を参照）。プロジェクトルートに `.env` を置くと自動で読み込まれます。

5. （任意）開発インストール
   ```
   pip install -e .
   ```

---

## 使い方（代表的な例）

下記は簡単な Python スニペットです。すべて kabusys パッケージをインポートして使用できます。

- DuckDB 接続の作成例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行（run_daily_etl）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は duckdb 接続
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI API key 必須）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- ファクター計算（例: モメンタム）:
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は dict のリスト (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)
```

- 監査 DB 初期化（監査専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンに設定されます
```

- カレンダー関連ユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- AI 系（score_news／score_regime）は OPENAI_API_KEY か api_key 引数が必要です。
- J-Quants 取得関数は JQUANTS_REFRESH_TOKEN を settings から読み出します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                    — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                 — ニュース NLU / スコアリング
  - regime_detector.py          — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py           — J-Quants API クライアント + 保存関数
  - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
  - etl.py                      — ETL 公開インターフェース
  - calendar_management.py      — マーケットカレンダー管理
  - news_collector.py           — RSS ニュース収集
  - quality.py                  — データ品質チェック
  - stats.py                    — 統計ユーティリティ（zscore 正規化）
  - audit.py                    — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py          — モメンタム / バリュー / ボラティリティ等
  - feature_exploration.py      — 将来リターン / IC / 統計サマリー
- monitoring/ (想定)             — 監視・通知用ロジック（README の記述はコードに依存）
- その他モジュール...

上記は主要ファイルのみ抜粋しています。実装ファイルには各機能の詳細ドキュメント（docstring）が含まれています。

---

## 開発・テスト時の注意

- 自動 .env ロードを無効化する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出し箇所はユニットテストでモックできるよう設計されています（内部関数の差し替え等）。
- DuckDB executemany の空リストは一部バージョンでエラーになるため、実装側で空リスト処理を行っています。

---

## 貢献 / ライセンス

この README はコードベースの要点をまとめたものです。実装/設計ドキュメント（DataPlatform.md / StrategyModel.md 等）がプロジェクトに存在する想定です。貢献・ライセンス情報はリポジトリのトップレベルにある LICENSE / CONTRIBUTING を参照してください。

---

もし特定の使い方（例: ETL を cron で回す方法、Slack 通知の実装例、バックテスト連携例）や、README の英語版・詳細な API リファレンスが必要であれば教えてください。必要に応じてサンプルコードや .env.example のテンプレートも作成します。