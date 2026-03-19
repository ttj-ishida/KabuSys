# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。J‑Quants API から市場データ・財務データ・カレンダーを取得し、DuckDB に保存。リサーチ用のファクター計算・特徴量生成・シグナル生成・ニュース収集・カレンダー管理・ETL パイプライン等を提供します。

## 主な特徴
- J-Quants API クライアント（ページネーション・トークン自動更新・レート制御・リトライ）
- DuckDB ベースのデータスキーマと初期化ユーティリティ（冪等）
- 日次 ETL パイプライン（差分更新、バックフィル、品質チェックのフック）
- ファクター計算（モメンタム、バリュー、ボラティリティ、流動性など）
- クロスセクション Z スコア正規化ユーティリティ
- 特徴量生成（ユニバースフィルタ、Z スコアクリップ、features テーブルへの UPSERT）
- シグナル生成（複数ファクターの重み付け、AI スコア統合、BUY/SELL の冪等保存）
- ニュース収集（RSS 取得、SSRF 対策、記事正規化、銘柄抽出、raw_news 保存）
- マーケットカレンダー管理（JPX カレンダー取得と営業日判定）
- 監査ログ（signal → order → execution のトレーサビリティ用スキーマ）
- テストや開発向けに自動 .env ロード機能（プロジェクトルートから .env/.env.local を読み込み）

---

## 機能一覧（モジュール別）
- kabusys.config
  - 環境変数読み込み（.env/.env.local、自動ロード。無効化フラグあり）
  - 必須変数取得と検証（環境・ログレベル等）
- kabusys.data
  - jquants_client: API 取得 / DuckDB 保存（raw_prices, raw_financials, market_calendar 等）
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得、前処理、raw_news 保存、銘柄紐付け
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - features / stats: Z スコア正規化など
  - audit: 監査ログスキーマ（signal_events / order_requests / executions 等）
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials 参照）
  - feature_exploration: 将来リターン計算, IC 計算, 統計サマリ
- kabusys.strategy
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, threshold, weights)
- kabusys.execution
  - （発注層の実装用プレースホルダ）
- kabusys.monitoring
  - （監視・アラート関連の想定領域）

---

## 動作要件
- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS）

（プロジェクトが配布される場合は pyproject.toml / requirements.txt を参照してください）

---

## インストール（開発環境）
ローカルで編集しながら使う想定の手順例:

1. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```

3. パッケージを編集可能モードでインストール（もしパッケージ化済みなら）
   ```
   pip install -e .
   ```

---

## 環境変数 / .env
自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（アプリケーション起動時に必要になる可能性がある環境変数）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API パスワード（execution を使う場合）
- SLACK_BOT_TOKEN: Slack 通知用トークン（監視/通知）
- SLACK_CHANNEL_ID: Slack チャネル ID

任意（デフォルト値あり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite path for monitoring.db（デフォルト: data/monitoring.db）

例 .env（骨子）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（DB 初期化・基本操作例）

1. DuckDB スキーマを初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   - ":memory:" を指定すればインメモリ DB になります（テスト向け）。

2. 日次 ETL を実行（市場カレンダー・株価・財務データ取得）
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   # conn は init_schema で作成した接続
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量生成（features テーブルの作成）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   n = build_features(conn, target_date=date.today())
   print(f"features upserted: {n}")
   ```

4. シグナル生成（signals テーブルの書き込み）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals generated: {total}")
   ```

5. ニュース収集ジョブの実行
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes は銘柄抽出に使う有効な銘柄コードのセット（例: {'7203','6758',...}）
   res = run_news_collection(conn, known_codes=set())
   print(res)
   ```

6. カレンダー更新バッチ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

---

## 使い方の注意点
- J-Quants の API レート制限（120 req/min）を内部で尊重しますが、大量の並列処理を行わないでください。
- get_id_token は内部で自動リフレッシュを行います。401 受信時に1回だけリフレッシュして再試行します。
- ETL の差分ロジックは DB の最終取得日を基に date_from を自動算出します（バックフィル日数あり）。手動で範囲を指定することも可能です。
- feature / signal の処理はルックアヘッドバイアス回避のため target_date 時点までのデータのみを用いる設計になっています。
- DuckDB のスキーマは冪等的（既存テーブルは上書きしない）。init_schema を繰り返し呼んでも安全です。
- ニュース収集では SSRF 対策や受信サイズ上限、XML パースの堅牢化（defusedxml）を行っています。

---

## ディレクトリ構成（主要ファイル）
（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - features.py
    - stats.py
    - audit.py
    - ...（quality 等の関連モジュールが別ファイルとして想定）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  # （モジュールがあればここに置かれる想定）

---

## 開発／テストのヒント
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から行われます。テスト時に環境影響を避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の ":memory:" を使うと単体テストが簡単になります。
- news_collector の外部ネットワーク呼び出しや jquants_client._urlopen などはモックしやすい設計になっています。

---

もし README に加えたい動作例、.env.example の自動生成、CI 用のスクリプト例、あるいは execution 層のサンプル実装が必要であれば教えてください。必要に応じて追記します。