# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、データスキーマ管理、特徴量計算、シグナル生成、ニュース収集、監査ログなど、戦略開発から発注管理までの主要機能をモジュール化して提供します。

---

## プロジェクト概要

主な目的は「ルックアヘッドバイアスを排除しつつ、冪等・トレーサビリティを担保した自動売買システム基盤」を提供することです。  
設計方針の要点：

- DuckDB を中心にローカル／軽量な分析用 DB を採用（raw → processed → feature → execution の多層スキーマ）
- J-Quants API からの差分フェッチ、レート制限・リトライ・トークン自動リフレッシュ対応
- 研究（research）で算出した生ファクターを取り込み、Z スコア正規化等で戦略用特徴量を生成
- features と AI スコアを統合してシグナル（BUY/SELL）を生成
- ニュースの収集と銘柄紐付け、監査ログによる発注〜約定のトレース

パッケージ名: `kabusys`（バージョン: 0.1.0）

---

## 主な機能一覧

- data
  - J-Quants クライアント（認証、ページネーション、レート制御、リトライ）
  - DuckDB スキーマ定義・初期化（init_schema / get_connection）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - ニュース収集（RSS → raw_news、記事ID正規化、SSRF対策）
  - 市場カレンダー管理（営業日判定 / next/prev_trading_day）
  - 汎用統計ユーティリティ（Zスコア正規化等）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- strategy
  - feature_engineering.build_features: raw factor を正規化して `features` テーブルに保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成
- monitoring / execution / auditing
  - DB 上の監査テーブルや execution 層のスキーマが定義済（発注・約定・ポジション管理用）

---

## 必要条件（推奨）

- Python 3.10 以上（`X | None` の型アノテーション等を使用）
- 必須ライブラリ（最低限）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

インストール（例）
```bash
python -m pip install "duckdb" "defusedxml"
```
実際のプロジェクトでは requirements.txt / Poetry 等で依存を管理してください。

---

## 環境変数（設定）

`kabusys.config.Settings` が環境変数から設定を読み込みます（パッケージ起動時にプロジェクトルートの `.env` / `.env.local` を自動ロード。これを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（実行に必要な値）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注連携を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルト値あり）
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等に使う SQLite パス（デフォルト: data/monitoring.db）

.env の例（抜粋）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカルでの起動例）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存ライブラリをインストール
   ```bash
   pip install duckdb defusedxml
   ```
   （追加パッケージはプロジェクトに合わせて導入してください）
4. 必要な環境変数を `.env` に設定（上記参照）
5. DuckDB スキーマ初期化
   以下は Python インタプリタやスクリプト内で実行できます。
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ファイル DB を作成
   # またはメモリ DB
   # conn = schema.init_schema(":memory:")
   conn.close()
   ```

---

## 使い方（主要な API / ワークフロー例）

以下はよく使うワークフローの簡単な例です。

1) 日次 ETL を実行してデータを更新する
```python
from datetime import date
import duckdb
from kabusys.data import pipeline, schema

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

2) 特徴量（features）を生成する
```python
from datetime import date
from kabusys.data import schema
from kabusys.strategy import build_features

conn = schema.get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"built features: {count}")
conn.close()
```

3) シグナルを生成して signals テーブルへ保存する
```python
from datetime import date
from kabusys.data import schema
from kabusys.strategy import generate_signals

conn = schema.get_connection("data/kabusys.duckdb")
n_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n_signals}")
conn.close()
```

4) ニュース収集ジョブを実行する
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes: 銘柄コードのセット（例: データベースから取得）
known_codes = {"7203", "6758", "9984"}
res = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count}
conn.close()
```

5) カレンダーの夜間更新ジョブ
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"calendar saved: {saved}")
conn.close()
```

注意点：
- 各 ETL / 保存処理は冪等（ON CONFLICT / トランザクション）設計になっています。
- 研究用途の関数（research.*）は prices_daily / raw_financials テーブルのみ参照し、本番発注ロジックには依存しません。

---

## ディレクトリ構成（主要ファイルと役割）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、必須チェック）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント、フェッチ/保存ユーティリティ
  - schema.py — DuckDB のスキーマ定義と init_schema()
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - news_collector.py — RSS 収集・正規化・DB 保存
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - audit.py — 監査ログ用 DDL
  - features.py — zscore_normalize の公開エイリアス
  - stats.py — 統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py — momentum / value / volatility の計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — build_features（ファクター合成・正規化・features 保存）
  - signal_generator.py — generate_signals（final_score 計算、BUY/SELL 生成）
- execution/ — 発注関連（初期用意あり；未実装ロジックは発展させる想定）
- monitoring/ — 監視／メトリクス関連（拡張想定）

---

## 開発・運用上の注意

- Python バージョンは 3.10 以上を推奨（型ヒントの表記に依存）
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われるため、テスト時や CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます
- J-Quants API のレート制限（120 req/min）に注意。client は内部でスロットリングとリトライを行いますが、運用スケジュール設計時に考慮してください
- DuckDB のスキーマはデータ互換性のため慎重に変更してください。DDL は schema.py に集約されています
- signals → 発注 → 約定のフローは監査ログが重要です。order_request_id などの冪等キーを適切に利用してください

---

## 貢献

改善・バグ修正、機能追加などは PR を歓迎します。特に以下が貢献しやすい領域です：

- execution 層（kabuステーション接続、注文送受信の実装・テスト）
- 品質チェックモジュール（data.quality による欠損・スパイク検出の拡張）
- AI スコア生成パイプライン（ai_scores テーブルへの投入ロジック）
- ドキュメントとサンプルスクリプト（運用手順の具体化）

---

この README はコードベースの主要機能・使い方を手早く把握するための概要です。詳細は各モジュールのドキュメント文字列（docstring）およびソースコードを参照してください。必要なら利用方法の具体的なサンプルや運用用スクリプト案も作成します。ご要望があれば教えてください。