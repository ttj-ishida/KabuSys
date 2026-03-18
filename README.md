# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
DuckDB を用いたデータレイヤ、J-Quants API クライアント、RSS ニュース収集、特徴量計算（ファクター）、ETL パイプライン、データ品質チェック、監査ログスキーマなどを含みます。

※ 本リポジトリはライブラリ（モジュール群）として設計されており、フルの運用アプリケーション（運用用 CLI や Web UI）は含まれていません。各モジュールを組み合わせて ETL バッチや戦略実行コンポーネントを構築することを想定しています。

## 主な機能（Feature）

- データ取得 / 永続化
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー） — レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT で更新）
- データレイヤ（DuckDB スキーマ）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化ユーティリティ
- ETL パイプライン
  - 差分更新（最終取得日からの自動算出、backfill 対応）
  - 日次 ETL（カレンダー取得 → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損、主キー重複、スパイク（前日比）、日付不整合（未来日／非営業日）など
- ニュース収集（RSS）
  - RSS フィード取得、SSRF 対策、XML 脆弱性対策（defusedxml）、記事正規化、記事ID生成（正規化 URL -> SHA-256）
  - raw_news / news_symbols への冪等保存
- 研究用ユーティリティ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Spearman）計算、ファクター要約統計
  - Z スコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal / order_request / execution の監査スキーマと初期化ユーティリティ（UTC タイムスタンプを保証）

## 必要条件

- Python 3.10 以上（コード内での型アノテーション（|）等に依存）
- pip が利用可能な環境

推奨パッケージ（最低限）
- duckdb
- defusedxml

（プロジェクトの要件ファイルがあればそちらを参照してください。実行する機能に応じて追加の依存が必要になる場合があります。）

## 環境変数 / 設定

このパッケージは起動時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると、`.env` と `.env.local` を自動的に読み込む機能を持ちます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: モニタリング用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 'development' | 'paper_trading' | 'live'（デフォルト: development）
- LOG_LEVEL: ログレベル 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'（デフォルト: INFO）

設定値をコードから使うには:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .\.venv\Scripts\activate    # Windows
   ```

3. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```
   - 開発用途: pytest や mypy 等を追加でインストールしてください。

4. 環境変数を設定
   - プロジェクトルートに `.env`（と `.env.local`）を作成する例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - テスト時など自動読み込みを抑止する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

## 使い方（簡単な例）

以下は代表的なユースケースの Python スニペットです。

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = init_schema(":memory:")
```

- 日次 ETL を実行（J-Quants トークンは settings から自動取得される）:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = run_daily_etl(conn)  # target_date を渡さなければ本日が対象
print(result.to_dict())
```

- ニュース収集ジョブを実行:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes を渡すと本文から銘柄コード抽出して news_symbols に紐付ける
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

- ファクター計算（研究用途）:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
# これらは list[dict] を返します（date, code, 各カラム）
```

- Z スコア正規化:
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

- 監査ログスキーマ初期化:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit_kabusys.duckdb")
```

- 品質チェック:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

各関数・クラスはドキュメンテーションコメント（docstring）を持っているので、詳細はソースを参照してください。

## ディレクトリ構成（主要ファイル）

パッケージルート: src/kabusys

- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント（取得 + 保存ユーティリティ）
  - news_collector.py        — RSS ニュース収集 & 保存ロジック
  - schema.py                — DuckDB スキーマ定義・初期化
  - pipeline.py              — ETL パイプライン（差分取得 / 日次 ETL）
  - features.py              — 特徴量ユーティリティの公開インターフェース
  - stats.py                 — 統計ユーティリティ（zscore_normalize 等）
  - calendar_management.py   — 市場カレンダー管理ユーティリティ
  - audit.py                 — 監査ログスキーマと初期化
  - etl.py                   — ETL 結果クラスの公開
  - quality.py               — データ品質チェック
- research/
  - __init__.py
  - factor_research.py       — モメンタム/ボラティリティ/バリュー等のファクター計算
  - feature_exploration.py   — 将来リターン / IC / ファクターサマリ
- strategy/                   — 戦略関連（将来的な拡張用）
- execution/                  — 発注実行関連（将来的な拡張用）
- monitoring/                 — モニタリング関連（将来的な拡張用）

（実ファイルはリポジトリ内の src/kabusys 以下を参照してください。）

## 注意事項 / 運用上のポイント

- 本ライブラリは「データ取得・前処理・特徴量計算・品質チェック・監査ログ設計」を主目的としており、実際の発注ロジック（証券会社との送受信）は別途実装が必要です。
- J-Quants の API レート制限や認証トークンの取り扱いに注意してください（トークンは secrets 管理の徹底を推奨）。
- DuckDB ファイル（デフォルト data/kabusys.duckdb）はアプリケーションからのアクセスに対し排他制御が必要な場合があります。複数プロセスでの同時書き込みは設計を確認してください。
- ニュース収集には SSRF 対策や XML の安全パーサ（defusedxml）を利用していますが、外部 URL を扱う際は追加のセキュリティ対策を検討してください。
- 環境設定は .env と OS 環境変数の組み合わせでロードされます。デフォルトの読み込み優先度は OS 環境変数 > .env.local > .env です。
- KABUSYS_ENV の値によってシステム挙動（paper_trading / live）を分ける想定です。実装を拡張する際は settings.is_live / is_paper / is_dev を利用してください。

---

詳細な使い方や運用要件、CI/CD での初期化やバッチ運用のサンプルは今後のドキュメント追加で補完してください。ソースコード中に各関数の振る舞い・設計方針が記載されていますので、まずは該当モジュールの docstring を参照することをおすすめします。