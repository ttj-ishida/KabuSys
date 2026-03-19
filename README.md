# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
Data（市場データ取得・ETL）、Research（ファクター計算・解析）、Strategy（特徴量合成・シグナル生成）、Execution（発注・監視）を層別に実装したモジュール群を提供します。

主な設計方針:
- DuckDB を中心としたローカルデータレイク（整合性と冪等性を意識）
- ルックアヘッドバイアス回避（target_date 時点のデータのみを利用）
- API 呼び出しはレート制御・リトライ・トークンリフレッシュを備える
- DB 操作は冪等（ON CONFLICT / トランザクション）で安全に実行

---

## 機能一覧（主な提供機能）

- データ取得・保存
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）
  - レートリミット／自動リトライ／トークン自動リフレッシュ対応
  - DuckDB への冪等保存ユーティリティ（raw_prices / raw_financials / market_calendar 等）
- ETL パイプライン
  - 差分取得（最終取得日からの差分）・バックフィル・品質チェックを含む日次 ETL
  - calendar / prices / financials の個別ジョブおよび日次ジョブ
- データスキーマ管理
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
- ニュース収集
  - RSS フィード取得、前処理、記事の DB 保存、銘柄抽出
  - SSRF / XML 攻撃対策、受信サイズ制限、トラッキングパラメータ除去
- Research（因子・解析）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）やファクターサマリ
  - z-score 正規化ユーティリティ
- Strategy（特徴量・シグナル）
  - features テーブルの構築（正規化・クリップ・ユニバースフィルタ）
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成
  - 保有ポジションのエグジット（ストップロス等）判定
- カレンダー管理／ユーティリティ
  - 営業日判定／前後の営業日取得／カレンダー更新ジョブ
- 監査（audit）スキーマ（signal → order → execution のトレーサビリティ用テーブル）

---

## 必要条件 / 依存関係

- Python 3.10+
- 外部パッケージ（最低限）
  - duckdb
  - defusedxml

（requirements.txt や pyproject.toml があればそれに従ってください）

---

## 環境変数（設定）

package 内の `kabusys.config.Settings` を通じて環境変数で設定を読み込みます。プロジェクトルートの `.env` / `.env.local` が自動読み込みされます（CWD に依存せずパッケージ位置からプロジェクトルートを探索）。

重要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意 / デフォルトあり
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化（テスト用）

.env の例（.env.example を参考に作成してください）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（ローカル開発用）

1. Python と依存パッケージをインストール
   - 仮想環境を作成して有効化
   - pip install duckdb defusedxml
   - （プロジェクトに requirements/pyproject がある場合はそれに従う）

2. 環境変数設定
   - プロジェクトルートに `.env`（及び `.env.local`）を作成し、必要なキーを設定
   - テスト実行時に自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定

3. DuckDB スキーマ初期化
   - Python REPL かスクリプトから:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - :memory: を渡すとメモリ DB で初期化できます（テスト用）。

---

## 使い方・主要 API（コード例）

以下はライブラリを使う際の代表的なワークフロー例です。

1) データベース初期化
```
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から差分取得して保存）
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量作成（features テーブルへ）
```
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, date(2024, 1, 5))
print(f"features upserted: {n}")
```

4) シグナル生成（signals テーブルへ）
```
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, date(2024, 1, 5))
print("signals total:", count)
```

5) RSS ニュース収集（news -> raw_news / news_symbols）
```
from kabusys.data.news_collector import run_news_collection

# sources: dict of {source_name: rss_url} を渡せます（省略時はデフォルト）
known_codes = {"7203", "6758", "9432"}  # 例: 有効銘柄コードセット
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

6) カレンダー更新ジョブ
```
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("calendar records saved:", saved)
```

注意:
- 各処理は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。
- 多くの DB 書き込みはトランザクション・冪等（DELETE / INSERT の日付単位置換、ON CONFLICT）で安全に設計されています。
- J-Quants API 呼び出しは内部でレート制御とリトライを行いますが、API キーやネットワーク制限に注意してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py             — RSS 取得・前処理・保存
    - schema.py                     — DuckDB スキーマ定義・初期化
    - stats.py                      — zscore 等の統計ユーティリティ
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - features.py                   — features 公開ラッパー（zscore 再エクスポート）
    - calendar_management.py        — カレンダー管理・ジョブ
    - audit.py                      — 監査ログ関連スキーマ
  - research/
    - __init__.py
    - factor_research.py            — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py        — 生ファクターを正規化して features を作る
    - signal_generator.py           — features と ai_scores からシグナルを作る
  - execution/                      — 発注 / 実行 層（初期ファイル群）
  - monitoring/                     — モニタリング用モジュール（DB/Slack 等に接続する想定）

（実際の modules は上記のファイル群に対応します。README の作成時点では execution パッケージはプレースホルダの可能性あり）

---

## 運用上の注意点

- 本ライブラリは「自動売買」システムの構成要素として多くのリスクを含みます。実際の発注・資金投入を行う前に十分なテストと監査を実施してください。
- 本番運用（KABUSYS_ENV=live）ではログ・通知・監視を適切に設定し、誤発注を防ぐための安全策（DRY RUN / paper_trading モード、発注前の risk-check）を必須にしてください。
- API のレート・認証仕様は外部サービスに依存します（J-Quants 等）。利用規約・レートポリシーに従ってください。
- DuckDB のバージョンによっては FOREIGN KEY / ON DELETE の挙動が異なる場合があります。schema.py のコメントにもある通り制約等は DB のバージョン要件に依存します。

---

## 貢献・拡張

- 新しいデータソースやニュースソースの追加、AI スコア統合、execution 層（ブローカー API 統合）等はモジュール分割に従って追加できます。
- テスト: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動ロードを無効化できます（テスト用に設定注入する際に便利）。

---

この README はコードベースの主要機能をまとめたものです。より詳細な仕様（StrategyModel.md / DataPlatform.md 等）や API の挙動はソース内ドキュメント（関数 docstring）を参照してください。README の補足・改善点があれば知らせてください。