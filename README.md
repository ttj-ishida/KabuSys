# KabuSys

日本株向けのデータ基盤・研究・自動売買補助ライブラリです。  
DuckDB を使ったデータ管理、J-Quants / RSS からの ETL、ニュースの LLM によるセンチメント分析、ファクター計算、監査ログスキーマの初期化などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象としたデータプラットフォームとリサーチ / 実行支援のためのユーティリティ群をまとめたパッケージです。主な目的は以下です。

- J-Quants API からの株価 / 財務 / カレンダー取得と DuckDB への ETL（差分取得・冪等保存）
- RSS ニュース収集と前処理、LLM を用いたニュースセンチメント評価（銘柄別）
- 市場レジーム判定（MA と マクロ記事の LLM センチメントを合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 取引監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマの初期化

設計方針として、Look-ahead バイアス回避、API の堅牢なリトライ・レート制御、DuckDB での冪等保存、外部依存の最小化（標準ライブラリ中心）を重視しています。

---

## 機能一覧（抜粋）

- データ / ETL
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - jquants_client: fetch / save 関数（fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar, get_id_token）
  - market_calendar 管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック（SSRF 対策・サイズ制限）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブル DDL / init_audit_db

- AI / NLP
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI (gpt-4o-mini) で評価し ai_scores に書き込み
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュース LLM を合成し market_regime に書き込み

- Research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize

- 設定 / ユーティリティ
  - config.Settings: .env 自動読み込み（.env / .env.local）と必須環境変数チェック

---

## セットアップ手順

前提: Python 3.10+ を想定（typing の一部注釈など）。

1. リポジトリをクローン（またはソース配置）
   - 例: git clone <your-repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   追加: もし packaging/setup を用意する場合は `pip install -e .` を利用してください。

4. 環境変数の準備
   - プロジェクトルート（.git や pyproject.toml がある階層）に `.env` または `.env.local` を置くと自動読み込みされます（自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   例: `.env.example`（プロジェクトルートに置く）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API（必要に応じて）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI (news_nlp / regime_detector で利用)
   OPENAI_API_KEY=your_openai_api_key

   # Slack（通知用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB ファイルディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要 API と簡単なサンプル）

以下の例は Python スクリプトや REPL で実行できます。DuckDB 接続には `duckdb.connect()` を使用します。

- 基本的な設定と DB 接続
```python
import duckdb
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))
```

- 日次 ETL を実行する（J-Quants トークンは settings から自動取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメント評価（ai_scores へ書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI の API キーは OPENAI_API_KEY 環境変数か、api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
# mom は dict のリスト: [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

- 監査ログ DB 初期化（独立した audit DB を作る例）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- 市場カレンダーの判定例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- OpenAI 呼び出しがある関数（score_news, score_regime）は OPENAI_API_KEY 環境変数を参照します。関数引数 `api_key` で明示的に渡すことも可能です。
- jquants_client.get_id_token() は settings.jquants_refresh_token を使用して ID トークンを取得します。J-Quants の refresh token を .env に設定してください。
- ETL / AI 周りは API レートやコストに注意して運用してください。

---

## ディレクトリ構成（主なファイル）

概要（src/kabusys 以下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py          — ニュースの LLMセンチメント評価と ai_scores 書き込み
  - regime_detector.py   — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py    — J-Quants API クライアント（fetch / save / auth / rate limit）
  - pipeline.py          — ETL パイプライン（run_daily_etl 等）
  - etl.py               — ETLResult の再エクスポート
  - news_collector.py    — RSS 収集と前処理
  - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
  - quality.py           — データ品質チェック（欠損・スパイク等）
  - audit.py             — 監査ログスキーマ定義 / 初期化
  - stats.py             — zscore_normalize 等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py   — calc_momentum, calc_value, calc_volatility
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank

各モジュールは DuckDB 接続オブジェクトを受け取り、DB 上のテーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, prices_daily 等）を参照 / 更新します。スキーマ定義は一部モジュール（audit.py）に含まれており、初期化ユーティリティが用意されています。

---

## 追加メモ / 運用注意

- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に `.env` と `.env.local` を自動読み込みします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを抑制できます（テスト用途など）。

- ログレベル / 実行環境:
  - settings.env は `development` / `paper_trading` / `live` のいずれか。`LOG_LEVEL` でログレベルを指定できます。

- エラーハンドリング:
  - ETL パイプラインは各ステップでエラーハンドリングを行い、部分失敗でも他のステップは継続する設計です。ETLResult の errors / quality_issues を確認して運用判断してください。

- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト時のホスト判定等）や受信サイズ上限を実装していますが、実運用時はアクセス元や User-Agent ポリシー等を考慮してください。
  - J-Quants / OpenAI の認証情報は安全に管理してください（CI シークレット管理、Vault 等の利用を推奨）。

---

## 貢献 / 開発者向け

- コードはモジュールごとに分かれており、ユニットテストを追加しやすい設計です。OpenAI / ネットワーク周りの外部依存は関数をモック可能な形で実装しているため、unittest.mock で置き換えてテストできます。
- 新しい ETL 対象を追加する際は jquants_client の fetch/save のペアを実装し、pipeline.run_* に組み込んでください。
- LLM プロンプトやバッチサイズ等は定数としてモジュール内で定義しているため、チューニングしやすくなっています。

---

必要であれば README を拡張して、セットアップの自動化（poetry/requirements.txt）、具体的な DB スキーマ（raw_* / ai_scores / market_regime などの CREATE 文）、実行用 CLI スクリプトや systemd / cron の運用例を追加できます。どの部分を詳細化したいか教えてください。