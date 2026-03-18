# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）です。  
データ収集（J-Quants）、DuckDB を使ったデータ基盤、特徴量計算・ファクター研究、ETL パイプライン、ニュース収集、品質チェック、監査ログ（発注→約定のトレース）等の基盤機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得
  - J-Quants API クライアント（レート制御・リトライ・トークン自動更新・ページネーション対応）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー取得
- データ基盤
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - 冪等保存（ON CONFLICT 相当）を行う保存ユーティリティ
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得 + バックフィル）
  - 市場カレンダー先読み、品質チェックの統合（欠損 / スパイク / 重複 / 日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集
  - RSS フィード収集（gzip 対応）と前処理、記事 ID のハッシュ化による冪等保存
  - SSRF 対策、受信サイズ制限、トラッキングパラメータ除去、銘柄コード抽出
- 研究・特徴量
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- カレンダー管理
  - market_calendar に基づく営業日判定、前後営業日の取得、期間内営業日取得
  - 夜間バッチでのカレンダー差分更新ジョブ
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレース用スキーマ、トランザクション性・冪等性を考慮
- 開発・運用上の配慮
  - .env / .env.local の自動読み込み（プロジェクトルート基準）
  - 環境ごとの切替（development / paper_trading / live）、ログレベルチェック

---

## 動作要件

- Python 3.10 以上（typing の `|` を使っているため）
- 必要な Python パッケージ（最低限）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクトをパッケージとしてインストールする場合（開発時）:
```bash
pip install -e .
```
（setuptools/poetry 等のセットアップがあれば上記を使用してください）

---

## 環境変数 / 設定

KabuSys は .env / .env.local（プロジェクトルート）または環境変数から設定を読み込みます。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト用など）。

主要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN : Slack Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）

その他（デフォルト値あり）
- KABUSYS_ENV : 環境。`development`（デフォルト） / `paper_trading` / `live`
- LOG_LEVEL : `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト `INFO`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると .env の自動ロードを無効化
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH : SQLite（モニタリング用）パス（デフォルト `data/monitoring.db`）
- KABUSAPI ベース URL : `KABU_API_BASE_URL`（デフォルト `http://localhost:18080/kabusapi`）

例: .env（必須トークンは適宜設定してください）
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXX
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
   （プロジェクトで requirements.txt / pyproject.toml があればそちらを利用）
4. .env を作成（.env.example を参照して必要な環境変数を設定）
5. DuckDB スキーマ初期化（次の「使い方」を参照）

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトでの基本操作例です。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数に基づく既定値を返します
conn = init_schema(settings.duckdb_path)
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日を基準に実行
print(result.to_dict())
```

- ニュース収集（RSS）ジョブ（既知銘柄セットを渡して銘柄紐付けまで）
```python
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

- ファクター計算（例: モメンタム）
```python
from kabusys.research import calc_momentum

from datetime import date
records = calc_momentum(conn, target_date=date(2025, 1, 31))
# records は各銘柄の mom_1m / mom_3m / mom_6m / ma200_dev を持つ dict のリスト
```

- IC（Information Coefficient）計算
```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2025,1,31), horizons=[1])
# factor_records は上記 calc_momentum の出力など
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- 監査ログ用スキーマ初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- J-Quants API 呼び出し（fetch_*）を利用する場合は JQUANTS_REFRESH_TOKEN を設定してください。
- 自動で .env を読み込む仕組みはプロジェクトルート（.git または pyproject.toml を基準）を探索します。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効にしてください。

---

## よく使うモジュール一覧（主な公開 API）

- kabusys.config.settings
  - settings.jquants_refresh_token / kabu_api_password / slack_bot_token / slack_channel_id
  - settings.duckdb_path / sqlite_path / env / log_level / is_live / is_paper / is_dev
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats / kabusys.data.features
  - zscore_normalize

---

## ディレクトリ構成（主なファイル）

プロジェクトは src/kabusys 配下に実装されています。主なファイルと役割：

- src/kabusys/__init__.py
  - パッケージ定義（version 等）
- src/kabusys/config.py
  - 環境変数読み込み・設定管理
- src/kabusys/data/
  - jquants_client.py : J-Quants API クライアント（取得 / 保存）
  - news_collector.py : RSS ニュース収集と保存ロジック
  - schema.py : DuckDB スキーマ定義と init_schema
  - pipeline.py : ETL パイプライン（run_daily_etl 等）
  - quality.py : データ品質チェック
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - calendar_management.py : カレンダー管理／営業日ロジック
  - audit.py : 監査ログスキーマと初期化ユーティリティ
  - features.py / etl.py : 公開インターフェースの再エクスポート
- src/kabusys/research/
  - feature_exploration.py : 将来リターン計算・IC・統計サマリー
  - factor_research.py : momentum / volatility / value 等のファクター
  - __init__.py : 主要関数を再エクスポート
- src/kabusys/strategy/、src/kabusys/execution/、src/kabusys/monitoring/
  - 戦略、発注、監視レイヤーのプレースホルダ / 将来的な実装領域

（上記は本リポジトリに含まれるソースの要約です）

---

## 運用上の注意

- 本ライブラリは本番口座の発注や資金移動を行う可能性のあるモジュールを含む設計になっています。特に production（KABUSYS_ENV=live）の環境変数・資格情報の管理、監査ログの保存、発注ロジックのテストを厳密に行ってください。
- J-Quants のレート制限（120 req/min）に従う実装が組み込まれていますが、分散環境や複数クライアントでの同時利用時は追加の調整が必要です。
- DuckDB のバージョンや SQL 互換性に依存するため、環境差分に注意してください（特に外部キーや ON DELETE の挙動などは DuckDB のバージョンによって差異があります）。

---

## 貢献 / 拡張

- strategy / execution / monitoring パッケージは拡張用に分離されています。具体的な戦略実装やブローカ接続はこれらのモジュールを実装して統合してください。
- テスト: KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境依存を切り離し、DuckDB の ":memory:" を使用してユニットテストを作成すると容易にテスト可能です。

---

質問や README の補足（例: サンプル .env.example の追加、CI のセットアップ手順、具体的な戦略実装例など）が必要であれば教えてください。README を目的に合わせて追加調整します。