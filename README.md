# KabuSys

日本株自動売買システムのコアライブラリ（リサーチ / データパイプライン / 戦略 / 発注基盤の骨組み）

このリポジトリは、J-Quants API などからデータを取得して DuckDB に蓄積し、ファクター算出・特徴量作成・シグナル生成を行い、発注・約定・ポジション管理のためのスキーマとユーティリティを提供します。プロダクション（live）／ペーパー（paper_trading）／開発（development）モードを想定しています。

主な設計方針:
- ルックアヘッドバイアス防止（各処理は target_date 時点のデータのみを使用）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全）
- 外部 API 呼び出しのリトライ・レート制御・トークン自動更新（J-Quants クライアント）
- テスト容易性を考慮した依存注入（id_token 等の注入）

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（fetch / save: 株価、財務、マーケットカレンダー）
  - RSS ニュース収集（安全対策: SSRF ブロック、XML 攻撃対策、トラッキング除去）
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
- ETL パイプライン
  - 日次差分ETL（市場カレンダー・株価・財務の差分取得と保存）
  - 品質チェックフック（quality モジュール経由）
- ファクター / 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research/factor_research.py）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー（research/feature_exploration.py）
- 特徴量 & シグナル生成（strategy）
  - 特徴量生成（Zスコア正規化、ユニバースフィルタ、features テーブルへ UPSERT）
  - シグナル生成（複数コンポーネントの重み付け集計、Bear レジーム抑制、SELL 条件）
- Execution / Audit スキーマ
  - signals / signal_queue / orders / executions / positions 等の実務向けスキーマ
  - 監査ログ（signal_events / order_requests / executions）による完全トレーサビリティ
- 共通ユーティリティ
  - 統計ユーティリティ（z-score 正規化）
  - カレンダー管理ユーティリティ（営業日判定など）

---

## セットアップ手順

前提
- Python 3.9+（型ヒントなどに合わせて）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
  - （必要に応じて他パッケージ）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境の作成と依存インストール（例）
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml

   （プロジェクトには追加の依存がある場合があります。requirements.txt があればそれを使ってください）

3. 環境変数設定
   プロジェクトルートに `.env` / `.env.local` を配置することで自動読み込みされます（config.py の自動ロード機能）。
   自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須となる主な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabu API のパスワード
   - SLACK_BOT_TOKEN: Slack ボットトークン（通知等で使用）
   - SLACK_CHANNEL_ID: Slack チャネル ID
   任意 / デフォルトがあるもの:
   - KABUSYS_ENV: development / paper_trading / live （デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
   - KABU_API_BASE_URL: kabu ステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）

   例 .env (簡易)
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb

4. データベース初期化
   Python REPL またはスクリプトで DuckDB スキーマを初期化します。

   例:
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---

## 使い方（代表的な操作例）

以下はライブラリを直接呼び出す例です。CLI ラッパーは本コードベースには含まれていないため、スクリプトやジョブから呼び出してください。

1. DuckDB 接続とスキーマ初期化
   from kabusys.data.schema import init_schema
   conn = init_schema('data/kabusys.duckdb')

2. 日次 ETL 実行
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # 今日分を取得・保存・品質チェック
   print(result.to_dict())

   オプション:
   - target_date: 特定日を指定
   - id_token: J-Quants の id_token を注入してテストを簡単にする
   - run_quality_checks: 品質チェックをスキップする場合は False に設定

3. 特徴量のビルド（戦略用 features テーブル更新）
   from kabusys.strategy import build_features
   from datetime import date
   cnt = build_features(conn, date(2025, 1, 31))
   print("upserted", cnt)

4. シグナル生成
   from kabusys.strategy import generate_signals
   from datetime import date
   total = generate_signals(conn, date(2025, 1, 31))
   print("signals created", total)

   weights や threshold をオーバーライド可能:
   generate_signals(conn, date.today(), threshold=0.65, weights={"momentum": 0.5, "value": 0.2, ...})

5. RSS ニュース収集ジョブ
   from kabusys.data.news_collector import run_news_collection
   res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
   print(res)

6. マーケットカレンダー更新（夜間バッチ）
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print("calendar saved:", saved)

7. J-Quants からのデータ取得（直接利用）
   from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
   token = get_id_token()
   quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

注意点:
- 関数は DuckDB の接続オブジェクトを受け取る設計です。並列実行時は接続の扱いに注意してください。
- J-Quants のレート制御やトークン自動更新は jquants_client 内で行われます。
- ETL 等のジョブは失敗しても可能な限り次のステップを継続する設計になっています（エラーハンドリングあり）。結果オブジェクトで詳細を確認してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live, デフォルト development)
- LOG_LEVEL (DEBUG/INFO/... デフォルト INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

---

## ディレクトリ構成

（省略した小ファイルを含む主要なツリー）

src/kabusys/
- __init__.py
- config.py
  - 環境変数・設定のロードと検証（自動 .env ロード機能含む）
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（リトライ・レート制御・ID トークン更新）
  - news_collector.py
    - RSS 収集・前処理・raw_news / news_symbols 保存
  - schema.py
    - DuckDB スキーマ定義と init_schema / get_connection
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - pipeline.py
    - ETL パイプライン（run_daily_etl, run_prices_etl, ...）
  - features.py
    - data.stats の再エクスポート
  - calendar_management.py
    - カレンダー取得・営業日ユーティリティ・calendar_update_job
  - audit.py
    - 監査ログ用スキーマ DDL
- research/
  - __init__.py
  - factor_research.py
    - momentum / volatility / value のファクター計算
  - feature_exploration.py
    - 将来リターン、IC、統計サマリー等
- strategy/
  - __init__.py
  - feature_engineering.py
    - features テーブル作成ロジック（Z スコア正規化、ユニバースフィルタ）
  - signal_generator.py
    - final_score 計算、BUY/SELL シグナル生成、signals テーブルへの保存
- execution/
  - __init__.py
  - （発注実装層は今後の実装箇所。現状はスキーマ主体）
- monitoring/ (プロジェクトに含まれる場合)
  - （監視・アラート用の DB / ロジック想定）

各モジュールはドキュメント文字列で設計方針や入出力、冪等性・エラーハンドリングについて詳細に記述しています。実装の詳細は該当ファイルの docstring を参照してください。

---

## 開発上の注意・ベストプラクティス

- ルックアヘッドバイアス回避のため、すべての戦略・ファクター計算は target_date 当日以前のデータのみを参照するように実装されています。コード変更時はこの前提が崩れないか確認してください。
- DuckDB のトランザクションや ON CONFLICT を利用した冪等保存を多用しています。テストでインメモリ(":memory:") を使うと高速に検証できます。
- J-Quants の API レート制限（120 req/min）に合わせた RateLimiter を実装済みです。クライアント実装を変更する場合はレート制御に注意してください。
- RSS パーサは defusedxml を使用し、SSRF 対策や受信サイズチェックを行っています。外部フィード追加時はソースの安全性を考慮してください。
- settings（config.py）のプロパティはいくつか必須値を要求します。テストでは環境変数をモックするか `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env の自動読み込みを抑制してください。

---

この README はコードベースの主要機能・使い方を要約したものです。より詳細な設計資料（StrategyModel.md / DataPlatform.md / Research 文書等）がある場合はそちらも合わせて参照してください。質問や補足があれば具体的なユースケース（例: ETL のカスタム日付範囲、weight のチューニング、ニュースソース追加など）を教えてください。具体例に沿った README の追記やサンプルスクリプトを作成します。