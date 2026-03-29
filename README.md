# KabuSys

日本株のデータプラットフォームと自動売買・リサーチ基盤コンポーネント群です。  
DuckDB をデータストアに、J-Quants / RSS / OpenAI 等を組み合わせて、ETL → 品質チェック → AI評価 → ファクター計算 → 監査ログまでをカバーするライブラリ群を提供します。

主な特徴
- J-Quants API クライアント（株価・財務・マーケットカレンダー取得）とレート制御・再試行ロジック
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と銘柄紐付け（raw_news / news_symbols）
- OpenAI を使ったニュースセンチメント評価（ai.news_nlp）と市場レジーム判定（ai.regime_detector）
- ファクター計算・特徴量探索（research モジュール）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
- 汎用統計ユーティリティ（z-score 正規化等）

以下は本リポジトリ内の主な機能と使い方、セットアップ手順、ディレクトリ構成の説明です。

---

## 機能一覧（主要モジュールと概要）

- kabusys.config
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local）と設定アクセス（settings オブジェクト）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）

- kabusys.data
  - jquants_client: J-Quants API クライアント（認証・ページネーション・再試行・保存関数）
  - pipeline / etl: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分 ETL）
  - quality: データ品質チェック群（欠損 / 重複 / スパイク / 日付不整合）
  - news_collector: RSS フィード取得と raw_news への保存（SSRF 対策・サイズ制限）
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
  - audit: 監査テーブルの DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ヘルパ

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとにニュースをまとめて LLM に投げ、ai_scores テーブルへ結果を書き込む
  - regime_detector.score_regime: ETF（1321）の MA 偏差とマクロニュースの LLM センチメントを合成して market_regime へ書き込む

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（特徴量評価）

（パッケージ __init__ では data / strategy / execution / monitoring 等を公開していますが、本配布コードでは data / ai / research 等が主要実装です）

---

## 必要条件（Prerequisites）

- Python 3.10+
- ネットワーク接続（J-Quants API, OpenAI, RSS ソース など）
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml

インストール例（仮の最小セット）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール
   - 編集開発用:
     ```
     git clone <repo-url>
     cd <repo-dir>
     pip install -e .
     ```
   - あるいは必要な依存を個別にインストール（上記参照）

2. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと、`kabusys.config` が自動で読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意 / デフォルト:
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - LOG_LEVEL=INFO|DEBUG|...
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. DuckDB の初期スキーマ（監査ログなど）を作成する場合:
   - Python から init_audit_db / init_audit_schema を使って初期化します（後述）。

---

## 使い方（主要例）

以下はライブラリを利用する際の代表的な呼び出し例です。実行前に必ず必要な環境変数（OpenAI の API キーや J-Quants のトークン等）を用意してください。

- DuckDB 接続を作る:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコア付け（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY か、api_key 引数で指定
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB とスキーマ初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 既存 conn にスキーマを追加する場合:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- ファクター計算・研究ユーティリティ
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m","mom_3m","mom_6m"])
```

- 設定値にアクセスする
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

---

## 注意点 / 設計上の留意点

- ルックアヘッドバイアス防止:
  - AI モジュールや ETL 内の関数は内部で `datetime.today()` / `date.today()` を直接参照せず、引数で渡された target_date に基づいて処理します。バックテストや再現性の観点で重要です。
- OpenAI / J-Quants の API 呼び出しは再試行・バックオフを備えていますが、API キーやネットワークの問題に依存します。フェイルセーフとして失敗時は中立スコア（0.0）やスキップにフォールバックする実装箇所があります。
- news_collector は SSRF 対策、Rss サイズ上限、XML パースの安全化（defusedxml）等を実装しています。
- DuckDB の executemany などの挙動（バージョン依存）に配慮した実装を行っています。

---

## ディレクトリ構成（抜粋）

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
  - etl.py (エイリアス)
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py (ETLResult 等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/（その他ユーティリティ）
- (strategy/, execution/, monitoring/ が __all__ に含まれていますが、上記が本リポジトリの主要実装です)

（上記は実際のソース配置に基づく抜粋です。詳細はソースツリーを参照してください。）

---

## よくある操作例・トラブルシューティング

- 環境変数が読み込まれない場合:
  - パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
  - テスト時は自動読み込みを無効にして明示的に os.environ を操作してください。

- OpenAI 呼び出しのテスト:
  - モジュール内の `_call_openai_api` 関数を unittest.mock.patch で差し替えてモックできます（news_nlp / regime_detector でそれぞれ独立実装されているため、個別に差し替え可能）。

- J-Quants 認証エラー:
  - get_id_token が 401 を受け取る際は自動でリフレッシュを試みます。refresh_token が正しいことを確認してください。

---

## ライセンス・貢献

（必要に応じてライセンスや貢献方法をここに記述してください）

---

README は以上です。実運用や開発向けに、必要ならば以下の追記を提供できます：
- .env.example のサンプルファイル全文
- requirements.txt の推奨依存一覧
- CI / テスト実行方法
- API レート制御・ロギング構成の詳細

必要な追加内容があればお知らせください。