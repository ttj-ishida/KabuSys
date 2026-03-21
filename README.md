# KabuSys

日本株自動売買プラットフォームのコアライブラリ（ミニマム実装）。  
市場データの取得・ETL、特徴量計算、シグナル生成、ニュース収集、監査スキーマ等を含むモジュール群を提供します。

> 注意: これはフル機能の運用システムではなく、内部ロジックや DB スキーマ・ETL の実装を示すコードベースです。実際の発注・運用には十分な検証・テストと運用ルールが必要です。

## 主な機能

- 環境設定管理
  - `.env` / 環境変数読み込み（自動ロード機能付き）
  - 必須変数チェック（settings オブジェクト）
- データ取得・ETL（J-Quants API 経由）
  - 株価（日足）、財務データ、JPX カレンダーの差分取得（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- DuckDB スキーマ定義・初期化（冪等）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義
- データ処理ユーティリティ
  - Zスコア正規化など（外部ライブラリに依存しない実装）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量生成（strategy.feature_engineering）
  - research モジュールの生ファクターを正規化・合成して features テーブルへ保存
  - ユニバースフィルタ（最低株価・最低売買代金）
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算
  - BUY / SELL シグナル生成（Bear レジーム抑制、エグジット判定含む）
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、raw_news 保存、銘柄コード抽出
  - SSRF / XML Bomb / 大容量応答対策等の安全対策
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定、次/前営業日、期間の営業日列挙
  - 夜間バッチでカレンダー更新
- 監査ログスキーマ（data.audit）
  - signal → order_request → execution までのトレースを可能にするテーブル群

## 前提条件

- Python 3.10+（型ヒントで union 表記などを使用）
- DuckDB
- defusedxml（RSS の安全なパース）
- ネットワークアクセス（J-Quants API、RSS フィード等）
- J-Quants のリフレッシュトークン等の環境変数

主なライブラリ（pip インストール例）
- duckdb
- defusedxml

必要に応じて他の HTTP ライブラリ等を追加できますが、現状は標準ライブラリ + 上記のみで動作するよう設計されています。

## セットアップ手順（開発用）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   （requirements.txt が無い場合は最低限以下を入れてください）
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を配置すると自動的にロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていると無効）。主な変数:

   - JQUANTS_REFRESH_TOKEN=...     （必須: J-Quants API 用リフレッシュトークン）
   - KABU_API_PASSWORD=...        （必須: kabuステーション API パスワード）
   - KABU_API_BASE_URL=...        （任意: デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN=...          （必須: Slack 通知用）
   - SLACK_CHANNEL_ID=...         （必須: Slack 通知用）
   - DUCKDB_PATH=data/kabusys.duckdb  （任意: DuckDB ファイルパス）
   - SQLITE_PATH=data/monitoring.db    （任意）
   - KABUSYS_ENV=development | paper_trading | live
   - LOG_LEVEL=INFO | DEBUG | ...

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

   自動ロードを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

## データベース初期化

DuckDB のスキーマを初期化するには `kabusys.data.schema.init_schema()` を呼び出します。例:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

初期化は冪等（既にテーブルがあればスキップ）です。

## ETL（データパイプライン）実行例

日次 ETL は `kabusys.data.pipeline.run_daily_etl` を使います。J-Quants のトークンは settings から読まれますが、テストのため `id_token` を直接渡すことも可能です。

```python
from kabusys.data import pipeline
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

run_daily_etl は以下を順に実行します:
1. market_calendar の差分取得・保存
2. prices（日足）の差分取得・保存（バックフィルあり）
3. financials（財務）の差分取得・保存
4. 品質チェック（オプション）

戻り値は ETLResult 型で、品質問題やエラーの一覧を含みます。

## 特徴量生成 / シグナル生成（戦略ワークフロー）

特徴量生成（features テーブルの作成）:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 10))
print(f"features upserted: {count}")
```

シグナル生成（signals テーブルへの書き込み）:

```python
from datetime import date
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
n_signals = generate_signals(conn, target_date=date(2024, 1, 10))
print(f"signals written: {n_signals}")
```

generate_signals は weights（重み）や閾値（threshold）を引数で渡せます。AI スコアは ai_scores テーブルから読み込まれます。Bear レジーム判定、エグジット判定（ストップロス等）を含みます。

## ニュース収集実行例

デフォルト RSS ソースからニュースを収集して DB に保存します（raw_news / news_symbols）。

```python
from kabusys.data.schema import init_schema
from kabusys.data import news_collector as nc

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "6501"}  # 既知の銘柄コードセット
results = nc.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

内部で URL 正規化、ID 作成（SHA-256 先頭32文字）、前処理、SSRF/圧縮/サイズチェック等を実施します。

## カレンダー更新ジョブ

夜間バッチとして JPX カレンダーを更新する関数:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved calendar rows: {saved}")
```

## 監査ログ（発注→約定のトレース）

data.audit モジュールは signal_events / order_requests / executions など監査用テーブル定義を含みます。init_schema により必要テーブルは生成されます。実際の発注ロジック（broker API 呼び出し）と連携して order_requests を挿入・更新し、executions を保存することでトレース可能になります。

## 開発・デバッグのヒント

- 設定は `kabusys.config.settings` を通じて参照できます（属性アクセス）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行われます。テスト時に環境設定を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のリクエストは内部で固定間隔スロットリング（120 req/min）とリトライを行います。大量取得時は注意。
- DuckDB 接続は `duckdb.connect()` により得たコネクションオブジェクトをそのまま関数に渡して使用します。トランザクション制御は各モジュールで行われる箇所があります（BEGIN/COMMIT/ROLLBACK）。

## ディレクトリ構成

主要ファイル／ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS ニュース収集・保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン（差分更新等）
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - features.py                  — data.stats の再エクスポート
    - calendar_management.py       — 市場カレンダーの管理・ジョブ
    - audit.py                     — 監査ログスキーマ（signal/order/execution）
    - audit_indexes...?            — （インデックス定義は schema 内）
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Volatility/Value の計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py       — features のビルド（正規化・フィルタ）
    - signal_generator.py          — final_score 計算・BUY/SELL 生成
  - execution/
    - __init__.py                  — 発注関連モジュール（未実装部分含む）
  - monitoring/                     — 監視関連（存在は示唆されるが詳細はコード参照）
- pyproject.toml / setup.py 等（プロジェクトルート想定）
- .env.example（プロジェクトルートに作成推奨）

（上記はコードベースの主要モジュールを抜粋しています。実際の repo には追加ドキュメント・テストが含まれることがあります。）

## 運用上の注意

- 実際の注文（発注 API）を有効にする前に、ペーパー取引／ロジック検証を徹底してください。コードにはペーパー/本番フラグ（KABUSYS_ENV）があり、live 環境時の保護が必要です。
- 取引や資金管理の責任は利用者側にあります。本リポジトリは学習・研究・プロトタイプ目的で提供されています。
- 外部 API の利用（J-Quants 等）は利用規約に従ってください。大量リクエストや商用利用時は API 提供元と合意が必要です。

---

必要があれば README に追記すべき内容（例: インストール用 requirements.txt の提案、テストの実行方法、CI 設定、運用チェックリスト 等）を教えてください。