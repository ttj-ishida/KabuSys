# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤ライブラリ（KabuSys）の README。  
このリポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（オーディット）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ基盤を構成するためのライブラリ群です。主な目的は次のとおりです。

- J-Quants API からの株価・財務・市場カレンダー等の差分取得と DuckDB への保存（ETL）
- RSS によるニュース収集と前処理、銘柄紐付け
- OpenAI を用いたニュースセンチメント解析（銘柄単位）およびマクロセンチメントを使った市場レジーム判定
- 研究（Research）向けファクター計算 / 特徴量探索ツール（バックテスト用のデータ前処理）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 注文〜約定までを追跡するための監査ログ（DuckDB に監査スキーマを初期化）

設計上の特徴:
- DuckDB によるローカル永続化（軽量で高速）
- Look-ahead bias を避ける設計（日時参照・クエリ条件に注意）
- OpenAI（gpt-4o-mini）を JSON モードで利用する想定（API 呼び出しはリトライ・フォールバック実装あり）
- ETL は差分取得・バックフィルをサポートし、品質チェックは Fail-Fast ではなく問題を集約して返す

---

## 機能一覧

- データ取得 / ETL
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（J-Quants）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL の結果を表す ETLResult クラス
- ニュース収集・NLP
  - RSS フィード取得・前処理（news_collector）
  - OpenAI を使った銘柄ごとのニュースセンチメント score_news
  - マクロニュース + ETF MA200 を合成した市場レジーム判定 score_regime
- 研究（Research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 特徴量解析: calc_forward_returns, calc_ic, factor_summary, rank
  - zscore 正規化ユーティリティ
- データ品質チェック
  - 欠損データ / スパイク / 重複 / 日付不整合 を検出
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ（Audit）
  - 監査スキーマ初期化: init_audit_schema / init_audit_db
- 設定管理
  - 環境変数読み込み、.env 自動読み込み（config.Settings）

---

## 環境変数（主なもの）

必須（実行する機能に応じて必要）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack チャンネル ID
- KABU_API_PASSWORD — kabuステーション API のパスワード（注文実行を使う場合）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合）

任意／デフォルトあり:

- KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動ロードを無効化
- KABUS_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用の SQLite パス（デフォルト data/monitoring.db）

注意:
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を起点として行われます。
- 環境変数が未設定で必須のプロパティへアクセスすると Settings が ValueError を投げます。

例（.env）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（開発環境向け）

1. Python の仮想環境を作成・有効化
   - 推奨: Python 3.10+（コードは typing の新機能や最新パッケージを想定）
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows
     ```

2. 依存ライブラリをインストール
   - 主要依存（最低限）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実プロジェクトでは requirements.txt / pyproject.toml を用意していることが多いです。パッケージ化済みなら:
     ```
     pip install -e .
     ```

3. 環境変数を設定
   - プロジェクトルートに .env を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えば無効化可能）。
   - 必要なキーを .env に記載してください（上の「環境変数」セクション参照）。

4. データベース用ディレクトリの作成
   - デフォルトで data/ 下に DuckDB ファイルが作られます。必要に応じてディレクトリを作成してください:
     ```
     mkdir -p data
     ```

---

## 使い方（主要 API と実行例）

以下はライブラリを Python スクリプトから呼ぶ基本例です。

- DuckDB 接続を作成して ETL を実行（例: 日次 ETL）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメント解析（score_news）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数か api_key 引数で指定
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマの初期化:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # or ":memory:"
# conn は初期化済みの DuckDB 接続
```

- 研究用ユーティリティ（ファクター計算）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- データ品質チェック:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- OpenAI 呼び出しは API 利用料金やレート制限を伴います。API キーは環境変数 OPENAI_API_KEY で指定可能です。
- J-Quants API 呼び出しは認証（JQUANTS_REFRESH_TOKEN）が必要です。API レート制限が実装されていますが、運用時はさらに考慮してください。
- ETL / AI モジュールはそれぞれ DuckDB のテーブルを前提とします。最初に ETL を走らせて必要テーブルを作成・埋める必要があります。

---

## ディレクトリ構成（主要ファイル）

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                # 環境変数 / 設定読み込み
   ├─ ai/
   │  ├─ __init__.py
   │  ├─ news_nlp.py           # ニュースセンチメント解析（OpenAI）
   │  └─ regime_detector.py    # マクロ + ETF MA200 を使ったレジーム判定
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py     # J-Quants API クライアント + DuckDB 保存関数
   │  ├─ pipeline.py           # ETL パイプライン（run_daily_etl 等）
   │  ├─ etl.py                # ETL 結果クラス再エクスポート
   │  ├─ news_collector.py     # RSS 収集・前処理
   │  ├─ calendar_management.py# 市場カレンダー管理
   │  ├─ quality.py            # データ品質チェック
   │  ├─ stats.py              # 統計ユーティリティ（zscore_normalize）
   │  ├─ audit.py              # 監査ログスキーマ定義・初期化
   │  └─ ...                   # （将来的に jquants_client の補助等）
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py    # ファクター計算（momentum/value/volatility）
   │  └─ feature_exploration.py# forward returns, IC, summary
   └─ research/...             # （他の研究ユーティリティ）
```

---

## 開発・運用上の注意

- 日付取り扱い
  - 多くの処理は Look-ahead bias を避けるため、内部で date.today() を不用意に使わず、外部から target_date を与える設計になっています。バックテストや再現性ある実行では target_date を明示してください。
- トランザクション
  - 重要な DB 書き込みは BEGIN/COMMIT/ROLLBACK を使った冪等性を意識した保存を行っていますが、呼び出し側で大きなトランザクションを張る場合は副作用に注意してください（DuckDB のトランザクション特性に注意）。
- リトライ / フォールバック
  - OpenAI や J-Quants 呼び出しはリトライ実装があります。API 失敗時は部分的にスキップして継続する設計が多いため、ログと品質チェック結果を監視して運用判断してください。
- セキュリティ
  - news_collector は SSRF 対策、XML インジェクション対策（defusedxml）、応答サイズチェックなどを実装しています。ただし運用環境のポリシーに沿って追加の制約（プロキシ・IP ホワイトリストなど）を適用してください。

---

## ライセンス / 貢献

（このリポジトリにライセンス情報がある場合はここに記載してください。例: MIT）

貢献:
- バグ報告・プルリクエストは歓迎します。設計方針に沿って、特にテストを含めた変更をお願いします。

---

以上。質問や README に追加したい具体的な使用例（Docker 化、CI、テスト手順など）があれば教えてください。必要に応じて README を拡張します。