# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（研究・データ基盤・戦略・実行層の基礎実装）。

このリポジトリは以下の機能群を提供します：
- J-Quants API からのマーケットデータ・財務データ取得クライアント（ページネーション・リトライ・トークン自動更新・レート制御対応）
- DuckDB を使ったデータスキーマ定義・初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック呼び出し）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・サイズ上限・XML 攻撃対策）
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ・features テーブルへの UPSERT）
- シグナル生成（ファクター・AI スコア統合、BUY/SELL 判定、日付単位の冪等書き込み）
- マーケットカレンダー管理・営業日ロジック
- 監査ログ用スキーマ（signal → order_request → executions のトレース）

---

## 機能一覧（概要）

- data/
  - jquants_client: J-Quants API クライアント（トークン取得、ページネーション、保存ユーティリティ）
  - schema: DuckDB スキーマの DDL と初期化（raw/processed/feature/execution 層）
  - pipeline: 日次 ETL（calendar / prices / financials）と差分ロジック、結果オブジェクト
  - news_collector: RSS 取得 → raw_news 保存、銘柄抽出
  - calendar_management: market_calendar の更新、営業日判定ユーティリティ
  - stats: Zスコア正規化などの共通統計処理
- research/
  - factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算
  - feature_exploration: forward returns / IC / summary 等の解析ユーティリティ
- strategy/
  - feature_engineering: 生ファクターの正規化、ユニバース適用、features テーブルへの保存（冪等）
  - signal_generator: features と ai_scores を統合して final_score を計算、BUY/SELL を生成して signals テーブルへ保存（冪等）
- config: 環境変数の自動読み込み (.env / .env.local の読み込み順序)、必須チェック、設定ラッパー
- execution / monitoring: （プレースホルダ／パッケージエクスポート用）

---

## 前提・必須ソフトウェア

- Python 3.10 以上（構文に | 型合成等を使用しているため）
- pip
- 必要パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - defusedxml
  - （プロジェクトで追加パッケージがある場合は requirements.txt を参照）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

```
git clone <repo-url>
cd <repo>
```

2. 仮想環境を作成して依存をインストール

```
python -m venv .venv
source .venv/bin/activate
pip install -e .    # パッケージ化されていれば開発インストール
# または最低限:
pip install duckdb defusedxml
```

3. 環境変数（.env）を準備

ルートに `.env`（および必要なら `.env.local`）を配置します。利用される主要な環境変数:

- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
- KABU_API_PASSWORD=<kabu_password>
- KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN=<slack_bot_token>
- SLACK_CHANNEL_ID=<slack_channel_id>
- DUCKDB_PATH=data/kabusys.duckdb  （省略可、デフォルト有り）
- SQLITE_PATH=data/monitoring.db    （省略可）
- KABUSYS_ENV=development|paper_trading|live  （省略時: development）
- LOG_LEVEL=INFO|DEBUG|...  （省略時: INFO）

注意:
- パッケージはプロジェクトルート（.git や pyproject.toml のあるディレクトリ）を自動的に探索して `.env` を読み込みます。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

4. DuckDB スキーマ初期化

Python REPL やスクリプトから初期化できます。例:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

この処理で必要なテーブルとインデックスが作成されます（冪等）。

---

## 使い方（主要なワークフロー例）

以下は代表的なユースケースの呼び出し例です。実運用ではスケジューラ（cron / Airflow 等）から呼ぶことを想定しています。

1) 日次 ETL 実行（市場カレンダー → 価格 → 財務 → 品質チェック）

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を渡さなければ今日の日付を使用
print(result.to_dict())
```

2) 特徴量の構築（features テーブルへの書き込み）

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, date(2024, 1, 10))
print(f"Features upserted: {count}")
```

3) シグナル生成（features と ai_scores を使って signals に書き込む）

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
num_signals = generate_signals(conn, date(2024, 1, 10))
print(f"Signals written: {num_signals}")
```

4) ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードのセット（例: {'7203','6758',...}）
result = run_news_collection(conn, known_codes={'7203','6758'})
print(result)  # {source_name: saved_count}
```

