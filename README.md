# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）の簡易 README。

このリポジトリは市場データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ管理などの基盤機能を提供します。戦略層と発注層は分離されており、研究環境（research）で作成したファクターを本番用に正規化して利用できます。

---

## 概要

- パッケージ名: kabusys
- 目的: 日本株のデータ取得・加工・特徴量生成・シグナル生成のための基盤ライブラリ
- 主な技術:
  - DuckDB（オンディスク / インメモリ DB）
  - J-Quants API クライアント（rate limit / retry / token refresh 対応）
  - RSS ベースのニュース収集（SSRF 対策・XML サニタイズ）
  - ファクター計算（momentum / volatility / value 等）
  - 特徴量正規化（Z スコア）とシグナル生成ロジック
- Python: 推奨 Python >= 3.10（PEP 604 の型記法や list[str] 等を利用）

---

## 機能一覧

主な提供機能（モジュール別）

- kabusys.config
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local）と Settings クラス
- kabusys.data.jquants_client
  - J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
  - レート制限、リトライ、401 の自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT 対応）
- kabusys.data.schema
  - DuckDB のスキーマ定義と初期化（raw / processed / feature / execution レイヤ）
  - init_schema(), get_connection()
- kabusys.data.pipeline
  - 日次 ETL（差分取得、バックフィル、品質チェック呼び出し）
  - 個別 ETL ジョブ（価格、財務、カレンダー）
- kabusys.data.news_collector
  - RSS フィード取得・前処理・raw_news 保存・銘柄抽出
  - SSRF 対策、XML サニタイズ、トラッキングパラメータ除去
- kabusys.research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 解析ユーティリティ（forward returns, IC, factor summary, rank）
- kabusys.strategy
  - build_features(conn, target_date): 生ファクターの統合、正規化、features テーブルへの UPSERT
  - generate_signals(conn, target_date, ...): features / ai_scores / positions を元に BUY/SELL シグナル生成
- kabusys.data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）

---

## セットアップ手順

1. Python を準備
   - Python 3.10 以上を推奨

2. パッケージ依存をインストール
   - 必要なパッケージの例:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

3. ソースをインストール（任意）
   - 開発中は editable install：
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション等の API パスワード（発注用）
- SLACK_BOT_TOKEN: Slack への通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID: 通知先の Slack チャンネル ID

オプション（デフォルトあり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で自動 .env ロードを無効化
- KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと .env の自動ロードを止め、テスト等で明示的に環境変数をセットできます。
- DUCKDB_PATH: データベースファイルのパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視系（monitoring）で SQLite を使う場合のパス

.env の例（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易サンプル）

以下は最低限の動作例です。実運用ではログ設定・エラーハンドリング等を適切に追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ファイル未作成ならディレクトリも作成されます
```

2) 日次 ETL を実行（J-Quants トークンは settings から取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を渡さないと今日が対象
print(result.to_dict())
```

3) 特徴量（features）を構築
```python
from kabusys.strategy import build_features
from datetime import date

cnt = build_features(conn, date(2024, 1, 10))
print(f"features upserted: {cnt}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

n = generate_signals(conn, date(2024, 1, 10))
print(f"signals created: {n}")
```

5) RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出に使う有効な銘柄コードのセット（例: {"7203","6758",...}）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # ソースごとの新規保存件数
```

6) J-Quants からの日足取得を直接呼ぶ（テスト用）
```python
from kabusys.data import jquants_client as jq
from datetime import date

records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
jq.save_daily_quotes(conn, records)
```

注意: 上記関数の多くは DuckDB 接続を受け取り、features / prices_daily / raw_financials / market_calendar などのテーブルが存在する前提です。初回は init_schema() を実行してください。

---

## ディレクトリ構成（主なファイルと簡単な説明）

（リポジトリを src 配下で扱う前提のツリー）

- src/kabusys/
  - __init__.py
    - パッケージ初期化。公開モジュールを定義。
  - config.py
    - 環境変数の自動読み込み、Settings クラス（各種設定値）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック）
    - schema.py
      - DuckDB スキーマ定義と init_schema()
    - pipeline.py
      - 日次 ETL パイプラインと個別 ETL ジョブ
    - news_collector.py
      - RSS 取得・前処理・DB 保存・銘柄抽出
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - features 用ユーティリティ（zscore の再エクスポート）
    - calendar_management.py
      - market_calendar の管理・営業日判定ロジック・更新ジョブ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions 等）
    - pipeline.py
      - ETL 実行の中心（上記参照）
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value の計算
    - feature_exploration.py
      - IC 計算・将来リターン・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - 生ファクターの統合・正規化・features テーブルへの UPSERT
    - signal_generator.py
      - final_score 計算と BUY/SELL シグナル生成
  - execution/
    - __init__.py
    - （発注処理・kabu API 連携などを格納する想定の空パッケージ）
  - monitoring/
    - （監視・メトリクス系を格納する想定の空パッケージ）

---

## 設計上の注意点 / ポイント

- ルックアヘッドバイアス対策
  - features / signals / research の各処理は target_date 時点の情報のみを使用するよう設計されています。
  - データ取得では fetched_at を UTC で記録し「いつそのデータが利用可能になったか」を追跡できます。
- 冪等性
  - J-Quants から得たデータの保存は ON CONFLICT / UPSERT を使い、複数回の実行でも重複挿入が発生しないようにしています。
- レート制限・リトライ
  - jquants_client は固定間隔スロットリングと指数バックオフを備えています。401 はトークン再取得して 1 回だけリトライします。
- セキュリティ
  - news_collector は SSRF 対策、defusedxml による XML サニタイズ、トラッキングパラメータ除去などを実装しています。
- データ品質
  - pipeline.run_daily_etl は ETL 後に品質チェックを呼び出す仕組みを持ち、欠損やスパイクの検出を行います（quality モジュールを利用）。

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索して行います。テスト等で自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のテーブルが存在しないエラー
  - まず `init_schema(db_path)` を実行してスキーマを作成してください。get_connection() は既存 DB に接続するのみで初期化は行いません。
- J-Quants の認証失敗
  - `JQUANTS_REFRESH_TOKEN` が正しく設定されているか確認してください。jquants_client は自動的に ID トークンをリフレッシュしますが、何度も 401 が返る場合はトークンが無効な可能性があります。

---

必要に応じて README に実行スクリプト例、CI 設定、テスト手順、より詳細な API 仕様（各テーブル定義や StrategyModel.md へのリンク等）を追記できます。追加したい項目があれば教えてください。