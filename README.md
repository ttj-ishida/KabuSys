# KabuSys

KabuSys は日本株のデータ取得・前処理・特徴量生成・シグナル生成・ETL を一貫して行うためのライブラリ群です。J-Quants API から市場データや財務データを取得し、DuckDB をバックエンドにして戦略用の特徴量（features）やシグナル（signals）を生成します。ニュース収集やマーケットカレンダー管理、監査ログ用スキーマなども含まれます。

主な用途:
- データパイプライン（J-Quants → DuckDB）
- 研究用ファクター計算および特徴量構築
- 戦略のシグナル生成（BUY / SELL 判定）
- RSS ベースのニュース収集と銘柄紐付け
- カレンダー管理・監査ログ

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出）
  - 必須環境変数を型安全に取得
- データ取得（J-Quants クライアント）
  - 株価日足（ページネーション対応、レート制限・リトライ実装）
  - 財務諸表（四半期等）
  - マーケットカレンダー
  - DuckDB への冪等保存（ON CONFLICT 処理）
- ETL パイプライン
  - 差分取得（最終取得日からの差分）／バックフィル
  - 品質チェックフレームワークとの統合（欠損・スパイク等）
  - 日次バッチ（run_daily_etl）
- 特徴量（Feature）計算
  - Momentum / Volatility / Value 等のファクター計算（研究モジュールを利用）
  - クロスセクショナルな Z スコア正規化（clip ±3 等の処理）
  - features テーブルへの日付単位の UPSERT（冪等）
- シグナル生成
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム検出による BUY 抑制
  - エグジット（SELL）判定（ストップロスなど）
  - signals テーブルへの日付単位の置換（冪等）
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 上限、XML 安全パーサ）
  - 記事ID の正規化ハッシュ化、raw_news に冪等保存、news_symbols で銘柄紐付け
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティ
  - calendar_update_job による夜間差分更新
- スキーマ／監査
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema による初期化

---

## 前提（依存関係）

主な外部依存（インストールが必要）
- Python 3.8+
- duckdb
- defusedxml

※その他、環境によって requests 等が必要になる場合があります。パッケージ配布のセットアップファイル（pyproject.toml / requirements.txt）がある場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストールします（例: pip）。

   ```bash
   pip install duckdb defusedxml
   # またはプロジェクトの requirements/pyproject を使用
   ```

3. 環境変数を用意します。プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知用ボットトークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）

   任意（デフォルトあり）
   - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : SQLite（監視用）パス（デフォルト: data/monitoring.db）

   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマを初期化します（初回のみ）:

   Python REPL またはスクリプトで:

   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返す
   ```

---

## 使い方（主要な操作例）

以下は主要な API の使用例です。すべて DuckDB のコネクション（kabusys.data.schema.init_schema が返すもの）を最初に用意します。

- DuckDB 接続の初期化（再掲）

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL（市場カレンダー/株価/財務 → DuckDB に保存、品質チェック実行）

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）構築

  ```python
  from kabusys.strategy import build_features
  from datetime import date

  n = build_features(conn, target_date=date(2025, 1, 6))
  print(f"features upserted: {n}")
  ```

- シグナル生成

  ```python
  from kabusys.strategy import generate_signals
  from datetime import date

  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total}")
  ```

- ニュース収集（RSS）

  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は抽出に利用する銘柄コード集合（例: {'6758','7203',...}）
  results = run_news_collection(conn, sources=None, known_codes=set(['6758','7203']))
  print(results)
  ```

- カレンダー夜間更新ジョブ

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

注意:
- run_daily_etl 等の関数は内部で例外処理を行い、結果に error 情報を格納します。運用スクリプト側で結果（ETLResult）を確認して通知や再試行の判断を行ってください。
- API トークンの自動リフレッシュやレート制御は内部で実装されています。認証失敗や API 制限に対するログを追ってください。

---

## 自動 .env ロードの挙動

- パッケージ import 時に（kabusys.config）プロジェクトルートを .git または pyproject.toml を基準に探索し、見つかったルートから `.env`（先にロード）→ `.env.local`（上書き）を読み込みます。OS 環境変数が既にセットされているキーは上書きされません（.env.local は override=True だが protected によって OS 環境変数は保護されます）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに有用）。

---

## ディレクトリ構成（主要ファイル）

パッケージルートは src/kabusys/ を想定し、主要モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存ロジック
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義・初期化（init_schema）
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - features.py            — features の公開ラッパ
    - calendar_management.py — カレンダー管理 / calendar_update_job
    - audit.py               — 監査ログスキーマ定義
    - ...（その他 data 層ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成ロジック（build_features）
    - signal_generator.py    — シグナル生成ロジック（generate_signals）
  - execution/               — 発注 / ブローカー連携層（空の __init__ を含む）
  - monitoring/              — 監視・Slack 通知等（将来的な実装）

この README の内容はコードのドキュメント文字列（docstring）をもとに作成しています。個々の関数・クラスには更に詳細な docstring が付与されていますので、実装や挙動の確認はソースコードを参照してください。

---

## 運用上の注意 / ベストプラクティス

- ルックアヘッドバイアス対策のため、各処理は「target_date 時点で利用可能なデータのみ」を利用するよう設計されています。ETL/戦略のバッチ実行時は target_date の扱いに注意してください。
- DuckDB ファイルはバックアップやスナップショットを取り、データ破損に備えてください。
- AI スコアや外部ニュースを利用する場合は、欠損や異常値に備えて中立値（0.5）で補完するなどフォールトトレラントな設計になっていますが、運用ルールは必ず確認してください。
- 本ライブラリは発注 API（kabuステーション等）への直接のフル実装を含まない層があります。実際の注文送出や本番運用は必ず検証環境で十分にテストしてください（paper_trading モードの活用を推奨）。

---

## 開発・貢献

- テスト・CI の整備、依存関係の pin、パッケージ化（pyproject.toml、requirements.txt）を行うことで導入が容易になります。
- バグ修正や新機能追加の際は、ドキュメント（StrategyModel.md、DataPlatform.md 等）と実装の整合性を必ず確認してください。

---

質問や追加で README に載せたい実行例・運用手順があれば教えてください。利用ケースに合わせたサンプルスクリプト（cron ジョブ例、Docker Compose 設定、簡易監視スクリプト等）を作成できます。