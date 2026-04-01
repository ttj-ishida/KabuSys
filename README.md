# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買／リサーチ用のライブラリ群です。J-Quants API や RSS、OpenAI（LLM）を組み合わせてデータ収集・ETL、品質チェック、ファクター計算、ニュース NLP、マーケットレジーム判定、監査ログ管理などを提供します。

---

## 主な機能

- データ収集 / ETL
  - J-Quants から株価（日次 OHLCV）、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - RSS ベースのニュース収集（SSRF 対策・トラッキング除去・前処理）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出
- リサーチ / ファクター計算
  - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR）、バリュー（PER/ROE）、流動性指標など
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ、Zスコア正規化
- ニュース NLP（OpenAI）
  - 銘柄別ニュースのセンチメント分析（gpt-4o-mini, JSON Mode）
  - マクロニュースを元に市場レジーム（bull/neutral/bear）を判定
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブル定義、初期化ユーティリティ
- 設定管理
  - .env 自動ロード（プロジェクトルート判別）と Settings API
- 安全・堅牢性設計
  - API レート制御・リトライ、Look-ahead バイアス対策、フェイルセーフ（API失敗時のフォールバック）、SSRF対策 など

---

## 前提条件

- Python 3.10+（型アノテーションで union | を使用）
- 推奨パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

※他に標準ライブラリの urllib, json, logging などを使用します。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   実環境では requirements.txt を用意している場合はそれを利用してください。

4. 環境変数設定
   プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込まれます（優先順: OS 環境 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の API 呼び出しで使用）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリング）パス（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   例: `.env`
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡易例）

以下はライブラリの代表的な利用例です。すべて Python スクリプト内で行います。

- Settings の利用（設定値取得）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- DuckDB 接続を開いて ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(__import__('pathlib').Path('data/kabusys.duckdb')))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア付け（OpenAI API キーは環境変数か api_key 引数で指定）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # 書込銘柄数を返す
  print("written:", written)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続
  ```

- 研究系関数の利用（ファクター計算等）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  ```

注意点:
- LLM（OpenAI）関連関数は API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）。
- ETL / Fetch 関数はネットワーク I/O を伴うため、例外処理やリトライのログを参照してください。
- look-ahead バイアス対策として、関数は内部で date を明示的に受け取り、datetime.today() を参照しない設計です。

---

## 自動 .env 読み込みの挙動

- 起点はこのパッケージの config モジュール内で __file__ を基準に親ディレクトリを探索し、`.git` または `pyproject.toml` が見つかったディレクトリをプロジェクトルートとみなします。
- 読み込み順: OS 環境 > .env.local > .env
- `.env` のパースはシェル形式（export KEY=val、引用符、コメント取り扱い等）に対応しています。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで利用可能）。

---

## 主要モジュール / ディレクトリ構成

（抜粋。実ファイルは src/kabusys 配下）

- kabusys/
  - __init__.py (パッケージ公開)
  - config.py (環境変数 / Settings)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLP スコア付け)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存ユーティリティ)
    - pipeline.py (ETL パイプライン: run_daily_etl 等)
    - etl.py (ETL インターフェース再公開)
    - calendar_management.py (市場カレンダー管理)
    - news_collector.py (RSS ニュース収集)
    - stats.py (統計ユーティリティ: zscore_normalize)
    - quality.py (データ品質チェック)
    - audit.py (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py (モメンタム・ボラティリティ・バリュー)
    - feature_exploration.py (将来リターン・IC・統計サマリ)
  - ai/regime_detector.py, ai/news_nlp.py などは OpenAI を呼び出すロジックとリトライ処理を内包

---

## 注意事項 / 設計上のポイント

- Look-ahead バイアス対策: 日付パラメータは明示的に渡す設計（内部で date.today() を参照しない関数が多い）。
- 冪等性: ETL 保存処理は ON CONFLICT DO UPDATE や INSERT ... ON CONFLICT を用いて再実行可。
- フェイルセーフ: LLM API や外部 API の一時失敗はスコアを 0.0 とするなど安全側の振る舞い。
- セキュリティ: RSS 収集時の SSRF 防止、defusedxml を利用した XML パース等の対策あり。
- ログレベルと環境: settings.log_level / settings.env で挙動確認。KABUSYS_ENV は development / paper_trading / live のいずれか。

---

## テスト / 開発

- 自動 .env ロードはテストで邪魔になる場合があるため、テスト実行時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定するとよいです。
- OpenAI 呼び出し部分は内部の _call_openai_api 関数をモックしてテスト可能（ユニットテスト用に差し替えを想定）。

---

ご不明点や追加の利用例（CI / デプロイ、監視、Slack 通知の実装例など）が必要でしたら教えてください。README のサンプル .env.example や requirements.txt のテンプレートも作成できます。