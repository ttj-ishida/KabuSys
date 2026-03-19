# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（研究・データ基盤・戦略生成・発注/監査基盤の骨組み）

このリポジトリは、J-Quants API や RSS ニュース等から市場データを取得して DuckDB に蓄積し、
特徴量生成、シグナル生成、監査ログ／発注管理までを一貫して扱うためのモジュール群を提供します。
研究用ユーティリティ（ファクター計算・IC解析等）も含まれ、戦略開発と運用バッチの両方に対応します。

主な目的:
- データ ETL（J-Quants からの株価・財務・カレンダー取得）
- データ品質チェック、スキーマ管理（DuckDB）
- ファクター計算・特徴量正規化
- シグナル生成（BUY/SELL）ロジック
- ニュース収集と銘柄紐付け（RSS）
- 監査ログ / 発注トレーサビリティのためのスキーマ

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（差分取得、ページネーション、リトライ、トークン自動更新）
  - 株価（日足）、財務情報、マーケットカレンダー取得
  - RSS ベースのニュース収集（安全対策、トラッキングパラメータ除去、記事ID生成）
  - DuckDB への冪等保存（ON CONFLICT を利用）

- ETL パイプライン
  - run_daily_etl：カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - 差分更新、バックフィル、営業日調整

- スキーマ管理
  - DuckDB のスキーマ初期化（raw / processed / feature / execution 層）
  - 各種 INDEX 定義

- 研究支援（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算
  - ファクター統計サマリー、ランク処理

- 特徴量・シグナル
  - 特徴量作成（Z スコア正規化、ユニバースフィルタ）
  - シグナル生成（複数コンポーネントの重み付け統合、Bear レジーム抑制、エグジット判定）
  - シグナルは `signals` テーブルへ日付単位で冪等保存

- ニュース収集
  - RSS フィード取得、XML パース（defusedxml）
  - 記事保存（raw_news）、銘柄抽出・紐付け（news_symbols）

- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

- 監査（audit）
  - signal_events / order_requests / executions など、トレース可能な監査テーブル設計

---

## 前提 / 必要環境

- Python 3.10 以上（型注釈に `X | None` 構文を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml

pip でのインストール例（プロジェクトルートで）:
```bash
python -m pip install "duckdb" "defusedxml"
# または開発環境であれば requirements.txt を用意してインストール
```

環境変数の自動読み込み:
- プロジェクトルートに `.env` / `.env.local` を置くと、自動でロードされます（ただしテスト等で無効化可能）。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主要なもの）

設定は環境変数で行います。最低限必要なものは以下です:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション等の API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

.env の雛形はプロジェクトに `.env.example` を置く想定です（存在しない場合は README に従って作成してください）。

---

## セットアップ手順（概要）

1. リポジトリをクローン／取得
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (PowerShell)
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
4. 環境変数を設定（.env ファイルをプロジェクトルートに作成）
   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
5. DuckDB スキーマ初期化（Python から実行）
   以下は最小例です（プロジェクトルートで実行）:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```
   このコマンドはデータディレクトリを自動で作成し、すべてのテーブルとインデックスを作成します。

---

## 使い方（主要なユースケース）

以下は Python スクリプトやバッチで呼び出すための代表的な API 例です。

- DuckDB の初期化と接続
```python
from kabusys.data.schema import init_schema, get_connection
# 初回: スキーマを作成して接続を得る
conn = init_schema("data/kabusys.duckdb")
# 以降: 既存 DB に接続するだけなら
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL の実行（市場カレンダー、株価、財務、品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
# conn は上で作った DuckDB 接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）作成
```python
from datetime import date
from kabusys.strategy import build_features
# build_features は features テーブルへ日付単位で置換保存（冪等）
count = build_features(conn, target_date=date(2025, 1, 31))
print(f"built features for {count} codes")
```

- シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
# generate_signals は signals テーブルへ日付単位で置換保存（冪等）
total_signals = generate_signals(conn, target_date=date(2025, 1, 31), threshold=0.6)
print(f"generated {total_signals} signals")
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄コードセット（例: 上場銘柄リスト）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

- カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved {saved} calendar records")
```

- J-Quants から直接データを取得して保存する（低レベル）
```python
from kabusys.data import jquants_client as jq
from datetime import date
records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
jq.save_daily_quotes(conn, records)
```

ログ設定やエラーハンドリングは呼び出し側（スクリプト／バッチ）で行ってください。KABUSYS_ENV / LOG_LEVEL に応じて動作モードを切り替えられます。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは Python パッケージ `kabusys`（src 配下）に分割されています。概略:

- src/kabusys/
  - __init__.py (パッケージ定義、__version__)
  - config.py (環境変数と Settings)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント)
    - news_collector.py (RSS ニュース取得・保存)
    - schema.py (DuckDB スキーマ定義と初期化)
    - stats.py (統計ユーティリティ: zscore_normalize)
    - pipeline.py (ETL パイプライン実装)
    - features.py (data.stats の再エクスポート)
    - calendar_management.py (マーケットカレンダー管理)
    - audit.py (監査ログ用 DDL / 初期化)
    - quality.py (品質チェックモジュール: pipeline から参照される想定)*
  - research/
    - __init__.py
    - factor_research.py (momentum/volatility/value 計算)
    - feature_exploration.py (forward returns, IC, summary, rank)
  - strategy/
    - __init__.py (build_features, generate_signals を公開)
    - feature_engineering.py (features 構築フロー)
    - signal_generator.py (シグナル生成ロジック)
  - execution/
    - __init__.py (発注 / 実行層のプレースホルダ)
  - monitoring/ (パッケージ参照のみが __all__ にある想定、実装は別途)
- pyproject.toml / setup.cfg 等（配布設定、プロジェクトルートで .env の自動読み込みを行う）

(*注: quality モジュールは pipeline から参照されています。実装ファイルがある場合は同ディレクトリに配置されます。)

---

## 実運用上の注意

- セキュリティ
  - RSS のフェッチでは SSRF 対策・リダイレクト検査・レスポンスサイズ制限を実装していますが、
    運用環境ではネットワークポリシー（プロキシ／ファイアウォール）を適切に設定してください。
  - トークン等の秘密情報は `.env` を用いる場合でも適切なアクセス管理を行ってください。

- レート制限とリトライ
  - J-Quants API はレート制限（120 req/min）を想定した固定間隔スロットリングを実装しています。
    大量の銘柄を一括で取得する際は処理時間や API 制限に注意してください。

- ルックアヘッドバイアス
  - 特徴量・シグナル生成ロジックはルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ使用）を意識しています。
    新機能を追加する際も同様の原則を守ってください。

- 冪等性
  - DB への保存は可能な限り冪等性（ON CONFLICT）を担保しています。バッチの再実行に耐えるよう設計されています。

---

## 参考 / 開発者向け

- 主要 API の参照は各モジュールの docstring に詳細な設計・仕様（StrategyModel.md / DataPlatform.md 相当）が書かれています。
- テスト・CI の導入、さらに詳細な依存関係ファイル（requirements-dev.txt など）はプロジェクト状況に合わせて追加してください。

---

この README はコードベース（src/kabusys）に基づいて作成しています。実際の利用時はプロジェクトルートのドキュメント（.env.example、DataPlatform.md、StrategyModel.md 等）があればそちらも参照してください。必要であれば README を英訳したり、コマンドラインツールの使い方（CLI スクリプト例）を追加します。