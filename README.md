# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
DuckDB をデータレイヤに用い、J-Quants から市場データ・財務情報・カレンダーを取得し、リサーチ→特徴量生成→シグナル生成→発注監査までの基本的なワークフローを提供します。

主な設計方針：
- ルックアヘッドバイアス防止（各処理は target_date 時点のデータのみを使用）
- ETL / 保存は冪等（ON CONFLICT / トランザクション）で実装
- 外部 API 呼び出しは専用クライアントで扱い、レート制限・リトライ・トークンリフレッシュを実装
- DuckDB ベースでローカル/軽量に動作

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / 保存
  - J-Quants クライアント（株価日足、財務データ、マーケットカレンダー）
  - raw データを DuckDB に冪等保存（raw_prices, raw_financials, market_calendar など）
- ETL パイプライン
  - 差分取得（最終取得日からの差分）、バックフィル、品質チェック統合（run_daily_etl）
- カレンダー管理
  - 営業日判定、next/prev 営業日、カレンダー更新ジョブ
- ニュース収集
  - RSS フィード収集、記事正規化、銘柄抽出、raw_news / news_symbols への保存
  - SSRF / XML Bomb / 大きすぎるレスポンス等に対する防御
- ファクター（リサーチ）
  - モメンタム / ボラティリティ / バリューなどのファクター計算（research/factor_research）
  - 将来リターン・IC 計算・統計サマリー（research/feature_exploration）
- 特徴量生成（strategy/feature_engineering）
  - 生ファクターを正規化（Zスコア）・ユニバースフィルタ適用し features テーブルへ保存
- シグナル生成（strategy/signal_generator）
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成し signals テーブルへ保存
- スキーマ / 監査
  - DuckDB のスキーマ初期化（data/schema.init_schema）
  - 発注 / 約定 / 監査向けテーブル群

---

## 前提条件

- Python 3.10+
- DuckDB
- defusedxml (RSS の安全なパースに使用)
- ネットワーク経由で J-Quants API にアクセス可能な環境（J-Quants の API トークンが必要）
- （kabuステーション 連携や Slack 通知を用いる場合はそれぞれの認証情報）

例: 必須ライブラリ（簡易）
- duckdb
- defusedxml

インストールは後述の手順参照。

---

## セットアップ手順

1. リポジトリをクローン／ワークツリーへ配置

2. 仮想環境作成（任意）
```bash
python -m venv .venv
source .venv/bin/activate
```

3. 依存パッケージをインストール
（requirements.txt がある場合はそちらを使ってください。無い場合は最低限以下をインストール）
```bash
pip install duckdb defusedxml
```

4. パッケージを開発モードでインストール（任意）
```bash
pip install -e .
```

5. 環境変数の設定
プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

主要な環境変数（README 用簡易一覧）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（実際に execution を使う場合）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（通知を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 等（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment (development / paper_trading / live)
- LOG_LEVEL: ログレベル (DEBUG/INFO/... 等)

.env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期化（DB スキーマ作成）

DuckDB のスキーマを初期化します。Python REPL から行う例:

```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
```

またはスクリプトで:
```bash
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

init_schema はテーブル作成を冪等に行います。

---

## 基本的な使い方（主要 API）

以下は代表的なワークフロー例です。各 API はモジュール関数として呼び出します（CLI は提供していないため、スクリプトやジョブとして利用してください）。

1) 日次 ETL（市場カレンダー・株価・財務データを取得）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")  # 初回は init_schema を使う
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量の構築（features テーブルに保存）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"built features: {count}")
```

3) シグナル生成（signals テーブルに保存）
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
num = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {num}")
```

4) ニュース収集ジョブ（RSS 取得・raw_news 保存・銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 開発 / 研究用機能

- research パッケージ内には IC 計算（calc_ic）、将来リターン計算（calc_forward_returns）、ファクター計算（calc_momentum / calc_volatility / calc_value）などがあり、リサーチ用途に利用できます。
- data.stats.zscore_normalize は特徴量正規化ユーティリティとして再利用可能。

---

## ロギング / 環境切替

- 環境切替は KABUSYS_ENV で行い、`development`, `paper_trading`, `live` が許容値です（設定ミスは例外になります）。
- LOG_LEVEL でログレベルを指定（DEBUG/INFO/…）。

---

## ディレクトリ構成（主要ファイル）

(プロジェクトの src 配下を元にした抜粋)

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 読み込みロジック含む）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存関数）
    - news_collector.py     — RSS 取得・正規化・保存
    - schema.py             — DuckDB スキーマ定義 / init_schema
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— カレンダー更新・営業日ロジック
    - features.py           — feature ユーティリティ（再エクスポート）
    - audit.py              — 監査ログ / 発注追跡用テーブル
  - research/
    - __init__.py
    - factor_research.py    — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py— 将来リターン・IC・サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py— 生ファクターの正規化・ユニバースフィルタ・features 書込
    - signal_generator.py   — final_score 計算、BUY/SELL 判定、signals 書込
  - execution/               — （発注 / execution 層の実装場所。今回の抜粋では空）
  - monitoring/              — （監視 / メトリクス系を置く想定の場所）

---

## 注意事項 / 運用上のヒント

- J-Quants API のレート制限 (120 req/min) を遵守するため、jquants_client では内部でスロットリングとリトライが実装されています。
- ETL は差分更新を行う設計ですが、運用でのバックフィルや API 側の訂正を吸収するための再取得ロジックが含まれています（backfill_days など）。
- features / signals テーブルへの書き込みは「日付単位の置換（削除→挿入）」をトランザクションにより原子性を保って行います。
- news_collector は外部フィードの扱いに慎重な設計（SSRF 検査、圧縮サイズ上限、defusedxml）を取り入れています。
- 本リポジトリは戦略や発注ロジックのスケルトンを多数含みます。実際の本番運用には追加のテスト、リスク管理、監査・復旧手順が必須です。

---

もし README に含めたい追加の使用例（cron ジョブ、Docker 化、CI/CD 設定、Slack 通知の具体的な使い方 など）があれば教えてください。必要に応じてサンプルスクリプトやテンプレート .env.example も作成します。