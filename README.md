# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB を用いたデータパイプライン（ETL）・データ品質チェック・ニュース収集・LLM を使ったニュースセンチメント評価や市場レジーム判定、監査ログ（トレーサビリティ）など、運用に必要な基盤機能を提供します。

## 主な機能
- データ取得・ETL
  - J-Quants API から株価（日足）・財務データ・取引カレンダーを差分取得して DuckDB に保存（冪等保存）
  - 日次バッチ（run_daily_etl）でカレンダー取得→株価→財務→品質チェックを実行
- データ品質管理
  - 欠損値・重複・スパイク・日付不整合の検出（quality モジュール）
- ニュース収集
  - RSS フィード取得、前処理、raw_news / news_symbols への冪等保存（SSRF 対策・gzip/サイズ制限など実装）
- AI（LLM）によるセンチメント評価
  - 銘柄別ニュースのセンチメントスコア生成（news_nlp.score_news）
  - マクロニュース + ETF の MA200 乖離から市場レジーム判定（regime_detector.score_regime）
  - OpenAI の JSON Mode（gpt-4o-mini）を利用（リトライ・フェイルセーフ設計）
- リサーチ用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン、IC 計算、Z-score 正規化など
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（init_audit_db / init_audit_schema）

---

## 要件
- Python 3.10 以上（型注釈に | が使用されているため）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

（実際のプロジェクトでは requirements.txt / pyproject.toml に依存関係を記載してください）

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ... （省略）

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを利用してください）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートの .env / .env.local または OS 環境変数で設定します。
   - 自動的に .env（優先度低）→ .env.local（優先度高）が読み込まれます（OS 環境変数は常に最優先）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 必要な環境変数（主なもの）
以下はコード内で参照される主要な環境変数です。プロジェクト固有の .env.example を参考にしてください。

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL      : kabu API の base URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）
- OPENAI_API_KEY         : OpenAI API キー（news_nlp, regime_detector 使用時）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : 環境 (development, paper_trading, live)（デフォルト: development）
- LOG_LEVEL              : ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

config.Settings クラス経由でアクセスできます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## 使い方

以下は代表的なユースケースの実行例（Python インタプリタやスクリプト内で実行）。

- DuckDB 接続の作成
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（株価 / 財務 / カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別センチメント付与）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # OPENAI_API_KEY が環境変数に設定されていること
  num_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", num_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを組合せ）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- リサーチ用ファクター計算例
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

---

## ディレクトリ構成（主要ファイル）
（リポジトリの `src/kabusys` 相対）

- __init__.py
- config.py
  - 環境変数の自動読み込みと Settings クラス
- ai/
  - news_nlp.py          — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py   — マクロニュース + MA200 乖離で市場レジーム判定
- data/
  - pipeline.py          — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py    — J-Quants API クライアント（fetch, save 等）
  - news_collector.py    — RSS 取得・前処理・raw_news 保存
  - calendar_management.py — 市場カレンダーの判定 / 更新ロジック
  - quality.py           — データ品質チェック
  - stats.py             — 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py             — 監査ログスキーマ初期化 / init_audit_db
  - pipeline.py exports ETLResult via data/etl.py
- research/
  - factor_research.py   — モメンタム / ボラティリティ / バリュー等
  - feature_exploration.py — 将来リターン / IC / 統計サマリー / rank
- research.__init__.py exports utilities
- ai.__init__.py exports score_news

（この README はコードベースの主要モジュールを要約しています。実際のファイル一覧はリポジトリを確認してください）

---

## 開発 / テストに関する注意点
- 自動 .env ロード: config モジュールはプロジェクトルート（.git または pyproject.toml）を検索して .env / .env.local を自動読み込みします。テストでこれを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しの差し替え: テスト時は内部の _call_openai_api を unittest.mock.patch で差し替える設計になっています（例: kabusys.ai.news_nlp._call_openai_api）。
- DuckDB の executemany はバージョン差で挙動差があるため、pipeline 等では空リストバインドを避ける工夫があります。テスト時は小さなダミーデータで動作確認してください。
- セキュリティ: news_collector は SSRF 対策（リダイレクト検査、プライベート IP 拒否）や受信サイズ上限・gzip 解凍上限などを実装しています。

---

## 参考・トラブルシューティング
- 「環境変数が設定されていません」のエラーは config._require によるものです。`.env.example` を参考に必須変数を設定してください。
- OpenAI API 利用時の失敗はフェイルセーフにより 0.0（中立）を使って継続する実装が多くあります。ログを確認してください。
- J-Quants API 呼び出しは自動的にトークンリフレッシュ（401 時）・リトライ・レート制御を行います。接続エラー／レート超過が続く場合はネットワークとトークンの有効性を確認してください。

---

この README はコードベースの主要機能と利用方法をまとめたものです。詳細な API 仕様や運用手順（サービス起動スクリプト、Crontab / Airflow の設定、Slack 通知フロー等）は別途ドキュメント化することを推奨します。