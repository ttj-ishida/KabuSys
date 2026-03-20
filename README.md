# KabuSys

KabuSys は日本株向けに設計された自動売買・データ基盤ライブラリです。J-Quants API や RSS ニュースを取り込み、DuckDB に保存・整形して特徴量を生成し、戦略シグナルを作成する一連の処理を提供します。研究（research）→ データ（data）→ 戦略（strategy）→ 発注（execution）という層設計により、安全性・再現性・冪等性を重視して実装されています。

主な用途：
- J-Quants からの株価・財務・カレンダー取得（差分 ETL）
- RSS ニュースの収集と銘柄紐付け
- ファクター計算（モメンタム／ボラティリティ／バリュー等）
- 特徴量の標準化（Z スコア）と features テーブルへの保存
- 最終スコアの計算と BUY/SELL シグナル生成
- DuckDB を用いた永続化とクエリ

---

## 機能一覧

- データ収集
  - J-Quants API クライアント（レート制御、リトライ、ID トークン自動リフレッシュ）
  - RSS フィード収集（SSRF 除去、トラッキングパラメータ削除、XML 昇格脆弱性対策）
- ETL / パイプライン
  - 差分取得（最終取得日ベース）、バックフィル、品質チェックフレームワーク
  - market_calendar / raw_prices / raw_financials 等の冪等保存
- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - init_schema() による自動初期化
- 研究・ファクター
  - モメンタム／ボラティリティ／バリューの計算（prices_daily / raw_financials を参照）
  - 将来リターン・IC（Spearman）・統計サマリー等のユーティリティ
- 特徴量・シグナル生成
  - Z スコア正規化、外れ値クリップ、スコア合成（重み付け）
  - Bear 相場抑制、ストップロス等のエグジット判定
- 監査・トレーサビリティ
  - signal_events / order_requests / executions など監査用テーブル（UUID ベース）

---

## 動作要件

- Python 3.10 以上（型注釈に `|` を使用）
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml
- （実運用では urllib/標準ライブラリを多数使用）

requirements.txt がない場合は手動でインストールしてください：
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン（あるいはソースを配置）
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - 追加のユーティリティやテストライブラリは任意
4. 環境変数を設定
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（コード内 Settings から）:
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
     - KABU_API_PASSWORD — kabu ステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack チャネル ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
     - LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

   例 .env（ルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化
   - Python から schema.init_schema を呼び出して DuckDB スキーマを作成します（":memory:" を使えばインメモリ）。
   - 例:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

---

## 使い方（主な API とサンプル）

ここでは代表的なワークフロー例を示します。各例は Python スクリプト内で実行します。

1) DB 初期化
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL（市場カレンダー・株価・財務を差分取得）
```
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量の作成（features テーブルへ UPSERT）
```
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（features + ai_scores → signals）
```
from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, date.today())
print(f"signals written: {total}")
```

5) RSS ニュース収集（raw_news / news_symbols へ保存）
```
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

6) 直接 J-Quants から取得して保存する例
```
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token

token = get_id_token()  # settings から refresh token を利用
recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, recs)
```

注意点:
- run_daily_etl 等は内部で例外を拾って続行する設計ですが、ETLResult.errors を確認して異常を検出してください。
- J-Quants API はレート制限（120 req/min）をクライアント側で遵守します。大量フェッチは時間を要します。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下に配置される想定です。主要ファイルとモジュールは以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダーユーティリティ
    - features.py            — 公開用特徴量ユーティリティ（再エクスポート）
    - audit.py               — 監査ログテーブル定義
    - (その他: quality.py など想定)
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — IC / 将来リターン / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — 特徴量の正規化・フィルタ・保存
    - signal_generator.py    — シグナル生成ロジック
  - execution/
    - __init__.py            — 発注 / broker 連携（将来的に拡張）
  - monitoring/              — 監視関連（placeholder）
  - その他モジュール...

各モジュールは「DuckDB 接続を受け取る」「発注 API に直接依存しない」などの設計方針に従い分離されています。

---

## 設定と環境変数の詳細

Settings（kabusys.config.Settings）が参照する主要なキー：
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須 if kabu 発注を使う)
- KABU_API_BASE_URL (optional, default http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須 if Slack 通知有効)
- SLACK_CHANNEL_ID (必須 if Slack 通知有効)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV ∈ {"development","paper_trading","live"} (default: development)
- LOG_LEVEL ∈ {"DEBUG","INFO","WARNING","ERROR","CRITICAL"} (default: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化します

.env の自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）を基準に行われます。

---

## 運用上の注意

- J-Quants のレート制限・リトライ方針、トークンの自動リフレッシュを実装していますが、運用環境では API クォータに注意してください。
- RSS フィード取得は SSRF 対策や受信サイズ限界を設けています。未検証フィードを登録する場合は注意してください。
- DuckDB による永続化はローカルファイル（デフォルト data/kabusys.duckdb）を用います。バックアップや排他アクセスは運用ポリシーに応じて設計してください。
- シグナル生成・発注は重大な金融リスクを伴います。paper_trading モードで十分な検証を行ってください。
- Schema の外部キーや ON DELETE 挙動は DuckDB のバージョン依存の制約があります（コメントで補足あり）。

---

## 貢献・拡張

- 追加する機能例:
  - execution 層のブローカー統合・注文送信・注文ステータス同期
  - 品質チェック（quality モジュール）のルール強化
  - AI スコア生成パイプライン（ai_scores 更新）
  - モニタリング・アラート（Slack 経由等）
- プルリクエストや issue にてご提案ください。CI / テストの追加も歓迎します。

---

この README はコードベースから抽出した実装設計に基づく概要です。詳しい仕様（StrategyModel.md, DataPlatform.md 等）は別ドキュメントを参照してください。必要があれば README に具体的な CLI やスケジューリング例（cron / systemd / Airflow）を追加できます。