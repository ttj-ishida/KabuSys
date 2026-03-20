# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
データ取得（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含む。DuckDBをデータ層に用い、ルックアヘッドバイアス対策や冪等性を意識して設計されています。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ収集
  - J-Quants API クライアント（株価日足 / 財務 / マーケットカレンダー）
  - RSS ベースのニュース収集（SSRF対策・トラッキングパラメータ除去・記事IDの冪等化）
- データ基盤
  - DuckDB スキーマ定義と初期化 / 接続ユーティリティ
  - ETLパイプライン（差分取得・バックフィル・品質チェック呼び出し）
  - 市場カレンダー管理（営業日判定・前後営業日取得・夜間更新ジョブ）
- リサーチ / 特徴量
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - Zスコア正規化ユーティリティ
  - 将来リターン・IC・統計サマリー等の分析関数
- 戦略層
  - 特徴量作成（researchで作成した生ファクターを正規化・フィルタして features テーブルへ）
  - シグナル生成（features と AI スコアを統合し BUY/SELL シグナルを生成）
- 実行・監査
  - 実行（Execution）層用スキーマ（orders / trades / positions 等）および監査ログ用テーブル（signal_events / order_requests / executions）
- 汎用ユーティリティ
  - 設定管理（.env の自動読み込み・環境変数の集中管理）
  - ロギング / レートリミット / リトライ戦略（J-Quants クライアント）

---

## 必要条件

- Python 3.9+（型ヒントで | を使用しているため）
- 必須パッケージ（例）:
  - duckdb
  - defusedxml

（実行環境に応じて他のパッケージが必要になることがあります。プロジェクトの pyproject.toml / requirements.txt を参照してください。）

---

## セットアップ手順

1. リポジトリをクローン（既にソースがある前提ならこのステップは不要）
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （開発時）pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` を配置すると自動で読み込まれます（.git / pyproject.toml を基準にプロジェクトルートを探索）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（Settings で参照・必須としているもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

その他（デフォルト値あり）
- KABUS_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, …）

.env の例（簡易）
```
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本的な例）

以下は Python REPL やスクリプトから主要機能を呼ぶ例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

2) 日次 ETL（J-Quants からデータ取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量構築（features テーブルへ）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date.today())
print(f"{n} 銘柄の features を構築しました")
```

4) シグナル生成（signals テーブルへ）
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"{count} 件のシグナルを保存しました")
```

5) ニュース収集ジョブ（RSS → raw_news / news_symbols）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes を渡すと記事と銘柄の紐付け抽出を行う
known_codes = {"7203", "6758", ...}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # 各ソースごとの新規保存件数
```

注意:
- 上記関数は DB の存在・スキーマ状態に依存します。初回は init_schema を必ず呼んでください。
- run_daily_etl などはエラーを捕捉しつつ処理を継続する設計です。結果オブジェクトに errors / quality_issues が格納されます。

---

## よく使うモジュール（概観）

- kabusys.config
  - 環境変数読み込み・Settings クラス
- kabusys.data
  - jquants_client.py — J-Quants API クライアント（取得／保存関数含む）
  - schema.py — DuckDB スキーマ定義と初期化
  - pipeline.py — ETL 実行フロー（run_daily_etl 等）
  - news_collector.py — RSS 取得・前処理・DB保存
  - calendar_management.py — 市場カレンダー管理、営業日判定
  - features.py / stats.py — Z スコア正規化等
  - audit.py — 監査ログ用テーブル定義
- kabusys.research
  - factor_research.py — モメンタム / ボラティリティ / バリューの計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- kabusys.strategy
  - feature_engineering.py — features テーブル作成
  - signal_generator.py — final_score 計算と signals テーブル生成
- kabusys.execution
  - （将来的な発注ラッパー等を想定したパッケージ）

---

## ディレクトリ構成

プロジェクトの主要ファイル・フォルダ構成（抜粋）
```
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      calendar_management.py
      stats.py
      features.py
      audit.py
      ...
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
      ...
    strategy/
      __init__.py
      feature_engineering.py
      signal_generator.py
    execution/
      __init__.py
    monitoring/
      ...
```

各サブパッケージは概ね次の責務を持ちます：
- data: データ取得・保存・ETL・カレンダー・ニュース等のデータ基盤
- research: リサーチ・ファクター計算・探索ツール
- strategy: 特徴量合成・スコアリング・シグナル生成
- execution: ブローカー（kabu）への発注ラッパーや注文管理（将来的に拡張）
- monitoring: 監視・アラート関連（インターフェース）

---

## 運用上の注意 / 設計上のポイント

- ルックアヘッドバイアス対策:
  - 各計算は target_date 時点で利用可能なデータのみを用いる設計を意識しています（fetched_at や日付選択に注意）。
- 冪等性:
  - J-Quants からの保存は ON CONFLICT / UPSERT を使い、重複を排除する実装です。
- レート制限・リトライ:
  - J-Quants クライアントは 120 req/min のレート制限と、指数バックオフを備えています。401 はトークン自動リフレッシュを試みます。
- セキュリティ:
  - RSS の取得・解析では SSRF 対策、defusedxml を利用した XML パース、レスポンスサイズ制限などを実装しています。
- テスト:
  - 環境変数自動読み込みはテストで邪魔になる場合があるため、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

## 追加情報 / 今後の拡張

- execution パッケージには証券会社 API（kabu API）との実取引ラッパーを実装予定（現在はスキーマと設定を用意）。
- モニタリング・アラート機能（Slack通知等）や戦略パラメータのUI化などの拡張が想定されています。

---

ご不明点や README に追記してほしい情報（例: CI／テスト方法、具体的なデプロイ手順、pyproject/依存一覧など）があれば教えてください。必要に応じて補足の章を追加します。