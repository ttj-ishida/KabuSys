# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。ETL、ニュース収集・NLP、ファクター計算、監査ログなど、量的運用システムで必要となる共通処理を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 概要

KabuSys は以下のような機能を持つライブラリです。

- J-Quants API からの株価・財務・カレンダー等の差分取得と DuckDB への保存（冪等）
- RSS ニュースの収集・前処理と raw_news への保存（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 想定）を使ったニュースセンチメント解析（銘柄毎の ai_score）とマクロセンチメントを使った市場レジーム判定
- ファクター（モメンタム・ボラティリティ・バリュー等）の計算、将来リターン計算、IC（情報係数）や統計サマリ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログテーブルの初期化および監査用DB（order / execution トレース）管理
- 設定管理（.env / 環境変数の自動読込）

設計上の共通方針：
- Look-ahead bias を避けるため内部で datetime.today() を直接参照しない箇所が多く、target_date を明示して処理します。
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを備えています。
- DuckDB を中心に SQL で集計・保存を行い、処理は基本的に冪等になるよう設計されています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存・認証・レート制御）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（missing_data / spike / duplicates / date_consistency）
  - 監査ログ（signal_events / order_requests / executions の DDL 初期化）
  - ニュース収集（RSS 取得、前処理、SSRF 対策、raw_news への保存）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄ごとの ai_score を生成）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロセンチメントの合成）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - .env / 環境変数読み込み、自動ロード、Settings クラス（settings）を提供

---

## 必要条件 / 依存ライブラリ

- Python 3.10 以上（type hint に X | Y 構文を使用）
- 必須ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml

インストール例（最低限）:
```bash
python -m pip install duckdb openai defusedxml
```

プロジェクトとしてインストール可能であれば（pyproject.toml/セットアップがある場合）:
```bash
python -m pip install -e .
```

---

## 環境変数 / .env

KabuSys はプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動読み込みします（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすれば自動ロードを無効化できます）。

主に利用される環境変数（必須は .env.example を参考に設定してください）:

- JQUANTS_REFRESH_TOKEN ・・・ J-Quants のリフレッシュトークン（get_id_token に利用）
- KABU_API_PASSWORD      ・・・ kabuステーション API パスワード（order 実行機能で利用想定）
- KABU_API_BASE_URL      ・・・ kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        ・・・ Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       ・・・ Slack 通知先チャネルID
- OPENAI_API_KEY         ・・・ OpenAI API キー（ai モジュールで使用）
- DUCKDB_PATH            ・・・ DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH            ・・・ SQLite（監視用）パス（default: data/monitoring.db）
- PID_FILE_PATH          ・・・ 実行監視用 PID ファイルパス（default: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT ・・・ 監視閾値
- KABUSYS_ENV            ・・・ エンバイロメント（development / paper_trading / live）
- LOG_LEVEL              ・・・ ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定はコードから以下のように参照できます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## セットアップ手順（ローカルで動かす場合）

1. Python の準備（3.10+ 推奨）
2. 必要なパッケージをインストール
   ```bash
   python -m pip install duckdb openai defusedxml
   ```
3. 環境変数 / .env を用意（上記参照）
4. DuckDB 用ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```
5. 監査用データベースの初期化（任意）
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn を保持して処理に利用できます
     ```
6. ETL 実行や AI スコア処理は下記「使い方」を参照

---

## 使い方（主な API の例）

以下は簡単な呼び出し例です。すべて target_date を明示して呼ぶことでルックアヘッドバイアスを避けます。

- 日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別 ai_score の生成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示するか、OPENAI_API_KEY を環境変数で設定
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジームのスコアリング
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  status = score_regime(conn, target_date=date(2026, 3, 20))
  print("status:", status)
  ```

- 監査DB の初期化（既出）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS フィード取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- OpenAI 呼び出しは外部 API 料金が発生します。テスト時は関数内部の _call_openai_api をモックすることを推奨します（テスト用に設計済み）。
- J-Quants API はレート制御・トークンリフレッシュを組み込んでいます。JQUANTS_REFRESH_TOKEN を設定してください。

---

## よくあるワークフロー

1. データ取得（run_daily_etl）で prices / financials / calendar を DuckDB に取り込む
2. データ品質チェック（run_daily_etl の run_quality_checks=True で実行）
3. ニュース収集 → ai スコア（score_news）で ai_scores を更新
4. research の関数でファクターを計算・正規化（zscore_normalize）し、バックテストやシグナル生成に利用
5. 戦略でシグナルを生成 → 監査テーブルに記録（init_audit_schema でテーブル整備）
6. 発注・約定の記録を executions テーブルに保存してトレーサビリティを確保

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイルと役割（本リポジトリで提供されているもの）です。

- src/kabusys/
  - __init__.py                   — パッケージ定義（__version__）
  - config.py                      — 環境変数 / .env ロードと Settings
  - ai/
    - __init__.py                  — ai パブリック API（score_news をエクスポート）
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py       — マーケットカレンダー管理（営業日判定等）
    - pipeline.py                  — ETL パイプライン実装（run_daily_etl 等）
    - etl.py                       — ETLResult の公開（再エクスポート）
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査ログ DDL / 初期化
    - jquants_client.py            — J-Quants API クライアント（fetch/save / 認証）
    - news_collector.py            — RSS 取得・前処理・保管ロジック
  - research/
    - __init__.py                  — 研究向けユーティリティのエクスポート
    - factor_research.py           — ファクター計算（momentum/value/volatility）
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー

注: パッケージ __all__ では "strategy", "execution", "monitoring" も挙がっていますが、ここに示したコードベースは data / ai / research / config が中心です。戦略実行（execution）やモニタリング部分は別途実装される想定です。

---

## テストおよび開発のヒント

- AI / 外部 API を伴う処理は単体テストでモックすることを推奨します。各モジュール内に _call_openai_api 等をモックできる設計がされています。
- .env の自動ロードを無効にしたいテストでは環境変数に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB はファイルベースでも in-memory（":memory:"）でも利用可能です。テストでは in-memory DB を利用すると後片付けが楽です。

---

## ライセンス / 貢献

README に含まれているコードは内部仕様を示すための抜粋です。実際のライセンスや貢献方針はリポジトリのトップレベルの LICENSE / CONTRIBUTING ドキュメントを参照してください。

---

何か追加で README に記載したい項目（CI 手順、具体的な .env.example、サンプルデータでの動作確認手順など）があれば教えてください。必要に応じてサンプル .env.example やコマンド一式を追記します。