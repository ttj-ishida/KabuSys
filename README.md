# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python ライブラリ群です。データ取得（J-Quants）、ETL、データ品質チェック、特徴量計算、ニュース収集、監査ログ管理など、戦略開発〜運用に必要な基盤機能を提供します。

主な設計思想は次のとおりです。
- DuckDB を中心としたローカルデータレイク（冪等性を保った保存）
- J-Quants API からの差分取得と堅牢なリトライ／レート制御
- Research 環境では外部 API や発注機能へアクセスしない（安全）
- XML/HTTP 関連に対するセキュリティ考慮（SSRF、XML Bomb 等）
- 各モジュールはテスト容易性と再利用性を重視して設計

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` の自動読み込み（必要に応じて無効化可能）
  - 必須環境変数のラップ（`kabusys.config.settings`）

- データ取得・保存（J-Quants）
  - 株価日足（OHLCV）取得と DuckDB への冪等保存
  - 四半期財務データ取得と保存
  - JPX マーケットカレンダー取得と保存
  - レート制限（120 req/min）、リトライ、ID トークン自動更新

- ETL パイプライン
  - 差分取得（最終取得日に基づく自動範囲算出）
  - カレンダー取得、株価・財務データ取得、品質チェックを連続実行
  - ETL 結果を表す `ETLResult`（品質問題・エラーの集約）

- データ品質チェック
  - 欠損データ検出（OHLC 欠損）
  - スパイク（急騰・急落）検出
  - 重複チェック（主キー重複）
  - 日付整合性チェック（未来日付、非営業日のデータ）

- ニュース収集
  - RSS フィード取得（gzip 対応、SSRF 防止、トラッキングパラメータ除去）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等性を確保
  - raw_news / news_symbols の冪等保存

- 研究用（Research）
  - モメンタム・バリュー・ボラティリティ等のファクター計算（DuckDB を参照）
  - 将来リターン計算、IC（Spearman ρ）計算、統計サマリー
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）

- スキーマ / 監査ログ
  - DuckDB のスキーマ定義と初期化 (`kabusys.data.schema.init_schema`)
  - 監査ログ（signal_events, order_requests, executions）用テーブルと初期化補助

## 必要条件

- Python 3.10 以上（PEP 604 型注釈等を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール例:
```bash
pip install duckdb defusedxml
# もしパッケージをローカル開発インストールするなら:
# pip install -e .
```

（プロジェクトをパッケージ化している場合は requirements を参照してください）

## セットアップ手順

1. リポジトリをクローン / checkout
2. 仮想環境を作成して有効化（任意）
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定
   - `.env` または `.env.local` をプロジェクトルートに作成できます。
   - 自動読み込みはデフォルトで有効。無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数例（最低限）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN : Slack 通知に使用（使用しない場合も設定可能）
- SLACK_CHANNEL_ID : Slack チャンネル ID（使用する場合）

その他（任意）:
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視DBなど（デフォルト: data/monitoring.db）

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

## 使い方（簡単な例）

以下は主要ユースケースの簡単な利用例です。

- DuckDB スキーマ初期化:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# これで必要なテーブルがすべて作成されます
```

- 日次 ETL の実行:
```python
from datetime import date
import duckdb
from kabusys.data import pipeline

conn = duckdb.connect("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集の実行:
```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes に有効銘柄コードのセットを渡すと記事→銘柄紐付けを行う
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

- J-Quants から日足データを直接取得して保存:
```python
from kabusys.data import jquants_client as jq
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

- 研究用ファクター計算:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
tm = date(2024, 1, 31)
mom = calc_momentum(conn, tm)
vol = calc_volatility(conn, tm)
val = calc_value(conn, tm)
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- データ品質チェック:
```python
from kabusys.data import quality
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for issue in issues:
    print(issue)
```

## 自動環境変数読み込みの挙動

- パッケージは起動時にプロジェクトルート（.git または pyproject.toml がある場所）を探索し、`.env`→`.env.local` の順に読み込みます。
- OS 環境変数が優先されます（`.env` は未設定キーのみ設定）。`.env.local` は既存 OS 環境変数を保護しつつ上書き可能です。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに有用）。

## ディレクトリ構成

以下はリポジトリ内の主要ディレクトリ / ファイルの概要（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得/保存/リトライ/レート制御）
    - news_collector.py
      - RSS ニュース収集・前処理・DB 保存
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize など統計ユーティリティ
    - pipeline.py
      - ETL パイプライン（run_daily_etl など）
    - quality.py
      - データ品質チェック
    - calendar_management.py
      - 営業日ロジック、calendar_update_job
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）初期化
    - etl.py (公開インターフェース)
    - features.py (公開インターフェース)
  - research/
    - __init__.py
      - 研究用ユーティリティ再エクスポート
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー、rank
    - factor_research.py
      - momentum/value/volatility ファクター計算
  - strategy/
    - __init__.py
    - （戦略モデルや戦略実行ロジックを置く場所）
  - execution/
    - __init__.py
    - （発注/ブローカー連携を置く場所）
  - monitoring/
    - __init__.py
    - （監視・アラート関連）

（上記一覧は現在の実装ファイルを抜粋したものです）

## セキュリティ・運用上の注意

- J-Quants の API トークンや kabuステーションのパスワードは厳重に管理してください（.env を git で管理しない）。
- ニュース取得では外部 URL を扱うため SSRF 対策や応答サイズチェックを実装していますが、運用環境で追加の制約（プロキシ、IP フィルタリング等）を検討してください。
- production / live 環境で発注を行う場合は十分なテストとリスク管理（paper_trading を使用した検証）を行ってください。
- DuckDB ファイルは定期的にバックアップしてください。

## 貢献・拡張

- Strategy / Execution 層は抽象化されているため、独自戦略の実装やブローカーインテグレーションを追加できます。
- 追加の品質チェックやデータソースを data パッケージに拡張する際は既存の ETL 設計方針（差分取得・冪等性）に合わせてください。

---

以上が本プロジェクトの README です。必要であれば、具体的なスクリプト例（systemd タイマーや cron 連携、CI/CD 用のワークフロー）や、より詳細な環境変数一覧・サンプル `.env.example` を追記できます。どの情報を追加しますか？