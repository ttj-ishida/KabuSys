# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群。  
J-Quants からのデータ取得・ETL、ニュース収集・LLM ベースのニュースセンチメント、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（オーダー／約定トレーサビリティ）などを提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（設定）
- 使い方（最もよく使うエントリポイント例）
- ディレクトリ構成（主要ファイルの説明）
- 設計上の注意・運用ノート

---

## プロジェクト概要
KabuSys は日本株向けの研究・自動売買システムのコアライブラリです。J-Quants API からの差分 ETL、DuckDB を利用したデータ保存、RSS からのニュース収集、OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価と市場レジーム判定、ファクター計算・解析、監査ログ（signal → order_request → executions のトレーサビリティ）のためのスキーマ初期化などを備えています。

設計方針の要点：
- Look-ahead bias を避ける（target_date を明示する／現在時刻を安易に参照しない）
- DuckDB によるローカル永続化（ETL は冪等に実行）
- 外部 API 呼び出しはリトライ／バックオフ・レート制御を実装
- 部分失敗でも他のデータを保護する（部分置換など）

---

## 機能一覧
- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、上場情報、JPX カレンダーを差分取得（pagination 対応）
  - run_daily_etl による日次 ETL（calendar → prices → financials → 品質チェック）
  - ETL 結果を ETLResult オブジェクトで取得
- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付不整合チェック
- ニュース収集
  - RSS フィード取得、URL 正規化、SSRF 防止、前処理、raw_news への保存（冪等）
- ニュース NLP（LLM）
  - 銘柄ごとにニュースをまとめて gpt-4o-mini に送信し ai_scores を作成（score_news）
  - レート制限 / リトライ / 応答バリデーションを実装
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離とマクロニュース（LLM）を重み合成して日次レジーム判定（score_regime）
- リサーチ用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility / Liquidity）
  - 将来リターン計算、IC（Spearman）計算、z-score 正規化、統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions 用スキーマ定義および初期化（init_audit_db / init_audit_schema）
- 設定管理
  - .env および環境変数から設定読み込み（自動読み込みあり。プロジェクトルートは .git または pyproject.toml を基準に探索）

---

## セットアップ手順

前提
- Python 3.10 以上（型記法に `|` を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール（例）
   - 必須の代表的な依存：duckdb, openai, defusedxml
   - 開発時は必要に応じて追加パッケージがあるかもしれません。

   例：
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトの requirements.txt / pyproject を使用
   ```

4. パッケージをローカルにインストール（開発モード）
   ```
   pip install -e .
   ```

5. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml がある場所）から `.env` と `.env.local` を自動読み込みします（既定）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数（主なもの）
設定は `kabusys.config.settings` 経由で取得されます。主に以下を設定してください。

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に必要）

例 .env（簡易）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースはシンプルなシェル互換処理を行い、クォートやコメントに対応します。

---

## 使い方（代表的なコード例）

以下は Python REPL あるいはスクリプトから利用する際の例です。各例は `kabusys` パッケージがインストール済みであることを前提とします。

- DuckDB 接続を作成して ETL を実行する（例: 日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（AI）を実行して ai_scores に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を .env で指定していれば None でOK
print("scored:", n_written)
```

- 市場レジームスコアを計算して market_regime テーブルに保存する
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # parent ディレクトリがなければ自動作成
```

- ファクター計算（研究用）
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# 返り値は dict のリスト: [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

注意:
- OpenAI 呼び出しには api_key を直接渡すか、環境変数 OPENAI_API_KEY を使用してください。未設定だと ValueError が発生します。
- 多くの処理は target_date を明示することで look-ahead bias を防いでいます。バックテストで使用する際は十分に注意してください。

---

## ディレクトリ構成（主要ファイル）
（パッケージルート: src/kabusys）

- __init__.py
  - パッケージのバージョンと公開モジュールリスト

- config.py
  - 環境変数 / .env の自動ロードと settings オブジェクト

- ai/
  - news_nlp.py: ニュースの LLM センチメント評価（score_news）
  - regime_detector.py: ETF（1321）MA + マクロニュースで日次レジーム判定（score_regime）
  - __init__.py: ai の公開 API（score_news を再エクスポート）

- data/
  - pipeline.py: ETL のメイン処理（run_daily_etl, run_prices_etl, ...）と ETLResult
  - jquants_client.py: J-Quants API クライアント（fetch_*, save_*）
  - news_collector.py: RSS 取得 / 前処理 / raw_news への保存（SSRF / Gzip / トラッキング除去対策あり）
  - quality.py: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - calendar_management.py: JPX カレンダー管理と営業日ユーティリティ（is_trading_day, next_trading_day 等）
  - stats.py: z-score 正規化等の統計ユーティリティ
  - etl.py: ETLResult の再エクスポート
  - audit.py: 監査ログテーブル定義・初期化（init_audit_schema / init_audit_db）

- research/
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー、rank 等
  - __init__.py: 便利関数の再エクスポート

---

## 設計上の注意・運用ノート
- Look-ahead bias 防止:
  - 多くの API は target_date を受け取り、内部で datetime.now()/date.today() を直接参照しない設計です。バックテスト・研究用途では target_date を明示して利用してください。
- 冪等性:
  - J-Quants データの保存は ON CONFLICT DO UPDATE によって上書きされ、安全に再実行できます。
- リトライ / レート制御:
  - J-Quants クライアントは 120 req/min の制限を守る RateLimiter を実装。OpenAI 呼び出しは 429 / ネットワーク断 / 5xx に対して指数バックオフで再試行します。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト先の検査、プライベート IP 拒否）や XML パース対策（defusedxml）、gzip サイズ制限を備えています。
- テスト:
  - OpenAI / HTTP 呼び出し部分はテストしやすいよう、内部呼び出し関数（例: _call_openai_api, _urlopen）をモック可能になっています。
- DB バージョン依存:
  - DuckDB のバージョン差（executemany の空リスト扱いなど）に注意して実装上の回避策を入れています。

---

必要に応じて README を拡張して、CI/CD、デプロイ、監視（Slack 通知等）の手順やサンプル .env.example、SQL スキーマの詳細、例外処理のポリシーを追加できます。追加したい項目があれば教えてください。