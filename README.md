# KabuSys — 日本株自動売買システム (README)

KabuSys は日本株向けのデータパイプライン、特徴量計算、シグナル生成、ニュース収集、監査/スキーマ管理などを含む汎用ライブラリ群です。研究（research）→ データ処理（data）→ 戦略（strategy）→ 発注/実行（execution）という層を想定したモジュール設計がされています。

---

目次
- プロジェクト概要
- 機能一覧
- 動作環境・依存関係
- セットアップ手順
- 環境変数（.env）
- 使い方（基本的な利用例）
- ディレクトリ構成
- 補足 / トラブルシューティング

---

プロジェクト概要
- DuckDB をバックエンドに用いた日本株向けデータプラットフォームと戦略モジュールの集合体。
- J‑Quants API からのデータ取得、RSS ニュース収集、ファクター計算（モメンタム／ボラティリティ／バリュー等）、Z スコア正規化、戦略の最終スコア計算とシグナル生成、シグナル→オーダー→約定までの監査テーブル設計を含みます。
- ルックアヘッドバイアス対策、ETL の冪等性、API レート制御・リトライ、SSRF 対策など実運用を想定した実装方針が組み込まれています。

---

機能一覧
- 環境設定管理（.env 自動ロード、必須値チェック）
- DuckDB スキーマ定義・初期化（init_schema）
- J‑Quants API クライアント（レートリミット・リトライ・トークン自動更新）
  - 日次株価（OHLCV）取得
  - 財務データ取得
  - マーケットカレンダー取得
- ETL パイプライン（差分取得、バックフィル、品質チェックとの連携）
- ファクター計算（momentum / volatility / value）
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ、features テーブルへのUPSERT）
- シグナル生成（複合重み付け、Bear レジーム抑制、BUY/SELL の日次置換保存）
- ニュース収集（RSS フィード取得、前処理、raw_news 保存、銘柄抽出）
- 監査ログ（signal_events / order_requests / executions 等のDDL 定義）
- 汎用統計ユーティリティ（zscore_normalize, rank, calc_ic 等）

---

動作環境・依存関係
- Python 3.10 以上（型注釈で | 記法を使用）
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml
- その他：標準ライブラリ（urllib 等）を利用。実運用では追加の依存（Slack通知等）がある場合があります。

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# プロジェクトをパッケージ化している場合:
# pip install -e .
```

---

セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
2. 依存パッケージをインストール（上記参照）
3. 環境変数の用意
   - プロジェクトルートに `.env`（およびテスト用に `.env.local`）を配置することで自動的に読み込まれます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
4. DuckDB スキーマ初期化
   - デフォルトの DB パスは `data/kabusys.duckdb`（settings.duckdb_path）。明示的に初期化するには下記コードを実行します。

例: DB 初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH によって上書き可
conn = init_schema(settings.duckdb_path)
```

---

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須: 発注を行う場合）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須: Slack連携を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development / paper_trading / live)
- LOG_LEVEL: ロギングレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)

注意:
- Settings は環境変数が未設定の場合に ValueError を投げます（必須項目）。
- テスト時に .env の自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

使い方（基本的な利用例）

1) DuckDB の初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行（市場カレンダー、株価、財務データの差分取得・保存）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量の構築（features テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date(2024, 1, 5))
print(f"built features: {count}")
```

4) シグナル生成（signals テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import generate_signals

total = generate_signals(conn, target_date=date(2024, 1, 5))
print(f"signals written: {total}")
```

5) ニュース収集ジョブ（RSS から raw_news 保存 + 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使用する有効な銘柄コードの集合（例: {"7203","6758",...}）
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

6) J‑Quants データ取得（個別呼び出し）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,5))
saved = save_daily_quotes(conn, records)
print(f"saved {saved} price rows")
```

注意点:
- 各「日付単位の置換」操作（例: features / signals）は冪等に実装されています。target_date に対する既存行は削除され、新規挿入されます。
- API 呼び出しにはレート制限およびリトライロジックが入っています。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J‑Quants API クライアント（取得／保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義と init_schema
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - features.py            — features を再エクスポート
    - news_collector.py      — RSS ニュース取得・保存ロジック
    - calendar_management.py — 市場カレンダー管理・更新ジョブ
    - audit.py               — 監査ログ用 DDL
    - pipeline.py            — ETL の実装（差分取得等）
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン/IC/統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — 特徴量合成・Zスコア正規化 → features へ保存
    - signal_generator.py    — final_score 計算・BUY/SELL シグナル生成
  - execution/                — 発注/実行層（将来的な拡張ポイント）
  - monitoring/              — 監視・モニタリング（SQLite 等、未実装箇所あり）

各モジュールには docstring と実装コメントが豊富に書かれており、設計意図やエラー処理方針（冪等性、トランザクション制御、ログレベルなど）が明示されています。

---

補足 / トラブルシューティング
- Python バージョン: 3.10 以上を推奨（PEP 604 の | 型を使用）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。CI やテストで自動ロードを回避するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB 接続時に権限やファイルパスの問題が出る場合はパスの親ディレクトリの作成権限を確認してください（init_schema は親ディレクトリを自動作成します）。
- J‑Quants API で 401 が返った場合、トークンを自動リフレッシュして再試行します。リフレッシュに失敗すると例外が発生しますので、`JQUANTS_REFRESH_TOKEN` の値を確認してください。
- RSS 収集では SSRF / XML Bomb / 大容量レスポンス対策等を実装していますが、外部 URL を扱うためネットワーク例外は必ずハンドルしてください。

---

開発者向けメモ
- 主要な公開 API:
  - kabusys.config.settings — アプリケーション設定（環境変数ラッパー）
  - kabusys.data.schema.init_schema / get_connection
  - kabusys.data.pipeline.run_daily_etl
  - kabusys.strategy.build_features
  - kabusys.strategy.generate_signals
  - kabusys.data.news_collector.run_news_collection
- 単体テストを書く際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を有効化して環境依存を切り離し、DuckDB の `:memory:` を使うと便利です。

---

以上が本リポジトリの README です。必要があれば、.env.example のテンプレートや、具体的な CI / デプロイ手順、Slack 通知や発注フロー（kabu ステーション統合）の利用例を追記します。どの部分を詳細化したいか教えてください。