# KabuSys

日本株自動売買プラットフォームのモジュール群（ライブラリ）。  
データ ETL、ニュース NLP（LLM を使ったセンチメント）、市場レジーム判定、研究用ファクター計算、監査ログなどの基盤機能を提供します。

現在のバージョン: 0.1.0

## 概要

KabuSys は日本株の自動売買システム構築を支援する内部ライブラリ群です。  
主に以下の役割を持ちます。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去等）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング（銘柄別）とマクロセンチメントの算出
- ETF を用いた市場レジーム判定（bull/neutral/bear）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索ユーティリティ
- 監査ログ（signal → order_request → execution のトレース）用の DuckDB 初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針としては Look-ahead バイアス防止、冪等性、外部 API の堅牢なリトライ制御、DB 側での安全な保存を重視しています。

---

## 主な機能一覧

- Data/ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: API 呼び出し、ページネーション、保存（raw_prices, raw_financials, market_calendar）
  - data.quality: 欠損・スパイク・重複・日付不整合のチェック
  - data.calendar_management: 営業日判定・前後営業日検索、calendar_update_job
  - data.audit: 監査テーブルの初期化・専用 DB の生成
- News
  - news_collector: RSS 取得、前処理、raw_news への保存（SSRF・サイズ制限・トラッキング除去など）
  - ai.news_nlp.score_news: 銘柄別ニュースセンチメントを計算して ai_scores テーブルへ保存
- Regime
  - ai.regime_detector.score_regime: ETF（1321）MA200乖離 + マクロニュース（LLM）を合成して market_regime を書き込み
- Research
  - research.factor_research: calc_momentum / calc_value / calc_volatility
  - research.feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 共通ユーティリティ
  - config.settings: 環境変数管理（.env 自動読み込み、必須キーチェック）
  - data.stats.zscore_normalize: クロスセクション Z スコア正規化

---

## 動作要件

- Python 3.10+
- 必須ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク（J-Quants API、RSS ソース、OpenAI API へのアクセス）

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーへ配置

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください）
   - pip install -e .

4. 環境変数（.env）を用意

   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   必須の環境変数（config.Settings が要求するもの）:
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API のパスワード
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack チャンネル ID

   オプション（デフォルト値あり）:
   - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に渡さない場合は環境変数を使用）

   簡易 .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（代表例）

以下は Python コードから利用する基本的な例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

1) DuckDB 接続を開く（ファイル DB）
```py
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行する
```py
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

3) ニュース NLP（銘柄別センチメント）を算出する
```py
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを引数で渡すか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", count)
```

4) 市場レジームを判定して保存する
```py
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ用 DB 初期化（別 DB を使う場合）
```py
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

6) 研究用ファクター計算
```py
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

注意点:
- score_news / score_regime は OpenAI API 呼び出しを行います。API レート制限や料金に注意してください。
- ETL・API 呼び出しはリトライやレート制御を組み込んでいますが、ネットワーク/認証情報は正しく設定してください。
- 各処理は Look-ahead バイアス防止に配慮して実装されています（target_date 以前のデータのみ参照）。

---

## 環境変数の自動読み込み

- config.py はプロジェクトルート（.git または pyproject.toml の存在を基準）を探索し、そこに `.env` と `.env.local` があれば順に読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要なソースファイル構成（抜粋）:

- src/kabusys/
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
    - etl.py (re-export)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（その他ユーティリティ）
- その他:
  - data/ (デフォルトの DB 保存先ディレクトリを想定)

各モジュールの責務は README の先頭「概要」や各ファイルの docstring に記載されています。実装は DuckDB を中心に設計され、ETL と分析・運用で使えるユーティリティを提供します。

---

## 開発・テスト

- 単体テストフレームワークや CI 設定はリポジトリに依存します。テスト時は OpenAI / J-Quants の外部 API 呼び出しをモックすることを推奨します（ソース内にモックしやすい設計の箇所があります）。
- 環境変数自動ロードをテストで無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 免責・注意

- 本ライブラリは自動売買の一部機能を提供しますが、実際の売買アルゴリズムや資金管理・リスク管理の実装は別途必要です。実運用前に十分な検証を行ってください。
- OpenAI / J-Quants API キーの管理・課金・レート制限には注意してください。
- 監査ログや実際の発注処理を扱う場合は権限・ログ保護・バックアップを適切に行ってください。

---

必要があれば、特定の利用シナリオ（例: ETL の cron 設定、バックテストでのデータ取り扱い方針、Slack 通知のサンプル）についても README に追記します。どの部分を詳しく書くか教えてください。