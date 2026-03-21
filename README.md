# KabuSys

KabuSys は日本株の自動売買／データ基盤を目的とした Python パッケージです。J-Quants API や RSS ニュースを取り込み、DuckDB をバックエンドにしてデータを管理・処理し、特徴量生成・シグナル作成・発注監査までの基盤処理を提供します。

主な設計方針:
- ルックアヘッドバイアス防止（計算は target_date 時点のデータのみを使用）
- 冪等性（DB への保存は ON CONFLICT で重複排除）
- 外部依存を最小化（多くは標準ライブラリ + duckdb）
- セキュリティ考慮（RSS の SSRF 対策、XML パースの安全化など）

---

## 機能一覧

- データ取得／保存
  - J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー）
  - RSS からのニュース収集（正規化・トラッキングパラメータ除去・SSRF 対策）
  - DuckDB スキーマ定義・初期化・接続ユーティリティ
  - 差分 ETL（prices / financials / calendar）と品質チェックパイプライン
- データ加工・統計
  - cross-sectional Z スコア正規化ユーティリティ
  - forward returns / IC（Spearman）計算、ファクター統計要約
- 戦略層
  - ファクター計算（momentum / volatility / value / liquidity）
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals：BUY / SELL の算出、Bear レジーム抑制、エグジット判定）
- 実行・監査
  - DuckDB 上の実行層スキーマ（signals / orders / executions / positions 等）
  - 監査ログテーブル（signal_events / order_requests / executions 等）
- 設定管理
  - .env/.env.local または環境変数からの設定読み込み（自動読み込み機能あり）
  - 環境切替（development / paper_trading / live）

---

## 要件

最低限必要なパッケージ例:
- Python 3.10+
- duckdb
- defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発インストール（プロジェクトルートで）
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成、必要パッケージをインストールします。

2. 環境変数または .env ファイルを用意します。
   - 自動でプロジェクトルートの `.env` と `.env.local` が読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. 必要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（任意、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマの初期化:
   - Python REPL またはスクリプトから init_schema を呼びます。

---

## 使い方（主要な例）

以下は基本的な操作の例です。パッケージは `src/kabusys` 下に実装されており、Python コードから関数を呼び出して利用します。

- DuckDB の初期化と接続:
```python
from kabusys.data.schema import init_schema, get_connection

# ファイル DB を初期化（親ディレクトリがなければ作成されます）
conn = init_schema("data/kabusys.duckdb")
# 既存 DB に接続するだけなら
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL を実行（J-Quants から差分取得して保存）:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- ファーチャー構築（features テーブルへの書き込み）:
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2024, 1, 5))
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブルへの書き込み）:
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date(2024, 1, 5), threshold=0.60)
print(f"signals written: {count}")
```

- RSS ニュース収集（news -> raw_news, news_symbols 保存）:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コード集合（抽出時に使用）
known_codes = {"7203", "6758", ...}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

- 市場カレンダー更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- 設定（環境変数）取得:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

---

## 初期化・運用に関する注意点

- .env の自動ロード
  - デフォルトでプロジェクトルート（.git または pyproject.toml のある階層）から `.env` と `.env.local` をロードします。
  - テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DuckDB の初期化は一度行えば OK（init_schema は冪等）。既存 DB に接続する場合は get_connection を使用します。

- J-Quants API の呼び出しはレート制御・リトライを含みます（120 req/min のスロットリング、401 時のトークン自動リフレッシュなど）。

- RSS フェッチでは SSRF 対策や受信サイズ制限、defusedxml による安全な XML パース等を行っています。

- ETL は「差分取得」を行い、バックフィルによって直近数日のリトライで API 側の後出し修正を吸収します。

- ログレベルは環境変数 `LOG_LEVEL` で制御します（settings.log_level）。

---

## 開発者向け：よく使うモジュール一覧

- kabusys.config
  - 環境変数読み込み・バリデーション（settings オブジェクト）
- kabusys.data
  - jquants_client.py: J-Quants API クライアント（fetch / save）
  - schema.py: DuckDB スキーマ初期化
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - news_collector.py: RSS 収集と DB 保存
  - calendar_management.py: 市場カレンダー管理
  - stats.py: zscore_normalize 等
- kabusys.research
  - factor_research.py: momentum / volatility / value の計算
  - feature_exploration.py: forward returns / IC / summary
- kabusys.strategy
  - feature_engineering.py: build_features（生ファクターを正規化して features に保存）
  - signal_generator.py: generate_signals（final_score 計算、BUY/SELL 判定）
- kabusys.execution / kabusys.monitoring
  - 実行・監視用のプレースホルダモジュール（将来的な拡張想定）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - calendar_management.py
      - features.py
      - audit.py
      - ...（その他データ関連モジュール）
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
    - monitoring/
      - __init__.py

---

## よくある質問 / トラブルシューティング

- Q: .env が読み込まれない
  - A: プロジェクトルートの判定は `__file__` を基点に行われるため、実行コンテキストによっては期待するルートが見つからない場合があります。必要に応じて明示的に環境変数をエクスポートするか、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動でロードしてください。

- Q: J-Quants の 401 エラーが出る
  - A: refresh token の期限切れや誤りが考えられます。`JQUANTS_REFRESH_TOKEN` を確認してください。ライブラリは 401 受信時に自動でトークンをリフレッシュして再試行します（1 回のみ）。

- Q: DuckDB のスキーマ初期化で失敗する
  - A: ファイルパスの親ディレクトリが作成されないと失敗する可能性がありますが、init_schema は親ディレクトリを自動作成します。権限や既存コネクション、ファイルロックを確認してください。

---

この README はコードベースの主要機能と典型的な使い方をまとめた簡易ガイドです。各モジュールの詳細な仕様（StrategyModel.md, DataPlatform.md 等）がプロジェクト内にある想定ですので、実運用や拡張を行う際は該当設計ドキュメントを参照してください。