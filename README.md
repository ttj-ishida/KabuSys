# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
DuckDB をデータ層に、J-Quants API や RSS をデータソースとして取り込み、研究（research）→ 特徴量作成 → シグナル生成 → 発注（execution）までのワークフローを想定したモジュール群を提供します。

主に以下の用途を想定しています。
- 市場データ・財務データの差分 ETL（J-Quants）
- ニュースの RSS 収集と銘柄紐付け
- ファクター計算（Momentum / Volatility / Value など）
- ファクター正規化・特徴量作成（features テーブル）
- シグナル生成（final_score の計算、BUY/SELL 判定）
- DuckDB スキーマの初期化・管理

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（レート制御・リトライ・トークンリフレッシュ対応）
  - RSS ベースのニュース収集（SSRF 対策・トラッキングパラメータ除去）
  - DuckDB への冪等保存（ON CONFLICT を利用）

- ETL / データ品質
  - 日次差分 ETL（市場カレンダー、株価、財務データ）
  - 品質チェックフレームワーク（quality モジュールとの連携想定）
  - calendar_update_job（市場カレンダー更新）

- 研究・戦略
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - クロスセクション Z スコア正規化（zscore_normalize）
  - 特徴量作成（build_features）→ features テーブルへ保存
  - シグナル生成（generate_signals）→ signals テーブルへ保存
  - Sell（エグジット）判定ロジック（ストップロス等）

- 発注・監査（設計）
  - Execution / audit 用スキーマが定義済み（発注連携層は発展余地あり）

---

## 必要条件 / 依存ライブラリ

必須（最低限）:
- Python 3.10+
- duckdb
- defusedxml

その他、標準ライブラリ以外の依存はモジュールごとに必要になります。環境に合わせてインストールしてください。

例:
pip install duckdb defusedxml

（パッケージをセットアップする場合はプロジェクトの pyproject.toml / requirements を参照してください）

---

## 環境変数（主な設定項目）

本プロジェクトは .env（または .env.local）を自動読み込みします（プロジェクトルートの検出は .git または pyproject.toml を基準）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注連携を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot Token
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUS_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite パス（デフォルト: data/monitoring.db）

例 .env（サンプル）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（ローカルでの最小セットアップ）

1. リポジトリをクローン、仮想環境を作成
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   # またはプロジェクトがパッケージ化されていれば:
   pip install -e .
   ```

3. 環境変数を設定（プロジェクトルートに .env を作成）
   - 先述の必須項目を .env に記述してください。

4. DuckDB スキーマ初期化
   - Python REPL かスクリプト内で：
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を生成・テーブル作成
   conn.close()
   ```

---

## 使い方（コード例）

以下は代表的な操作の簡単な例です。

- 日次 ETL を実行（市場カレンダー・株価・財務の取得と保存）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 特徴量を作成（features テーブルへ保存）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date(2024, 2, 28))
print("features upserted:", count)
conn.close()
```

- シグナル生成（features / ai_scores / positions を参照して signals を作成）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema(settings.duckdb_path)
total = generate_signals(conn, target_date=date(2024, 2, 28))
print("signals written:", total)
conn.close()
```

- ニュース収集ジョブの実行（RSS フィード収集）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

- 市場カレンダー更新ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print("calendar saved:", saved)
conn.close()
```

---

## 運用上の注意

- J-Quants API のレート制限（120 req/min）に合わせた待ち制御やリトライを組み込んでいます。ただし大量のバックフィルや同時実行には注意してください。
- ニュース収集部は外部 URL を扱うため、SSRF や XML インジェクション等の対策（実装済み: defusedxml、ホストチェック、レスポンスサイズ制限等）がありますが、運用環境での更なる堅牢化を推奨します。
- features / signals などは日付単位で「置換（削除->挿入）」を行い冪等性を保っています。複数プロセスからの同時実行やトランザクション設計に注意してください。
- 発注・ブローカー連携は execution 層で行う想定ですが、現状は設計・スキーマが中心の実装です（実際のブローカー API の接続実装が必要）。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの Python パッケージは `src/kabusys` 以下）

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の自動読み込み、設定アクセス
- src/kabusys/data/
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py — RSS 収集、記事前処理、DB 保存
  - schema.py — DuckDB スキーマ定義と初期化（init_schema）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - calendar_management.py — 市場カレンダー管理・ジョブ
  - audit.py — 監査ログ／発注トレーサビリティ用定義
  - features.py — data.stats の再エクスポート
- src/kabusys/research/
  - factor_research.py — calc_momentum / calc_volatility / calc_value
  - feature_exploration.py — forward returns / IC / factor summary
- src/kabusys/strategy/
  - feature_engineering.py — build_features（features 作成フロー）
  - signal_generator.py — generate_signals（最終スコア / BUY/SELL 判定）
- src/kabusys/execution/
  - （発注周りの実装を置くためのパッケージ）
- src/kabusys/monitoring/
  - （監視・モニタリング関連の実装用）

---

## 開発・貢献

- コードはモジュール単位でユニットテスト化し、ETL 部分は外部 API をモックしてテストを推奨します（jquants_client._request や news_collector._urlopen のモック等）。
- .env.example をプロジェクトルートに用意し、運用時は .env.local を使って機密情報を上書きする運用を想定しています。
- 大きな変更を行う場合は DuckDB スキーマの互換性（DDL / PRIMARY KEY / CHECK 制約）に注意してください。

---

## ライセンス

（ここにライセンス情報を記載してください。プロジェクトに合わせて追加してください。）

---

README に記載した内容はこのリポジトリ内の実装（schema / pipeline / research / strategy / data）に基づきまとめています。実運用前に各モジュールのログ出力やテストを十分に行い、API トークンやネットワークアクセスの取り扱いに注意して設定してください。