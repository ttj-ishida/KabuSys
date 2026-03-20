# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。  
DuckDB をデータレイクとして利用し、J-Quants API や RSS などからデータを収集・保存し、リサーチ（ファクター計算）→ 特徴量生成 → シグナル生成 のワークフローを提供します。

## 主な特徴
- J-Quants API クライアント（レートリミット・リトライ・トークン自動更新対応）
- DuckDB ベースのデータスキーマ（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェックとの連携）
- ファクター計算（Momentum / Value / Volatility / Liquidity）
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ）
- シグナル生成（複数コンポーネントを重み付けして final_score を算出、BUY/SELL を生成）
- ニュース収集（RSS → 前処理 → raw_news 保存、記事→銘柄紐付け）
- ニアリアルタイム/バッチの運用を想定した設計（冪等性・トランザクション制御・監査ログ設計）

## 機能一覧（主要モジュール）
- kabusys.config
  - 環境変数の自動読み込み（`.env`, `.env.local`）、必須値チェック
- kabusys.data.jquants_client
  - J-Quants API の HTTP レイヤ、fetch / save (daily quotes, financials, market calendar)
- kabusys.data.schema
  - DuckDB のスキーマ定義と初期化（init_schema / get_connection）
- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl） / 個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
- kabusys.data.news_collector
  - RSS フィード取得・前処理・DB 保存、銘柄抽出、SSRF 対策
- kabusys.research.factor_research
  - Momentum / Volatility / Value 等のファクター計算
- kabusys.strategy.feature_engineering
  - ファクター正規化・ユニバースフィルタ・features テーブルへの UPSERT（build_features）
- kabusys.strategy.signal_generator
  - features と ai_scores を統合して BUY / SELL シグナルを生成（generate_signals）
- kabusys.data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）

---

## 要求環境・依存
- Python >= 3.10（typing の新しい構文を使用）
- 必須ライブラリ（少数）
  - duckdb
  - defusedxml
- そのほか標準ライブラリ（urllib, datetime, math など）

簡易 requirements.txt（例）
```
duckdb
defusedxml
```

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存インストール
   ```
   pip install -r requirements.txt
   # または最低限:
   pip install duckdb defusedxml
   ```

4. パッケージのインストール（開発モード）
   ```
   pip install -e .
   ```

5. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます（デフォルト）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例 `.env`（必要なキー）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here

   # kabuステーション (発注を使う場合)
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意

   # Slack (通知などを使う場合)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス (デフォルト)
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易ガイド・例）

以下は Python REPL / スクリプトでの基本的な操作例です。

1. DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH から取得（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2. 日次 ETL 実行（J-Quants トークンは settings.jquants_refresh_token で取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

3. 特徴量のビルド（features テーブルを更新）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2024, 1, 31))
print(f"upserted features: {n}")
```

4. シグナル生成（signals テーブルを更新）
```python
from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
print(f"signals generated: {total}")
```

5. ニュース収集ジョブ（RSS から raw_news に保存し銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 銘柄抽出に利用する有効なコード集合（例は DB 内の prices_daily から取得）
known_codes = {row[0] for row in conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()}

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6. J-Quants からのデータ取得を直接行いたい場合（テスト・デバッグ用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings の refresh token を使用して idToken を取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 注意事項 & 運用上のポイント
- 環境変数の必須項目（不足すると Settings が例外を投げます）
  - JQUANTS_REFRESH_TOKEN
  - SLACK_BOT_TOKEN （Slack 機能を使う場合）
  - SLACK_CHANNEL_ID （Slack 機能を使う場合）
  - KABU_API_PASSWORD （kabu ステーションを使う場合）
- 自動ロード順序: OS 環境変数 > .env.local > .env。テストから自動ロードを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- データ保存関数は冪等（ON CONFLICT / upsert）で実装されています。
- J-Quants API はレート制限（120 req/min）に厳格に対応しています。多数のリクエストを伴うバッチ処理は考慮してください。
- DuckDB ファイル（デフォルト data/kabusys.duckdb）はローカルファイルとして扱われます。バックアップ・ロック運用は利用環境に合わせて設計してください。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（fetch/save）
    - news_collector.py               — RSS 収集 / 前処理 / 保存
    - schema.py                       — DuckDB スキーマ定義・init_schema
    - stats.py                        — zscore_normalize 等統計ユーティリティ
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py          — market_calendar 管理・営業日ロジック
    - audit.py                        — 監査ログ用スキーマ（signal_events 他）
    - features.py                      — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py              — Momentum / Volatility / Value 計算
    - feature_exploration.py          — forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py          — build_features（正規化・ユニバース）
    - signal_generator.py             — generate_signals（final_score・SELL 条件）
  - execution/                         — 発注・実行層（今後の拡張想定）
  - monitoring/                        — 監視・モニタリング（今後の拡張想定）

---

## 貢献・拡張ガイド（簡単に）
- 新しい ETL チェックや品質ルールは `kabusys.data.quality`（存在する場合）に追加する想定です。
- AI スコア等の外部データを統合する場合は `ai_scores` テーブルへの書込みインターフェースを追加してください（既存の generate_signals は ai_scores を参照します）。
- 発注ロジックは execution 層に分離してあり、strategy 層は発注 API に依存しない設計です。証券会社 API のラッパーを execution 配下に実装してください。

---

## ライセンス・その他
- ライセンス情報はリポジトリのルート（LICENSE）を参照してください（存在しない場合はメンテナに問い合わせてください）。

---

README の内容はプロジェクト初期の概要と主要な使い方に焦点を当てています。詳しい API（各関数の引数や返り値、例外挙動）は各モジュールの docstring を参照してください。必要であれば運用手順（cron / systemd / Kubernetes など）や Slack 通知の設定例、CI 用ジョブ定義のテンプレートも追記できます。どの情報が欲しいか教えてください。