# KabuSys — 日本株自動売買基盤（README）

KabuSys は日本株向けのデータプラットフォームと自動売買基盤のコアライブラリです。  
J-Quants / RSS / OpenAI（LLM）と連携してデータ収集・ETL・品質チェック・ニュースセンチメント解析・市場レジーム判定・ファクター計算・監査ログを提供します。

主な設計方針：Look‑ahead bias を避ける（日付を明示的に渡す）、DuckDB を中心に冪等保存（ON CONFLICT）、外部 API のリトライ/レート制御、フェイルセーフ（API 失敗時はスコアを 0 にフォールバックする等）。

---

## 主要機能（抜粋）

- データ取得 / ETL
  - J-Quants から株価（日足）・財務・上場情報・市場カレンダーの差分取得（ページネーション対応）
  - DuckDB へ冪等保存（ON CONFLICT）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損・重複・スパイク（急騰/急落）・日付不整合の検出
- ニュース収集・NLP
  - RSS からのニュース取得（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI を用いた記事/銘柄ごとのセンチメント解析（gpt-4o-mini, JSON Mode）
  - news_nlp.score_news による ai_scores テーブルへの書き込み
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離 + マクロニュースセンチメントを合成して日次レジーム判定（bull/neutral/bear）
  - regime_detector.score_regime
- リサーチ / ファクター
  - モメンタム、ボラティリティ、バリュー等のファクター計算（research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ（トレーサビリティ）
  - シグナル → 発注 → 約定に至るトレース用テーブル群と初期化ユーティリティ（data.audit）
- ユーティリティ
  - 環境設定読み込み（.env 自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - 汎用統計ユーティリティ（z-score 正規化）

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（一例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - その他：typing（標準）、urllib 等標準ライブラリ

（実プロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン / workdir を作成
   - プロジェクトルートに `pyproject.toml` / `.git` がある想定（config の自動 .env ロードに使われます）。

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存ライブラリをインストール
   - 例（最低限）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 編集開発用にパッケージをインストール:
   ```bash
   pip install -e .
   ```

4. 環境変数 / .env を用意
   - プロジェクトルートに `.env` または `.env.local` を配置すると、自動で読み込まれます（読み込み順：OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. データベース格納用ディレクトリを作成（必要に応じて）
   - デフォルト: `data/kabusys.duckdb`（Settings.duckdb_path）
   ```bash
   mkdir -p data
   ```

---

## 環境変数（主なもの）

必須（アプリの利用に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知に使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- KABU_API_PASSWORD — kabuステーション API パスワード（実行/発注を行う場合）

OpenAI 関連:
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）

設定（任意 / デフォルトあり）:
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env の自動ロードを無効化

例：.env（参考）
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要 API の例）

以下は Python からの直接利用例です。すべての関数は DuckDB の接続オブジェクトを受け取ります（duckdb.connect() の返り値）。

- DuckDB 接続例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント解析（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY でも可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_db_path = Path("data/audit.duckdb")
audit_conn = init_audit_db(audit_db_path)
# audit_conn を使用して監査テーブルにアクセスできます
```

- ファクター計算（研究用）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore_normalize 等を使って正規化可能
from kabusys.data.stats import zscore_normalize
z_records = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- ほとんどの関数は target_date を明示的に受け取ります（datetime.today() を内部で参照しない設計） — バックテストや再現性に有利です。
- OpenAI 呼び出し等の外部 API はリトライやフェイルセーフを持ちますが、API キーとレート制御の準備をしてください。
- テストでは _call_openai_api 等の内部ヘルパーをモックして API 呼び出しを差し替えることが想定されています。

---

## 典型的なワークフロー（概略）

1. .env をセットアップして API キー等を配置する
2. DuckDB 初期スキーマを準備（別途 schema 初期化ユーティリティがあれば実行）
3. 日次バッチ（run_daily_etl）を実行してデータを取得・保存
4. ニュース収集ジョブ（news_collector.fetch_rss + 保存ロジック）を定期実行
5. AI スコアリング（score_news）を実行して ai_scores を更新
6. レジーム判定（score_regime）を実行して market_regime を更新
7. research モジュールでファクターを算出し、戦略層にパス
8. 監査テーブルにシグナル／発注／約定をログとして残す

---

## ディレクトリ構成（抜粋）

プロジェクトは src パッケージ配下に実装されています。主なファイル/モジュール:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存関数
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult の公開
    - calendar_management.py     — マーケットカレンダー管理
    - news_collector.py          — RSS ニュース収集
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（z-score 等）
    - audit.py                   — 監査ログ用 DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py         — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー
  - （strategy / execution / monitoring 等のサブパッケージも公開予定/存在）

---

## テスト / 開発時のヒント

- 自動 .env 読み込みを無効化したい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しや外部 HTTP をテストする場合は、内部の _call_openai_api や _urlopen をモックして差し替える設計になっています（ユニットテストの容易化）。
- DuckDB の executemany は空リストを受け付けないバージョンの扱いに注意（コード内でチェック済み）。

---

## 注意事項 / 設計上の留意点

- 多くの箇所で「ルックアヘッドバイアスの回避」が設計目標になっています。バックテスト時は target_date より未来のデータを参照しないよう注意してください。
- 外部 API（J-Quants / OpenAI）に依存するため、適切な API キー管理とレート制御が必須です。
- 本リポジトリはインフラや戦略実行部分（実際の発注ロジック）と組み合わせて利用される想定です。実際の売買を行う場合はリスク管理とテストを十分に行ってください。

---

以上が KabuSys の概要と使い方の入門ガイドです。詳細は各モジュール（kabusys/data, kabusys/ai, kabusys/research）のドキュメントとコードコメントを参照してください。必要であれば README に載せる内容（例: CI / デプロイ手順、追加の設定例、schema 初期化手順等）を追記しますので指示ください。