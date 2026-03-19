# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システムのライブラリ群です。データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、監査・実行レイヤーの土台を提供し、研究／本番まで一貫して利用できるよう設計されています。

主な設計方針：
- ルックアヘッドバイアスを防ぐため、各処理は対象日時点のデータのみ参照します。
- DuckDB をコアDBとして用い、IDEMPOTENT（冪等）な保存を重視します。
- 外部API呼び出し（例: J-Quants）のレート制御・リトライ・トークンリフレッシュを備えます。
- 本番（live）／ペーパー（paper_trading）／開発（development）を環境変数で切替可能。

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価・財務・カレンダー等）
  - RSS ニュース収集・前処理・銘柄抽出
  - DuckDB スキーマ定義・初期化（raw / processed / feature / execution レイヤ）
  - ETL パイプライン（日次差分更新・バックフィル・品質チェック）

- 研究 / 解析
  - ファクター計算（Momentum / Volatility / Value 等）
  - 前方リターン計算、IC（Information Coefficient）計算、統計サマリー

- 戦略
  - 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ）
  - シグナル生成（コンポーネントスコア合成、Bear レジーム抑制、BUY/SELL 判定）

- ニュース処理
  - RSS フィード取得（SSRF対策、サイズ制限、gzip対応）
  - 記事ID生成（URL 正規化＋SHA256）
  - raw_news / news_symbols への冪等保存

- 実行 / 監査（基盤）
  - signal / order / execution / positions などの実行レイヤ用スキーマ
  - 監査ログ用テーブル（signal_events / order_requests / executions）

---

## 必要条件

- Python 3.10 以上（typing の `|` 演算子等を使用）
- 主要依存（例）:
  - duckdb
  - defusedxml
- 実行環境に応じて追加ライブラリが必要になる場合があります（HTTP 暗号化や Slack 通知など）。

（パッケージ化時には requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順（開発向け）

1. リポジトリをクローンし、仮想環境を作成する（例）:
   ```bash
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール:
   ```bash
   pip install -U pip
   pip install duckdb defusedxml
   # development 用に editable install
   pip install -e .
   ```

3. 環境変数を設定（.env をプロジェクトルートに置くと自動で読み込まれます）。
   - 自動読み込みは OS 環境変数 > .env.local > .env の順で適用されます。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. DuckDB スキーマを初期化:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # デフォルト data/kabusys.duckdb
   ```

---

## 必要な環境変数

必須（アプリが期待する主要な環境変数）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注連携を行う場合）
- SLACK_BOT_TOKEN — Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するフラグ（"1"で無効）
- KABU_API_BASE_URL — kabu API のエンドポイント（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要なサンプル）

以下はライブラリの代表的な利用フロー例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL 実行（市場カレンダー取得 → 株価/財務取得 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定しなければ today が使われます
  print(result.to_dict())
  ```

- 特徴量作成（features テーブルへ書き込む）
  ```python
  from kabusys.strategy import build_features
  from datetime import date

  cnt = build_features(conn, date(2024, 1, 10))
  print(f"built features: {cnt}")
  ```

- シグナル生成（signals テーブルへ書き込む）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date

  total = generate_signals(conn, date(2024, 1, 10))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  known_codes = {"7203", "6758", "9984"}  # 事前に known_codes を用意
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J-Quants からのデータ取得（低レベル）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  token = get_id_token()  # settings.jquants_refresh_token を使用して id_token を取得
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,10))
  ```

注:
- API 呼び出しは内部でレート制御・リトライ・401 トークンリフレッシュを行います。
- 各処理は冪等に実装されているため、何度実行しても重複データが上書きされます（DuckDB 側の ON CONFLICT 等で担保）。

---

## ディレクトリ構成（主要ファイル・モジュール）

（プロジェクトルートの `src/kabusys/` 配下）

- __init__.py
  - パッケージのエントリポイント（__version__ = "0.1.0"）

- config.py
  - 環境変数・設定読み込み（.env 自動ロード、Settings クラス）

- data/
  - jquants_client.py: J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py: RSS 取得・前処理・raw_news 保存・銘柄抽出
  - schema.py: DuckDB スキーマ定義と init_schema/get_connection
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - calendar_management.py: market_calendar 管理（営業日判定、更新ジョブ）
  - audit.py: 監査ログ用テーブル DDL / 初期化（signal_events / order_requests / executions）
  - features.py: data.stats の公開ラッパ

- research/
  - factor_research.py: モメンタム／ボラティリティ／バリュー等のファクター計算
  - feature_exploration.py: 前方リターン計算、IC／統計サマリー
  - __init__.py: 研究系関数の再エクスポート

- strategy/
  - feature_engineering.py: ファクターの正規化・ユニバースフィルタ・features への保存
  - signal_generator.py: final_score 計算、BUY/SELL シグナル生成、signals への保存
  - __init__.py: build_features / generate_signals の公開

- execution/
  - （発注・order 管理などの実装が配置される想定。現在はパッケージ面での名前空間あり）

- monitoring/
  - （監視・アラート機能などを配置する想定）

---

## 開発上の注意点 / 実装メモ

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml の位置）を基準に行われます。CWD に依存しません。
- DuckDB のファイルは既定で `data/kabusys.duckdb`。初回は `init_schema()` を必ず実行してテーブルを作成してください。
- J-Quants のリクエストにはモジュールレベルでトークンキャッシュとレート制限があり、ページネーション処理でもトークンを共有します。
- RSS 取得は SSRF 対策、gzip サイズ制限、XML パースの防御（defusedxml）など安全性を考慮しています。
- 戦略部分はルックアヘッド防止のため、全て target_date 時点のデータのみを参照します。
- ログレベルや環境（development / paper_trading / live）は環境変数で切替可能です。

---

ご不明点や README に追加してほしいサンプル（CI、テスト実行方法、Docker 化の手順など）があればお知らせください。