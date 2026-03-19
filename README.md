# KabuSys

KabuSys は日本株の自動売買基盤（研究・データプラットフォーム・戦略・実行・監視）を想定した Python パッケージです。  
DuckDB をデータ格納に用い、J-Quants API から市場データを取得して特徴量を生成し、戦略シグナルを算出します。設計上、ルックアヘッドバイアス対策・冪等性・堅牢な ETL・API レート制御・セキュリティ対策（SSRF / XML パース攻撃対策）などが組み込まれています。

バージョン: 0.1.0

---

## 主な機能一覧

- データ収集（J-Quants API）  
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの取得。レート制限、再試行、トークン自動更新に対応。
- ETL パイプライン（差分更新／バックフィル）  
  - run_daily_etl 等の関数でカレンダー／価格／財務データを差分取得・保存。
- DuckDB スキーマ定義・初期化  
  - raw / processed / feature / execution 層のテーブルを定義。init_schema() で初期化。
- ニュース収集（RSS）  
  - RSS 収集、前処理、トラッキングパラメータ除去、記事ID の SHA-256 による冪等保存、SSRF 対策、XML 脆弱性対策。
- 研究（research）ユーティリティ  
  - ファクター計算（モメンタム・ボラティリティ・バリュー）、将来リターン、IC 計算、統計サマリ等。
- 特徴量生成（feature engineering）  
  - 生ファクターを正規化（Z スコア）、ユニバースフィルタ適用、features テーブルへ日付単位で UPSERT（冪等）。
- シグナル生成（signal generation）  
  - 正規化済み特徴量と AI スコアを統合して final_score を算出。BUY/SELL シグナルを signals テーブルへ保存。Bear レジーム抑制やエグジット（ストップロス等）を実装。
- カレンダー管理、営業日ユーティリティ  
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days など。
- 監査ログ（audit）設計  
  - シグナル→発注→約定までトレーサビリティを取るテーブル定義を含む。
- 汎用統計ユーティリティ（zscore_normalize 等）

---

## セットアップ手順

前提:
- Python 3.9+（実行環境に合わせて確認してください）
- DuckDB（Python ライブラリとして pip でインストール）
- ネットワークアクセス（J-Quants API への接続）

1. リポジトリをチェックアウトしてパッケージをインストール
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m pip install -e .
   ```
   あるいは依存パッケージを個別にインストール:
   ```bash
   python -m pip install duckdb defusedxml
   ```

2. 環境変数を設定（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabu ステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知に使う Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャネル ID（必須）

   オプション:
   - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL : DEBUG / INFO / ...（デフォルト: INFO）
   - DUCKDB_PATH : デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH : デフォルト "data/monitoring.db"

   .env / .env.local の自動読み込み:
   - パッケージはプロジェクトルート（.git または pyproject.toml がある場所）から `.env` と `.env.local` を自動的に読み込みます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. DuckDB スキーマ初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema, settings
   conn = init_schema(settings.duckdb_path)  # デフォルトは data/kabusys.duckdb
   ```
   これで全テーブルとインデックスが作成されます（冪等）。

---

## 使い方（主要 API の例）

以下は代表的な使い方の例です。実運用時はログ設定や例外ハンドリングを適切に行ってください。

1. 日次 ETL（市場カレンダー＋株価＋財務＋品質チェック）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 特徴量ビルド（feature_engineering）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   ```

3. シグナル生成
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals written: {total}")
   ```

4. ニュース収集ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "4502"}  # 有効銘柄コードのセット
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

5. J-Quants から直接データ取得（低レベル）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes
   quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   ```

---

## 重要な環境変数

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- KABUSYS_ENV (development / paper_trading / live) — settings.is_live / is_paper / is_dev で参照
- LOG_LEVEL (DEBUG/INFO/...)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 にすると .env 自動読み込みを無効化)

settings モジュール例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

設定が未定義の必須キーを参照すると ValueError が発生します（明示的な早期検出のため）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールと役割の一覧です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                - 環境変数・設定管理（.env 自動読み込み、検証）
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント（レート制御・リトライ・保存関数）
    - news_collector.py      - RSS 収集・前処理・DB 保存（SSRF/XML 対策）
    - schema.py              - DuckDB スキーマ定義・初期化
    - pipeline.py            - ETL パイプライン（run_daily_etl 等）
    - features.py            - data.stats の再エクスポート
    - stats.py               - zscore_normalize 等の統計ユーティリティ
    - calendar_management.py - カレンダー更新・営業日ユーティリティ
    - audit.py               - 監査ログ用テーブル定義
    - quality.py?            - （品質チェックモジュール; pipeline から参照される想定）
  - research/
    - __init__.py
    - factor_research.py     - ファクター計算（momentum/volatility/value）
    - feature_exploration.py - 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py - features 作成（正規化・ユニバースフィルタ）
    - signal_generator.py    - final_score 算出・BUY/SELL シグナル生成
  - execution/
    - __init__.py            - 実行層（発注等）用のエントリ（実装は拡張想定）
  - monitoring/              - 監視・アラート用（実装や補助コードを想定）

補足: 上記はソース内コメントやモジュールの docstring に基づく主要機能の説明です。実際の実装・追加モジュールはリポジトリ全体を参照してください。

---

## 運用上の注意点

- J-Quants API のレート制限を尊重してください（モジュール内で 120 req/min 制御が実装されていますが、複数プロセスでの同時アクセスは注意が必要）。
- production（live）モードでは誤発注防止や追加の安全チェックが必要です。KABUSYS_ENV を適切に設定してください。
- DuckDB ファイルや SQLite ファイルはバックアップ・権限管理を行ってください。
- ニュース収集は外部 RSS に依存するため、ソース側の変更やフォーマットによりパース失敗が発生する可能性があります。ログ監視を推奨します。
- テスト環境で自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

---

## 貢献 / 拡張ポイント（概略）

- execution 層: 証券会社 API とのブリッジ（冪等な送信・再試行・監査連携）
- リスク管理 / ポートフォリオ最適化モジュール
- AI スコアリングパイプライン（ai_scores 登録）
- モニタリング / アラート（Slack 連携や Prometheus Exporter 等）
- テストカバレッジの拡充（ユニット／統合テスト）

---

README に含める追加情報（運用手順、CI、デプロイ手順、より詳細な API リファレンス等）や、特に強調したい点があれば教えてください。必要に応じてサンプルスクリプトや CLI ラッパーの例も作成します。