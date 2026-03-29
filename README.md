# KabuSys

日本株自動売買・データ基盤ライブラリ（KabuSys）。  
株価/財務/ニュースの ETL、データ品質チェック、ニュースセンチメント（LLM）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定トレース）などを含むモジュール群です。

---

## 概要

KabuSys は日本株を対象としたデータパイプラインと研究・実運用に使えるユーティリティ群を提供します。主な設計方針は以下の通りです。

- Look-ahead bias の排除（日時を明示的に渡す、内部で date.today() を安易に使わない）
- DuckDB を用いたローカルデータベース管理
- J-Quants API との差分取得（レート制限・リトライ・トークン更新対応）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント／市場レジーム判定（JSON mode）
- ETL／品質チェック／監査ログ（発注→約定トレーサビリティ）の提供
- テストしやすい構造（API 呼び出しを差し替え可能）

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save の一連処理、レートリミット・リトライ実装）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS の安全な取得・正規化・raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ（signal_events / order_requests / executions テーブル・初期化ユーティリティ）
  - 統計ユーティリティ（Zスコア正規化）
- ai
  - ニュース NLP（score_news: ニュースを LLM で集約評価し ai_scores に保存）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロニュースの LLM 評価を合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）

---

## 前提条件

- Python 3.10+
- DuckDB
- OpenAI Python SDK（LLM を使用する機能を利用する場合）
- defusedxml（RSS パーシングの安全化）

推奨インストールパッケージ（例）:
- duckdb
- openai
- defusedxml

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）
4. 開発インストール（任意）
   - pip install -e .
5. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（※自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット）。
   - 主要な環境変数は後述します。

---

## 環境変数（主なもの）

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- kabuステーション API
  - KABU_API_PASSWORD: kabu API のパスワード（必須）
  - KABU_API_BASE_URL: API ベース URL（省略時: http://localhost:18080/kabusapi）
- Slack 通知
  - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DB パス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- システム設定
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合に必要）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下は最小限の利用例です。実行は Python スクリプトや REPL で行えます。

- DuckDB 接続を開く（デフォルトパスを使用）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（市場カレンダー・株価・財務の差分取得・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア付与（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されているか、api_key を渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DuckDB を作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル (signal_events / order_requests / executions) が作成されます
```

- ファクター計算 / 研究ユーティリティ
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns

momentum = calc_momentum(conn, target_date=date(2026,3,20))
forward = calc_forward_returns(conn, target_date=date(2026,3,20))
# zscore_normalize で標準化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

注意:
- AI（OpenAI）呼び出しにはネットワークと API キーが必要です。API エラー時はフェイルセーフの挙動（ゼロスコアにフォールバック等）をする箇所が多くあります。
- 日付は明示的に渡す設計のため、バックテスト時の Look-ahead を避けられます。

---

## 主要 API の挙動メモ（運用上の注意）

- J-Quants クライアントは 120 req/min の制限を順守する RateLimiter を内蔵。ID トークンは自動リフレッシュされる。
- ETL は差分取得 & 冪等保存（ON CONFLICT）を行います。部分失敗があっても他部分は継続する設計です。
- news_nlp / regime_detector の LLM 呼び出しは JSON Mode を用い、レスポンスのバリデーションを行います。API エラーやパース不能時はスコアを 0.0 として継続します。
- calendar_management の関数は market_calendar テーブルが無い場合に曜日ベースのフォールバックを使い、最大探索範囲を設けて無限ループを避けます。
- data.quality のチェックは Fail-Fast せず QualityIssue のリストを返すため、呼び出し元で重大度に応じた対応を行ってください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - etl.py (exports ETLResult)
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: e.g. clients, helpers)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (パッケージは __all__ に含まれる想定 — 実装により異なる)
- strategy/, execution/, monitoring/ (パッケージ公開名として __all__ に含まれますが、該当実装が存在する場合はそちらを参照)

（上記は本コードベースで提供されている主要モジュール群を抜粋したものです）

---

## トラブルシューティング / よくある質問

- .env が読み込まれない
  - 自動読み込みはプロジェクトルートの判定を行います（.git または pyproject.toml を基準）。テストや特殊環境で自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI のレスポンスパースが失敗する
  - モジュール側でパース失敗時は警告ログを出してスコアを 0 として継続します。万が一、LLM の出力が指定フォーマットに沿わない場合はプロンプト設計や model の見直しを検討してください。
- DuckDB の executemany で空リストエラーが出る
  - 一部の DuckDB バージョンでは executemany に空リストを渡せません。モジュールは事前に空チェックを入れているため通常は問題になりませんが、カスタム処理を追加する場合は注意してください。

---

## 開発・貢献

- コードはモジュール単位でテストしやすい構成になっています。外部 API 呼び出し部分（OpenAI / J-Quants / RSS ネットワーク）はテスト内でモック差し替えが可能です。
- 新たな ETL ジョブや品質チェックを追加する際は既存の ETLResult / QualityIssue 構造に準拠すると統合が容易です。

---

必要であれば、README に以下を追加して補完できます：
- requirements.txt の例
- .env.example のテンプレート
- より詳細な CLI 実行例（cron / airflow での運用例）
- テーブルスキーマ（DuckDB 用 DDL）や初期化スクリプトサンプル

要望があれば追記します。