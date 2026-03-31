# KabuSys

日本株用の自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、リサーチ用ファクター計算、監査ログ（オーダー追跡）、および市場レジーム判定などを含みます。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（API エラー時は処理継続）」です。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定のラッパー（settings オブジェクト）

- データ取得・ETL（J-Quants）
  - 株価日足（OHLCV）取得と DuckDB への冪等保存
  - 財務データ取得と保存
  - JPX マーケットカレンダー取得・保存
  - 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）

- データ品質チェック
  - 欠損 / 重複 / スパイク / 日付不整合検出
  - QualityIssue 型で詳細を返却

- ニュース収集
  - RSS フィード取得（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等登録ロジック

- ニュース NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM（gpt-4o-mini）でセンチメントを算出して ai_scores に保存
  - バッチ処理・リトライ・レスポンスバリデーション

- 市場レジーム判定（Regime Detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成し日次で 'bull'/'neutral'/'bear' を判定

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - UUID ベースのトレーサビリティ

- リサーチ用ファクター計算
  - Momentum / Volatility / Value ファクターの計算
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ、Z スコア正規化

---

## 要件

- Python 3.10 以上（typing の | 記法、list[str] 等を使用）
- 主な依存パッケージ（プロジェクトの requirements.txt を参照してくださいが、少なくとも以下が必要です）
  - duckdb
  - openai
  - defusedxml

（その他、運用向けに Slack SDK などが必要になる可能性があります。実プロジェクトでは requirements.txt を整備してください。）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし作業ディレクトリへ移動
   - git clone ...
   - cd <repo>

2. Python 仮想環境作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もし requirements.txt がない場合は最低限:
     - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動ロードされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. （初回のみ）監査用 DB の初期化
   - Python REPL やスクリプトから:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 必須 / 推奨 環境変数

以下はコード内で参照される代表的な環境変数です。実行する機能に応じて設定してください。

必須（使用する機能に依存）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client 用）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知を送るチャネル ID
- KABU_API_PASSWORD — kabuステーション API を使う場合

OpenAI:
- OPENAI_API_KEY — AI モジュール（news_nlp, regime_detector）で使用。関数呼び出しで api_key を渡すことも可能。

その他:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH — デフォルトの DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

.env 例（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な例）

以下は最小限の使用例です。実行は仮想環境内かアプリケーションコンテキストで行ってください。

- DuckDB 接続の作成（ファイルベース）
```
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL の実行（run_daily_etl）
```
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API キーが必要）
```
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数で与えるか、環境変数 OPENAI_API_KEY を設定しておく
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", n)
```

- 市場レジーム判定
```
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB の初期化（別ファイルに監査ログを保持したい場合）
```
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

- 設定値参照
```
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
```

注意:
- AI モジュールは OpenAI API を呼び出します。API 呼び出しの失敗時はフェイルセーフ（0.0 などのデフォルト値）で続行する設計ですが、API キーが未設定だと ValueError を投げます。
- ETL / 保存処理は DuckDB のテーブル定義に依存します。実行前にスキーマの準備やマイグレーションを行ってください（本 README ではスキーマ作成コマンド群は含めていません）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py          — ニュースの LLM スコアリング（score_news）
  - regime_detector.py   — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py    — J-Quants API クライアント & DuckDB への保存ロジック
  - pipeline.py          — ETL パイプライン（run_daily_etl など）
  - etl.py               — ETL の公開型再エクスポート（ETLResult）
  - news_collector.py    — RSS 収集と前処理
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - quality.py           — データ品質チェック
  - stats.py             — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py             — 監査ログのスキーマ定義と初期化
- research/
  - __init__.py
  - factor_research.py   — Momentum / Volatility / Value 等の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリ等
- research/...（補助ユーティリティ）

---

## 設計上の注意点 / 運用ノート

- ルックアヘッドバイアス対策:
  - 日付計算や DB クエリでは target_date 未満/指定の範囲のみを参照するよう配慮されています。
  - バックテストで使用する場合は ETL の取り込みタイミングに注意してください。

- 冪等性:
  - J-Quants からの保存は ON CONFLICT DO UPDATE を利用し冪等に設計されています。
  - 発注監査系（order_requests）は order_request_id を冪等キーとして扱う想定です。

- フェイルセーフ:
  - 多くの外部 API 呼び出しはリトライ・バックオフを備えており、最終的に失敗してもプロセス全体を止めない設計になっています（ただし重大エラーはログに記録されます）。

---

## 貢献 / ライセンス

この README はコードベースから要点を抜粋した概要です。実運用・開発ではテスト、CI、依存管理（requirements.txt / pyproject.toml）の整備、そして運用用ドキュメント（運用手順・監視・アラート）を別途用意してください。

ご要望があれば、README に以下の追加を作成します:
- 詳細な .env.example（項目別説明）
- DuckDB スキーマ生成 SQL のサンプル（初期テーブル作成）
- よくあるトラブルシューティング（ログの見方、API エラー対応）