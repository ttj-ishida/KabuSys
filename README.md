# KabuSys

日本株自動売買システム（KabuSys）のパッケージリポジトリドキュメントです。  
この README はプロジェクトの概要、主要機能、セットアップ手順、基本的な使い方、およびディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ取得（J-Quants 等）、ETL（DuckDB への保存）、特徴量計算、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、発注・監査のためのデータレイヤを提供する自動売買プラットフォーム向けライブラリです。  
設計上のポイント：

- DuckDB をデータ保存層として利用（Raw / Processed / Feature / Execution の多層スキーマ）
- J-Quants API からの差分取得（レート制限・リトライ・トークン自動更新対応）
- 研究用モジュール（research）と実行用モジュール（strategy / execution / monitoring）を分離
- ルックアヘッドバイアス対策、冪等性（ON CONFLICT）やトランザクションを重視

パッケージバージョンは src/kabusys/__init__.py の `__version__` を参照してください。

---

## 機能一覧

主要モジュールと提供機能（抜粋）：

- data
  - jquants_client: J-Quants API クライアント（株価・財務・カレンダー取得、保存）
  - schema: DuckDB のスキーマ定義と初期化（init_schema）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）の実装（run_daily_etl 他）
  - news_collector: RSS からニュース収集・前処理・DB 保存機能
  - calendar_management: 市場カレンダー管理、営業日判定（next/prev/is_trading_day 等）
  - stats: Z スコア正規化などの統計ユーティリティ
- research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy
  - feature_engineering.build_features: features テーブルの構築（ファクター合成・正規化）
  - signal_generator.generate_signals: features/ai_scores を統合して BUY/SELL シグナル生成
- execution / monitoring: 発注・監視層（雛形・インターフェース）
- config: 環境変数・設定管理（.env 自動ロード対応、必須変数チェック）

主な設計・運用上の注意点：

- DuckDB に対する書き込みはトランザクションやバルク挿入で原子性・効率性を担保
- NewsCollector は SSRF 対策・受信サイズ制限・XML パース対策を実装
- J-Quants クライアントはレート制御・リトライ・401 リフレッシュを実装

---

## セットアップ手順

前提

- Python 3.10 以上（typing の `X | Y` 記法を利用）
- DuckDB と必要な Python パッケージ（下記参照）

必要な Python ライブラリ（例）:
- duckdb
- defusedxml
（その他 logging / urllib 等は標準ライブラリ）

インストール例（ローカル開発）:
```
# 仮想環境作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 必要パッケージをインストール（プロジェクトの requirements.txt があればそれを使う）
pip install duckdb defusedxml
# 開発中はパッケージを編集可能インストール
pip install -e .
```

環境変数 / .env
- プロジェクトはルート（.git または pyproject.toml が存在するディレクトリ）配下の `.env` と `.env.local` を自動で読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化）。
- 必須環境変数（config.Settings が参照するもの）：
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabu ステーション API のパスワード
  - SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
  - SLACK_CHANNEL_ID — 通知先チャンネル ID
- オプション（デフォルトあり）：
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

データベース初期化
- DuckDB スキーマを作成するには Python REPL やスクリプトで `kabusys.data.schema.init_schema()` を呼びます。デフォルトのパスは設定で指定した DUCKDB_PATH（settings.duckdb_path）。

例:
```python
from kabusys.config import settings
from kabusys.data import schema

conn = schema.init_schema(settings.duckdb_path)
```

---

## 使い方（基本的な操作例）

以下は代表的なユースケースの Python スニペットです。実運用スクリプトはエラーハンドリングやログを適切に追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data import schema

conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）を構築
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features built for {count} symbols")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
num_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"generated {num_signals} signals")
```

5) ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes: 銘柄抽出に使う有効コードセット（例: {'7203','6758',...}）
results = run_news_collection(conn, known_codes={'7203','6758'})
print(results)
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"saved {saved} calendar rows")
```

注意:
- jquants_client の API 呼び出しは rate limit とリトライを考慮しており、本番では ID トークンやネットワーク状況に応じたエラーハンドリングが必要です。
- generate_signals / build_features は DuckDB 内のテーブル（prices_daily / raw_financials / features / ai_scores / positions 等）に依存します。ETL 実行とスキーマ初期化を先に行ってください。

---

## ディレクトリ構成

主要ファイル構成（src/kabusys 配下の抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                       # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py             # J-Quants API クライアント（fetch/save）
      - news_collector.py             # RSS ニュース収集と保存
      - schema.py                     # DuckDB スキーマ定義・初期化
      - stats.py                      # 統計ユーティリティ（zscore_normalize）
      - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py        # 市場カレンダー管理
      - features.py                   # データ向けの公開ユーティリティ
      - audit.py                      # 監査ログ（signal_events / order_requests / executions）
    - research/
      - __init__.py
      - factor_research.py            # ファクター計算（momentum/value/volatility）
      - feature_exploration.py        # IC / forward returns / 統計サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py        # features を組成して DB に保存
      - signal_generator.py           # final_score 計算 -> signals 登録
    - execution/                       # 発注・実行層のモジュール（空の __init__ あり）
    - monitoring/                      # 監視・通知関連（将来的な実装）
- pyproject.toml (または setup.py 等)
- .env / .env.local (プロジェクトルートに配置して環境変数を設定)

各モジュールのドキュメントはソース内の docstring（日本語）に詳細が書かれており、関数・クラスの利用方法や設計方針が示されています。

---

## 運用上の注意・補足

- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかであり、不正な値はエラーになります。live を使う際は安全性（実際の発注ロジックの確認、リスク制限）を十分確認してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。テスト等で自動ロードを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- NewsCollector / fetch_rss は外部 RSS を取得するため、ネットワークやコンテンツのフォーマットによって挙動が変わる可能性があります。SSRF や XML 脆弱性防止のため defusedxml を使用し、受信サイズ制限やホストのプライベートアドレス拒否を実装していますが、運用時はホワイトリスト運用等の追加対策も検討してください。
- DuckDB のファイルはデフォルト `data/kabusys.duckdb` に作成されます。バックアップや排他アクセス（同時接続）については DuckDB のドキュメントを参照してください。

---

もし README に追加したい利用例、CI / CD 設定、docker / systemd によるスケジューリング例、あるいは具体的な API キー管理のドキュメント（.env.example のテンプレートなど）が必要であれば教えてください。README を利用目的に合わせて拡張します。