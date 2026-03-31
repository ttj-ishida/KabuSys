# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買補助ライブラリ群です。J-Quants や RSS、OpenAI（LLM）などと連携してデータ収集・品質検査・ニュースセンチメント評価・市場レジーム判定・ファクター計算・監査ログ初期化などを提供します。

---

## 概要

主な目的は「日本株のデータ基盤」と「戦略・研究用ユーティリティ」を安定かつ再現可能に提供することです。  
設計方針としては以下を重視しています。

- Look-ahead bias を避ける（日時の扱いに注意）
- DuckDB を中心としたローカルデータストア
- J-Quants API からの差分ETL、冪等保存（ON CONFLICT/UPDATE）
- OpenAI（gpt-4o-mini）を用いたニュース NLP（JSON モード）とレジーム判定
- データ品質チェックと監査ログのスキーマ提供
- 自動で .env をプロジェクトルート（.git / pyproject.toml）から読み込み（無効化可）

---

## 機能一覧

- 環境設定読み込み・検証（kabusys.config）
  - .env / .env.local 自動読み込み（無効化可能）
  - 必須環境変数取得（例: JQUANTS_REFRESH_TOKEN 等）
  - 環境（development/paper_trading/live）・ログレベルの検証

- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants から株価（daily_quotes）、財務データ、マーケットカレンダーを差分取得
  - レート制御・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（raw_prices / raw_financials / market_calendar 等）

- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク（前日比）・重複・将来日付や非営業日のデータ検出

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、前処理、SSRF 対策、トラッキングパラメータ除去、raw_news への冪等保存

- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄ごとのニュースをまとめて LLM に送りセンチメント（ai_scores）を算出・保存
  - バッチサイズ・トークン制御、リトライ、レスポンスバリデーション

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の MA200 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して daily に 'bull'/'neutral'/'bear' を判定・保存

- 研究用機能（kabusys.research）
  - モメンタム・ボラティリティ・バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化

- 監査ログ・トレーサビリティ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブル定義、インデックス、初期化ユーティリティ
  - 監査 DB 初期化関数（init_audit_db）

---

## 必要要件 / 依存

主な依存（コードベースからの抜粋）:

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

その他は標準ライブラリ（urllib, json, logging, datetime, hashlib など）を使用します。  
実環境では OpenAI / J-Quants API の利用に伴うネットワーク接続と API キーが必要です。

インストール例（開発環境）:
```bash
python -m pip install -e .
# または必要パッケージを個別に
python -m pip install duckdb openai defusedxml
```

---

## 環境変数（主要）

プロジェクトは .env/.env.local または OS 環境変数を参照します。自動読み込みはデフォルトで有効。テストで無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（例）:

- JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY         — OpenAI API キー（score_news / score_regime に必要）
- KABU_API_PASSWORD     (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL     — kabu API 基本 URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       (必須) — Slack 通知用 Bot Token
- SLACK_CHANNEL_ID      (必須) — Slack チャンネル ID
- DUCKDB_PATH           — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH         — 実行監視用 PID ファイルパス（デフォルト: data/execution.pid）
- KABUSYS_ENV           — environment: development | paper_trading | live (default: development)
- LOG_LEVEL             — DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)

例: .env（テンプレート）
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. 必要パッケージをインストール
   - 例: python -m pip install -e . もしくは個別インストール
3. プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を作成
   - 上記の必須変数を設定
4. DuckDB 用ディレクトリを作成（必要なら）
   - 例: mkdir -p data
5. （任意）監査 DB を初期化
   - Python 例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主要な呼び出し例）

以下は Python REPL / スクリプトから直接利用する例です。実行前に .env に必要変数を設定してください。

- ETL（日次パイプライン）の実行例:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores 生成）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（market_regime テーブル書込）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB の初期化（専用 DB 作成）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブル等が作成されます
```

- 環境設定の利用:
```python
from kabusys.config import settings
print(settings.duckdb_path)         # Path オブジェクト
print(settings.is_live)             # bool
token = settings.jquants_refresh_token  # 必須で未設定なら例外
```

ログ出力や例外は各モジュールで適切に記録されます。実運用ではスケジューラ（cron / systemd timer）等から ETL やモデル更新ジョブを定期実行してください。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なソースは src/kabusys 以下に配置されています。主なファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（ai_scores）
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント / 保存ロジック
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       — 市場カレンダー管理
    - news_collector.py            — RSS 収集・前処理
    - quality.py                   — データ品質チェック
    - stats.py                     — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログスキーマ初期化
    - etl.py                       — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算 (momentum/value/volatility)
    - feature_exploration.py       — 将来リターン・IC・統計サマリー
  - ai/、data/、research/ の各テストや補助モジュールはプロジェクトに応じて追加

---

## 運用上の注意

- API キー管理:
  - J-Quants のリフレッシュトークンは安全に保管してください。get_id_token() で自動取得・キャッシュされます。
  - OpenAI はレート・費用を考慮してバッチ処理を設定してください（news_nlp はバッチ化・トリム済み）。

- Look-ahead bias に注意:
  - ランタイム関数は内部で date.today() を直接参照することを避ける設計になっていますが、呼び出す際は target_date を明示してください。

- 自動 .env 読み込み:
  - プロジェクトルート（.git / pyproject.toml）を基準に .env を自動読み込みします。テスト時に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB の互換性:
  - executemany に空リストを渡せないバージョン向けのガードがコード中にあります。DuckDB バージョンに応じた挙動を確認してください。

---

## 貢献 / 開発ヒント

- テスト時は外部 API 呼び出し（OpenAI / J-Quants / ネットワーク）をモックすることを推奨します。コード内にはモック差替えしやすい箇所（_call_openai_api のような関数）が設けられています。
- ローカルでの開発時は KABUSYS_ENV=development、LOG_LEVEL=DEBUG にして挙動を詳細確認してください。

---

不明点や README に追加したいサンプル（例: docker-compose、cron の具体例、SQL スキーマ定義抜粋など）があれば教えてください。必要に応じて追記します。