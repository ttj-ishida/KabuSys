# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリ。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、ファクター計算・リサーチユーティリティ、監査ログ（トレーサビリティ）など、自動売買システムのバックエンドに必要な機能群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

KabuSys は日本株自動売買システム向けの内部ライブラリです。主に以下を目的としています。

- J-Quants API からのデータ取得（株価日足、財務、JPX カレンダー）
- DuckDB を用いたローカルデータ保存（冪等保存）
- データ品質チェック（欠損・重複・日付不整合・スパイク検出）
- ニュース収集（RSS）と OpenAI によるニュースセンチメント評価
- 市場レジーム判定（ETF とマクロニュースの合成）
- ファクター計算 / リサーチユーティリティ（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマと初期化ユーティリティ

設計方針として、バックテスト等でのルックアヘッドバイアス回避、API 呼び出しのリトライ／フェイルセーフ、DuckDB での冪等保存、標準ライブラリ主体の実装を重視しています。

---

## 機能一覧（抜粋）

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・トークン更新・ページネーション・レート制御）
  - pipeline, etl: 日次 ETL パイプライン（カレンダー→価格→財務→品質チェック）
  - calendar_management: JPX カレンダー管理（営業日判定、next/prev trading day 等）
  - news_collector: RSS 取得・前処理（SSRF 対策・トラッキング除去・記事ID生成）
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit: 監査ログ用スキーマ定義 / 初期化（signal_events, order_requests, executions）
  - stats: z-score 正規化などの統計ユーティリティ
- ai/
  - news_nlp.score_news: OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアの生成と ai_scores への保存
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースの LLM センチメントを合成した市場レジーム判定
- research/
  - factor_research: モメンタム・バリュー・ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー、ランク化ユーティリティ
- config:
  - Settings クラスで環境変数管理（.env 自動ロード機能を含む）

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10 以上）
   - virtualenv や pyenv などを使用して隔離環境を作成してください。

2. ソースをチェックアウト

   例:
   - git clone … （プロジェクトルートに `pyproject.toml` / `.git` がある想定）

3. 依存ライブラリをインストール

   最低限の必須パッケージ（例）:
   - duckdb
   - openai
   - defusedxml

   例（pip）:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

   開発用途ではさらに linters やテストツールを追加してください。

4. パッケージをインストール（編集可能モード）
   ```
   pip install -e .
   ```
   （プロジェクトが PEP517/pyproject.toml を持つ前提）

5. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` に必要な環境変数を設定するか、OS 環境変数で設定します（詳細は後述）。
   - 自動ロードはデフォルトで有効。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 簡単な使い方（例）

- DuckDB 接続作成と日次 ETL 実行（pipeline.run_daily_etl を利用）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# デフォルトの DB パスは settings.duckdb_path（例: data/kabusys.duckdb）
conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが必要）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB 初期化（専用 DB）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成されます
```

- J-Quants から直接データを取得する（トークン自動リフレッシュ対応）

```python
from kabusys.data.jquants_client import fetch_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用の Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視 DB など、省略時: data/monitoring.db）
- PID_FILE_PATH: 実行監視用 PID ファイル
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL: ログレベル ("DEBUG", "INFO", ...)

config.Settings は .env ファイル（プロジェクトルートの .git または pyproject.toml を基準に探す）を自動で読み込みます。読み込み順は:
1. OS 環境変数（優先）
2. .env.local（上書き可能）
3. .env（最終）

自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 注意事項・設計上のポイント

- ルックアヘッドバイアス回避
  - AI / ETL / リサーチ系関数は内部で date.today() を盲目的に参照しない設計です。必ず target_date を渡して処理します。
- 冪等性
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を用いて冪等保存を行います。
- エラーハンドリング
  - API 呼び出しはリトライ（指数バックオフ）や 401 のトークンリフレッシュ等に対応しています。AI 呼び出し失敗時はフォールバック（スコア 0.0 等）する実装が所々にあります。
- セキュリティ
  - news_collector では SSRF 対策（リダイレクト検査 / プライベート IP ブロッキング）や defusedxml を利用した XML パースを行っています。
- DuckDB 互換性
  - 一部の executemany 操作は DuckDB のバージョン依存制約（空リスト不可など）に配慮して実装されています。

---

## ディレクトリ構成（主要ファイル）

（パスは src/kabusys 以下）

- __init__.py
  - パッケージ初期化、公開サブパッケージ定義（data, strategy, execution, monitoring）

- config.py
  - Settings クラス (.env 自動ロード、必須環境変数チェック)

- ai/
  - __init__.py
  - news_nlp.py: ニュースセンチメントの取得（score_news, calc_news_window 等）
  - regime_detector.py: ETF MA200 とマクロニュース LLM を合成して市場レジームを判定（score_regime）

- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得・保存・トークン管理・レート制御）
  - pipeline.py: ETL パイプライン（run_daily_etl, 個別 ETL ジョブ）
  - etl.py: ETLResult の再エクスポート
  - calendar_management.py: 市場カレンダー管理（営業日判定・next/prev/get_trading_days, calendar_update_job）
  - news_collector.py: RSS 取得・記事正規化（SSRF 対策、ID 生成、前処理）
  - quality.py: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログスキーマ定義・初期化（signal_events, order_requests, executions）
  - (その他) schema 初期化や補助ユーティリティが格納される想定

- research/
  - __init__.py
  - factor_research.py: calc_momentum, calc_volatility, calc_value
  - feature_exploration.py: calc_forward_returns, calc_ic, factor_summary, rank

---

## 開発・運用にあたっての補足

- テスト
  - API 呼び出しを含むモジュールはモック（unittest.mock.patch）で置き換えやすいように実装されています（例: OpenAI 呼び出し関数のラッパーを差し替え可能）。
- ロギング
  - 各モジュールは logger を使用し、重要なイベント・警告・エラーを出力します。実運用では適切にハンドラを設定してください。
- マイグレーション / スキーマ
  - audit.init_audit_schema 等でテーブルを初期化できます。既存 DB への影響に注意して利用してください。
- Secrets
  - API トークン等は .env を用いるかシークレット管理サービス（Vault 等）を利用し、ソースコードに埋め込まないでください。

---

必要であれば、README にサンプル .env.example、より詳しい API リファレンス、あるいは各モジュールの使用例（ETL の定期実行スケジュール例、Slack 通知フロー、kabu ステーション経由の実行例など）を追加します。どの部分を詳しく補足しますか？