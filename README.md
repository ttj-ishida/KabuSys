# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得（J‑Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査用スキーマなどを備えたモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のレイヤーで構成された小〜中規模の自動売買基盤向けライブラリです。

- Data layer: J‑Quants からの株価・財務・カレンダー・ニュース取得、DuckDB への冪等保存、品質チェック、カレンダー管理、ニュースの前処理と銘柄紐付け
- Research layer: ファクター計算（モメンタム、ボラティリティ、バリュー）・特徴量探索（forward returns、IC、統計要約）
- Strategy layer: 特徴量正規化（Zスコア）→ features テーブルへ保存、features + AIスコアからの売買シグナル生成
- Execution / Audit: 発注・約定・ポジション・監査ログ用スキーマ（テーブル定義と初期化）
- 設定管理: `.env` / 環境変数読み込みと validation

設計上のポイント:
- DuckDB を用いたオンプレ（ローカル）DB を想定し、ETL/解析/戦略は DB 接続を介して行う
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- J‑Quants API のレート制御、リトライ、トークン自動リフレッシュ対応
- 冪等性を重視（INSERT ... ON CONFLICT / DO UPDATE、トランザクション）

---

## 主な機能一覧

- J‑Quants API クライアント（レート制限・リトライ・トークン自動更新）
  - 株価（daily quotes）、財務（quarterly statements）、市場カレンダー取得
  - DuckDB への安全な保存（冪等）
- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分取得、バックフィル、品質チェック、日次 ETL 実行エントリポイント
- DuckDB スキーマ定義と初期化 (`kabusys.data.schema`)
  - raw / processed / feature / execution / audit のテーブル群を定義
- 特徴量計算（research）
  - モメンタム / ボラティリティ / バリューを DuckDB データから算出
- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - ファクターの統合・ユニバースフィルタ・Zスコア正規化・features テーブルへ UPSERT
- シグナル生成 (`kabusys.strategy.signal_generator`)
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成し signals テーブルへ保存
  - Bear レジーム抑制、エグジット（ストップロス・スコア低下）判定
- ニュース収集 (`kabusys.data.news_collector`)
  - RSS 収集、URL 正規化、記事ID（SHA‑256）、raw_news 保存、記事⇄銘柄紐付け（news_symbols）
  - SSRF / XML Bomb / Gzip Bomb 等の防御処理を実装
- 汎用統計ユーティリティ (`kabusys.data.stats`)
  - Zスコア正規化など

---

## 必要な環境変数 / 設定

Settings クラス（`kabusys.config.settings`）で参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL (省略可) — デフォルト: `http://localhost:18080/kabusapi`
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (省略可) — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH (省略可) — 監視用 SQLite パス（デフォルト: `data/monitoring.db`）
- KABUSYS_ENV (省略可) — `development` / `paper_trading` / `live`（デフォルト: `development`）
- LOG_LEVEL (省略可) — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` が自動で読み込まれます。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

簡単な `.env` 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python のインストール
   - 推奨 Python 3.8+（型ヒント、pathlib 等を使用）
2. 依存ライブラリのインストール（例）
   - 必要パッケージの一例:
     - duckdb
     - defusedxml
   - pip でインストール:
     ```
     pip install duckdb defusedxml
     ```
   - （もしパッケージ化されている場合は）プロジェクトルートで:
     ```
     pip install -e .
     ```
3. 環境変数を設定
   - 上記の `.env` をプロジェクトルートに作成するか、シェルで環境変数をエクスポートしてください。
4. DuckDB スキーマ初期化
   - Python REPL / スクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - メモリ DB を使う場合は `":memory:"` を渡せます。

---

## 使い方（代表的な例）

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得と保存）:
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）構築:
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")
  ```

- シグナル生成:
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total}")
  ```

- ニュース収集と保存:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # known_codes は既知の銘柄コード集合（抽出のため）
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)
  ```

- J‑Quants 直接利用例（トークンを利用してデータ取得）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  rows = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

注意点:
- 各関数は DuckDB の接続オブジェクトを受け取り DB 上のテーブルを参照・更新します。初回は必ず `init_schema()` でテーブルを作成してください。
- 各処理は「日付単位の置換（DELETE → INSERT）」を行うため冪等です。

---

## ディレクトリ構成（重要ファイル抜粋）

プロジェクトの主要なファイル/モジュール構成（src/kabusys 配下）:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/
  - jquants_client.py        — J‑Quants API クライアント（fetch/save）
  - news_collector.py       — RSS ニュース収集・前処理・保存
  - schema.py               — DuckDB スキーマ定義と初期化（init_schema）
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py  — market_calendar 管理・営業日判定
  - features.py             — features インターフェース（再エクスポート）
  - audit.py                — 監査ログ用スキーマ（signal_events, order_requests, executions）
- src/kabusys/research/
  - factor_research.py      — mom / volatility / value ファクター計算
  - feature_exploration.py  — forward returns, IC, factor summary, rank
- src/kabusys/strategy/
  - feature_engineering.py  — ファクター統合・ユニバースフィルタ・features への書込
  - signal_generator.py     — final_score 計算と signals 書込
- src/kabusys/execution/      — 発注/証券会社連携関連（空の __init__.py 等）
- src/kabusys/monitoring/     — 監視・モニタリング関連（参照される可能性あり）

---

## 追加メモ / 運用上の注意

- J‑Quants のレート制限（120 req/min）に対応する RateLimiter が実装されています。大量取得時は注意してください。
- トークン自動リフレッシュ: `get_id_token` がリフレッシュトークンから ID トークンを発行し、HTTP 401 時に自動でリフレッシュする処理を持ちます。
- ニュース収集では SSRF・XML の危険対策・レスポンスサイズ上限等の安全対策を実装していますが、運用時には許可する RSS ソースとタイムアウト等を適切に設定してください。
- 本リポジトリには戦略モデルの詳細（StrategyModel.md 等）やデータ設計（DataSchema.md）の参照がコード内コメントに記載されています。運用/改善時はそれらドキュメントを参照してください（プロジェクトによっては別途同梱されている想定）。

---

もし README に含めたい追加情報（例: CI / デプロイ手順、より詳細な `.env.example`、よくあるトラブルシュート等）があれば教えてください。必要に応じて追記して整備します。