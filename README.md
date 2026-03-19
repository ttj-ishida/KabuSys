# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
市場データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査/実行レイヤのためのユーティリティを含む軽量なPythonモジュール群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の階層を想定したデータ／戦略運用基盤を提供します。

- Data Layer (DuckDB): J-Quants から得た生データ（株価・財務・カレンダー・ニュース等）を保存・整形
- Feature Layer: research モジュールで算出した生ファクターを正規化・合成して `features` テーブルへ格納
- Strategy Layer: 正規化済み特徴量と AI スコアを統合して売買シグナルを生成
- Execution / Audit Layer: シグナル→注文→約定→ポジションの監査ログを保持（スキーマとユーティリティ提供）
- News Collection: RSS からニュースを収集・正規化し銘柄紐付け

設計上のポイント:
- ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）
- 冪等性を重視（DB 書き込みは ON CONFLICT / トランザクションで安全）
- 外部依存を最小化（標準ライブラリ + 必要最小限のパッケージで動作）
- ネットワーク：API レート制御、リトライ、SSRF対策など堅牢性を考慮

---

## 主な機能一覧

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能（プロジェクトルート検出）
  - 必須環境変数取得ヘルパー
- Data（kabusys.data）
  - J-Quants API クライアント（取得、ページネーション、トークン自動リフレッシュ）
  - DuckDB スキーマ定義 & 初期化（init_schema）
  - ETL パイプライン（差分取得 / backfill / 品質チェック）
  - ニュース収集（RSS 取得、正規化、DB 保存、銘柄抽出）
  - カレンダー管理（営業日判定、next/prev_trading_day など）
  - 統計ユーティリティ（Zスコア正規化）
- Research（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算 / IC（Spearman） / 統計サマリー
- Strategy（kabusys.strategy）
  - build_features: raw factor → 正規化 → features テーブルへ保存
  - generate_signals: features + ai_scores → final_score → signals テーブルへ書き込み
- News Collector（kabusys.data.news_collector）
  - RSS フィード取得・前処理・DB 保存・銘柄抽出
  - SSRF / XML/圧縮レスポンス対策、記事IDの正規化（SHA-256ベース）
- Execution / Audit（スキーマ・DDL）
  - signals / orders / executions / positions / audit テーブル定義等

---

## 必要環境（Python / ライブラリ）

- Python 3.9+（typing の Union 表記や型ヒントの互換性を考慮）
- 必要な外部パッケージ（例）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install duckdb defusedxml
```

必要に応じて他の依存をプロジェクトに追加してください（例: ロギング設定、テストフレームワークなど）。

---

## 環境変数（主なもの）

以下はコード内で参照される主な環境変数です。`.env` に設定して利用してください。

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須) — kabu API パスワード
  - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- Slack
  - SLACK_BOT_TOKEN (必須) — Slack ボットトークン
  - SLACK_CHANNEL_ID (必須) — 通知先チャネルID
- データベース / ファイルパス
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
- 実行環境 / ログ
  - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

自動 .env ロード:
- パッケージの config モジュールはパッケクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動で読み込みます。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に有用）。

簡単な .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo_dir>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成し、上記の必須キーを設定します。

5. DuckDB スキーマ初期化
   - Python REPL かスクリプトで初期化:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成されます
   conn.close()
   ```

---

## 使い方（代表的なワークフロー例）

ここでは日次 ETL → 特徴量生成 → シグナル生成 の基本的な流れを示します。

1. DuckDB 初期化（1回）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2. 日次 ETL を実行（J-Quants トークンは settings から取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3. 特徴量を作成（target_date を指定）
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, date(2025, 1, 31))
print(f"features upserted: {n}")
```

4. シグナル生成
```python
from kabusys.strategy import generate_signals

count = generate_signals(conn, date(2025, 1, 31), threshold=0.6, weights=None)
print(f"signals generated: {count}")
```

5. ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 銘柄抽出に用いる有効なコード集合（例: prices テーブル等から取得）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6. 設定値取得（programmatic）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- 生成された `signals` テーブルへは直接書き込みますが、実際の発注は execution 層と連携するコード（ブローカーAPI駆動）が別途必要です。
- run_daily_etl 等は例外を内部で捕捉しつつ継続する設計ですが、ログ・結果（ETLResult）を確認して問題を把握してください。

---

## ディレクトリ構成（主要ファイル）

（`src/kabusys` をルートとした主要モジュールとその概要）

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント & 保存ユーティリティ
    - schema.py                 — DuckDB スキーマ定義 / init_schema
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - news_collector.py         — RSS 取得・前処理・DB 保存
    - calendar_management.py    — 市場カレンダー管理・営業日判定
    - features.py               — zscore_normalize のエクスポート
    - stats.py                  — 統計ユーティリティ（zscore_normalize）
    - audit.py                  — 監査ログ用 DDL 定義
    - execution/                — （発注 / execution 層用プレースホルダ）
  - research/
    - __init__.py
    - factor_research.py        — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py    — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py    — build_features
    - signal_generator.py       — generate_signals
  - monitoring/                 — （監視 / アラート用プレースホルダ）

上記は主要モジュールのみ抜粋しています。詳細はソースを参照してください。

---

## 開発・テストに関するメモ

- config の自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を検出して行います。テストで自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB はインメモリ（":memory:"）でも動作するため単体テストの際に便利です： `init_schema(":memory:")`
- ネットワーク呼び出し（J-Quants / RSS）はモック可能な設計になっています（関数引数で id_token を注入する、内部 _urlopen を差し替える等）。

---

## ログ・運用

- settings.log_level を参照してログレベルを制御できます（LOG_LEVEL 環境変数）。
- ETL やジョブは冪等に設計されているため再実行により重複データ発生は抑えられます（DB の ON CONFLICT / DELETE→INSERT による日付単位の置換）。
- 監査ログ（audit テーブル群）によりシグナルから約定までのトレーサビリティを維持する設計です。

---

必要であれば README に動作例のスクリプトやテスト手順、CI 設定例、より詳細な `.env.example` を追加できます。追加希望があれば教えてください。