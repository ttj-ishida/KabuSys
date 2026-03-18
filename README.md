# KabuSys

日本株向けの自動売買・データプラットフォーム（ライブラリ）のREADMEです。  
このリポジトリはデータ収集（J-Quants）、ETL、データ品質チェック、特徴量生成、監査ログ、ニュース収集などを備えたバックエンド基盤を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成する共通ライブラリ群です。主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダーの取得（レート制限・リトライ・トークンリフレッシュ対応）
- DuckDB を使ったデータスキーマ定義・初期化・保存（冪等性を考慮）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策、トラッキングパラメータ除去）
- 研究（research）用のファクター計算・将来リターン・IC 計算・統計ユーティリティ
- 監査（audit）用スキーマ（signal → order → execution のトレーサビリティ）

注：発注実行ロジックや戦略（execution / strategy）はパッケージの骨組みとして用意されていますが、実運用で使用する前に十分な実装・検証が必要です。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ、ページネーション対応）
  - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分更新、バックフィル、品質チェックの統合）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出（SSRF 対策、gzip/サイズ制限）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダー管理（営業日判定、次/前営業日検索、夜間更新ジョブ）
  - audit: 監査ログ用スキーマ（signal / order_request / executions）
  - stats / features: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value などのファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、ファクター統計要約
- config.py: 環境変数・設定管理（.env 自動読み込み機能あり）
- strategy/, execution/, monitoring/: パッケージ領域（骨組み）

---

## セットアップ手順

1. リポジトリをクローンして、仮想環境を作る（例: venv / poetry / pipenv）。

2. 必要パッケージをインストール（代表的な依存のみ記載）。プロジェクトの実際の pyproject / requirements に合わせてください。

   pip (例)
   ```
   pip install duckdb defusedxml
   ```

   - duckdb: データベース
   - defusedxml: RSS パースの安全化
   - 標準ライブラリのみで動く部分も多いですが、実運用では追加の HTTP/ログ/テスト用ライブラリを使う場合があります。

3. 環境変数を用意する（.env ファイルをプロジェクトルートに置くと自動で読み込まれます）。
   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション等の API パスワード（発注実装時に使用）
   - SLACK_BOT_TOKEN       : Slack 通知に使う Bot トークン（必要に応じて）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   オプション / デフォルト:
   - KABUSYS_ENV           : development | paper_trading | live （デフォルト: development）
   - KABU_API_BASE_URL     : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視 DB パス（デフォルト: data/monitoring.db）
   - LOG_LEVEL             : ログレベル（DEBUG/INFO/...、デフォルト: INFO）

   自動読み込みの挙動:
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を自動読み込みします。
   - 読み込み優先順位: OS 環境 > .env.local > .env
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡単な例）

以下は Python スクリプト / インタラクティブでの利用例です。実行前に必ず環境変数（特に JQUANTS_REFRESH_TOKEN）を設定してください。

1) DuckDB スキーマ初期化
```
python - <<'PY'
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
print("initialized:", conn)
PY
```

2) 日次 ETL 実行（市場カレンダー・株価・財務を差分で取得して保存、品質チェック）
```
python - <<'PY'
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
PY
```

3) ニュース収集ジョブ（既定の RSS ソース）
```
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes を渡すと本文中の4桁銘柄コード抽出・紐付けを実施
known_codes = {"7203", "6758"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)
PY
```

4) 研究（ファクター計算、IC）
```
python - <<'PY'
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.research import calc_forward_returns, calc_ic, factor_summary
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")  # テスト用にメモリ DB を初期化してデータをロードする
# 実データがある前提で:
target = date(2024, 1, 4)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target)
# factor_records と forward_records を結合して IC を計算する例
# calc_ic は factor_records と forward_records を code で照合します
print(len(mom), len(vol), len(val), len(fwd))
PY
```

5) 監査スキーマの初期化（監査専用 DB）
```
python - <<'PY'
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
print("audit db initialized")
PY
```

注意点:
- J-Quants API のレート制限（120 req/min）はクライアント側で制御されます。大量取得時は並列化の制御に注意してください。
- production で発注を行う場合は KABUSYS_ENV を `live` に設定する想定ですが、まずは paper_trading / development で十分な検証を行ってください。

---

## ディレクトリ構成

以下は主要なファイル・ディレクトリの概観（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env ロード / settings
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得 & 保存）
    - news_collector.py          — RSS 収集・保存・銘柄抽出
    - schema.py                  — DuckDB スキーマ & init_schema / get_connection
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - quality.py                 — データ品質チェック
    - calendar_management.py     — 市場カレンダー管理（営業日判定等）
    - audit.py                   — 監査ログスキーマ初期化
    - etl.py                     — ETL API の再エクスポート
    - features.py                — 特徴量ユーティリティの公開インターフェース
    - stats.py                   — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py         — momentum/value/volatility 等のファクター計算
    - feature_exploration.py     — 将来リターン / IC / summary
  - strategy/                     — 戦略関連（パッケージ領域）
  - execution/                    — 発注実装領域
  - monitoring/                   — 監視 / メトリクス領域

（実際の tree はプロジェクトルートの `src/` 配下をご確認ください）

---

## 環境変数まとめ（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード（発注を行う際に使用）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 for Slack 通知)
- SLACK_CHANNEL_ID (必須 for Slack 通知)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化

---

## 運用上の注意 / セキュリティ

- RSS フィードや外部 URL を扱う箇所では SSRF 対策やサイズ制限、XML 攻撃対策（defusedxml）を導入しています。実運用でソースを追加する際もその方針を遵守してください。
- J-Quants の認証トークンは機密情報です。環境変数 / シークレットマネージャーで安全に保管してください。
- DuckDB は軽量で便利ですが、運用データのバックアップ戦略を必ず構築してください。
- 実際に発注を行うコードは十分にレビュー・テストを行ってから `live` 環境で実行してください。

---

## 開発・貢献

- コードベースはドキュメント文字列が豊富に記述されています。各モジュールの設計意図や制約は docstring を参照してください。
- テストスイート（unittest/pytest 等）は別途用意を推奨します。ETL・HTTP 呼び出しはモックを使ってテストしてください。

---

必要であれば、特定モジュールの詳しい使い方（関数引数や戻り値の例、サンプル SQL）を追記します。どの箇所を詳細化したいか教えてください。