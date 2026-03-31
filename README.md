# KabuSys

日本株向けの自動売買／データパイプライン・リサーチ基盤ライブラリです。  
このリポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP、LLM を用いた市場レジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などのコンポーネントを提供します。

バージョン: 0.1.0

---

## 主要機能（ハイレベル）

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存（duckdb）
  - 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質管理
  - 欠損・重複・日付不整合・スパイク検出
- ニュース収集 / 前処理
  - RSS フィードの取得、URL 正規化、前処理、記事ID生成（SHA-256）
  - SSRF とサイズ上限など安全対策を含む実装
- ニュース NLP / LLM スコアリング
  - 銘柄ごとのニュースを統合して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に保存
  - マクロニュースを LLM で評価して市場レジーム（bull/neutral/bear）を算出
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- 監査ログ（audit）
  - シグナル→発注→約定までのトレーサビリティ用テーブル定義と初期化ユーティリティ
- 設定管理
  - .env / .env.local / OS 環境変数から自動ロード（パッケージ起点でプロジェクトルートを探す）

---

## 必要条件 / 依存（代表）

このリポジトリ内のモジュールから推測される依存例：

- Python 3.10+
- duckdb
- openai (OpenAI の Python SDK)
- defusedxml
- （その他標準ライブラリ）

pip でインストールする例（プロジェクトに requirements.txt があればそれを使用してください）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

※ 実運用ではさらに logging / slack API / sqlite3 等の追加設定やバージョン固定を推奨します。

---

## 環境変数

自動で .env（プロジェクトルート）および .env.local を読み込みます（OS 環境変数が優先）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に必要な環境変数（コードから抽出）:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL      : kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        : Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）
- OPENAI_API_KEY         : OpenAI API キー（AI 関連機能で使用）
- DUCKDB_PATH            : DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH            : SQLite ファイルパス（監視系などに使用）
- KABUSYS_ENV            : 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL              : ログレベル ("DEBUG" | "INFO" | ...)

.env.example を作成して上記を管理してください。

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成 & 有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を作成
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

5. DuckDB の初期スキーマや監査DBを作成する（必要に応じて）
   - 監査ログ専用 DB の初期化例（Python スクリプト実行）:

     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     from kabusys.config import settings

     conn = init_audit_db(settings.duckdb_path)  # または別ファイルパス
     # conn は初期化済みの duckdb.DuckDBPyConnection
     ```

---

## 使い方（代表的な例）

以下は Python でライブラリを直接呼ぶ簡単な実行例です。

- DuckDB 接続を開く（設定ファイルのパスを利用する）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（市場カレンダー→株価→財務→品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を渡すことも可能
  print(result.to_dict())
  ```

- 個別 ETL ジョブを実行する
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  from datetime import date

  fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
  ```

- ニュースのセンチメントスコアを付与（OpenAI API キーが必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"written {n_written} ai_scores")
  ```

- 市場レジームをスコアリング
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

- 監査スキーマの初期化（既存接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- RSS フィード取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

注意点:
- OpenAI を用いる関数（score_news, score_regime）は API キーが必要です。引数 `api_key` に文字列を渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- J-Quants 関連（ETL）は `JQUANTS_REFRESH_TOKEN` を `.env` に設定しておく必要があります。

---

## ディレクトリ構成（主要ファイル）

概要的なツリー（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの LLM スコアリング（score_news）
    - regime_detector.py      — マクロ + MA200 を用いた市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存ロジック
    - pipeline.py             — ETL パイプライン / run_daily_etl (ETLResult)
    - etl.py                  — ETL の公開インターフェース（ETLResult 再公開）
    - news_collector.py       — RSS 取得 / 前処理
    - calendar_management.py  — 市場カレンダー管理 / 営業日判定
    - quality.py              — データ品質チェック（QualityIssue / run_all_checks）
    - stats.py                — Z スコア等の統計ユーティリティ
    - audit.py                — 監査ログ（トレーサビリティ）DDL と初期化
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Volatility / Value の計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー等

他に strategy/ execution/ monitoring といったパッケージが存在することが __all__ に示されていますが（__init__.py の公開リスト）、今回の抜粋では主に data / ai / research 周りの実装が含まれています。

---

## 実装上の設計上のポイント（参考）

- Look-ahead bias を避けるため、各モジュールは内部で `datetime.today()` を無闇に参照しないよう設計されています。関数は明示的に `target_date` を受け取ります。
- ETL / 保存処理は冪等（ON CONFLICT DO UPDATE）を意識して実装。
- API 呼び出しはリトライ（指数バックオフ）とレートリミット制御を備え、サーバーエラーやタイムアウトを適切にハンドリングします。
- セキュリティ面では RSS の SSRF 防止、XML パースの defusedxml 使用、HTTP レスポンスサイズ制限、URL 正規化（UTM 除去）などの対策があります。
- AI 呼び出しはレスポンスのパースやバリデーションで堅牢性を高め、失敗時はフェイルセーフ（スコア 0.0 等）として継続する設計です。

---

## よくある運用フロー（例）

1. nightly cron/job で ETL（run_daily_etl）を実行して DuckDB を更新
2. ETL 後にニュースの NLP（score_news）を実行して ai_scores を更新
3. 毎営業日の始めに regime_detector.score_regime を実行して市場レジームを記録
4. strategy 層が ai_scores / factor 値 / market_regime を参照してシグナル生成
5. 発注・約定は order_requests / executions へ監査ログとして残す（audit モジュール）

---

## 補足

- README はコードベースの抜粋に基づき作成しています。実際の環境では追加依存、設定、スクリプト（CLI / cron / Dockerfile / CI 設定など）が必要です。
- セキュリティや API レート制限は運用環境に応じた調整を行ってください。
- テストを行う場合は自動環境ロードを無効にするため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、明示的にテスト用環境を注入してください。

---

必要なら、README に記載するサンプル .env.example、簡単な Dockerfile、または各モジュールの API リファレンス（関数一覧・引数説明）を追加で生成します。どれを追加しますか？