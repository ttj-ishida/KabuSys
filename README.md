# KabuSys

日本株向け自動売買基盤（ライブラリ） — データ取得・ETL、特徴量生成、シグナル作成、ニュース収集、監査・実行レイヤを備えたモジュール群。

このリポジトリは DuckDB を中心としたオンプレ／ローカル分析環境と、J-Quants / kabuステーション 等の外部 API からのデータ取得を組み合わせ、アルファ探索からシグナル生成、発注トレーサビリティまでの基盤を提供します。

## 特徴 / 機能一覧

- データ取得・ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得・保存（ページネーション、レート制御、リトライ、トークン自動更新）
  - DuckDB に対する冪等保存（ON CONFLICT による更新）
  - ETL の品質チェックフレームワーク（欠損・スパイク等の検出）
- データスキーマ
  - Raw / Processed / Feature / Execution の多層スキーマを DuckDB で定義・初期化
  - 監査用テーブル群（signal_events / order_requests / executions 等）
- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー 等のファクター計算（research/factor_research）
  - Z スコア正規化ユーティリティ
  - 将来リターン・IC 計算などの探索用ユーティリティ（research/feature_exploration）
  - features テーブル構築（strategy/feature_engineering）
- シグナル生成
  - 正規化済みファクター・AI スコアを統合して final_score を算出
  - Bear レジーム抑制、BUY / SELL のエグジット判定、signals テーブルへの冪等保存
- ニュース収集
  - RSS フィードから記事を収集、正規化、raw_news に保存
  - SSRF/サイズ上限/GZIP 等の安全対策、記事と銘柄コードの紐付け
- その他ユーティリティ
  - 市場カレンダー管理（営業日判定、次/前営業日取得）
  - J-Quants クライアント（レートリミット、リトライ、トークンリフレッシュ）
  - 設定管理（.env 自動ロード・必須項目チェック）

---

## 要件

- Python 3.10+
- DuckDB Python パッケージ（duckdb）
- defusedxml（RSS パースの安全対策）
- （標準ライブラリで多くを実装しているため依存は最小限）

例:
pip install duckdb defusedxml

（プロジェクト全体をパッケージ化している場合は pip install -e . などでインストール可能）

---

## セットアップ手順

1. リポジトリをクローン / ソースにアクセス
2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （開発用に pip install -e . が可能であればそれも）
4. 環境変数 (.env) を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動でロードされます（自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）
   - 必須項目は Settings クラスで _require されます（不足時は ValueError）
   - 例（.env の最小例）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
5. DuckDB スキーマを初期化
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を渡すとインメモリ DB

---

## 使い方（主要ワークフロー）

以下はライブラリ API を直接呼ぶ最小例です。運用ではこれらを CLI / Airflow / cron などでラップします。

1) スキーマ初期化
- 初回のみ必要:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL を実行（株価・財務・カレンダー）
- ETL のエントリポイント:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

3) 特徴量の構築（features テーブルを作成）
- 検証用 / 戦略用:
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date(2024, 1, 31))
  print(f"upserted features: {n}")

4) シグナル生成（signals テーブルに BUY/SELL を書き込む）
- しきい値や重みをカスタマイズ可能:
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2024, 1, 31), threshold=0.6, weights={"momentum":0.4, "value":0.2, "volatility":0.15, "liquidity":0.15, "news":0.1})
  print(f"signals written: {total}")

5) ニュース収集ジョブ
- RSS ソースから記事収集 → raw_news / news_symbols 保存:
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))  # sources None でデフォルト
  print(results)

6) カレンダー更新ジョブ（夜間バッチ）
- jquants から JPX カレンダーを更新:
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

7) J-Quants から直接データ取得して保存
- jquants_client の fetch_* / save_* を組み合わせて利用可能:
  from kabusys.data import jquants_client as jq
  rows = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, rows)

注意点:
- すべての主要処理は「日付単位での置換（DELETE → INSERT）」で冪等性を保つ設計です。
- AI スコアや positions 等は別工程で更新される想定です（generate_signals は ai_scores / positions を参照します）。
- 実際の発注・execution 層は別モジュールで統合する想定で、戦略モジュール自体は発注 API に依存しません。

---

## 環境変数（主要なキー）

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL     : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : ローカル監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 をセットすると .env 自動読み込みを無効化

.env.example をプロジェクトルートに置いて使ってください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py  — 環境変数 / 設定管理（.env 自動ロード等）
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント（取得/保存/リトライ/レート制御）
  - news_collector.py        — RSS ニュース収集・前処理・保存
  - schema.py                — DuckDB スキーマ定義と初期化
  - stats.py                 — zscore_normalize など統計ユーティリティ
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py   — JPX カレンダー管理（営業日判定など）
  - audit.py                 — 監査ログテーブル DDL
  - features.py              — data.stats の再エクスポート
- research/
  - __init__.py
  - factor_research.py       — momentum/volatility/value 等ファクター計算
  - feature_exploration.py   — forward returns, IC, factor summary
- strategy/
  - __init__.py
  - feature_engineering.py   — features テーブル構築（正規化・フィルタ）
  - signal_generator.py      — final_score 計算、BUY/SELL 生成
- execution/                  — 発注/監視関連（パッケージの骨子）
- monitoring/                 — 監視用 DB 更新等（監視機能の場所）

（この README はコード内の docstring / コメントを基に要点を抜粋しています）

---

## 運用上の注意事項

- 本ライブラリは実際の売買ロジックを提供しますが、実運用前に十分なバックテスト・ペーパー取引での検証を行ってください。
- API トークンやパスワードは漏洩に注意し、適切に管理してください。
- DuckDB のファイルは適宜バックアップしてください。監査ログは削除しない前提で設計されています。
- カレンダー等の外部データは API 側で修正が入る可能性があるため、backfill 設定により直近数日を再取得する設計になっています。

---

## 参考（よく使うコードスニペット）

- スキーマ初期化と日次 ETL
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)
  print(result.to_dict())

- 特徴量作成 → シグナル生成
  from kabusys.strategy import build_features, generate_signals
  from datetime import date
  build_features(conn, date(2024,1,31))
  generate_signals(conn, date(2024,1,31))

---

必要であれば、この README をベースに CLI コマンド例（systemd / cron / Airflow 用のサンプル DAG / unit file）や .env.example の完全テンプレート、インストール用 requirements.txt を追加で作成できます。どの追加情報が必要か教えてください。