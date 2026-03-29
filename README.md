# KabuSys

日本株自動売買システムのコアライブラリ（内部ユーティリティ / ETL / 研究 / AIスコアリング）。  
このリポジトリはデータ取得・品質管理・特徴量計算・AIによるニュースセンチメント評価・監査ログなど、バックテスト／運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けのデータプラットフォームおよび研究・実行補助のためのモジュール群を提供します。主な目的は以下です。

- J-Quants API を用いた株価 / 財務 / カレンダー等の差分ETL
- DuckDB を利用したデータ保存と品質チェック
- ニュースの収集と LLM を用いた銘柄別センチメント算出（gpt-4o-mini等の JSON モードを想定）
- 市場レジーム判定（ETF + マクロニュースの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（signal → order → execution のトレーサビリティ）

設計上の特徴:
- ルックアヘッドバイアスを避ける（date.today() などを内部の決定ロジックに直接使わない）
- DuckDB を利用した idempotent な保存（ON CONFLICT を適用）
- API 呼び出しにはリトライ / レート制御を実装
- ニュース取得時の SSRF 対策、XML パーサーの安全化、受信サイズ制限などセキュリティ対策あり

---

## 機能一覧

- config
  - .env および環境変数の読み込み、自動ロード機能（プロジェクトルート検出）
  - 設定アクセス用 `settings` オブジェクト（J-Quants トークン、Kabu API、Slack 等）
- data
  - jquants_client: J-Quants API クライアント（認証・ページング・保存ロジック・レート制御）
  - pipeline / etl: 日次 ETL パイプライン（prices / financials / calendar）と ETL 結果クラス
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - news_collector: RSS 取得・前処理・raw_news への永続化補助（SSRF / Gzip / XML 安全対策）
  - calendar_management: JPX カレンダーの取り扱いと営業日計算ユーティリティ
  - stats: z-score 正規化などの統計ユーティリティ
  - audit: 監査ログ用スキーマ定義・初期化（signal_events / order_requests / executions）
- ai
  - news_nlp.score_news: 銘柄ごとにニュースをまとめて LLM に送りセンチメントを ai_scores に保存
  - regime_detector.score_regime: ETF 200日MA乖離とマクロニュースセンチメントを合成して market_regime を更新
- research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）や統計サマリー等

---

## 必要要件（主な依存）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK v1系を想定)
- defusedxml
- （標準ライブラリのみで動く箇所も多いですが、上記は主要な外部依存です）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# またはパッケージ化しているなら:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数または .env ファイルを準備
   - 自動ロード: パッケージ起点で親ディレクトリに `.git` または `pyproject.toml` がある場合、`.env` / `.env.local` を自動で読み込みます。テストなどで自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API のパスワード
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID : Slack チャンネル ID
   - 任意:
     - OPENAI_API_KEY : OpenAI 呼び出しで使用（score_news / score_regime の引数でも指定可）
     - KABUSYS_ENV : development / paper_trading / live （デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/…（デフォルト INFO）
     - DUCKDB_PATH / SQLITE_PATH : データベースパスの上書き
4. データディレクトリ作成
```bash
mkdir -p data
```
5. 監査用 DB を初期化（オプション）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（代表的な例）

以下は簡単な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect）を受け取ります。

- DuckDB 接続を開く
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に保存（OpenAI APIキーは env または api_key 引数で指定）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

- 市場レジームスコア計算
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査スキーマの初期化（既存接続に対して）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- RSS フィード取得（ニュースコレクタの単体利用）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- score_news / score_regime は大量の外部API呼び出しを伴う可能性があるため、APIキーとレート制御に注意してください。
- run_daily_etl は内部で calendar → prices → financials → quality check の順に実行します。失敗したステップはログおよび ETLResult に記録されます。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (オプション、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (score_news / regime_detector の API 呼び出しで未指定時に参照)
- DUCKDB_PATH / SQLITE_PATH (デフォルト: data/kabusys.duckdb / data/monitoring.db)
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を指定すると .env の自動読み込みを無効化

config モジュールの利用例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.is_live)
```

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py — パッケージ定義（data, strategy, execution, monitoring をエクスポート想定）
  - config.py — 環境変数 / .env 読み込み・Settings クラス
  - ai/
    - __init__.py — ai モジュール公開 API（score_news）
    - news_nlp.py — ニュース文章を LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — ETF とマクロニュースを合成して market_regime に書き込む
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 & DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py — ETL ユーティリティの公開インターフェース
    - quality.py — データ品質チェック一式
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py — JPX カレンダー管理と営業日演算
    - news_collector.py — RSS 収集・前処理・SSRF対策等
    - audit.py — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py — 研究用ユーティリティ公開
    - factor_research.py — ファクター計算（モメンタム／バリュー／ボラティリティ等）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - （その他）strategy/, execution/, monitoring/ — __all__ にあるが実装はこのコードベース断片には含まれていません

---

## 設計上の注意 / トラブルシューティング

- 必須環境変数未設定時は Settings が ValueError を投げます。開発時は .env をプロジェクトルートに置くか環境変数を設定してください。
- DuckDB 保存処理は executemany で空リストを投げると失敗するケース（DuckDB 0.10）を考慮しているため、結果のチェックを行っています。
- OpenAI や J-Quants API 呼び出しはリトライ・バックオフ実装がありますが、APIクォータやネットワーク障害には注意してください。
- ニュース取得は RSS の Content-Length / 解凍後サイズ制限を超える場合にスキップします（DoS対策）。
- calendar / market data が未取得の場合、営業日判定は曜日ベースのフォールバックを行います（完全なカレンダーがある場合は DB を優先）。

---

以上がこのコードベースの README 相当のまとめです。特定のセットアップ手順やサンプルスクリプト（CI / デプロイ / systemd ジョブ等）が必要であれば、用途に合わせた追加ドキュメントを作成します。どの部分を詳しく書きたいか教えてください。