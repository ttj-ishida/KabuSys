# KabuSys

日本株向けの自動売買／データ基盤ライブラリセットです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、マーケットレジーム判定、リサーチ（ファクター計算）や監査ログ（order→execution トレーサビリティ）など、量的投資・自動売買プラットフォーム構築に必要な共通機能を提供します。

バージョン: 0.1.0

---

## 主な機能一覧

- 環境設定管理
  - `.env` 自動読み込み（プロジェクトルートの検出、上書きルール、無効化フラグあり）
  - 必須環境変数のラッパー（`kabusys.config.settings`）

- データプラットフォーム（Data）
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ対応）
  - ETL パイプライン（株価 / 財務 / カレンダーの差分取得・保存）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS、SSRF 防止・トラッキングパラメータ除去・正規化）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）

- AI（OpenAI 経由）
  - ニュース NLP（銘柄ごとのセンチメントを LLM により算出して `ai_scores` に書き込み）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュース LLM の重み合成で `market_regime` に書き込み）
  - 安全な API 呼び出し、リトライ、レスポンス検証を実装

- Research（リサーチユーティリティ）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン計算、IC、統計サマリー、ランク付け）
  - Z-score 正規化ユーティリティ

- 汎用ユーティリティ
  - DuckDB に向けた各種保存処理（冪等処理）
  - 日付・時間ウィンドウ計算
  - 小規模な統計処理（外部依存を最小化）

---

## 前提・依存

- Python 3.10 以上（型注釈の union 表記 `X | Y` を使用）
- 主要依存パッケージ（一例）:
  - duckdb
  - openai
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
# またはプロジェクト配送方法に応じて:
# pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API のパスワード
- SLACK_BOT_TOKEN        — Slack 通知（Bot）トークン
- SLACK_CHANNEL_ID       — 通知先 Slack チャンネルID

AI 関連:
- OPENAI_API_KEY         — OpenAI API キー（news_nlp / regime_detector で利用可能）

オプション（デフォルトあり）:
- KABUSYS_ENV            — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABUS_API_BASE_URL     — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — SQLite（monitoring）パス（デフォルト: data/monitoring.db）

自動 .env 読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動で読み込みます。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン／配置
2. Python 環境を作成・有効化（venv / pyenv 等）
3. 依存パッケージをインストール
   ```bash
   python -m pip install -r requirements.txt
   # 無ければ手動で: pip install duckdb openai defusedxml
   ```
4. .env を作成（`.env.example` をプロジェクトに用意している場合は参照）
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. 初期データベース（監査ログ等）を初期化する（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # または接続済み DuckDB を渡して init_audit_schema(conn)
   ```

---

## 使い方（主要な例）

以下はライブラリを直接 Python から呼ぶ簡単な例です。用途に応じてスクリプトやジョブに組み込んでください。

- DuckDB 接続の作成（設定経由のパス使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（J-Quants からの差分取得・保存・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は duckdb 接続
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（ai_scores テーブルへ書き込む）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数に設定済みか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定（market_regime テーブルへ書き込む）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

res = score_regime(conn, target_date=date(2026, 3, 20))
print("done:", res)
```

- ファクター計算（研究用）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

- 監査ログスキーマ初期化（既存接続へ追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

---

## テスト・デバッグのヒント

- OpenAI 呼び出し等の外部 API はユニットテストでモックされるよう設計されています（内部 `_call_openai_api` を patch する等）。
- 自動 .env ロードをテストで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB をインメモリで使う場合は `duckdb.connect(":memory:")` を利用できます（テスト用）。

---

## ディレクトリ構成（主要ファイル）

以下は package の主要な構成です（`src/kabusys` 以下）:

- kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP スコアリング（ai_scores）
    - regime_detector.py               — 市場レジーム判定（market_regime）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント + 保存処理
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETLResult の re-export
    - calendar_management.py           — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py                — RSS ニュース収集（SSRF 対策等）
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査ログ（テーブル定義／初期化）
  - research/
    - __init__.py
    - factor_research.py               — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py           — 将来リターン、IC、サマリー等
  - (他に strategy / execution / monitoring 等のモジュール名が __all__ に記載されていますが、上のサブパッケージが中心実装です)

---

## 設計上のポイント（簡潔に）

- Look-ahead bias を避けるため、日付計算や DB クエリは target_date を明示的に与える設計。
- 外部 API 呼び出しはリトライ・バックオフ・エラーハンドリングを実装（フェイルセーフでスコアを 0 に落とす等）。
- DuckDB を用いた冪等保存（ON CONFLICT）・トランザクションにより一貫性を担保。
- セキュリティ考慮: RSS の SSRF 防止、XML の defusedxml 利用、URL 正規化による重複排除等。

---

何か特定の機能（例: ETL の詳細設定、OpenAI のプロンプト調整、kabu ステーション発注連携など）について詳しい README セクションを追加したい場合は、用途や想定ワークフローを教えてください。README をその用途向けに拡張します。