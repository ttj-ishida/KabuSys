# KabuSys — 日本株自動売買システム

軽量な研究〜本番までを想定した日本株向け自動売買基盤です。  
DuckDB をデータ層に使い、J-Quants API / RSS ニュース / kabuステーション 等と連携するための ETL、特徴量生成、シグナル生成、監査・実行の枠組みを提供します。

注意: 本リポジトリはライブラリコアのみを含み、実運用のためには証券会社 API キー管理、ブローカー接続、リスク管理ルール等を別途実装・確認してください。

## 主な機能

- データ収集（J-Quants からの日足 / 財務データ / 市場カレンダー）
  - レートリミット遵守、リトライ、トークン自動リフレッシュ
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- DuckDB スキーマ定義と初期化（冪等）
- 研究用ファクター計算（momentum / volatility / value）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（複数コンポーネントの重み付け、Bear レジーム抑制、エグジット判定）
- ニュース収集（RSS -> raw_news、SSRF/サイズ制限/トラッキング除去等の安全対策）
- 監査ログ / 発注トレーサビリティ（監査テーブル定義）
- ユーティリティ（マーケットカレンダー管理、統計関数、ranking/IC 計算）

## 必要条件

- Python 3.10 以上（型注釈で | を使用しているため）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
# 他に必要なパッケージがあれば追加
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

任意 / デフォルト:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）

例（.env の抜粋）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   # 追加パッケージがあればここでインストール
   ```

3. 環境変数を設定（.env をプロジェクトルートに作成）
   - 上記「環境変数 / 設定」を参照してください

4. DuckDB スキーマ初期化
   Python REPL / スクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   conn.close()
   ```

## 使い方（よく使う API / ワークフロー例）

基本ワークフロー（データ取得 → 特徴量生成 → シグナル生成）:

1. DuckDB 接続の初期化（1回目）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL（市場カレンダー・株価・財務データの差分取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # デフォルト: 今日を対象に実行
   print(result.to_dict())
   ```

3. 特徴量計算（target_date を指定）
   ```python
   from datetime import date
   from kabusys.strategy import build_features

   cnt = build_features(conn, target_date=date.today())
   print(f"features upserted: {cnt}")
   ```

4. シグナル生成（features と ai_scores を用いて BUY / SELL を作成）
   ```python
   from kabusys.strategy import generate_signals
   total_signals = generate_signals(conn, target_date=date.today())
   print(f"signals written: {total_signals}")
   ```

5. ニュース収集（RSS -> raw_news / news_symbols）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   # known_codes は既知の銘柄コードセット（抽出に使用）
   known_codes = {"7203", "6758", "9984", ...}
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

補足:
- ETL の戻り値 ETLResult に品質チェック・エラー情報が含まれます。
- generate_signals はデフォルトの重みと閾値を使いますが、weights/threshold を引数で変更できます。
- DuckDB のトランザクションを使って日付単位での置換（DELETE→INSERT）を行い原子性を担保しています。

## 開発用ヒント

- 自動で .env を読み込む仕組みがあります。テスト時に環境変数の自動ロードを無効にしたい場合は:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 設定検証は `kabusys.config.Settings` が行います。KABUSYS_ENV は `development`, `paper_trading`, `live` のいずれかでなければエラーになります。
- J-Quants API 呼び出しには内部で固定間隔のレートリミッタを使用しています（120 req/min）。
- ニュース収集では SSRF 対策、受信サイズ制限、XML の安全パース（defusedxml）を行っています。

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下に配置されています。主なファイル / モジュール:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存処理
    - news_collector.py             — RSS ニュース収集と保存
    - schema.py                     — DuckDB スキーマ定義 / init_schema
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - features.py                   — 再エクスポート（zscore_normalize）
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py        — 市場カレンダーユーティリティ
    - audit.py                      — 監査ログ（発注・約定トレーサビリティ）
    - execution/                     — 発注関連（空 / 拡張用）
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/volatility/value）
    - feature_exploration.py        — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py        — features テーブル生成（build_features）
    - signal_generator.py           — generate_signals（BUY/SELL 生成）
  - execution/                      — 実行層（将来的なブローカー接続等）
  - monitoring/                     — 監視・メトリクス（将来的な実装）

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下のソースを参照してください。）

## ライセンス・注意事項

- 本コードはテンプレート / 参考実装を目的としています。実際に資金を投入する前に安全性、規制、税務、接続するブローカーの仕様を充分確認してください。
- 実運用では追加のリスクチェック、テスト、監査、冗長化が必要です。

---

ご希望があれば以下も追加で用意します:
- docker-compose / コンテナ化手順テンプレート
- シンプルな CLI スクリプト例（日次ジョブを cron/airflow で回すための例）
- requirements.txt / pyproject.toml の草案
- テスト用のユニットテスト雛形（pytest）