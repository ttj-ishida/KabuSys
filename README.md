# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants と連携したデータ取得、DuckDB によるスキーマ管理、特徴量計算・正規化、シグナル生成、ニュース収集、マーケットカレンダー管理などを提供します。

主な設計方針：
- ルックアヘッドバイアス対策（target_date 時点のデータのみを使用）
- DuckDB を用いた冪等（idempotent）な保存処理
- 外部 API のレート制御・リトライ・トークン自動更新
- Production / Paper / Dev を区別した設定管理

バージョン: 0.1.0

---

## 機能一覧

- 環境・設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートを探索）
  - 必須環境変数チェック

- データ取得・保存（J-Quants）
  - 株価日足（OHLCV）取得・ページネーション対応
  - 財務データ取得（四半期 BS/PL）
  - JPX マーケットカレンダー取得
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）

- データ基盤（DuckDB スキーマ）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - スキーマ初期化ユーティリティ（init_schema）

- ETL パイプライン
  - 差分更新（最終取得日に基づく）
  - backfill による後出し修正の吸収
  - 品質チェックフック（quality モジュールへの連携を想定）

- 研究用ファクター計算（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン・IC 計算・統計サマリー

- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクターの結合、ユニバースフィルタ、Z スコア正規化、features テーブルへの保存（冪等）

- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出
  - BUY / SELL シグナルの生成（Bear レジーム判定、ストップロス等）
  - signals テーブルへの書き込み（冪等）

- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、raw_news 保存、記事と銘柄の紐付け
  - SSRF・XML Bomb 対策、受信サイズ制限、トラッキングパラメータ除去

- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定、前後営業日検索、夜間カレンダー更新ジョブ

- 監査ログ（data.audit）
  - signal → order → execution のトレーサビリティ（UUID 系列）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の union 演算子 `|` を使用）
- DuckDB ライブラリ
- defusedxml（RSS パーサのセキュリティ対策）
- その他標準ライブラリのみで実装されている箇所が多いですが、実行する機能により追加パッケージが必要になることがあります。

例（仮想環境を作ってインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージをローカルで編集・使用する場合
pip install -e .
```

環境変数
- プロジェクトは .env / .env.local をプロジェクトルートから自動ロードします（CWD ではなくパッケージファイル位置から .git または pyproject.toml を探索してルートを決定）。
- 自動ロードを無効化する場合:
  - `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

必須環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知（もし利用する場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意・デフォルト:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live, デフォルト development)
- LOG_LEVEL (DEBUG / INFO / ... デフォルト INFO)

例 .env（プロジェクトルートに保存）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（代表的な操作例）

以下は Python REPL やスクリプトからの利用例です。適宜ログ設定やエラーハンドリングを追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルを作成してスキーマを初期化
```

2) 日次 ETL を実行（株価・財務・カレンダーの差分取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると today
print(result.to_dict())
```

3) 特徴量の作成（features テーブルへ upsert）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date(2025, 3, 1))
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルへ upsert）
```python
from datetime import date
from kabusys.strategy import generate_signals

total_signals = generate_signals(conn, target_date=date(2025, 3, 1))
print(f"signals generated: {total_signals}")
```

5) ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 銘柄抽出で参照する有効コードセット（省略可）
known_codes = {"7203", "6758", "9432"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar rows updated: {saved}")
```

Tips:
- ETL の id_token をテスト注入したい場合は run_* 関数に id_token 引数を渡せます。
- run_daily_etl は品質チェックに失敗しても処理を継続する設計（呼び出し元で結果を評価してください）。

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定の読み込み、Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
    - news_collector.py
      - RSS 収集・前処理・raw_news/ news_symbols 保存
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - calendar_management.py
      - market_calendar の管理・営業日判定・更新ジョブ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions 等）
    - features.py
      - zscore_normalize の公開ラッパ

  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value ファクター計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー、rank ユーティリティ

  - strategy/
    - __init__.py
    - feature_engineering.py
      - ファクター結合・ユニバースフィルタ・正規化・features 保存
    - signal_generator.py
      - final_score 計算、BUY/SELL シグナル生成、signals 保存

  - execution/
    - __init__.py
      - （発注・ブローカー連携のための実装を想定）

その他:
- pyproject.toml（プロジェクトルートにある想定。config._find_project_root は .git または pyproject.toml を探します）
- .env / .env.local（環境変数をここに定義）

各モジュールの詳細はソースコード内の docstring に仕様・設計方針・処理フローが書かれています。まずは schema.init_schema → pipeline.run_daily_etl → strategy.build_features → strategy.generate_signals の順で動かしてデータを流し、必要に応じて news_collector や calendar_update_job をスケジュールしてください。

---

## 注意点 / トラブルシューティング

- 環境変数が足りない場合、Settings のプロパティ呼び出しで ValueError が発生します。エラーメッセージに従って .env を整備してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を起点に行います。テスト等で自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限・リトライは組み込まれていますが、ネットワーク/認証エラーはアプリケーション側での再試行ポリシーも検討してください。
- DuckDB のバージョンや SQL の互換性に注意してください（本コードは DuckDB を前提に記述されています）。
- ニュース RSS の取得では外部接続やリダイレクト先の検証を行っていますが、運用時は接続タイムアウトや一時的なエラーに備えたリトライ戦略を組み合わせてください。

---

README は以上です。追加で「導入手順のスクリプト例」や「運用で想定される cron / systemd ユニット例」、「品質チェック (quality モジュール) のドキュメント」を作成することも可能です。必要であれば教えてください。