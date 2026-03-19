# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants API や RSS ニュースを取り込み、DuckDB に格納・加工して特徴量生成・シグナル算出まで一貫して行える設計になっています。

主な利用ケース:
- データ取得（株価・財務・市場カレンダー）
- データ品質チェック・ETL（差分更新・バックフィル対応）
- ニュース収集と銘柄紐付け
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量の正規化（Z スコア）と戦略シグナル生成
- DuckDB スキーマ定義 / 監査テーブル（発注・約定トレース用）

---

## 機能一覧

- data/jquants_client
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ）
  - 株価（OHLCV）、財務データ、マーケットカレンダーの取得・DuckDB への冪等保存
- data/schema
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- data/pipeline
  - 差分 ETL（市場カレンダー → 株価 → 財務）と品質チェックの統合実行
- data/news_collector
  - RSS フィード取得、前処理、raw_news 保存、記事と銘柄コードの紐付け（SSRF/サイズ制限対策あり）
- data/calendar_management
  - JPX カレンダー管理（営業日判定、next/prev_trading_day、夜間更新ジョブ）
- data/stats
  - zscore_normalize（クロスセクション Z スコア正規化）
- research
  - ファクター計算（momentum / volatility / value）と探索ユーティリティ（forward returns, IC, summary）
- strategy
  - build_features: 原始ファクターの合成・正規化・features テーブルへの保存
  - generate_signals: features + ai_scores から final_score を計算し BUY/SELL シグナルを signals テーブルへ保存
- audit（監査ログ）
  - signal_events / order_requests / executions など、トレーサビリティ用テーブル定義
- config
  - .env / 環境変数の自動ロード（プロジェクトルート検出）と必須設定チェック

---

## 前提条件

- Python 3.10+
- 必要なパッケージ（最低限）
  - duckdb
  - defusedxml
  - （その他、実行環境に応じて requests 等が必要になる場合があります）

requirements.txt がプロジェクトに含まれていればそれを利用してください。ここでは最低限の例を示します。

例:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに入る
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb defusedxml
   # 必要に応じて他の依存を追加
   ```

4. 開発インストール（オプション）
   ```
   pip install -e .
   ```

5. 環境変数 / .env の設定  
   プロジェクトはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動読み込みします。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要な環境変数（代表的なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（主要な API / ワークフロー例）

以下の例は Python REPL / スクリプトでの基本的な実行例です。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

2. 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量の作成（build_features）
   ```python
   from kabusys.strategy import build_features
   from datetime import date

   n = build_features(conn, target_date=date(2024, 1, 10))
   print(f"built features: {n}")
   ```

4. シグナル生成（generate_signals）
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   total = generate_signals(conn, target_date=date(2024, 1, 10), threshold=0.6)
   print(f"signals generated: {total}")
   ```

5. ニュース収集ジョブ（RSS から raw_news へ保存して銘柄を紐付け）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   # known_codes は既知の銘柄コードセット（例: prices_daily から抽出）
   known_codes = {"7203", "6758", "9432"}
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

6. カレンダー夜間更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar entries saved: {saved}")
   ```

※ 上記は各モジュールが期待するテーブル（例: prices_daily, raw_financials 等）が存在することが前提です。init_schema() を使ってスキーマを作成してください。

---

## よくある運用上の注意

- .env の自動ロードはプロジェクトルートの検出に依存します。パッケージ配布後やテスト中に挙動を変えたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で環境変数を管理してください。
- J-Quants API のレート制限（120 req/min）はクライアント実装内で制御していますが、大規模なバックフィルを行う場合は API 利用制限に注意してください。
- ニュース収集では SSRF や XML BOM/GZIP の脆弱性対策を実装していますが、外部フィードの数やサイズによってはメモリ負荷が増えます。
- DuckDB のファイルはバックアップと権限設定に注意してください（特に運用環境では適切なアクセス制御を行うこと）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル構成は以下の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - calendar_management.py
    - features.py
    - audit.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (パッケージ一覧に含まれるが詳細は実装に依存)
  - その他モジュール...

簡易的なツリー表示（抜粋）:
```
src/kabusys/
├─ config.py
├─ data/
│  ├─ jquants_client.py
│  ├─ news_collector.py
│  ├─ schema.py
│  ├─ pipeline.py
│  ├─ calendar_management.py
│  └─ stats.py
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ strategy/
│  ├─ feature_engineering.py
│  └─ signal_generator.py
└─ execution/
   └─ __init__.py
```

---

## 開発・拡張のヒント

- strategy 層は発注 API（execution 層）への直接依存を持たない設計になっています。signals テーブルを起点に execution 層で発注ロジックを実装する想定です。
- research の関数は DuckDB 接続を受け取って SQL と純 Python で処理します。pandas 等に依存せず軽量に保たれています。
- J-Quants クライアントはページネーション・トークン再利用をサポートしているため、大量取得でも安定動作を目指しています。
- テスト時は環境変数自動ロードを無効化して、テスト用の一時環境変数を注入することを推奨します。

---

## ライセンス・コントリビューション

ライセンス情報・貢献ガイドラインはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本 README では省略）。

---

この README はコードベースの主要機能と使い方の概要を示しています。各モジュールのドキュメント文字列（docstring）に詳細な設計意図・例外ハンドリングの説明が含まれていますので、実装の詳細確認や拡張時は該当モジュールのソースを参照してください。