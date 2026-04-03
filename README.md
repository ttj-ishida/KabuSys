# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。  
DuckDB をデータストアとして用い、J-Quants などの外部 API からデータを取得・ETL し、AI（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定、ファクター計算、品質チェック、監査ログ管理などを行うためのユーティリティ群を提供します。

主な目的は「データ取得 → 品質チェック → 研究（ファクター計算 / 特徴量解析） → シグナル生成 → 監査／実行」のワークフローを安全に構築することです。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ユーティリティ
- データ ETL（J-Quants クライアント）
  - 株価日足（OHLCV）・財務データ・JPX カレンダーの差分取得、保存（冪等）
  - レート制御・リトライ・トークン自動リフレッシュ
- ニュース収集
  - RSS フィードの安全な取得（SSRF 対策・サイズ制限・トラッキング削除）
  - raw_news / news_symbols への冪等保存
- ニュース NLP / AI
  - ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini 等）でセンチメントを評価（score_news）
  - マクロニュース + ETF（1321）の MA200 乖離を合成して市場レジーム判定（score_regime）
  - API 呼び出しはリトライ・バックオフ・フェイルセーフ実装
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン、IC（情報係数）、統計サマリー、Zスコア正規化等
- データ品質チェック
  - 欠損、重複、スパイク（急変）、日付不整合などの検出
  - QualityIssue オブジェクトで問題を集約
- 監査ログ（Audit）
  - シグナル → 発注 → 約定までのトレーサビリティ用スキーマ初期化（DuckDB）
  - 冪等キー（order_request_id, broker_execution_id 等）を想定
- ユーティリティ
  - 市場カレンダー管理（営業日判定、next/prev trading day 取得）
  - DuckDB 用スキーマ初期化ユーティリティ等

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実行環境に応じてさらに urllib 等標準ライブラリ以外の依存を追加してください）

インストール例（最低限）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 必要なら他のパッケージも追加
```

---

## 環境変数（主要）

アプリケーションは環境変数または .env / .env.local から設定を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml の親ディレクトリ）を基に行われます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数：
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード（発注系で使用）
- OPENAI_API_KEY — OpenAI API キー（score_news, score_regime 等の AI 機能）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development | paper_trading | live
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

.env のパースはシェル風の記法（export、クォート、コメント）に対応しています。

---

## セットアップ手順（ローカル開発向け）

1. レポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   （プロジェクトに requirements.txt がある場合はそれを使用）
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定
   - ルートに `.env` を作成（.env.example を参照）
   - あるいは環境変数を直接エクスポート

5. データベース初期化（必要に応じて）
   - 監査ログ専用 DB を初期化する例:
     ```python
     from pathlib import Path
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(Path("data/audit.duckdb"))
     # これで監査用のテーブルが初期化されます
     ```

---

## 基本的な使い方（例）

- 共通設定取得:
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続と日次 ETL 実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント評価（score_news）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026,3,20))
print(f"書込銘柄数: {written}")
# OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定
```

- 市場レジーム判定（score_regime）:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査スキーマ初期化（既存接続に追加）:
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
init_audit_schema(conn, transactional=True)
```

- ニュース収集（fetch_rss）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["title"], a["datetime"])
```

注意:
- OpenAI 呼び出しはコスト・レート制約があるため、API キー管理と実行頻度に注意してください。
- J-Quants API はレート制限があり、モジュールは最小間隔スロットリング・リトライを実装しています。

---

## よくある操作コマンド（例）

- 自動 ETL を cron / systemd タイマーで回す場合は、Python スクリプトを作り上記 run_daily_etl を呼び出すとよいです。
- 開発中に .env の自動読み込みを無効化したい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・モジュール構成です（本ドキュメント作成時点の抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch / save）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult 再エクスポート
    - news_collector.py          — RSS ニュース収集
    - calendar_management.py     — 市場カレンダー管理（is_trading_day 等）
    - stats.py                   — zscore_normalize 等
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum/value/volatility）
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー
  - monitoring/                   — 監視・実行関連（フォルダ想定）
  - strategy/                     — 戦略実装層（フォルダ想定）
  - execution/                    — 発注 / ブローカー統合（フォルダ想定）

（実際のリポジトリではさらに細かいモジュール・ユーティリティが含まれます）

---

## 設計上の注意点・ガイドライン

- ルックアヘッドバイアスを避けるため、内部関数は date.today()/datetime.today() を安易に参照しない設計になっています。必ず明示的に target_date を渡して実行してください。
- API 呼び出し失敗時はフェイルセーフとして処理を継続する設計の箇所が多くあります（例: OpenAI 呼び出し失敗はゼロスコアにフォールバック）。運用上のポリシーに合わせてログ監視とアラートを設定してください。
- DuckDB の executemany に空のリストを渡すとエラーになるバージョンがあります（コード内で対策済ですが、DuckDB のバージョンに注意してください）。
- 監査ログは削除しない前提で設計されています。監査データ管理方針を定めてから運用してください。

---

## トラブルシューティング（短冊）

- OpenAI のレスポンスが想定 JSON ではない場合 → ライブラリはパース失敗をログに出しスキップします。レスポンス変化（モデルの挙動変更等）に注意。
- J-Quants 401 エラー → リフレッシュトークンの期限切れ、JQUANTS_REFRESH_TOKEN の更新が必要です。
- RSS 取得で SSRF/プライベートアドレス警告が出る → フィード URL が社内アドレス・非 http/https を指していないか確認してください。
- DuckDB のテーブル/DDL 関連エラー → スキーマ初期化（init_audit_schema 等）を確認してください。

---

必要に応じて README に実行例スクリプト、CI 設定、より詳しい API リファレンス（各関数の引数・戻り値）を追加できます。追加したい項目があれば教えてください。