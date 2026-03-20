# KabuSys

KabuSys は日本株向けの自動売買基盤ライブラリです。市場データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査／実行レイヤのスキーマ定義などを含む、研究→本番までを想定したモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアス回避：各処理は target_date 時点のデータのみを参照するよう設計されています。
- 冪等性：DB 保存は ON CONFLICT を使うなど冪等化を重視。
- 最小外部依存：主要な統計処理は標準ライブラリで実装（pandas 等に依存しない実装を目指す）。
- 安全対策：ニュース収集での SSRF 対策や XML の安全パース、J-Quants API のレート制御／リトライ・トークン自動更新等を組み込んでいます。

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ユーティリティ
- データ取得 / ETL
  - J-Quants API クライアント（ページネーション、リトライ、レート制御、トークン自動更新）
  - ETL パイプライン（市場カレンダー、株価、財務データの差分取得と保存）
  - DuckDB スキーマ定義・初期化
- データ処理 / 研究ユーティリティ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - Zスコア正規化・統計サマリ・IC（Spearman）計算
  - 将来リターン計算（ホライズン指定）
- 特徴量・シグナル生成
  - features テーブル生成（正規化・ユニバースフィルタ含む）
  - シグナル生成（最終スコア計算、Buy/Sell 生成、Bear レジーム抑制、エグジット判定）
- ニュース収集
  - RSS 取得、トラッキングパラメータ除去、記事ID生成、銘柄抽出、DuckDB保存（重複排除）
  - SSRF 対策、gzip サイズ制限、XML セキュアパース
- 実行／監査レイヤ
  - signal / order / execution / positions などを含むスキーマ（監査ログ・トレーサビリティ設計）

---

## 必要条件（推奨）

- Python 3.10+
- 必要パッケージ（一例）
  - duckdb
  - defusedxml
- （ネットワーク接続）J-Quants API 利用時は API トークン（リフレッシュトークン）が必要

インストール例:
```
pip install duckdb defusedxml
# またはプロジェクトに requirements.txt があればそれを使用
```

---

## 環境変数

以下の環境変数が利用されます（README の一部。実際の利用には .env.example を参照してください）:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API 用パスワード（必須）
- KABUSYS_ENV           : 環境 ("development" / "paper_trading" / "live")（省略時 "development"）
- LOG_LEVEL             : ログレベル（"DEBUG","INFO",...）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite (monitoring) のパス（デフォルト: data/monitoring.db）

自動 .env 読み込み:
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探索して .env, .env.local を自動で読み込みます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須変数が未設定の状態でアクセスすると ValueError が投げられます。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. （推奨）仮想環境を作成・有効化
3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
4. .env をプロジェクトルートに作成（以下は例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   - .env.local を使うと OS 環境変数より優先して上書きできます（自動ロード時）。
5. DuckDB スキーマ初期化（Python から）
   ```py
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")
   # あるいはインメモリ:
   # conn = init_schema(":memory:")
   ```

---

## 使い方（主要なユースケース）

以下は主要なワークフローのサンプルです。実運用ではこれらをバッチジョブやスケジューラ（cron / Airflow 等）に組み込みます。

1) 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
```py
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量構築（features テーブルの作成）
```py
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {n}")
```

3) シグナル生成
```py
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 1, 31), threshold=0.6)
print(f"signals written: {count}")
```

4) ニュース収集（RSS）
```py
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄コード集合（extract_stock_codes で利用）
known_codes = {"7203", "6758", "9432"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) J-Quants からデータ取得（直接）
```py
from kabusys.data import jquants_client as jq
# トークンは settings.jquants_refresh_token を使って内部で取得／キャッシュされます
records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
# DB に保存:
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)
```

---

## 主要モジュール / ディレクトリ構成

リポジトリの主要構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得 + 保存）
    - news_collector.py          — RSS ニュース収集・保存
    - pipeline.py                — ETL パイプライン / ジョブ
    - schema.py                  — DuckDB スキーマ定義・init
    - stats.py                   — 統計ユーティリティ（zscore 等）
    - features.py                — features 公開インターフェース
    - calendar_management.py     — 市場カレンダー管理（営業日判定 etc.）
    - audit.py                   — 監査ログスキーマ
    - (他: quality, monitoring 等のサブモジュール想定)
  - research/
    - __init__.py
    - feature_exploration.py     — IC, forward returns, summary
    - factor_research.py         — momentum/value/volatility 計算
  - strategy/
    - __init__.py
    - feature_engineering.py    — features を構築するワークフロー
    - signal_generator.py       — final_score 計算・signals 登録
  - execution/                   — 発注/実行レイヤ（空パッケージ or 実装済みモジュール）
  - monitoring/                  — 監視・メトリクス収集（実装想定）

（README の最後の方のソース内部ドキュメントにより詳細な設計メモが記載されています）

---

## 開発／テストについて

- Python バージョンは 3.10 以降を想定（型ヒントで | を使用）。
- ネットワーク呼び出し（API/RSS）は統合テストでモックすることを推奨します。
- jquants_client のテスト時にトークン自動更新やレートリミッタ挙動をモックすると良いです。
- DuckDB をインメモリ（":memory:"）で初期化すると単体テストが高速に行えます。

---

## 注意点 / 運用上の留意事項

- 本ライブラリは発注・実行ロジックと分離されており、戦略層は発注 API に直接依存しません。実際の発注は execution 層／オペレーション実装に委ねてください。
- Live 環境での運用前に paper_trading で十分な検証を行ってください。
- 環境変数や秘密情報は .env を使って管理するか、CI/CD のシークレット管理機能を使ってください。
- ニュース収集など外部入力は想定どおりでないデータ（巨大ペイロード、悪意ある XML 等）を受け取る可能性があります。fetch_rss 等は複数の防御層を備えていますが、運用側でも監視とレート制限を行ってください。

---

以上が KabuSys の概要と導入・利用ガイドです。さらに詳しい設計仕様（StrategyModel.md、DataPlatform.md 等）はソース内の docstring やプロジェクト内ドキュメントを参照してください。必要であれば README を英語版に翻訳したり、サンプルスクリプト（run_etl.py / run_signals.py 等）を追加で用意します。希望があれば教えてください。