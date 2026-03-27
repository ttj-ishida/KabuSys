# KabuSys

日本株のデータ基盤・リサーチ・自動売買のためのライブラリ群です。  
DuckDB をデータストアに用いて、J-Quants API からのデータ取得（ETL）、ニュースの NLP スコアリング、ファクター計算、監査ログ（発注・約定トレース）などを提供します。

## 主な特徴
- J-Quants API からの差分取得・保存（ETL）／ページネーション・リトライ・レート制御対応
- ニュース収集（RSS）と OpenAI を用いた銘柄別センチメントスコア生成（gpt-4o-mini）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 設定は .env / 環境変数で管理。プロジェクトルートから自動ロード（無効化可）

※ 設計上、バックテスト用にルックアヘッドバイアスが入りにくいよう配慮されています（明示的に date を渡す等）。

## 機能一覧（抜粋）
- data/
  - jquants_client: J-Quants API クライアント（fetch / save / id_token 管理）
  - pipeline / etl: 日次 ETL パイプライン（run_daily_etl など）
  - news_collector: RSS 取得・前処理・raw_news への保存
  - calendar_management: JPX カレンダー管理（営業日判定・next/prev 取得）
  - quality: データ品質チェック
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計（Zスコア正規化）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores へ書き込む
  - regime_detector.score_regime: 市場レジーム（日次）を market_regime に書き込む
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config: 環境変数管理（自動 .env ロード、Settings クラス）

---

## 必要条件
- Python 3.10 以上（typing に | 演算子等を使用）
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

実際のインストール要件はプロジェクトで管理する requirements.txt / pyproject.toml に合わせてください。

---

## セットアップ手順（開発用）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml または requirements.txt があればそれを使用）
   - 開発モードでインストールする場合: pip install -e .
4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（config モジュールによる）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の例:
```
# 認証
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...

# kabuステーション API (オプション)
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知（オプション）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# 環境・ログ
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO

# DB パス（相対パス可）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（主要 API とサンプル）

以下は最小限の例です。各関数は DuckDB 接続（duckdb.connect(...) が返す DuckDBPyConnection）を引数に取ります。

- 共通: DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー・株価・財務を差分取得し品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（raw_news / news_symbols -> ai_scores）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース融合）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化（監査専用 DB を作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
# 以降 audit_conn を使って監査テーブルに発行ログを保存できます
```

- カレンダー更新ジョブ（J-Quants から取得して market_calendar を更新）
```python
from kabusys.data.calendar_management import calendar_update_job
from datetime import date

saved_count = calendar_update_job(conn, lookahead_days=90)
print("saved", saved_count)
```

注意点:
- OpenAI API 呼び出しはコスト・レート制限に注意してください。score_news / score_regime はリトライやフォールバックを持ちますが、APIキーは必須です。
- J-Quants API は認証トークン（refresh token）を必要とします。settings.jquants_refresh_token が .env から読み込まれます。
- 多くの関数はデータの存在や品質に応じてフォールバック（例: データ不足時の中立値）します。ログを確認してください。

---

## ディレクトリ構成（主要ファイル）
プロジェクトは src/kabusys 配下に配置されています。主なモジュール:

- src/kabusys/
  - __init__.py
  - config.py                      : 環境変数 / .env 自動ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py                   : ニュース NLU によるスコアリング
    - regime_detector.py            : 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             : J-Quants API クライアント + 保存ロジック
    - pipeline.py                   : ETL パイプラインと run_daily_etl
    - etl.py                        : ETL インターフェース再エクスポート
    - calendar_management.py        : JPX カレンダー管理（営業日判定等）
    - news_collector.py             : RSS 取得・前処理・保存
    - quality.py                    : データ品質チェック
    - stats.py                      : 統計ユーティリティ（zscore_normalize）
    - audit.py                      : 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            : モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py        : 将来リターン、IC、統計サマリー等
  - research/...（ユーティリティ群）

---

## 開発・テストのヒント
- config の自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に探索します。テスト実行時に自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分は内部で _call_openai_api を定義しており、単体テストでは patch して差し替え可能です（例: unittest.mock.patch）。
- J-Quants クライアントは内部で RateLimiter を用いて 120 req/min の制御を行います。テストでネットワークをモック化する際は _request や get_id_token をモックしてください。
- DuckDB の executemany は空リストを受け付けないバージョンの注意点（コード内に回避処理あり）に留意してください。

---

## 注意事項
- 実運用での「発注」や「実際の資金運用」を行う場合は十分な検証・リスク管理が必須です。本ライブラリはデータ処理・モデル実験・監査ログの提供が主目的であり、実環境で使う前に安全なサンドボックスでの検証を強く推奨します。
- OpenAI / J-Quants の API キーは機密情報です。公開リポジトリに含めないでください。
- DuckDB ファイルの場所（DUCKDB_PATH）やログレベル等は .env で調整してください。

---

この README はコードベースに含まれる設計コメント・docstring をもとに要約しています。より詳細な仕様は各モジュールの docstring を参照してください。ご要望があれば「README にセットアップ用のスクリプト例を追加」「各 API のユースケース別サンプルを追加」など追記します。