5) J-Quants からのデータ取得（生データフェッチ & 保存）

jquants_client を直接呼んで fetch → save することも可能です。一般的には pipeline.run_* がラップします。

---

## 設定と環境変数

設定は主に環境変数で行います。config.Settings クラスがそれらをラップしており、必須項目に未設定があると起動時に ValueError を投げます。主な必須キー:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

任意・デフォルト値のあるキー:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト localhost:18080/kabusapi）
- DUCKDB_PATH / SQLITE_PATH: DB のファイルパス（デフォルトあり）
- LOG_LEVEL: ログレベル（デフォルト INFO）

---

## ディレクトリ構成（主要ファイル）

下記はパッケージ内の主なファイル・モジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント (fetch/save)
    - news_collector.py       — RSS ニュース収集／保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL（run_daily_etl / run_prices_etl 等）
    - features.py             — zscore_normalize の再エクスポート
    - calendar_management.py  — market_calendar 管理 / 営業日ユーティリティ
    - audit.py                — 監査ログ用スキーマ（signal / order / execution）
    - stats.py                — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — forward returns, IC, summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py  — 特徴量作成・正規化・ユニバースフィルタ
    - signal_generator.py     — final_score 計算・BUY/SELL 生成
  - execution/                — 実行層（プレースホルダ）
  - monitoring/               — 監視・モニタリング（プレースホルダ）

---

## 実装上の注意点・設計意図（抜粋）

- 冪等性: DB への保存は ON CONFLICT / トランザクションを用い、同一日付分は日付単位で置換する設計（UPSERT／DELETE+INSERT パターン）。
- ルックアヘッドバイアス対策: 戻り値に fetched_at を付与し、feature/signal の計算は target_date 時点の「利用可能データ」のみを前提とする。
- API 呼び出し: J-Quants はレート制限に合わせた固定間隔スロットリング、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュを備える。
- ニュース収集: SSRF 対策、XML の安全パーシング、サイズ上限、トラッキングクエリ除去、記事ID は正規化 URL の SHA-256 による短縮ハッシュを使用して冪等性を確保。
- カレンダー: market_calendar がない場合は土日フォールバック。DB に存在する日付は優先する設計で next/prev_trading_day 等を一貫して扱う。

---

## テスト・デバッグに便利なポイント

- env 自動ロードの無効化:
  - テストコード等で .env に依存せずに設定を差し替えたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のインメモリ利用:
  - テスト時は `init_schema(":memory:")` を使うことで一時的な DB を作成できます。
- jquants_client の HTTP 呼び出しは _request を通すため、モックすることで API 依存のテストが可能です。
- news_collector._urlopen やその他の内部関数はテスト用に差し替え（モック）可能なように実装されています。

---

## トラブルシューティング（よくある問題）

- 環境変数の未設定による起動エラー:
  - config.Settings の必須プロパティ（JQUANTS_REFRESH_TOKEN など）が未設定だと ValueError が発生します。`.env` を正しく配置しているか確認してください。
- DuckDB 初期化でディレクトリがない:
  - init_schema は親ディレクトリを自動作成しますが、ファイルパス指定に誤りがないか確認してください。
- J-Quants API の 401 / rate-limit:
  - jquants_client は 401 を検出するとリフレッシュを試みます。繰り返し 401 が返る場合はリフレッシュトークンが無効の可能性があります。
  - rate-limit に合わせたスロットリングを行いますが、環境によっては過剰な並列呼び出しに注意してください。

---

## 参考

- コード内ドキュメント（docstring）に各モジュールの設計方針・処理フローが詳述されています。実装や拡張を行う場合は docstring を参照してください。

---

もし README に含めたい追加の情報（CI/CD、ライセンス、具体的な運用スケジュール、Slack 通知の使い方など）があれば教えてください。必要に応じて追記します。