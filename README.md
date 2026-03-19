# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データプラットフォームです。J-Quants API から市場データと財務データ、RSS ニュースを収集して DuckDB に保存し、研究用ファクター計算・特徴量生成・シグナル生成・発注監査を行うためのモジュール群を提供します。

---

## 主な特徴

- J-Quants API クライアント
  - 日足（OHLCV）・財務諸表・JPX カレンダー取得（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し、ルックアヘッドバイアスを低減
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層を包含するスキーマ
  - 冪等（ON CONFLICT）での保存を前提とした実装
- ETL パイプライン
  - 日次差分更新（バックフィル対応）、品質チェック（別モジュール）
- 研究（research）モジュール
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
- 特徴量エンジニアリング
  - ファクターのZスコア正規化・ユニバースフィルタ適用・features テーブルへのUPSERT
- シグナル生成
  - 正規化済み特徴量＋AIスコアを統合して final_score を算出
  - Bear レジーム抑制、BUY/SELL シグナルを signals テーブルへ保存
  - 保有ポジションのエグジット判定（ストップロス等）
- ニュース収集
  - RSS 収集・前処理・記事ID生成（URL正規化→SHA-256）・銘柄抽出（4桁コード）
  - SSRF・XML攻撃・巨大レスポンス対策を組み込んだ実装
- 発注・監査スキーマ（テーブル群の設計）
  - シグナル→発注要求→約定 まで追跡可能な監査テーブル

---

## 必要条件（概略）

- Python 3.10+
- duckdb
- defusedxml
- （標準ライブラリのみで動作するユーティリティも多く含まれますが、外部ライブラリは上記を想定）

具体的な依存関係はプロジェクトの packaging / requirements ファイルを参照してください。

---

## セットアップ手順

1. リポジトリをクローン、またはプロジェクトを取得する

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb defusedxml

   （パッケージ化されている場合は pip install -e . などを利用）

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト値あり）:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト INFO）

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は Python スクリプトや REPL から呼び出す想定のサンプルです。

- スキーマ初期化（DuckDB）
  ```python
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")
  # または
  conn = get_connection("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量のビルド（build_features）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  count = build_features(conn, target_date=date(2025, 1, 20))
  print("features upserted:", count)
  ```

- シグナル生成（generate_signals）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  total_signals = generate_signals(conn, target_date=date(2025, 1, 20))
  print("signals written:", total_signals)
  ```

- ニュース収集（RSS → DB）
  ```python
  from kabusys.data.news_collector import run_news_collection
  res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(res)  # {source_name: saved_count}
  ```

- J-Quants からデータ取得（低レベル）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = save_daily_quotes(conn, records)
  ```

ログ出力や動作モード（開発／紙取引／ライブ）は環境変数 KABUSYS_ENV により切り替えられます（Settings.is_live / is_paper / is_dev を参照）。

---

## 注意点 / 運用メモ

- .env の自動ロード
  - パッケージはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）から `.env` / `.env.local` を自動読み込みします。
  - テスト等で自動ロードを避けたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限（120 req/min）やリトライロジックを組み込んでありますが、運用ではさらにスケジューリング（cron / Airflow など）とモニタリングを検討してください。
- ニュース RSS の取り扱い
  - _is_private_host / SSRF 対策・受信サイズ制限・defusedxml による XML 攻撃対策 を実装済みです。
- データの永続化は DuckDB を想定。DB のバックアップ・永続化戦略は運用側で用意してください。
- 発注・実行ロジックは設計・監査テーブルを備えていますが、実際の証券会社 API との接続・エラーハンドリングは別途 adapter を実装する必要があります。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得 / 保存）
    - news_collector.py           — RSS ニュース収集・保存
    - schema.py                   — DuckDB スキーマ定義と初期化
    - stats.py                    — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - features.py                 — data.stats の再エクスポート
    - calendar_management.py      — 市場カレンダー管理（営業日関数）
    - audit.py                    — 発注監査ログの DDL
    - (その他: quality 等は別モジュールとして参照想定)
  - research/
    - __init__.py
    - factor_research.py          — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py      — 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py      — features を構築する処理（正規化・UPSERT）
    - signal_generator.py         — final_score 計算・BUY/SELL 生成
  - execution/                    — 発注実装層（空の __init__ あり）
  - monitoring/                   — モニタリング用モジュール（未記載ファイルとして想定）

（README に記載されている以外にも細かなヘルパー関数が各モジュールに実装されています）

---

## 開発／貢献

- コーディング規約やテストはプロジェクト内の CONTRIBUTING.md / pyproject.toml / tests を参照してください（存在する場合）。
- 簡単なユニットテストは DuckDB のインメモリ ":memory:" DB を用いることで簡便に行えます。

---

## ライセンス

プロジェクトのルートにある LICENSE ファイルを参照してください。

---

問い合わせ・運用に関する質問があれば、該当モジュール名・目的（例: "シグナル生成ロジックの重み調整方法"）を添えて教えてください。README の補足やサンプルスクリプトを追加します。