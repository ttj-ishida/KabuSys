# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データ収集（J-Quants）、ETL、マーケットカレンダー管理、ニュース収集、特徴量計算、シグナル生成、監査/実行スキーマなどを含む一連の機能を提供します。研究（research）と本番（execution）層を分離し、DuckDB をデータストアとして利用する設計になっています。

バージョン: 0.1.0

---

## 特長（機能一覧）

- データ取得
  - J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - 株価（OHLCV）、財務データ、マーケットカレンダーの取得と DuckDB への冪等保存
- ETL / データパイプライン
  - 差分更新（最終取得日を基に差分を取得）
  - バックフィル対応（直近数日を再取得して API の後出し修正を吸収）
  - 品質チェック呼び出し（quality モジュールによる欠損・スパイク等の検出）
  - 日次 ETL の統合エントリポイント（run_daily_etl）
- カレンダー管理
  - JPX マーケットカレンダー保持・営業日判定・next/prev 営業日取得等
- ニュース収集
  - RSS フィード収集（SSRF対策、gzip 対応、トラッキングパラメータ除去、記事ID は URL の SHA-256 に基づく）
  - raw_news / news_symbols への冪等保存
- 研究（research）ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ
- 戦略（strategy）
  - 特徴量構築（build_features）：研究出力の正規化・フィルタリング・features テーブルへの UPSERT
  - シグナル生成（generate_signals）：features と ai_scores を統合して BUY/SELL シグナルを作成し signals テーブルへ登録
  - Bear レジーム抑制、売り（エグジット）ロジック（ストップロス等）を含む
- スキーマ / 監査 / 実行レイヤー
  - DuckDB のスキーマ定義と初期化（init_schema）
  - 実行・監査用テーブル（signals / signal_queue / orders / executions / positions / audit tables 等）

---

## 必要条件

- Python 3.10 以上（型注釈に PEP 604 の X | Y 構文を使用）
- DuckDB（Python バインディング）
- defusedxml（RSS パースの安全化）
- 標準ライブラリ（urllib 等）を使用

推奨インストール例（仮）:
pip install duckdb defusedxml

※プロジェクト配布時に requirements.txt / pyproject.toml を用意してください。

---

## 環境変数（主な設定）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development, paper_trading, live）デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）デフォルト: INFO

設定例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. Python 環境を用意（仮想環境推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   （パッケージはプロジェクトの pyproject.toml / requirements.txt に合わせてください）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートします。
   - 自動ロードは .env / .env.local を検索します（プロジェクトルートは .git または pyproject.toml を基準に検出）。

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで init_schema を呼び出します（DUCKDB_PATH は settings.duckdb_path を参照します）。
   例:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成・テーブルを作る
   conn.close()
   ```

---

## 使い方（主要な操作例）

以下はライブラリを利用するための典型的なコード例です。

1) DuckDB の初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行（J-Quants からデータ取得 → 保存 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量構築（research の計算結果を正規化して features テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（features と ai_scores を統合して signals テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import generate_signals

total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {total}")
```

5) ニュース収集ジョブの実行（RSS 収集 → raw_news 保存 → news_symbols 紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) J-Quants API からの直接取得例
```python
from kabusys.data.jquants_client import fetch_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 実行環境（env）について

- settings.is_live / is_paper / is_dev によって環境を判定できます。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかで指定します。
- 本番運用時は env=live にし、ログレベルや Slack 通知などを適切に設定してください。

---

## ディレクトリ構成（主要ファイル説明）

（`src/kabusys/` 以下）

- __init__.py
  - パッケージの公開 API を定義（data, strategy, execution, monitoring）

- config.py
  - 環境変数の自動読み込み（.env / .env.local）、Settings クラス（設定プロパティ）

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント、取得・保存ユーティリティ、レート制限、リトライ、認証
  - schema.py
    - DuckDB スキーマ定義と初期化（init_schema / get_connection）
  - pipeline.py
    - ETL パイプライン（run_daily_etl、個別 ETL ジョブ run_prices_etl 等）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - news_collector.py
    - RSS 収集、前処理、raw_news 保存、銘柄抽出・紐付け
  - calendar_management.py
    - 市場カレンダーの管理、is_trading_day / next_trading_day / get_trading_days 等
  - features.py
    - public re-export（zscore_normalize）
  - audit.py
    - 監査ログ用スキーマ（signal_events / order_requests / executions など）

- research/
  - __init__.py
  - factor_research.py
    - momentum / volatility / value 等のファクター計算
  - feature_exploration.py
    - 将来リターン calc_forward_returns、IC calc_ic、統計サマリー factor_summary

- strategy/
  - __init__.py
  - feature_engineering.py
    - research の生ファクターを正規化・合成して features テーブルへ保存
  - signal_generator.py
    - features と ai_scores を統合して BUY/SELL シグナルを算出し signals テーブルへ書き込む

- execution/
  - （発注・実行レイヤーの実装ファイル（空ファイルや将来的な実装））

- monitoring/
  - （監視・アラート用の実装が入る想定）

---

## ロギングとエラーハンドリング

- 多くのモジュールで logging を利用しています。アプリ側でログ設定を行ってください（例: logging.basicConfig や dictConfig）。
- ETL や収集処理はステップごとに個別に例外処理され、1ステップが失敗しても残りの処理は継続する設計です。最終的な結果は ETLResult 等で集約されます。

---

## 注意点 / 実運用上の考慮

- DuckDB のトランザクションはモジュール内で明示的に BEGIN/COMMIT/ROLLBACK が使用されています。アプリケーション側でもコネクションの使い方に注意してください。
- J-Quants API のレートリミット（120 req/min）やリトライ挙動を尊重してください。
- ニュース収集は SSRF 対策・レスポンスサイズ制限・XML パースの防護（defusedxml）を組み込んでいますが、外部フィードを追加する際はソースの信頼性を考慮してください。
- 本番実行（live）時は特に設定値と権限（API トークン、kabu API への接続、Slack トークンなど）を厳格に管理してください。

---

## 貢献・拡張ポイント（今後の導入候補）

- execution 層の証券会社ブローカーラッパーの実装（kabu API 実送信 / 注文追跡）
- AI スコアの算出パイプライン（ai_scores の生成）
- quality モジュールの実装と詳細ログ出力
- テストカバレッジと CI ワークフロー（自動 DB 初期化・モック J-Quants）

---

README に不足している点やサンプルスクリプト（起動スクリプトや CLI）の追加希望があれば、必要に応じて追記します。