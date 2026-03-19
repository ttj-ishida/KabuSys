# KabuSys

日本株向けの自動売買 / データプラットフォーム実装（ライブラリ）

短い説明:
KabuSys は J-Quants 等から市場データを取得・蓄積し、特徴量計算 → シグナル生成 → 発注監査までのワークフローを想定した Python パッケージです。DuckDB をデータ層に用い、研究（research）と運用（strategy / execution）を分離した設計を目指しています。

---

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価・財務・マーケットカレンダー）
  - RSS ベースのニュース収集（SSRF対策、トラッキングパラメータ除去、記事IDは正規化URLのSHA-256）
  - DuckDB への冪等保存（ON CONFLICT / INSERT ... DO UPDATE）

- ETL / Data Pipeline
  - 差分更新（最終取得日からの差分 + backfill）
  - 日次 ETL ジョブ（市場カレンダー → 株価 → 財務 → 品質チェック）

- データスキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義、監査ログ用テーブル群

- 研究（research）
  - ファクター計算: momentum / volatility / value（prices_daily / raw_financials を参照）
  - 特徴量探索: 将来リターン計算、IC（Spearman）計算、統計サマリー

- 戦略（strategy）
  - 特徴量構築（Zスコア標準化・ユニバースフィルタ・日次 upsert）
  - シグナル生成（ファクター統合、AIスコア反映、BUY/SELL 判定、エグジット条件、冪等保存）

- 運用補助
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day）
  - 監査ログ（signal_events / order_requests / executions など）

- セキュリティ・堅牢性配慮
  - API レート制御、リトライ、トークン自動リフレッシュ
  - RSS 取得時の SSRF 対策、XML パースの安全化（defusedxml）
  - 入力値検証・NULL 耐性・トランザクション処理（COMMIT / ROLLBACK）

---

## 必要要件（依存ライブラリ）

最低限のランタイム依存（コードから推測）:
- Python 3.9+
- duckdb
- defusedxml

（その他標準ライブラリ: urllib, datetime, logging, typing 等）

インストール方法は利用環境に合わせてください（下記セットアップ参照）。

---

## 環境変数 / 設定

アプリは環境変数またはプロジェクトルートの `.env` / `.env.local` を自動読み込みします（デフォルト）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（Settings クラス参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視 DB（SQLite）パス（デフォルト `data/monitoring.db`）
- KABUSYS_ENV — `development` | `paper_trading` | `live`（デフォルト `development`）
- LOG_LEVEL — `DEBUG`|`INFO`|`WARNING`|`ERROR`|`CRITICAL`（デフォルト `INFO`）

.env のパースは一般的な shell 形式（export 対応、クォート・コメント処理あり）を行います。

---

## セットアップ（開発環境向け）

例: 仮想環境を使う手順（UNIX 系）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成 & 有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb defusedxml
     ```
   - 開発時は editable インストール（setup.py / pyproject.toml がある場合）:
     ```
     pip install -e .
     ```
   - 実際の運用では requirements.txt / pyproject.toml を参照してください。

4. 環境変数を設定
   - 例 `.env` をプロジェクトルートに置く（.env.example を参考に作成）
   - または export で設定:
     ```
     export JQUANTS_REFRESH_TOKEN="..."
     export SLACK_BOT_TOKEN="..."
     export SLACK_CHANNEL_ID="..."
     ```

---

## 使い方（クイックスタート）

以下は Python REPL / スクリプトからの基本的な利用例です。

1) DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
```

2) 日次 ETL（J-Quants からのデータ取得と保存）
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```
- run_daily_etl は market_calendar → prices → financials → 品質チェック の順で実行します。
- id_token を明示的に渡すことも可能（test 用等）。

3) 特徴量構築（features テーブルへの保存）
```
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2024,1,10))
print(f"features upserted: {n}")
```

4) シグナル生成（signals テーブルへの保存）
```
from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, target_date=date(2024,1,10))
print(f"signals generated: {total}")
```
- 重みや閾値を引数で変更できます（weights / threshold）。

5) ニュース収集ジョブ
```
from kabusys.data.news_collector import run_news_collection
# known_codes を渡すと記事と銘柄の紐付けを試みる
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

6) マーケットカレンダー更新（夜間バッチ）
```
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- 外部 API 呼び出しを行う機能（J-Quants / RSS）は環境変数・API トークンを必要とします。
- 実運用（live）環境では `KABUSYS_ENV=live` を設定し、ログレベル等を調整してください。

---

## ディレクトリ構成（主要ファイルの説明）

（パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数・設定管理（Settings クラス、自動 .env ロード）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存・リトライ・RateLimit）
    - news_collector.py — RSS 取得・記事正規化・DB 保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py — zscore_normalize などの統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — market_calendar 管理（営業日判定、更新ジョブ）
    - audit.py — 監査ログ用テーブル DDL（signal_events / order_requests / executions 等）
    - features.py — data.stats の再エクスポートインターフェース
  - research/
    - __init__.py — 研究用 API の公開
    - factor_research.py — momentum / volatility / value 等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - strategy/
    - __init__.py — build_features / generate_signals を公開
    - feature_engineering.py — ファクター正規化・ユニバースフィルタ・features テーブル書込
    - signal_generator.py — features + ai_scores 統合 → final_score → signals 作成
  - execution/ — 発注実装用（現状空の __init__.py が含まれています）
  - monitoring/ — 監視用のモジュール格納を想定（現状は空）

---

## 開発・運用上の注意

- ルックアヘッドバイアス対策が随所に入っており、target_date 時点のデータのみを用いる実装方針です。運用時はデータの fetched_at などを意識してください。
- DuckDB のスキーマは初期化時に作成されますが、既存データへの変更は慎重に（DDL の互換性に注意）。
- ニュース収集・RSS 処理は外部ネットワークを利用するため、テスト時はネットワークや _urlopen のモックを推奨します。
- J-Quants API のレート制限（120 req/min）を尊重する設計になっていますが、大量取得や並列化の際は追加の制御が必要です。
- 本リポジトリには発注実行（execution 層）との実際のブローカー統合部分は限定的です。ライブ運用で実際のブローカーAPIに接続する場合は十分なテストと安全対策を行ってください。

---

## 貢献 / 改善案

- ドキュメントや型注釈の整備、テストケース（ユニット／統合）の追加
- CI による品質チェック（静的解析・型チェック・ユニットテスト）
- 発注実装の追加（kabu API 実装やモックブローカー）
- 追加のデータソース（ニュース源、代替データ）や AI スコア計算パイプラインの統合

---

何か特定のセットアップ手順やサンプルスクリプト（例: Cron/airflow ジョブ定義、Docker 化、CI 設定）を README に追記したい場合は目的（開発/本番/テスト）を教えてください。追加例を作成します。