# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants / RSS）、DuckDBベースのデータスキーマ、研究用ファクター計算、特徴量生成、シグナル生成、ETLパイプラインなどをモジュール化して提供します。発注・モニタリング層は分離されており、実運用（live）・紙トレード（paper_trading）・開発（development）を切り替えて利用できます。

---

## 主な特徴（機能一覧）

- 環境変数ベースの設定管理（.env 自動読み込み、保護機能あり）。
- J-Quants API クライアント
  - 株価日足、財務データ、JPX カレンダーの取得（ページネーション対応）。
  - レート制限・リトライ・トークン自動リフレッシュ対応。
- DuckDB スキーマ定義と初期化ユーティリティ（冪等な DDL 実行）。
- ETL パイプライン
  - 差分更新（バックフィル対応）、品質チェックフック付きの日次 ETL。
- 研究（research）モジュール
  - モメンタム / ボラティリティ / バリュー等のファクター計算。
  - 将来リターン計算、IC（Spearman）や統計サマリー。
- 戦略（strategy）モジュール
  - 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）。
  - シグナル生成（コンポーネントスコア統合、Bear レジーム考慮、BUY/SELL 判定、冪等）。
- ニュース収集（RSS）・記事→銘柄紐付け（SSRF 対策 / トラッキング除去 / 重複排除）。
- 監査（audit）テーブル定義（信頼できるトレーサビリティ設計）。

---

## 動作要件（目安）

- Python 3.10 以上（型注釈や union 型表記を想定）
- duckdb
- defusedxml
- （必要に応じて）其它の依存パッケージ（HTTP 標準ライブラリを多用していますが、環境に応じて追加）

インストール例（プロジェクトに pyproject.toml / setup がある前提）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージとしてインストール可能なら:
# pip install -e .
```

---

## 環境変数

自動的にプロジェクトルートの `.env` → `.env.local` を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必要な環境変数の一例:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite（デフォルト: data/monitoring.db）

簡易 `.env.example`（README 用サンプル）:
```env
# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# 任意（変更可能）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境の作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 依存関係のインストール
   ```bash
   pip install duckdb defusedxml
   # もしプロジェクトがパッケージ化されていれば:
   # pip install -e .
   ```

4. `.env` を作成（.env.example を参照）し、必要な値を設定

5. DuckDB スキーマの初期化
   Python REPL かスクリプトで:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # または ":memory:" でインメモリ
   ```

---

## 使い方（主要ユースケース）

以下は典型的なワークフローの例です。

- 日次 ETL（市場カレンダー・株価・財務を差分取得して保存）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量作成（研究モジュールで算出した raw factor を正規化して features テーブルへ）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print("features upserted:", count)
```

- シグナル生成（features / ai_scores / positions を参照して BUY/SELL を作成）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema(settings.duckdb_path)
signals_count = generate_signals(conn, target_date=date.today())
print("signals created:", signals_count)
```

- ニュース収集ジョブ（RSS 取得 → raw_news 登録 → 銘柄紐付け）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema(":memory:")
known_codes = {"7203", "6758", ...}  # 事前に既知の銘柄コードを用意
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

注意:
- run_daily_etl は内部でカレンダーを先に更新し、対象日を営業日に調整してから株価/財務の差分取得を行います。
- 環境が `KABUSYS_ENV=live` の場合は実運用モードとして扱われます。紙トレード（paper_trading）・開発（development）を適切に使い分けてください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの `src/kabusys/` を中心に抜粋）

- kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・設定管理
  - data/
    - __init__.py
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - jquants_client.py — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py — RSS 収集・前処理・DB 保存
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — JPX カレンダーの管理・営業日ロジック
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - features.py — データ層の特徴量ユーティリティ（再エクスポート）
    - audit.py — 監査ログ用 DDL
    - quality.py (参照されるが本リストに含まれていない場合あり)
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成ロジック
    - signal_generator.py — final_score 計算と signals 生成ロジック
  - execution/
    - __init__.py — 発注・約定・ポジション管理層（実装／拡張ポイント）
  - monitoring/ — 監視・メトリクス収集など（実装／拡張ポイント）

各モジュールには docstring と設計方針・処理フローが詳述されています。実運用向けの処理（発注・ブローカー連携）や外部接続周りは execution 層を実装して分離することを想定しています。

---

## 運用・開発時の注意事項

- 自動的に `.env` を読み込みますが、テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。
- J-Quants のレート制限やレスポンス失敗に備えたリトライ／レートリミッタを実装していますが、運用では API キーやネットワーク状況を監視してください。
- DuckDB のトランザクションや ON CONFLICT を用いて冪等性を確保していますが、スキーマ変更時は注意してマイグレーションを行ってください。
- news_collector は外部 URL を扱うため SSRF／XML bomb 等の対策を施しています（_SSRFBlockRedirectHandler / defusedxml / レスポンスサイズ制限など）。

---

## 今後の拡張ポイント（参考）

- execution 層（証券会社 API 連携）の実装（注文送信・約定取得・再送制御など）
- モニタリング / アラート（Slack 通知や Prometheus エクスポータ）
- 品質チェックモジュール（quality）やテストカバレッジの拡充
- AI スコア生成パイプラインの統合（ai_scores テーブルの生成）

---

不明点や README へ追加したい項目（例: CLI コマンド、CI 設定、より詳細な .env.example）などがあれば教えてください。必要があればデプロイスクリプトや運用手順のテンプレートも作成します。