# KabuSys

日本株向けの自動売買基盤コンポーネント群です。データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、DuckDB スキーマ・監査ログなどのユーティリティを含みます。

## プロジェクト概要
KabuSys は以下のレイヤーを想定したシステムです。

- データ取得（J-Quants API）と生データ保存（raw layer）
- ETL による整形済みデータ作成（processed layer）
- 戦略・AI 用特徴量の作成・保存（feature layer）
- シグナル生成と発注トラッキングのためのスキーマ（execution / audit layer）
- RSS ベースのニュース収集（news）と銘柄紐付け

設計上のポイント：
- DuckDB を用いたローカル DB（オンディスク／インメモリ）管理
- ファクター計算・シグナル生成はルックアヘッドバイアスを避ける設計
- J-Quants API のレート制御・リトライ・トークン自動更新を備えたクライアント
- 冪等性（ON CONFLICT 等）を意識した DB 書き込み

## 主な機能一覧
- data/
  - jquants_client: J-Quants API から日足・財務・カレンダーを取得、DuckDB へ保存するユーティリティ
  - pipeline: 差分 ETL（市場カレンダー・日足・財務）と品質チェックの統合
  - schema: DuckDB のスキーマ初期化（raw / processed / feature / execution / audit）
  - news_collector: RSS を取得して raw_news に保存、記事→銘柄の紐付け
  - calendar_management: 営業日判定 / next/prev 営業日等のユーティリティ
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン、IC、ファクター統計サマリの探索ツール
- strategy/
  - feature_engineering: research の生ファクターを正規化・合成して features テーブルに保存
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成
- config: .env /環境変数の読み込みと settings（必要な環境変数をラップ）
- execution / monitoring: （将来の発注実装やモニタリング用のプレースホルダ）

## 必要な環境変数
config.Settings で参照される主要な環境変数（必須は README 中に明記）:

必須
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルト値あり）
- KABUSYS_ENV — one of development, paper_trading, live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動 .env ロード:
- パッケージはプロジェクトルートから `.env` → `.env.local` の順で自動ロードします（環境変数優先）。
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

## セットアップ手順（開発）
1. Python 3.9+ をインストール
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール（プロジェクトに requirements.txt がない場合は主要依存のみ）
   - pip install duckdb defusedxml
   - その他（用途に応じて）: requests 等を追加する場合があります
4. 環境変数を準備
   - プロジェクトルートに `.env` を作成（.env.example があれば参照）
   - 必須トークンを設定（例）:
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - KABU_API_PASSWORD=xxxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
5. DuckDB スキーマ初期化（スクリプト例は下段「使い方」を参照）

## 使い方（簡単な例）
以下は Python スクリプトから各主要機能を呼び出す最小例です。

1) DuckDB スキーマの初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行（市場カレンダー・日足・財務を差分取得）:
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）構築:
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"upserted features: {count}")
```

4) シグナル生成:
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema(settings.duckdb_path)
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {n}")
```

5) ニュース収集ジョブ（既知銘柄セットを渡して紐付けする例）:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

運用例:
- 上記の ETL / feature / signal 生成は cron やスケジューラ（Airflow 等）で日次実行すると良いです。
- J-Quants のレート制限や token ルーティンは jquants_client が制御します。

## 実装上の注意点
- DuckDB へは冪等的な INSERT（ON CONFLICT または INSERT ... RETURNING）で保存することを前提としています。
- ファクター計算・シグナル生成は target_date 時点のデータのみを参照することで将来情報の混入を防いでいます。
- RSS 取得は SSRF 対策や応答サイズ制限、XML の安全パーサ（defusedxml）を使っています。
- settings は実行時に環境変数を参照して必要な値を取得します。未設定の必須変数は ValueError を投げます。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロード / Settings クラス
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save）
    - pipeline.py — ETL（run_daily_etl など）
    - schema.py — DuckDB スキーマ定義と init_schema
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - features.py — data.stats の再エクスポート
    - calendar_management.py — market_calendar の更新・営業日ユーティリティ
    - news_collector.py — RSS 取得・前処理・DB 保存（raw_news, news_symbols）
    - audit.py — 監査ログ用スキーマ定義（signal_events, order_requests, executions 等）
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — forward returns / IC / factor summary
  - strategy/
    - __init__.py
    - feature_engineering.py — features の構築（build_features）
    - signal_generator.py — final_score 計算と signals テーブルへの書き込み（generate_signals）
  - execution/ — 発注関連の実装プレースホルダ
  - monitoring/ — 監視・記録関連のプレースホルダ

（上記はソース内 docstring に基づく簡易サマリです）

## 依存関係（主なもの）
- Python 標準ライブラリ
- duckdb
- defusedxml
- （ネットワーク呼び出しに urllib を使用しているため requests は必須ではありませんが、運用で使う場合は追加可能）

requirements.txt を作る際は最低限:
- duckdb
- defusedxml

を含めてください。

## 開発・寄稿
- バグ修正・機能追加は PR をお願いします。ユニットテスト・型注釈・ログメッセージの整合性を重視しています。
- 設計ドキュメント（DataPlatform.md / StrategyModel.md 等）に沿う実装ポリシーが随所にコメントされています。追加の仕様に合わせて各モジュールを拡張してください。

---

何か特定の導入手順（Docker 化、CI 設定、具体的な cron 設定例）や、README に追加したい情報があれば教えてください。必要に応じてサンプルスクリプトやテンプレート .env.example も作成します。