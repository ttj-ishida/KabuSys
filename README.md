# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のリポジトリ用 README。  
本ドキュメントはこのコードベースの概要、主要機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- 前提
- セットアップ手順
- 環境変数（.env）
- 基本的な使い方（コード例）
- よく使うユースケース
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含む自動売買プラットフォームのコアライブラリです。  
設計方針としては、ルックアヘッドバイアス回避、冪等性（idempotency）、堅牢なエラーハンドリング、DuckDB を中心としたローカルDB運用を重視しています。

主に以下のレイヤーを含みます：
- data: J-Quants クライアント、ETL、DuckDB スキーマ定義、ニュース収集、カレンダー管理、統計ユーティリティ
- research: 研究用のファクター計算や探索ツール
- strategy: 特徴量エンジニアリング、シグナル生成
- execution: 発注/実行に関する層（パッケージに置かれています）
- monitoring: 監視／ロギング等（パッケージインターフェースには含まれます）

---

## 機能一覧（実装済み・主要機能）

- J-Quants API クライアント
  - 日足データ、財務データ、マーケットカレンダー取得（ページネーション対応）
  - レートリミット対応、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存 utilities（ON CONFLICT を利用）

- DuckDB スキーマ管理
  - raw / processed / feature / execution レイヤーのテーブル定義と初期化
  - インデックス作成

- ETL パイプライン
  - 日次差分 ETL（calendar, prices, financials）
  - 差分取得ロジック、バックフィル、品質チェック（quality モジュールを呼ぶ設計）

- 研究（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリー

- 戦略（strategy）
  - ファクター正規化（Zスコア）と features テーブルへの書き込み
  - features と AI スコア統合による final_score 計算、BUY/SELL シグナル生成（signals テーブルへ保存）
  - Bear レジーム抑制、エグジット（ストップロス等）

- ニュース収集（news_collector）
  - RSS フィード取得、前処理、raw_news 保存、銘柄抽出（簡易正規表現）
  - SSRF 対策、XML の安全パース、サイズ制限、ID 冪等化（URL 正規化→ハッシュ）

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / get_trading_days 等ユーティリティ
  - カレンダー差分更新ジョブ

- 監査ログ（audit）設計（テーブル定義含む）
  - signal_events / order_requests / executions など監査用テーブル

---

## 前提

- Python 3.10 以上（型ヒントに union | を使用）
- 必要な主要パッケージ（最低限）：
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS フィード等）
- J-Quants のリフレッシュトークン等の外部認証情報

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを優先してください）

---

## セットアップ手順

1. リポジトリをクローン／取得します。

2. 仮想環境を作成して有効化（推奨）：
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール（最低限）：
   ```
   pip install duckdb defusedxml
   ```
   - 実環境では logging/requests 等を追加することもあるため、プロジェクトで提供されている要件ファイルがあればそちらを使用してください（pip install -r requirements.txt または pip install -e .）。

4. DuckDB スキーマを初期化する（例）:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   これにより必要なテーブル群が作成されます。

---

## 環境変数（.env）

KabuSys は .env ファイルまたは環境変数から設定を読み込みます。プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（Settings から参照されるもの）：

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants API 用リフレッシュトークン。

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード。

- KABU_API_BASE_URL (任意)  
  kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）。

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン。

- SLACK_CHANNEL_ID (必須)  
  Slack 送信先チャンネル ID。

- DUCKDB_PATH (任意)  
  デフォルト DB パス（デフォルト: data/kabusys.duckdb）。

- SQLITE_PATH (任意)  
  監視等に使う SQLite パス（デフォルト: data/monitoring.db）。

- KABUSYS_ENV (任意)  
  実行モード: development / paper_trading / live（デフォルト: development）。

- LOG_LEVEL (任意)  
  ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）。

.env の読み込みルール：
- OS 環境変数が優先される
- .env が読み込まれ、さらに .env.local は上書き（ただし OS 環境変数は保護）
- export KEY=val 形式、引用符、インラインコメント等に対応するパーサを使用

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 基本的な使い方（コード例）

以下は対話的にライブラリを利用する際の代表的なフロー例です。

1) DB の初期化（1回だけ）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行（J-Quants からデータ取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn)
print(res.to_dict())
```

3) 特徴量（features）を構築
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナルを生成して保存
```python
from kabusys.strategy import generate_signals
from datetime import date

num_signals = generate_signals(conn, target_date=date.today())
print(f"signals generated: {num_signals}")
```

5) RSS ニュース収集（news_collector の統合ジョブ）
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット（例）
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) マーケットカレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## よく使うユースケースと注意点

- ETL を定期実行する際は cron / scheduler から run_daily_etl を呼び出す。J-Quants のレート制限に注意する（内部で制御あり）。
- DuckDB ファイルのバックアップ（データ保全）は運用ポリシーに従って定期的に行うこと。
- features / signals は日付単位で置換（DELETE + bulk INSERT）するため、同一日に何度でも安全に再実行可能（冪等）。
- NewsCollector は外部 URL の扱いがあるため、ファイアウォールやプロキシ設定等に注意。
- settings.is_live / is_paper を使って実行モードに応じた挙動切替を実装することを想定している（実行時は KABUSYS_ENV を設定）。

---

## ディレクトリ構成

主要なファイル／モジュール構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境設定と Settings クラス
    - data/
      - __init__.py
      - jquants_client.py          # J-Quants API クライアント（取得 & 保存）
      - schema.py                  # DuckDB スキーマ定義と init_schema
      - pipeline.py                # ETL パイプライン（run_daily_etl 等）
      - stats.py                   # Zスコア正規化等統計ユーティリティ
      - news_collector.py          # RSS 収集・保存・銘柄抽出
      - calendar_management.py     # マーケットカレンダー管理
      - features.py                # features の公開インターフェース
      - audit.py                   # 監査ログ（テーブル定義）
      - pipeline.py                # ETL 実行ロジック
    - research/
      - __init__.py
      - factor_research.py         # モメンタム/ボラティリティ/バリュー計算
      - feature_exploration.py     # 将来リターン / IC / summary
    - strategy/
      - __init__.py
      - feature_engineering.py     # features の構築
      - signal_generator.py        # final_score と signals 生成
    - execution/
      - __init__.py                # 発注/実行層（雛形）
    - monitoring/                  # 監視 / 通知等（パッケージインターフェースに含める想定）
    - ... その他

（リポジトリ全体には README や docs、CI 設定ファイル等が含まれる場合があります）

---

必要に応じて README の補足（例: デプロイ手順、CI 実行、テストの書き方、外部サービス連携方法など）を追加で作成できます。どの情報を優先的に追記したいか教えてください。