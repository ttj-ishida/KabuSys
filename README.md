# KabuSys — 日本株自動売買プラットフォーム（README）

概要
---
KabuSys は日本株のデータ基盤・リサーチ・AI支援の自動売買プラットフォーム向けコンポーネント群です。  
主に以下を提供します。

- J-Quants API を用いた株価・財務・カレンダーデータの差分ETLパイプライン
- ニュース収集（RSS）と LLM を用いたニュースセンチメント算出
- マーケットレジーム（強気 / 中立 / 弱気）判定（ETF とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用スキーマ初期化ユーティリティ
- 環境変数管理ユーティリティ（.env 自動ロード機能）

機能一覧
---
主な機能（モジュール単位）

- kabusys.config
  - .env／環境変数の自動ロード
  - settings オブジェクトから設定値を取得（JQUANTS_REFRESH_TOKEN 等）
- kabusys.data
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: J-Quants API クライアント（取得 + DuckDB への保存）
  - news_collector: RSS 収集・記事正規化・raw_news 保存ロジック（SSRF対策やサイズ制限あり）
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ作成・DB初期化
  - stats: zscore 正規化ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM（gpt-4o-mini）でセンチメント評価し ai_scores へ保存
  - regime_detector.score_regime: ETF(1321)のMA乖離とマクロニュースを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

セットアップ手順
---
前提
- Python 3.10+
- 必要パッケージ: duckdb, openai, defusedxml（他、標準ライブラリを使用）

基本的なセットアップ例（開発環境）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトを pip パッケージ化している場合は `pip install -e .`）

3. 環境変数 / .env の準備
   - プロジェクトルートに .env を置くと、自動的に読み込まれます（config モジュール）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（主に）環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN=<あなたの J-Quants refresh token>
- KABU_API_PASSWORD=<kabu ステーション API パスワード>  ※ 発注連携がある場合
- SLACK_BOT_TOKEN=<Slack Bot トークン>  ※ モニタリング通知がある場合
- SLACK_CHANNEL_ID=<Slack チャンネルID>
- OPENAI_API_KEY=<OpenAI API キー>  ※ news_nlp / regime_detector 実行時に必要

任意（デフォルトあり）
- KABUSYS_ENV=development|paper_trading|live  (default: development)
- LOG_LEVEL=DEBUG|INFO|...  (default: INFO)
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  (自動 .env ロード無効化)

使い方（簡易例）
---
以下は主要な操作の利用例です。実行は Python スクリプトまたは REPL から行えます。

1) DuckDB 接続を作成して日次 ETL を実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # デフォルトパスは settings.duckdb_path
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを LLM でスコアリング（ai_scores テーブルへ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
# OPENAI_API_KEY が環境にない場合は api_key="sk-..." を渡すことも可能
```

3) マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 返り値は初期化済みの DuckDB 接続
```

5) 環境設定の取得（settings）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
```

注意点
- LLM（OpenAI）を呼ぶ関数（score_news / score_regime）は OpenAI API キーが必要です。api_key 引数か環境変数 OPENAI_API_KEY を利用してください。
- ETL / API 呼び出しは外部ネットワークに依存するため、適切なエラーハンドリングとリトライが組み込まれていますが、本番運用ではレート制限や API 使用料に注意してください。
- DuckDB の executemany に関する制約（古いバージョン等）を配慮した実装がなされています。DuckDB は最新版を推奨します。
- .env の読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ディレクトリ構成（概要）
---
プロジェクトの主要ファイル/ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP スコアリング
    - regime_detector.py               — マーケットレジーム判定
  - data/
    - __init__.py
    - pipeline.py                      — ETL パイプライン本体、run_daily_etl 等
    - jquants_client.py                — J-Quants API クライアント & 保存ロジック
    - news_collector.py                — RSS 収集・前処理・保存
    - quality.py                       — データ品質チェック
    - calendar_management.py           — 市場カレンダー管理、営業日判定
    - etl.py                           — ETLResult の公開（再エクスポート）
    - stats.py                         — zscore_normalize 等の統計ユーティリティ
    - audit.py                         — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算
    - feature_exploration.py           — 将来リターン計算、IC、統計サマリ
  - monitoring/                         — （将来の監視・アラート用コンポーネント）
  - strategy/                           — （戦略レイヤ、サンプル・実装場所）
  - execution/                          — （発注・ブローカー連携層）

（上記はコードベース内の主要モジュールを抜粋した概要です）

開発・運用上のヒント
---
- テスト時には環境自動読み込みを無効に（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）し、必要な値をテストコードで注入してください。
- LLM 呼び出し箇所はリトライとフォールバック（失敗時は中立スコア）を行うよう実装されていますが、APIコスト・レイテンシに注意してください。
- J-Quants API のトークンリフレッシュやレート制限は jquants_client に組み込まれています（内部キャッシュ・RateLimiter）。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に配置されます。デプロイ時は適切に永続化してください。

ライセンス・貢献
---
本リポジトリのライセンスはリポジトリ側で指定してください。バグ報告や機能提案は Issue を通じてお願いします。

---

この README はコードベースの主要機能と利用方法を簡潔にまとめたものです。詳細は各モジュールの docstring（ソースコード内コメント）を参照してください。必要であればサンプルスクリプトや運用手順書の作成を支援します。