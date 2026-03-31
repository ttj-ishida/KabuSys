# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、ファクター計算、監査ログ、マーケットカレンダー管理、そして市場レジーム判定などの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）と設定
- 使い方（簡易サンプル）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システムや研究プラットフォーム向けに設計されたモジュール群です。  
主に次の領域をカバーします。

- データ取得/ETL（J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存）
- ニュース収集（RSS）と前処理
- OpenAI を用いたニュースセンチメント解析（銘柄ごと）およびマクロセンチメントの合成による市場レジーム判定
- ファクター算出・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック
- 監査ログテーブル（signal → order_request → executions のトレーサビリティ）
- カレンダー（営業日）管理

設計上の重要点として、ルックアヘッドバイアス回避（日時を明示的な引数で渡す）、API 呼び出し時の堅牢なリトライ・フェイルセーフ処理、DuckDB を中心とした冪等保存を重視しています。

---

## 主な機能（機能一覧）

- ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得、バックフィル、品質チェックの実行
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch / save のラッパー（rate limiting、トークンリフレッシュ、ページネーション、冪等保存）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、前処理、raw_news への保存想定
  - SSRF/サイズ制限などの安全対策実装
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合チェック
- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize など
- ファクター計算（kabusys.research.factor_research）
  - Momentum、Volatility、Value 等
- 特徴量探索（kabusys.research.feature_exploration）
  - 将来リターン計算、IC、統計サマリー、ランキング
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄別ニュースをまとめて OpenAI に送信し ai_scores を生成
- レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime を算出
- 監査ログ初期化（kabusys.data.audit）
  - 監査用テーブル作成/インデックス、専用 DB 初期化ユーティリティ

---

## セットアップ手順

前提:
- Python 3.9+ を推奨
- OS によっては DuckDB のネイティブ拡張が必要になる場合があります（pip で duckdb が入ります）

1. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. パッケージをインストール  
   （プロジェクトに requirements.txt がない場合は最低限以下をインストールしてください）
   ```
   pip install duckdb openai defusedxml
   ```
   - openai: OpenAI API 呼び出し用
   - duckdb: 内部 DB
   - defusedxml: RSS パースの安全化

   （実際のプロダクトではさらにロギングや Slack 連携等の依存を追加してください）

3. パッケージをローカル開発インストール（ソースがパッケージ化されている想定）
   ```
   pip install -e .
   ```

4. 環境変数設定（次節参照）。ローカルではプロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

## 環境変数（.env）と設定

KabuSys は環境変数から設定を取得します（kabusys.config.Settings）。自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。

主な必須設定:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（fetch API 用）
- KABU_API_PASSWORD      — kabuステーション等に接続する際のパスワード（使用箇所に依存）
- SLACK_BOT_TOKEN        — Slack 通知に使用
- SLACK_CHANNEL_ID       — Slack チャンネル ID
- OPENAI_API_KEY         — OpenAI API キー（news_nlp / regime_detector で使う）
  - 関数呼び出し時に api_key 引数で渡すことも可能（引数が優先）

任意/デフォルト:
- KABUSYS_ENV (development|paper_trading|live) — 動作モード（デフォルト: development）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — ログレベル（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

サンプル .env（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_kabu_password

# オプション
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

自動ロードの順序:
- OS 環境変数
- .env.local（存在する場合、.env の値を上書き）
- .env

自動ロードを無効化するには:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（簡易サンプル）

以下は代表的なユースケースの簡単な例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）をセットしてください。

- DuckDB 接続準備と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を使うことも可
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア算出（OpenAI API キーは環境変数 OPENAI_API_KEY を使用するか、api_key に渡す）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written ai_scores for {num_written} codes")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って order_events / order_requests 等に書き込めます
```

- 設定取得の例
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env, settings.is_live)
```

注意:
- OpenAI 呼び出しは料金が発生します。API キーの管理に注意してください。
- run_daily_etl 等は内部で例外を捕捉してログに残しますが、重要なエラーは ETLResult.errors に蓄積されます。結果を確認してください。

---

## よくある運用上の注意

- ルックアヘッド防止: 多くの関数は内部で datetime.today()/date.today() に依存せず、target_date を明示的に引数で受け取る設計になっています。バックテスト時は必ず適切な target_date を渡してください。
- 冪等性: ETL や save_* 関数は ON CONFLICT DO UPDATE 等で冪等に保存する設計ですが、外部から DB に直接操作を行うと期待通りに動かない場合があります。
- テスト: 自動 .env ロードはテスト時に干渉することがあるため、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- API レートとリトライ: J-Quants クライアントはレート制限・リトライを実装しています。大規模なループでの呼び出しには配慮してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要モジュールと役割を示します（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py                       — 環境変数/設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント算出（OpenAI）
    - regime_detector.py             — マクロ＋ETF MA200 を合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント & DuckDB 保存ロジック
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL の公開型（ETLResult）
    - calendar_management.py         — マーケットカレンダー管理（営業日判定等）
    - news_collector.py              — RSS 取得・前処理・保存ロジック
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                       — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py         — 将来リターン, IC, 統計サマリー
  - research/ (他補助ファイル)
  - その他（strategy / execution / monitoring などは __all__ に示唆あり）

（上はコードベースからの要約です。実際のパッケージにはさらにファイルが含まれる可能性があります）

---

## サポート & 開発メモ

- ログや例外は各モジュールで詳細に記録する設計です。運用時はロギング設定（ハンドラ、フォーマット、出力先）を適切に設定してください。
- テストでは外部 API 呼び出し（OpenAI, J-Quants）をモック化して実行することを推奨します。モジュール内の _call_openai_api などはテスト差し替え可能に設計されています。
- データベーススキーマ（raw_prices, raw_financials, ai_scores, market_regime, market_calendar 等）は ETL / audit モジュールの期待する形式である必要があります。初期スキーマ作成は別途 schema 初期化ユーティリティ（未公開ファイル想定）を用意してください。

---

この README はコードベースの主要機能を説明するサマリです。詳細な API やスキーマ、運用手順は各モジュールの docstring を参照してください。必要であればサンプルスクリプトや追加の手順書を作成します。どの部分を詳細化したいか教えてください。