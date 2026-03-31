# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
DuckDB をデータレイヤに、J-Quants や RSS / OpenAI（LLM）を活用してデータ取得・品質管理・ニュースセンチメント・市場レジーム判定・ファクター計算を行い、戦略や約定監査の基盤機能を提供します。

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API失敗時はスキップかデフォルト値）」です。

---

## 機能一覧

- 環境変数／設定読み込み（.env 自動読み込み、上書きルールあり）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得 & DuckDB への冪等保存
  - 財務データ取得 & 保存
  - JPX マーケットカレンダー取得 & 保存
  - トークン自動リフレッシュ、レートリミット管理、リトライ
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得 / backfill 対応
  - ETLResult に結果を集約
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集（RSS）と前処理（URL 正規化、SSRF 対策、XML 安全パース）
- ニュース NLP（OpenAI）で銘柄ごとのセンチメントスコア生成（ai_scores テーブルへ書込）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー）
- 監査ログ（signal_events / order_requests / executions テーブル）と初期化ユーティリティ
- マーケットカレンダー管理（営業日判定 / next/prev / get_trading_days / calendar 更新ジョブ）

---

## 動作環境 / 前提

- Python 3.10+
- 主な依存ライブラリ（例）
  - duckdb
  - openai (新しい SDK の OpenAI クラスを利用)
  - defusedxml
- ネットワーク接続（J-Quants API, RSS フィード, OpenAI）

依存はプロジェクトの pyproject.toml / requirements.txt を参照してください（本コード抜粋には明示ファイルは含まれていません）。

---

## 環境変数（必須 / 推奨）

必須とされている主な環境変数：

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack のチャネルID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必要）
- KABUSYS_ENV — 実行環境: "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

自動的に読み込まれるファイル（プロジェクトルート検出時）:
- .env（OS 環境変数より低優先）
- .env.local（.env を上書き可能）

自動ロードを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

注意: 必須変数が未設定の場合、settings オブジェクト経由でアクセスすると ValueError が発生します（例: settings.jquants_refresh_token）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン / チェックアウト
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - またはプロジェクトに pyproject.toml / requirements.txt があればそれを利用
4. 開発インストール（プロジェクトルートに pyproject.toml がある場合）
   - pip install -e .
5. .env を作成
   - リポジトリルートに .env や .env.local を作成して必須キーを設定
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

---

## 使い方（代表的な API / コマンド例）

下記は Python から直接利用する簡単な例です。DuckDB 接続は `duckdb.connect(path)` で得られる `DuckDBPyConnection` を渡します。

- 共通設定の参照:
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- ETL（日次パイプライン）を実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントの計算（ai_scores へ書き込む）:
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None の場合 env の OPENAI_API_KEY を使用
print("written:", n_written)
```

- 市場レジーム判定（market_regime へ書込む）:
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB の初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリ自動作成
```

- カレンダー更新ジョブ実行:
```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

注意点:
- OpenAI 呼び出しは API エラーに対してリトライやフォールバック（記事なし→0.0）実装済みですが、APIキーが未設定だと ValueError になります。
- DuckDB の executemany はバージョン差による挙動の注意（コード内で考慮済）。

---

## よくある操作・トラブルシューティング

- 環境変数が読み込まれない / テストで自動ロードを止めたい:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OPENAI_API_KEY が無い状態で score_news/score_regime を呼ぶと ValueError:
  - API キーを渡すか、環境変数に設定してください。
- DuckDB のパスやログレベル等を環境変数で上書き:
  - DUCKDB_PATH / LOG_LEVEL 等を .env で設定できます。
- J-Quants の 401 エラー時:
  - get_id_token でリフレッシュトークンを元に ID トークンが再取得され自動リトライします。

---

## ディレクトリ構成（主要ファイル）

（抜粋）プロジェクトは src/kabusys 配下に主要モジュールを配置しています。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（OpenAI）で銘柄別スコア生成
    - regime_detector.py             — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得/保存ロジック）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL の公開型再エクスポート（ETLResult）
    - news_collector.py              — RSS 収集・前処理・保存
    - calendar_management.py         — 市場カレンダー管理（営業日判定・更新ジョブ）
    - stats.py                       — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py                     — データ品質チェック（各種チェック）
    - audit.py                       — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py             — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py         — 将来リターン / IC / 統計サマリー
  - ai, data, research の他に strategy / execution / monitoring 等のサブパッケージが想定（__all__ に宣言）

---

## 開発上の注意

- ルックアヘッドバイアス対策として、内部実装は基本的に date / target_date を明示的に受け取り、date.today() 等を直接参照しない設計になっています。テストやバックテスト時は必ず明示的な日付を与えてください。
- OpenAI 呼び出し部分はテスト容易性のため _call_openai_api をモック可能に実装しています（unittest.mock.patch を推奨）。
- RSS の取得は SSRF 対策・受信上限・XML 安全パーサ（defusedxml）を利用しています。

---

この README はコード抜粋に基づいた概要説明です。実運用や CI/CD、デプロイ、運用監視、Slack 通知・kabuAPI 統合の詳細はプロジェクト内のドキュメント（Design / DataPlatform / Strategy ドキュメント）を参照してください。必要であれば README に含める追加のコマンド例や運用手順（systemd / cron / Airflow など）も作成します。