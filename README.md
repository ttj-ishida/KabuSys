# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL、ニュース収集・NLP（LLM 評価）、ファクター計算、データ品質チェック、マーケットカレンダー管理、監査ログ（トレーサビリティ）、J-Quants / kabu ステーション連携などを含むモジュール群を提供します。

## 主な特徴
- データ取得（J-Quants）と ETL パイプライン（差分取得、冪等保存、品質チェック）
- ニュース収集（RSS）と LLM（OpenAI）による銘柄別センチメント評価（news_nlp）
- マクロニュースと ETF MA 乖離を組み合わせた市場レジーム判定（regime_detector）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー、IC 等）
- マーケットカレンダー管理と営業日ユーティリティ
- 監査ログ（signal / order_request / execution）スキーマの初期化ユーティリティ
- DuckDB を中心とした軽量なオンプレデータベース構成
- 自動 .env ロード（プロジェクトルートの .env / .env.local）

---

## 必要条件
- Python 3.10+
- duckdb
- openai（OpenAI SDK）
- defusedxml
- そのほか標準ライブラリ（urllib, json, datetime, logging 等）

（プロジェクトの requirements.txt / pyproject.toml に依存関係を追加している想定です）

---

## インストール（開発環境）
例: 仮想環境作成 → インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
# もしくは requirements.txt があるなら:
# pip install -r requirements.txt
```

---

## 環境変数（設定）
設定は .env / .env.local または実環境変数から読み込まれます。自動読み込みはプロジェクトルート（.git または pyproject.toml）から行われ、無効化するには以下を設定します:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境キー（README 用サンプル）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（監視等）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : environment ('development' | 'paper_trading' | 'live')（デフォルト: development）
- LOG_LEVEL             : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- OPENAI_API_KEY        : OpenAI API キー（LLM 呼び出し時に参照）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ（DB 初期化など）
- DuckDB 接続:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 監査ログ DB 初期化（専用ファイル）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
  ```

- 監査スキーマを既存接続に追加
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

---

## 使い方（代表的な API）
以下はライブラリの主要ユースケース（サンプル）です。

- 日次 ETL 実行（市場カレンダー・株価・財務 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの LLM スコア付け（指定日のウィンドウ）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```

- 市場レジーム判定（ETF 1321 + マクロニュース）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算・研究用ユーティリティ
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- ニュース RSS 取得（個別）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  ```

注意点:
- OpenAI 呼び出しには OPENAI_API_KEY が必要です。テスト時は各モジュールの _call_openai_api をモックしてください。
- J-Quants はレート制限・トークン管理が実装されています。JQUANTS_REFRESH_TOKEN を設定してください。

---

## よくある利用シナリオ / 実運用のヒント
- 開発環境では KABUSYS_ENV=development、本番（注文実行）では live / paper_trading を使い分けてください。
- 自動 .env ロードが不要なテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- news_nlp と regime_detector は LLM に依存するため、API 失敗時はフェイルセーフ（スコア 0 等）で継続する設計です。
- DuckDB の executemany は空パラメータでエラーになるバージョンがあるため、該当箇所では空チェック済みです。

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py — パッケージ定義（version, __all__）
- config.py — 環境変数・設定管理（.env 自動ロード、Settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（銘柄別）
  - regime_detector.py — マクロ + ETF MA で市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証・再試行・レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult 再エクスポート
  - news_collector.py — RSS 収集・前処理・保存ロジック
  - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログ（シグナル→発注→約定）スキーマ初期化
- research/
  - __init__.py
  - factor_research.py — momentum / value / volatility 計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー / ランク関数

---

## テスト・開発のヒント
- OpenAI や外部 HTTP を使う箇所はモック（unittest.mock.patch）してユニットテストを行ってください。各モジュールにモックしやすい内部ラッパー関数（例: _call_openai_api, _urlopen）が用意されています。
- DuckDB のインメモリ接続(":memory:") を使うとテストが容易です。
- .env の自動ロードはプロジェクトルートベースなので、テスト実行時に意図した .env が拾われないように注意してください（KABUSYS_DISABLE_AUTO_ENV_LOAD を利用）。

---

## 参考
- OpenAI: gpt-4o-mini を JSON mode（response_format）で利用する実装が含まれています。
- J-Quants API: rate limiting / token refresh / pagination を扱うクライアント実装あり。

---

追加の項目（運用や CI 連携、Detailed schema 等）が必要でしたら、利用シナリオに合わせて README を拡張します。どの部分を詳しく説明したいか教えてください。