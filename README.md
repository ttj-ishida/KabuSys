# KabuSys

日本株向けの自動売買およびデータプラットフォーム用ライブラリセットです。  
ETL（J-Quants からの価格・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を使用したセンチメント）、市場レジーム判定、ファクター研究、監査ログ（発注/約定のトレーサビリティ）など、運用・研究のための機能群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の用途を想定した Python モジュール群です。

- J-Quants API を用いたデータ取得（株価日足、財務、上場銘柄情報、JPX カレンダー）
- DuckDB を用いたローカルデータベース保存（ETL の冪等保存）
- ニュース RSS 収集と前処理（SSRF 対策・トラッキング除去等）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（銘柄別 ai_score）およびマクロセンチメントを加味した市場レジーム判定
- ファクター（モメンタム、ボラティリティ、バリュー等）の計算、将来リターン・IC 計算、統計ユーティリティ
- 監査ログ（signal / order_request / executions）テーブルの初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴:
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を直接参照しない設計）
- 冪等性重視（ETL 保存は ON CONFLICT DO UPDATE 等）
- フェイルセーフ（外部 API エラー時は処理を継続、可能な限り部分成功を保持）
- DuckDB を中心とした軽量なオンプレデータレイク構成

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants との通信、取得・保存関数（fetch_* / save_*）
  - pipeline: 日次 ETL 実行エントリ（run_daily_etl）および個別 ETL（run_prices_etl 等）
  - news_collector: RSS 取得・前処理・raw_news 保存補助
  - calendar_management: JPX カレンダー判定・更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal_events / order_requests / executions）のスキーマ初期化
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを銘柄別に集約して OpenAI でセンチメント評価し ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 とマクロニュース（LLM）を合成して market_regime を書き込む
- research/
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数 / .env 管理（プロジェクトルートの .env/.env.local を自動ロード。無効化可能）

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10+ を推奨
- DuckDB, OpenAI SDK 等が必要

1. リポジトリをクローン
   - git clone ...（リポジトリ URL）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。ここで挙げているのは主要依存のみです。）

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると、自動的に読み込まれます（ただしテスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須（運用によって必要なもの）:
     - JQUANTS_REFRESH_TOKEN=...   （J-Quants のリフレッシュトークン）
     - OPENAI_API_KEY=...         （OpenAI API キー。score_news/score_regime に必要）
   - その他（必要に応じて）:
     - KABU_API_PASSWORD=...      （kabuステーション API パスワード、発注機能等で使用）
     - KABU_API_BASE_URL=...     （kabu API のベース URL、デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH=data/kabusys.duckdb  （DuckDB ファイルパス）
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - KABUSYS_ENV=development|paper_trading|live

   サンプル .env (プロジェクトルートに `.env.example` を置くことを推奨):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

---

## 使い方（簡易ガイド）

以下は代表的なユースケースの簡単な使い方例です。実行は Python スクリプトまたは REPL から行います。

- DuckDB 接続の例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（J-Quants からの差分取得と品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別 ai_scores）を取得して DB に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されていれば api_key=None で動作
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに date, regime_score, regime_label 等が保存される
```

- ファクター計算（研究用）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
# 結果は各銘柄ごとの dict リストとして返る
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

- ニュース RSS の取得単体（raw_news テーブル保存は別途実装）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意:
- OpenAI 呼び出しを使う機能（score_news, score_regime）は API キーが必要です。関数に api_key を直接渡すことも可能です。
- ETL/保存操作は DuckDB に対する変化を伴います。実行前にバックアップやファイルパス設定の確認を行ってください。
- 自動 .env ロードはプロジェクトルートの検出に基づきます。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールとその役割です（抜粋）。

- src/
  - kabusys/
    - __init__.py                # パッケージ定義（version 等）
    - config.py                  # 環境変数 / .env ロード / Settings
    - ai/
      - __init__.py
      - news_nlp.py              # ニュース NLP（score_news）
      - regime_detector.py       # 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント（fetch_*/save_*）
      - pipeline.py              # ETL パイプライン（run_daily_etl など）
      - news_collector.py        # RSS フィード収集・前処理
      - calendar_management.py   # 市場カレンダー管理
      - quality.py               # データ品質チェック
      - audit.py                 # 監査ログスキーマ初期化
      - stats.py                 # 統計ユーティリティ（zscore_normalize）
      - etl.py                   # ETLResult 再エクスポート
    - research/
      - __init__.py
      - factor_research.py       # ファクター計算（momentum/value/volatility）
      - feature_exploration.py   # 将来リターン / IC / 統計サマリー

---

## 注意事項 / 推奨事項

- API キーの管理は適切に行ってください（Git 管理下に直接置かない等）。
- OpenAI の呼び出しにはコストとレート制限があるため、運用時はバッチ化やキャッシュを検討してください。モジュール内でもバッチ処理・リトライ制御を行っています。
- J-Quants API のレート制限を守るため、jquants_client 内に簡易レートリミッタを実装しています。ETL 実行は長時間になる可能性があります。
- DuckDB のバージョンにより executemany の挙動が異なることがあるため、pipeline 等で互換性対策がなされています。DuckDB の推奨バージョンをプロジェクトのパッケージングで指定することを推奨します。

---

## さらに詳しく / 開発者向け

- テスト: 各モジュールは外部依存を抽象化しており、network/DB 呼び出しをモックしてユニットテストが書きやすい設計です。例えば OpenAI 呼び出しは内部でラッパー関数を用意しているため patch で差し替え可能です。
- ログレベル: LOG_LEVEL 環境変数で調整（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 環境切り替え: KABUSYS_ENV で development / paper_trading / live を切替。値検証は config.Settings 側で行われます。

---

ご要望があれば、README に以下のような追加情報も追記できます：
- CI 設定例（pytest / GitHub Actions）
- Docker イメージ化手順
- 詳細なテーブルスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime など）
- 実運用でのデプロイ・監視設計（プロセス監視、PID/kill flag など）

必要ならどれを追加するか教えてください。