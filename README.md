# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
市場データ取得・ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマなど、戦略実装と運用に必要な基盤処理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API 等から日本株データ（株価・財務・カレンダー）を取得して DuckDB に保存する ETL パイプライン
- Research 層で計算した生ファクターを正規化・合成して特徴量（features）を作成する仕組み
- 正規化済み特徴量と AI スコアを統合して売買シグナル（BUY/SELL）を生成する戦略ロジック
- RSS からのニュース収集と銘柄紐付け（raw_news / news_symbols）
- JPX マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）
- DuckDB 上のスキーマ定義・初期化／監査テーブル等の管理

設計上のポイント:
- ルックアヘッドバイアスを避けるため、target_date 時点のデータのみを使用する設計
- DuckDB を中心にオンプレミスで完結するデータレイヤを提供（外部依存を最小化）
- 冪等性（ON CONFLICT / トランザクション）を重視した実装

---

## 主な機能一覧

- データ取得／保存（J-Quants クライアント）
  - fetch/save: daily quotes（OHLCV）、financial statements、market calendar
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- DuckDB スキーマ管理
  - init_schema(db_path) によるテーブル初期化（raw / processed / feature / execution 層）
- 特徴量生成（strategy.feature_engineering）
  - calc_momentum / calc_volatility / calc_value を組み合わせて features を構築（build_features）
- シグナル生成（strategy.signal_generator）
  - 正規化済み特徴量と AI スコアを重み付き合算して BUY/SELL を生成（generate_signals）
  - Bear レジーム抑制、ストップロス等のエグジット判定を実装
- ニュース収集（data.news_collector）
  - RSS 取得、URL 正規化、記事 ID 生成、raw_news 保存、銘柄抽出と紐付け
  - SSRF 対策、XML 安全パーサ、受信サイズ制限など安全設計
- マーケットカレンダー管理（data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティ
- 研究用ユーティリティ（research）
  - 将来リターン計算、IC（Spearman）の計算、ファクター統計サマリ、Z スコア正規化

---

## 動作環境・依存関係

- Python: 3.10 以上（typing の | 演算子等を使用）
- 必須ライブラリ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリを多用しているため外部依存は最小限です。プロジェクトに合わせて追加パッケージ（例: Slack 通知用 slack-sdk など）を導入してください。

推奨インストール方法（仮想環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発時はパッケージインストール（プロジェクトルートに setup.py/pyproject.toml がある前提）
pip install -e .
```

---

## 環境変数（設定）

設定は .env ファイルまたは環境変数で行います。自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（ただしテスト時などは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

オプション:
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

簡単な .env.example:
```text
# .env.example
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## セットアップ手順（概要）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージのインストール
   ```bash
   pip install --upgrade pip
   pip install duckdb defusedxml
   # もし pyproject.toml や setup.py があれば開発インストール
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、必要な環境変数を export してください（上の .env.example を参照）。

5. DuckDB スキーマ初期化
   ```bash
   python - <<'PY'
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   init_schema(settings.duckdb_path)
   print("DuckDB schema initialized:", settings.duckdb_path)
   PY
   ```

---

## 使い方（主なユースケース）

以下は簡単な実行例（管理ジョブやワンオフ実行）です。スクリプトや cron / Airflow / systemd タイマー等から呼び出して運用します。

- 日次 ETL（市場カレンダー・株価・財務を取得して品質チェックまで実施）
```bash
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
conn = init_schema(settings.duckdb_path)
res = run_daily_etl(conn)
print(res.to_dict())
PY
```

- DuckDB に対して特徴量をビルド（target_date を指定）
```bash
python - <<'PY'
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, date(2024,1,1))
print("features upserted:", count)
PY
```

- シグナル生成（target_date 指定）
```bash
python - <<'PY'
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
conn = get_connection("data/kabusys.duckdb")
n = generate_signals(conn, date.today())
print("signals generated:", n)
PY
```

- ニュース収集ジョブ（一括）
```bash
python - <<'PY'
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
# known_codes は銘柄コードのセット（抽出に使用）
known_codes = {"7203","6758"}
conn = get_connection("data/kabusys.duckdb")
result = run_news_collection(conn, known_codes=known_codes)
print(result)
PY
```

- カレンダー更新バッチ
```bash
python - <<'PY'
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar entries saved:", saved)
PY
```

---

## ディレクトリ構成

主要なファイル・モジュール構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py      # RSS ニュース収集・保存
    - schema.py              # DuckDB スキーマ定義と初期化
    - stats.py               # 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - features.py            # features インターフェース（再エクスポート）
    - calendar_management.py # カレンダー関連ユーティリティ
    - audit.py               # 監査ログ用スキーマ定義
    - execution/             # （将来的な）発注・ブローカー連携層
  - research/
    - __init__.py
    - factor_research.py     # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py # 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py # features の組成・正規化処理
    - signal_generator.py    # final_score 計算と signals 生成
  - execution/               # 発注ロジック（空のパッケージ、将来的実装）
  - monitoring/              # 監視用モジュール（未展開）
  - その他ドキュメント: DataPlatform.md / StrategyModel.md 相当の設計ドキュメントに準拠した実装

※ この README はコードベースの実装を元にした概略ドキュメントです。詳細仕様（StrategyModel.md、DataPlatform.md、DataSchema.md 等）は別途プロジェクト内設計書を参照してください。

---

## 運用上の注意

- J-Quants API の利用制限（レート制限）を守るため、jquants_client は内部でスロットリングとリトライを実装しています。大量取得や短期間の連続実行に注意してください。
- DuckDB のファイルパスは共有ファイルシステム上で複数プロセスから同時アクセスすると問題が起きる場合があります。運用設計で排他制御（ジョブ調整）を検討してください。
- 環境変数に機密情報（トークン／パスワード）を含むため、適切なパーミッション管理と秘密管理の運用を推奨します。
- 本ライブラリは実際の発注（実運用）に用いる場合、事前に十分なテストとリスク評価を行ってください（paper_trading モードでの検証を推奨）。

---

## 貢献

バグ報告や改善提案は Issue を作成してください。機能追加や修正は Pull Request を歓迎します。コーディング規約・テスト・型アノテーションを順守してください。

---

以上。必要であれば README にサンプルデータの準備手順、詳細な .env.example、CI / デプロイ手順、ユニットテスト実行方法（pytest 等）を追加します。どの情報を優先して追記しましょうか？