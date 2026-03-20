# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買戦略基盤の骨組みを提供する Python パッケージです。J-Quants API や RSS ニュースからデータを取得し、DuckDB に保存、ファクター計算 → 特徴量正規化 → シグナル生成までの主要パイプラインを備えています。

主な設計方針：
- ルックアヘッドバイアス対策（target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT/UPSERT を利用）
- ネットワーク安全性（RSS の SSRF 対策など）
- 外部依存を最小化（可能な限り標準ライブラリで実装）

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価日足・財務・市場カレンダー）
  - RSS フィードからのニュース収集（前処理・URL 正規化・銘柄抽出）
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution レイヤー）
- ETL パイプライン
  - 差分取得（最終取得日を基に差分のみ取得）
  - 保存（冪等保存）
  - 品質チェック（欠損・スパイクなどの検出。quality モジュールを使用）
  - 日次ジョブ（run_daily_etl）
- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC（Info. Coefficient）・統計サマリー
  - Z スコア正規化ユーティリティ
- 戦略レイヤ
  - 特徴量構築（build_features: 各ファクターを正規化して features テーブルへ）
  - シグナル生成（generate_signals: features + ai_scores を統合して BUY/SELL を作成）
- ニュース処理
  - RSS の取得、記事 ID 生成、raw_news への保存、銘柄抽出と紐付け
- 監査 / 実行レイヤ（スキーマを含む）
  - signals / signal_queue / orders / trades / executions / positions などのテーブルを提供

---

## 必要条件（依存パッケージ）

このリポジトリでは最低限以下のパッケージを使用します（pip でインストールしてください）：

- Python 3.9+
- duckdb
- defusedxml

例：
pip install duckdb defusedxml

（プロジェクトの package 構成に応じて他のライブラリが追加される可能性があります）

---

## 環境変数（設定）

設定は .env ファイル（プロジェクトルートの `.env` / `.env.local`）または OS 環境変数から読み込まれます。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

主な環境変数：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 用パス（監視用デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

設定はコード中の `kabusys.config.settings` から参照できます。必須変数が未設定の場合は実行時に ValueError が発生します。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
4. 必要な環境変数を用意
   - プロジェクトルートに `.env`（または `.env.local`）を作成して上記の必須キーを設定
     例（.env）:
       JQUANTS_REFRESH_TOKEN=your_refresh_token
       KABU_API_PASSWORD=your_kabu_password
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C0123456
       DUCKDB_PATH=data/kabusys.duckdb
       KABUSYS_ENV=development
5. データベーススキーマを初期化
   - 例: Python スクリプトから init_schema を呼び出す（下記「使い方」参照）

---

## 使い方（主要ユースケース）

以下はパッケージ内部 API を使った最小ワークフロー例です。適宜スクリプトにまとめて cron / ジョブランナーから実行してください。

1) DuckDB の初期化
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = init_schema(db_path)     # テーブル作成済みの接続を返す
# 既に初期化済みなら get_connection(settings.duckdb_path) でも可
```

2) 日次 ETL を実行（J-Quants から市場カレンダー・株価・財務を差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）を構築
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナルを生成して signals テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {n}")
```

5) ニュース収集の例
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes: 既知銘柄コードのセット（抽出に使用）
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

注意:
- 上のコードはパッケージ内の公開 API を直接呼び出す例です。実際の運用ではログ、例外ハンドリング、リトライ、ジョブ管理を組み合わせてください。
- J-Quants の API にはレートリミットや認証があるため、id token の取得やレート制御は jquants_client が処理します。

---

## よくある操作コマンド（例）

- スキーマ初期化（シンプルスクリプト）
  - python -c "from kabusys.data.schema import init_schema; from kabusys.config import settings; init_schema(settings.duckdb_path)"
- 日次 ETL 実行（スクリプト化推奨）
  - python -m your_project.scripts.daily_etl  （スクリプトを作成して実行する想定）

---

## トラブルシューティング

- 環境変数のエラー:
  - settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN）が未設定だと ValueError が発生します。`.env` を作成するか環境変数を設定してください。
- DuckDB ファイルのパスエラー:
  - デフォルトの DB パスは `data/kabusys.duckdb`。親ディレクトリが存在しない場合は init_schema が自動作成しますが、ファイルパスの権限などを確認してください。
- RSS 取得でエラーが出る:
  - ネットワークやレスポンス形式の差異、XML パースエラーが原因です。ログを確認してください。SSRF 保護により private ホストや非 http/https スキームは拒否されます。
- J-Quants API 呼び出しで 401 が出る:
  - jquants_client は 401 を検知した場合、1 回トークンをリフレッシュしてリトライします。refresh token が無効な場合は再発行してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイルは以下のような構成です（src/kabusys 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント + 保存
      - news_collector.py      # RSS 収集・前処理・保存
      - schema.py              # DuckDB スキーマ定義と初期化
      - pipeline.py            # ETL パイプライン（run_daily_etl 等）
      - stats.py               # 統計ユーティリティ（zscore_normalize）
      - features.py            # features 再エクスポート
      - calendar_management.py # マーケットカレンダー管理
      - audit.py               # 監査ログスキーマ（signal/order/execution 等）
    - research/
      - __init__.py
      - factor_research.py     # momentum/volatility/value の計算
      - feature_exploration.py # 将来リターン・IC・summary
    - strategy/
      - __init__.py
      - feature_engineering.py # build_features
      - signal_generator.py    # generate_signals
    - execution/                # 発注 / 実行層（空 __init__ が存在）
    - monitoring/               # 監視関連（__all__ に列挙されているが実装は別途）
    - その他モジュール...

---

## 貢献・拡張案

- 実行層（execution）の具体的実装（証券会社 API 連携、約定処理）
- リスク管理・ポートフォリオ最適化の追加
- ai_scores を算出する ML パイプラインの統合
- 単体テスト／CI の整備（特にネットワーク呼び出しをモックする形）
- ロギング / メトリクス（Prometheus / Sentry など）の追加

---

## ライセンス

（ここに適切なライセンス記載を入れてください）

---

README に書かれている内容はコードに基づく概要です。実運用にあたっては認証情報・API 料金・レート制限・法令遵守（自動売買に関する規制）を必ず確認してください。必要であれば、README に記載するサンプルスクリプトや CLI を追加することをおすすめします。