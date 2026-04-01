# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ収集）、ニュース NLP（OpenAI を用いた銘柄センチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

主な設計方針：
- ルックアヘッドバイアスの回避（内部で date.today()/datetime.now() を直接参照しない設計）
- DuckDB を主要なデータストアとして利用
- 外部 API 呼び出しはリトライ・バックオフを備えた堅牢な実装
- ETL / 保存処理は冪等（idempotent）に設計

---

## 機能一覧

- data
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー、上場情報）
  - ETL パイプライン（差分取得・保存・品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS -> raw_news、SSRF 考慮、トラッキング除去）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマの初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（Zスコア正規化）
- ai
  - ニュースの NLP スコアリング（gpt-4o-mini を利用、JSON Mode）
  - 市場レジーム判定モジュール（ETF 1321 の MA200 とマクロニュースセンチメントを合成）
- research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（将来リターン計算、IC、統計サマリー）
- config
  - 環境変数 / .env ファイルの自動ロードと管理（自動ロードは無効化可能）

主要な性質：
- 各 ETL/保存処理は冪等（ON CONFLICT / UPDATE 等）を意識
- 外部 API のリトライ・レートリミット制御を実装
- テスト向けのフック（例: OpenAI 呼び出しの差し替え、KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## セットアップ手順

前提：Python 3.9+ 推奨（typing 注釈に Union|None 形式を使用）。プロジェクトルートに pyproject.toml/.git がある想定。

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements ファイルがあればそちらを使用してください）

3. パッケージをローカルインストール（開発時）
   - python -m pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` もしくは `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードは無効化されます）。
   - 重要な環境変数例：
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD : kabu ステーション API のパスワード（必要に応じて）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知用
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要なユースケース）

以下は簡単な Python スニペット例です。適宜ログ設定やエラーハンドリングを追加してください。

- DuckDB 接続を用意する
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数に設定しているか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化（独立DB または 既存 DuckDB にスキーマ追加）
```python
from kabusys.data.audit import init_audit_db, init_audit_schema

# 監査専用 DB ファイルを作成して初期化
audit_conn = init_audit_db("data/audit.duckdb")

# 既存 conn にスキーマを追加する場合
init_audit_schema(conn, transactional=True)
```

- J-Quants API トークン取得（直接利用したい場合）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って取得
```

注意点：
- score_news / score_regime は OpenAI API を呼ぶため、APIキーは環境変数か引数で明示してください。
- テスト時に外部呼び出しをモックする設計（内部の _call_openai_api を patch 可能）です。
- ETL 実行はデータ欠損や品質チェックで errors/quality_issues を返すため、結果を確認して運用判断を行ってください。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py — パッケージエントリ（version 等）
- config.py — 環境変数 / .env の自動読み込みと Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアントと保存関数
  - pipeline.py — ETL パイプライン（run_daily_etl 等） + ETLResult
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集と前処理
  - calendar_management.py — 市場カレンダー管理・ジョブ
  - quality.py — データ品質チェック
  - stats.py — 汎用統計関数（zscore_normalize）
  - audit.py — 監査ログ（DDL/初期化）
- research/
  - __init__.py
  - factor_research.py — Momentum/Volatility/Value の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー、ランク付け

その他：
- README.md（このファイル）
- pyproject.toml / .git / .env.example （プロジェクトルート想定）

---

## 運用上の注意 / ヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の API レート制限や OpenAI のレート制限に注意してください。各クライアントはリトライ・バックオフ・レート制御を行いますが、運用時の大量リクエストは避けてください。
- look-ahead バイアス回避のため、バックテストやリサーチで使用する際は「データをいつ取得できたか（fetched_at）」と「バックテストの参照日」を厳密に管理してください。
- DuckDB の executemany に対する互換性（空リスト不可など）を考慮して保存処理を実装しています。直接 SQL を編集する場合は注意してください。
- OpenAI 呼び出しの振る舞い（JSON Mode / response_format）に依存しているため、SDK のバージョン差分に注意してください。テストでは内部の _call_openai_api をモックして差し替えることを推奨します。

---

問題や改善提案があれば教えてください。README の追加項目（デプロイ手順、CI 設定、より詳細な .env.example など）を作成します。