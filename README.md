# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームのコアライブラリです。  
DuckDB をデータ層に据え、J-Quants API などから市場データ・財務データ・ニュースを取得して ETL → 特徴量生成 → シグナル生成 → 発注（実行）へとつなぐことを目的としています。

主な設計方針
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- 冪等性（DB の INSERT は ON CONFLICT で保護）
- API レート制御・リトライ・トレーサビリティ（監査ログ）
- Research と Production を分離し、外部依存を最小化

---

## 機能一覧
- データ取得・保存
  - J-Quants API クライアント（jquants_client）
    - 日次株価（OHLCV）、財務データ、JPX カレンダー等の取得（ページネーション対応）
    - レートリミット、リトライ、トークン自動リフレッシュを実装
  - ニュース収集（RSS）と記事保存（news_collector）
    - URL 正規化、SSRF 対策、トラッキングパラメータ除去、記事→銘柄紐付け
- ETL パイプライン（data.pipeline）
  - 差分更新（backfill を含む）、品質チェック呼び出し、日次 ETL 実行
- データスキーマ管理（data.schema）
  - DuckDB に必要なテーブル群（Raw / Processed / Feature / Execution）を作成
- 特徴量計算 / 正規化（research.factor_research、data.stats）
  - モメンタム、ボラティリティ、バリュー等
  - z-score 正規化ユーティリティ
- 特徴量集約（strategy.feature_engineering）
  - 複数ファクターを統合して features テーブルへ保存（ユニバースフィルタ、Zスコアクリップ等）
- シグナル生成（strategy.signal_generator）
  - features と AI スコア（ai_scores）を統合して最終スコアを計算、BUY/SELL シグナルを生成して signals テーブルへ保存
  - Bear レジーム判定、エグジット（ストップロスなど）
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定 / 前後営業日取得 / 夜間カレンダー更新ジョブ
- 監査ログ（data.audit）
  - signal → order_request → execution のトレーサビリティを担保するテーブル群

---

## 必要条件
- Python 3.10 以上（PEP 604 の union 型（|）を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS 取得などを行う場合）

（プロジェクトに requirements.txt / pyproject.toml があればそちらを優先してください）

インストール例（最小）
```bash
python -m pip install "duckdb" "defusedxml"
# もしパッケージを開発編集モードで使うなら:
pip install -e .
```

---

## 環境変数（設定）
環境変数は .env ファイル（プロジェクトルート）または OS 環境変数から読み込まれます。自動ロードはデフォルトで有効です（.git または pyproject.toml を起点に .env/.env.local を読み込み）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID

任意 / デフォルト値あり
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

注意:
- Settings クラス（kabusys.config.settings）からこれらを参照可能です。必須変数が未設定だと ValueError が発生します。

---

## セットアップ手順（基本）
1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt   # あれば
   # minimal
   pip install duckdb defusedxml
   ```

4. 環境変数を設定（プロジェクトルートに .env を作成）
   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

---

## 使い方（主要 API の例）

- 日次 ETL（市場カレンダー / 株価 / 財務 / 品質チェック）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# DB 初期化（1回目）
conn = init_schema(settings.duckdb_path)

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

- 特徴量構築（features テーブルに保存）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = build_features(conn, target_date=date(2025, 1, 15))
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルに保存）
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
total_signals = generate_signals(conn, target_date=date(2025, 1, 15))
print(f"signals written: {total_signals}")
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes を与えると記事中の銘柄抽出・紐付けを行う
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意点
- 各処理は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。接続は共有可能ですが、トランザクションの取り扱いに注意してください。
- 実運用（live）モードでは KABUSYS_ENV=live を設定してください。設定により一部の挙動（発注レイヤなど）を分離できます。

---

## ディレクトリ構成（主要ファイル）
リポジトリは src/kabusys パッケージ下に実装されています。主要モジュールを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + 保存）
    - news_collector.py      — RSS 収集・記事保存・銘柄抽出
    - pipeline.py            — ETL パイプライン（日次 ETL 等）
    - schema.py              — DuckDB スキーマ定義 / 初期化
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - features.py            — features の公開インターフェース
    - calendar_management.py — カレンダー管理 / バッチ更新
    - audit.py               — 監査ログ用テーブル定義
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — ファクター正規化・features テーブル書込
    - signal_generator.py    — final_score 計算・BUY/SELL シグナル生成
  - execution/
    - __init__.py            — 発注・約定管理（将来的な実装）
  - monitoring/              — 監視用モジュール（placeholder）

各モジュールはドキュメント文字列で設計意図と処理フローが記載されています。実装例を参照して統合ワークフローを構築してください。

---

## 開発・拡張のヒント
- DuckDB 上のクエリはパフォーマンスに影響するので、必要に応じてインデックスや SQL を調整してください（data.schema に主要インデックス定義あり）。
- ニュース収集や外部 API 呼び出しは外部ネットワークに依存するため、単体テストではモックを活用してください（例: news_collector._urlopen を差し替え可能）。
- 設定値は settings を通して取得することで一元管理できます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って環境変数の自動ロードを抑止してください。
- Strategy / Execution 層は分離設計。戦略で生成した signals を execution 層で安全に発注するワークフローを実装してください（order_request の冪等性等に注意）。

---

## ライセンス / 貢献
- ライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING ファイルをご覧ください（存在する場合）。

---

この README はコードベースから抽出した主要情報をまとめたものです。各モジュールの docstring に詳細な仕様・設計意図が記載されていますので、実装を変更する際は該当ファイルの先頭コメントを参照してください。