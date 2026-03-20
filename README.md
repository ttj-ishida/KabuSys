# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群。  
データ取得（J-Quants）、ETL、マーケットカレンダー管理、ニュース収集、特徴量作成、シグナル生成、監査・実行用スキーマなどを含むモジュール設計になっています。研究用（research）コンポーネントと運用用コンポーネントを分離し、ルックアヘッドバイアス対策や冪等性（idempotency）を重視しています。

バージョン: 0.1.0

---

## 主な機能

- データ取得
  - J-Quants API クライアント（レート制限、リトライ、トークン自動更新、ページネーション対応）
  - 株価（OHLCV）・財務データ・市場カレンダーの取得と DuckDB への冪等保存
- ETL パイプライン
  - 差分取得（最終取得日を元に差分のみ取得）、バックフィルのサポート
  - 日次 ETL（market calendar → prices → financials → 品質チェック）
- カレンダー管理
  - market_calendar テーブルの更新、営業日判定（DB 優先、未登録日は曜日フォールバック）
  - next/prev trading day / get_trading_days / is_sq_day 等のユーティリティ
- ニュース収集
  - RSS フィードからの記事収集（SSRF対策、XML攻撃対策、トラッキングパラメータ除去、記事IDは正規化URLの SHA256）
  - raw_news / news_symbols への冪等保存
- 研究用ファクター計算（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 特徴量エンジニアリング
  - 生ファクターの正規化（Z スコア）、ユニバースフィルタ（最低株価、平均売買代金）、±3 でクリップ、features テーブルへの UPSERT
- シグナル生成
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ冪等保存
  - Bear レジーム抑制、エグジット（ストップロス、スコア低下）判定
- スキーマ・監査
  - DuckDB 用のスキーマ定義（Raw/Processed/Feature/Execution 層）
  - 監査ログ（signal_events, order_requests, executions 等）設計（UTC タイムスタンプ、冪等キー）
- 共通ユーティリティ
  - zscore 正規化などの統計ユーティリティ

---

## 要件 / 推奨環境

- Python 3.10 以上（型アノテーションで 3.10 構文を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API など外部 API にアクセスする場合）
- J-Quants のリフレッシュトークン等の外部サービス認証情報

（実際のパッケージ化・requirements.txt はプロジェクトに応じて用意してください）

---

## 環境変数（主に必須）

このライブラリは .env（プロジェクトルート）および .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live). デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL). デフォルト: INFO
- KABU_API_BASE_URL — kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite DB（モジュールによって使用）。デフォルト: data/monitoring.db

.env の読み込み優先順位:
OS 環境変数 > .env.local > .env

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存ライブラリをインストール（例）
   ```
   pip install duckdb defusedxml
   # 実際はプロジェクトの requirements.txt / pyproject.toml を使用してください
   ```

4. パッケージをインストール（開発モード）
   ```
   pip install -e .
   ```

5. .env をプロジェクトルートに作成（例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（代表的な例）

以下は簡単な Python スニペット例です。実際の運用ではエラーハンドリング・ログ設定・認証情報管理を適切に実装してください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（J-Quants からデータ取得→保存→品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しない場合は today が使われる
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルへ保存）
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, date(2024, 1, 4))
  print(f"features upserted: {count}")
  ```

- シグナル生成（signals テーブルへ保存）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2024, 1, 4))
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ（RSS 収集 → raw_news / news_symbols 保存）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes は銘柄抽出に利用するコードセット（例: 上場銘柄コードセット）
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(res)
  ```

- カレンダー更新（夜間バッチなどで実行）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar entries saved: {saved}")
  ```

- J-Quants の low-level 呼び出し（取得のみ）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 重要な設計上の注意

- ルックアヘッドバイアス防止:
  - ファクター / シグナル計算は target_date 時点で利用可能なデータのみを参照するように設計されています。
  - jquants_client は fetched_at を UTC で付与し「いつデータを知り得たか」を記録します。
- 冪等性:
  - DB への保存は可能な限り ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING を使って冪等に行います。
  - ETL は差分取得 + バックフィルを組み合わせて API の後出し修正に追随します。
- セキュリティ:
  - RSS フェッチでは SSRF 対策、XML パース防御（defusedxml）、受信サイズ制限などを実装しています。
  - J-Quants クライアントはレート制限とリトライを実装しています。

---

## ディレクトリ構成（抜粋）

ソースは `src/kabusys` 以下に配置されています。主なモジュール / ファイル:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - schema.py               — DuckDB スキーマ定義・初期化（init_schema）
    - stats.py                — zscore_normalize 等統計ユーティリティ
    - news_collector.py       — RSS 収集・前処理・保存ロジック
    - calendar_management.py  — market_calendar 管理・営業日ユーティリティ
    - features.py             — データ層向けの feature ユーティリティ再エクスポート
    - audit.py                — 監査ログ（signal_events / order_requests / executions）
    - pipeline quality 等（品質チェックモジュールが別途存在）
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  — ファクター合成・正規化→features テーブル
    - signal_generator.py     — final_score 計算・BUY/SELL シグナル生成
  - execution/                — (発注・約定管理等の実装ディレクトリ)
  - monitoring/               — (監視・アラート用モジュール; __all__ に含まれるが実装はプロジェクト参照)

（上記は主要ファイルのみの抜粋です。プロジェクト全体のツリーはリポジトリを参照してください。）

---

## 開発 / 貢献

- コードの変更 / テスト追加は PR をお願いします。  
- 簡易的な動作確認は DuckDB のインメモリまたはローカルファイルで可能です（例: init_schema(":memory:")）。

---

## 参考

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- データベースファイルの既定値は `data/kabusys.duckdb`（DuckDB）および `data/monitoring.db`（SQLite）です。

---

必要であれば README に以下を追加できます:
- 具体的な .env.example のテンプレート
- 追加の実行例（cron / systemd / Docker / CI での運用例）
- テーブルスキーマの簡易図や ER 図
- よくあるエラーとトラブルシュート

要望があれば追記します。