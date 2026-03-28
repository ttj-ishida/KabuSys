# KabuSys — 日本株自動売買基盤 (README)

概要
----
KabuSys は日本株向けに設計されたデータ基盤・リサーチ・AI 支援・監査ログを含む自動売買システムのコアライブラリです。J-Quants からのデータ取得、DuckDB を用いた ETL、ニュースの NLP スコアリング、OpenAI を用いたマクロセンチメント評価、ファクター計算、監査ログ（注文→約定のトレーサビリティ）などの機能を提供します。

主な設計方針
- ルックアヘッドバイアスを避けるため日付操作は明示的に行う（date.today() を内部で使わない関数設計）
- ETL / 保存は冪等（ON CONFLICT / INSERT … DO UPDATE）で安全に実行
- 外部 API 呼び出しはリトライ・レートリミット対応、失敗はフェイルセーフ（可能な範囲で継続）
- DuckDB をデータストアとして利用し、軽量にローカル保存可能

機能一覧
--------
- データ取得 / ETL
  - J-Quants からの日足株価、財務データ、マーケットカレンダー取得（jquants_client）
  - 差分 ETL と品質チェック（data.pipeline, data.quality）
  - ニュース RSS 収集と保存（data.news_collector）
  - 市場カレンダー管理（data.calendar_management）
- AI / NLP
  - ニュースを銘柄別に集約して OpenAI (gpt-4o-mini) でセンチメントスコアを生成（ai.news_nlp.score_news）
  - ETF とマクロニュースを組み合わせた市場レジーム判定（ai.regime_detector.score_regime）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（情報係数）、統計サマリー（research.feature_exploration）
  - Z-score 正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ / トレーサビリティ
  - signal_events / order_requests / executions の監査スキーマ初期化・DB作成（data.audit）
  - 監査 DB 初期化ユーティリティ（init_audit_db）

前提と依存
-----------
- Python 3.10+
- 主な Python パッケージ（プロジェクトに requirements.txt がない場合は手動でインストール）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS）

推奨インストール例
-----------------
例: 仮想環境作成・依存インストール（プロジェクトルートで実行）

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 任意で開発用ツールや linters を追加
```

環境変数（.env）
----------------
自動で .env / .env.local をプロジェクトルートから読み込む仕組みがあります。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（必須／任意）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- OPENAI_API_KEY (任意) — OpenAI 呼び出しで使われる API キー（ai モジュールが参照）
- DUCKDB_PATH (任意) — デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

（例 .env の断片）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

セットアップ手順（簡易）
-----------------------
1. リポジトリをクローン
2. 仮想環境を作成して依存をインストール（上記参照）
3. .env を作成して必要な環境変数を設定
4. DuckDB データベースファイルのディレクトリを作成（例: data/）
5. 必要に応じて監査 DB 初期化（下記参照）

使い方（コード例）
-----------------

- DuckDB 接続を作る（ファイル DB / メモリ）
```python
import duckdb
from kabusys.config import settings

# ファイル DB を使う場合
conn = duckdb.connect(str(settings.duckdb_path))

# メモリ DB を使う場合
# conn = duckdb.connect(":memory:")
```

- 日次 ETL 実行（データ取得・保存・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定して実行（省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（前日 15:00 JST ～ 当日 08:30 JST のウィンドウ）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーを引数で渡すか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
print(f"scored {count} symbols")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
```

- 監査 DB 初期化（監査専用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.db")
# audit_conn を使って監査テーブルにアクセス可能
```

- J-Quants クライアントの直接利用（デバッグや開発時）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

# トークンは settings.jquants_refresh_token によって解決される
quotes = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,19))
```

ディレクトリ構成（主要ファイル）
------------------------------
プロジェクトの主要なソース構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                  # 環境変数と設定管理
  - ai/
    - __init__.py
    - news_nlp.py              # ニュース NLP スコアリング
    - regime_detector.py       # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント & DuckDB 保存
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - quality.py               # データ品質チェック
    - news_collector.py        # RSS ニュース収集
    - calendar_management.py   # 市場カレンダー管理
    - stats.py                 # 統計ユーティリティ（zscore_normalize）
    - audit.py                 # 監査ログスキーマ定義 / 初期化
    - etl.py                   # ETL 用の公開インターフェース（ETLResult）
  - research/
    - __init__.py
    - factor_research.py       # Momentum / Value / Volatility ファクター
    - feature_exploration.py   # 将来リターン計算、IC、統計サマリ
  - research/* (他モジュール)

運用上の注意
-----------
- 秘密情報（API トークン）は必ず安全に管理してください（.env を Git 管理しない等）。
- OpenAI / J-Quants の API 利用に伴う課金やレート制限に注意してください。
- 本ライブラリは実取引機能（発注/約定）を含む設計要素があります。live 環境での使用は十分な検証と安全対策（リスク管理、監査、権限管理）を行ってください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml の存在する親ディレクトリ）を基準に探索します。テスト環境などで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

貢献 / 開発
-----------
- 開発時は仮想環境を利用し、依存を明示的に追加してください
- 単体テスト用に OpenAI / ネットワーク呼び出しはモック化してテストを書くことを推奨します（コード内でも mock 用に差し替え可能な実装あり）
- DuckDB をローカルに用いるため、テスト用に :memory: 接続を利用できます

ライセンス
---------
（このリポジトリにライセンスファイルがある場合はそちらを参照してください。README に明記がない場合はリポジトリ所有者に確認してください。）

お問い合わせ
-------------
- 実装に関する質問や不具合はリポジトリの Issue を作成してください。
- 本ドキュメントに不足があれば README を更新する PR を歓迎します。

以上。必要があれば「具体的な .env.example のテンプレート作成」や「ETL 実行の詳細なデバッグ手順」の追記を行います。