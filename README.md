# KabuSys

KabuSys は日本株のデータプラットフォーム、リサーチ、AI スコアリング、監査ログ、ETL、ニュース収集、ならびに取引実行（発注）に必要な基盤ロジックを集約したライブラリ群です。  
このリポジトリは「データ取得・品質管理・ファクター計算・AI によるニュースセンチメント判定・市場レジーム判定・監査ログ／発注トレーサビリティ」を主に扱います。

主な用途の例:
- J-Quants からの株価／財務／カレンダー ETL
- raw_news の収集と OpenAI による銘柄センチメント算出（ai_scores）
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター（Momentum / Value / Volatility 等）の計算・検証
- 監査ログテーブルの初期化（order_requests/executions 等）
- データ品質チェック

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主な API と使用例）
- ディレクトリ構成
- 環境変数（主要なもの）
- 注意事項

---

## プロジェクト概要

KabuSys はバックテスト／リサーチ／運用の基盤を想定した Python モジュール群です。  
主な設計方針：
- Look-ahead バイアスを避ける（target_date 指定や DB の過去データのみ参照）
- DuckDB を主要なローカルストアとして利用
- J-Quants API（株価・財務・カレンダー）を差分 ETL で取得・保存
- OpenAI（gpt-4o-mini 等）を利用してニュースのセンチメントを算出（JSON Mode を利用）
- 品質チェック／監査ログテーブルにより信頼性を担保
- 外部 API 呼び出しはリトライ・バックオフ・レート制御を実装

---

## 機能一覧

- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 環境判定（development / paper_trading / live）やログレベルなどの取得
- Data（kabusys.data）
  - J-Quants クライアント（fetch/save, token refresh, rate limit）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集器（RSS 取得・前処理・保存補助）
  - データ品質チェック（欠損・スパイク・重複・将来日付等）
  - 監査ログ（audit テーブル作成 / init_audit_db）
  - 汎用統計（zscore_normalize）
- AI（kabusys.ai）
  - ニュース NLP（score_news: 銘柄ごとにセンチメントを ai_scores に書き込む）
  - 市場レジーム判定（score_regime: ETF MA とマクロニュースを合成）
  - OpenAI 呼び出しはリトライやフォールバックを実装（失敗時はゼロスコアで回避）
- Research（kabusys.research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（forward returns, IC, factor summary, rank）
- その他ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（型表記 Path | None 等を使用）
- Git クローン済みのリポジトリ

1. リポジトリをクローンしてワークディレクトリに移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .\.venv\Scripts\activate   # Windows
   ```

3. 必要パッケージをインストール
   requirements.txt がない場合は主要依存をインストールしてください:
   - duckdb
   - openai
   - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` および開発用に `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（詳細は下部参照）を設定してください。

5. 開発インストール（任意）
   ```
   pip install -e .
   ```

---

## 使い方（代表的な API と実行例）

以下は簡単な利用例です。各例は Python インタプリタやスクリプト内で実行できます。

1) DuckDB 接続を作り ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')  # ファイルがなければ作成
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの AI スコア（銘柄ごと）を算出して ai_scores テーブルへ書く
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
# OPENAI_API_KEY が環境変数に設定されていること
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

3) 市場レジームを判定して market_regime テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ（audit）データベースを初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db('data/monitoring.db')  # または ":memory:"
```

5) News RSS を取得する（単体）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a['title'], a['datetime'])
```

注意:
- OpenAI 呼び出しは外部 API です。テスト時は kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api をモックしてください（unittest.mock.patch が想定されている実装箇所あり）。
- J-Quants API を使う関数は認証トークン（JQUANTS_REFRESH_TOKEN）を必要とします。get_id_token が自動でトークンをリフレッシュします。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py            -- ニュースセンチメント算出（ai_scores への書き込み）
  - regime_detector.py     -- ETF MA + LLM による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py      -- J-Quants API クライアント（fetch/save）
  - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
  - calendar_management.py -- 市場カレンダー操作（is_trading_day など）
  - news_collector.py      -- RSS フェッチと前処理ユーティリティ
  - quality.py             -- データ品質チェック（欠損/スパイク/重複/日付不整合）
  - stats.py               -- zscore_normalize 等の統計ユーティリティ
  - audit.py               -- 監査ログテーブル作成と init_audit_db
  - etl.py                 -- ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py     -- ファクター計算（momentum/value/volatility）
  - feature_exploration.py -- 将来リターン/IC/統計サマリ等
- research/... その他
- その他モジュール群（strategy, execution, monitoring などは __all__ に含まれるが今回の抜粋により詳細は省略）

---

## 主要な環境変数

（プロジェクトの .env または OS 環境変数で指定）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client.get_id_token に使用。

- OPENAI_API_KEY (必須 for AI 機能)  
  OpenAI の API キー。score_news / score_regime で使用。

- KABU_API_PASSWORD  
  kabu ステーション API のパスワード（発注等に使用）

- KABU_API_BASE_URL (オプション)  
  デフォルト: http://localhost:18080/kabusapi

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (オプション)  
  LINE 通知を行う場合に利用

- DUCKDB_PATH (省略時: data/kabusys.duckdb)  
- SQLITE_PATH (省略時: data/monitoring.db)  
- PAPER_FILL_MODE (paper trading 用、default "instant")  
  有効値: instant | partial | never | reject

- KABUSYS_ENV  
  有効値: development, paper_trading, live

- LOG_LEVEL  
  DEBUG|INFO|WARNING|ERROR|CRITICAL

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます（テスト用等）。

---

## 注意事項 / 実運用メモ

- Look-ahead バイアスに注意して設計されています。target_date を必ず外部から与える等の運用ルールに従ってください。
- OpenAI の呼び出しはコストとレートに注意して使ってください。score_news は銘柄をチャンクして最大 _BATCH_SIZE でバッチ処理します。
- J-Quants のレート制限（120 req/min）を守るために内部でレートリミッタを実装していますが、過度な並列化は控えてください。
- ニュース収集時は SSRF / XML 攻撃対策（defusedxml, プライベート IP 禁止等）が組み込まれていますが、運用時の追加対策（プロキシ制御、受信ドメイン制限等）を検討してください。
- DuckDB の executemany に関するバージョン依存の注意点（空リスト渡せない等）が実装内に対処済みです。環境の DuckDB バージョンに合わせて運用してください。

---

もし README に追加したい具体的な例（例えば ETL を cron で回す方法、監視・デーモン化のサンプル、Kabu ステーションとの接続方法等）があれば教えてください。必要に応じて .env.example のサンプルやもっと詳しい API リファレンスも作成できます。