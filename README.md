# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースのNLPスコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）などのユーティリティを提供します。

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- J-Quants API から株価・財務・市場カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と OpenAI を使ったニュースセンチメント（銘柄別）スコアリング
- マクロニュース + ETF MA を合成した市場レジーム判定（bull / neutral / bear）
- 研究（リサーチ）用途のファクター計算、将来リターン・IC 計算などの統計ユーティリティ
- 発注 / 約定フローに対する監査ログ（監査テーブルの初期化・管理）
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計原則として「ルックアヘッドバイアス防止」「冪等性」「フォールトトレランス（API失敗時のフェイルセーフ）」を重視しています。

---

## 主な機能一覧

- kabusys.data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（レート制御・リトライ・トークン自動更新）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
  - ニュース収集: RSS の安全な取得と raw_news への保存（SSRF 対策等）
  - 品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize

- kabusys.ai
  - ニュース NLP（銘柄ごとのセンチメント）: score_news
  - 市場レジーム判定（ETF + マクロニュース）: score_regime

- kabusys.research
  - ファクター計算: calc_momentum / calc_volatility / calc_value
  - 特徴量探索・評価: calc_forward_returns / calc_ic / factor_summary / rank

- 設定管理
  - 環境変数・.env 自動読み込み（src/kabusys/config.py）
  - 主要設定は kabusys.config.settings 経由で参照

---

## セットアップ手順

前提
- Python >= 3.10（`|` 型アノテーションなどを利用）
- 必要なライブラリ: duckdb, openai, defusedxml（および標準ライブラリ）

例: 仮想環境作成と必要パッケージのインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 実際のプロジェクトでは requirements.txt / pyproject.toml を用意している場合はそれに従ってください
```

環境変数
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（src/kabusys/config.py の自動ロード）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系で使用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（監視・通知モジュール用）

データベースパス（デフォルト）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）

ログ設定
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

簡易の .env サンプル
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（例）

以下は Python REPL やスクリプトから利用する際の代表的な例です。

1) DuckDB に接続して日次 ETL を実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を渡さないと今日が対象（内部で営業日に調整される）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄別）をスコアリングして ai_scores テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にある場合、api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

3) 市場レジーム判定（ETF 1321 の MA + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ（order / execution）用の DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル（signal_events, order_requests, executions 等）が作成されます
```

5) 研究用：モメンタムファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{ "date":..., "code":..., "mom_1m":..., ...}, ...]
```

API キーの明示
- score_news / score_regime などは `api_key` 引数で OpenAI API キーを直接渡すこともできます。引数省略時は環境変数 `OPENAI_API_KEY` を参照します。

エラーハンドリング
- 多くの処理は外部 API に依存するため失敗しうる点に注意してください。関数はログ出力／フェイルセーフ（スコア0.0で代替等）を行う場合がありますが、呼び出し元側で結果や例外を確認してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数・.env ロードと Settings
    - ai/
      - __init__.py
      - news_nlp.py                   # ニュースセンチメント（score_news）
      - regime_detector.py            # 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py             # J-Quants API クライアント（fetch / save）
      - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py        # 市場カレンダー管理
      - news_collector.py             # RSS 収集（SSRF 対策等）
      - quality.py                    # データ品質チェック
      - stats.py                      # 統計ユーティリティ（zscore_normalize）
      - audit.py                      # 監査ログテーブル定義・初期化
      - etl.py                        # ETL の公開型（ETLResult）
    - research/
      - __init__.py
      - factor_research.py            # ファクター計算（momentum/value/volatility）
      - feature_exploration.py        # 将来リターン・IC・統計サマリー
    - ai/ (説明済)
    - monitoring/ (存在想定: 監視・Slack 通知用モジュール等)
    - execution/ (存在想定: 発注・ブローカー連携)
    - strategy/ (存在想定: 戦略実装)
- pyproject.toml / setup.py / requirements.txt （存在する場合はこれに従ってください）

（注）README に載せたのは主要なモジュールの抜粋です。実際のリポジトリ内にさらに補助モジュールが含まれる可能性があります。

---

## 設定・運用上の注意

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト等で自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは外部 API 領域に依存します。レスポンスパースに失敗した場合はフェイルセーフでスコアを 0.0 とする実装が多く、呼び出し側でログ・結果を確認してください。
- J-Quants API にはレート制限があるため jquants_client は内部でレート制御とリトライを行います。ID トークンは自動リフレッシュされます。
- DuckDB に対する複数スレッド/プロセスからの同時アクセスやトランザクションの扱いは注意が必要です（DuckDB の特性に従ってください）。
- 監査ログは削除しない前提の設計です。運用時はディスク容量管理とバックアップ方針を用意してください。

---

## 依存ライブラリ（代表）

- duckdb
- openai
- defusedxml

実際の依存は pyproject.toml / requirements.txt を参照してください。

---

## 貢献・開発

- テスト: 各モジュールは外部依存（ネットワーク / API）を受けるため、ユニットテストでは HTTP / OpenAI / urllib 等の呼び出しをモックしてテスト可能です（コード内にモック推奨箇所のコメントあり）。
- コーディング規約: ログを多用し、操作はなるべく冪等に（ON CONFLICT 等）行う方針です。
- ドキュメント化: 各関数にドキュメンテーションコメントが付与されています。詳細は該当ソースの docstring を参照してください。

---

必要であれば README に例となる .env.example、requirements.txt、よくあるトラブルシュート（OpenAI レート、J-Quants 認証エラー、DuckDB ファイルパス問題等）を追記します。どの情報を追加しますか？