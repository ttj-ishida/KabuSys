# KabuSys

KabuSys は日本株のデータプラットフォームおよび自動売買支援ライブラリです。J-Quants からのデータ取得（OHLCV / 財務 / カレンダー）、ニュース収集・NLP による銘柄センチメント評価、研究（ファクター計算 / IC 等）、ETL パイプライン、監査ログ（発注→約定のトレーサビリティ）、市場レジーム判定などの機能を提供します。

主に DuckDB を内部データ格納に使用し、OpenAI（gpt-4o-mini）をニュースセンチメント・マクロセンチメント判定に利用します。設計上、バックテストやフェイルセーフを考慮し「ルックアヘッドバイアス」を防ぐ実装方針が採られています。

バージョン: 0.1.0

---

## 主な特徴

- データ ETL
  - J-Quants API からの日次差分取得（株価・財務・カレンダー）
  - 差分更新・バックフィル・ページネーション・レートリミット・リトライ対応
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェックと QualityIssue 出力
- ニュース収集 & NLP
  - RSS 取得（SSRF対策・gzip制限・トラッキング除去）
  - OpenAI を使った銘柄別センチメント（ai.score_news）
  - マクロニュース + ETF MA で市場レジーム判定（ai.score_regime）
- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）、ファクターサマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブル作成ユーティリティ
  - 監査 DB 初期化関数（init_audit_db / init_audit_schema）
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）および Settings API

---

## セットアップ手順

1. リポジトリをクローン（想定）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール
   - このコードベースは以下の主要依存を想定しています:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   - プロジェクトルートに `.env`（および開発用に `.env.local`）を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
   - 任意:
     - OPENAI_API_KEY — OpenAI API キー（ai モジュール実行時に引数で渡すことも可）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — モニタリング用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. 自動環境読み込みを無効化したい場合（テスト等）
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（主要関数 / 例）

以下はライブラリをインポートして使う最小例です。実行には適切な環境変数とデータベースへの書き込み権限が必要です。

- DuckDB 接続と ETL 実行（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（ai.score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定しているか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
  # conn は duckdb 接続
  ```

- RSS フェッチ（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- ai モジュール（news_nlp / regime_detector）は OpenAI API を利用します。API 呼び出しは失敗/制限に対してリトライやフォールバック（0.0）を取る設計ですが、APIキーが必須です。
- 多くの関数は DuckDB 接続 (duckdb.DuckDBPyConnection) を引数に取ります。ファイル DB へ接続してから渡してください。

---

## 設計上の注意（重要な方針）

- ルックアヘッドバイアス防止
  - ai モジュールや ETL は内部で date.today()/datetime.now() を不用意に参照せず、target_date を明示的に渡して処理することを想定しています。
  - prices や news のクエリは target_date 未満 / 半開区間などでルックアヘッドを避けるよう実装されています。

- フェイルセーフ設計
  - OpenAI / HTTP API の一時障害時は暫定値（例: macro_sentiment=0.0）で継続するように作られており、例外を上位へ伝播させない箇所があります（ただし重大な DB 書き込み失敗等は伝播します）。

- 冪等性
  - J-Quants からの保存処理は ON CONFLICT DO UPDATE（または INSERT … ON CONFLICT）で冪等保存を行います。
  - 監査ログの order_request_id は冪等キーとして期待されます。

- セキュリティ対策
  - RSS の取得は SSRF 対策（リダイレクト先検査・プライベートアドレス検出等）を実装しています。
  - XML パースは defusedxml を使用して XML 攻撃に備えています。

---

## ディレクトリ構成

主要なモジュールと説明:

- src/kabusys/
  - __init__.py — パッケージ定義（公開サブパッケージ: data, strategy, execution, monitoring）
  - config.py — 環境変数 / 設定管理（Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（score_news）
    - regime_detector.py — マクロ + ETF MA で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - etl.py — ETL 公開インターフェース（ETLResult）
    - pipeline.py — ETL 実装（run_daily_etl, run_prices_etl 等）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（QualityIssue, run_all_checks）
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
    - jquants_client.py — J-Quants API クライアント（fetch_*, save_*）
    - news_collector.py — RSS 収集ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - (その他) strategy, execution, monitoring などのパッケージ（README に示した範囲での公開）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しで失敗しても処理が続く
  - 設計上、LLM 呼び出しの障害時はフォールバック値（0.0）で継続します。ログを確認して原因を特定してください（レート制限・APIキー・ネットワーク等）。
- DuckDB の書き込みに失敗した
  - transaction（BEGIN/COMMIT/ROLLBACK）周りで例外処理が入っていますが、例外が出た場合はスタックトレースを確認の上、DB ファイルのパーミッション・ディスク容量を確認してください。

---

## ライセンス / 貢献

この README はコードベースの要点をまとめたものです。実際のリポジトリには LICENSE、CONTRIBUTING ガイド、.env.example などを用意することを推奨します。

貢献やバグ報告は Pull Request / Issue で行ってください。

---

必要であれば、具体的なユースケース（例: バックテスト用のデータ初期ロード手順、J-Quants トークンの取得方法、詳細なログ設定方法等）を追記します。どの項目を詳しく書き足しますか?