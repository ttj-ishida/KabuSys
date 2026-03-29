# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ等を含むモジュール群を提供します。

主な設計方針：
- バックテストでのルックアヘッドバイアスを防ぐ（target_date を明示的に扱う等）
- ETL とデータ品質チェックを分離し、部分失敗でも他処理は継続
- DuckDB を一次データストアとして利用（冪等保存、ON CONFLICT を活用）
- OpenAI / J-Quants 等の外部 API 呼び出しにはリトライ・レート制御等の耐障害設計あり

---

## 機能一覧

- config
  - 環境変数の読み込み（`.env`, `.env.local` 自動ロード。無効化フラグあり）と型安全な設定取得
- data
  - ETL（J-Quants からの株価 / 財務 / カレンダー取得・保存）
  - market calendar 管理（営業日判定、next/prev/trading days）
  - ニュース収集（RSS、SSRF対策、記事正規化）
  - J-Quants クライアント（認証、レート制限、リトライ）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ（signal -> order_request -> execution のトレーサビリティ）
  - ユーティリティ（統計、Zスコア正規化）
- ai
  - ニュースセンチメント（gpt-4o-mini JSON mode を使って銘柄別スコア生成）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを合成）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索・IC 計算・統計サマリ

---

## セットアップ手順

基本的な依存（代表例）：
- Python 3.10+
- duckdb
- openai
- defusedxml

リポジトリルートに pyproject.toml 等がある想定です。開発環境の例：

1. 仮想環境作成・有効化
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\Scripts\activate    # Windows
```

2. 必要パッケージをインストール（プロジェクトの requirements がある場合はそれを利用）
```bash
pip install duckdb openai defusedxml
# 開発中は editable install を推奨
pip install -e .
```

3. 環境変数（.env）を用意
プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須の環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション等の API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID

オプション:
- OPENAI_API_KEY — OpenAI 呼び出し（score_news / regime_detector で指定しない場合は環境変数から取得）
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト `data/monitoring.db`
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`

例（.env）
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的なユースケース）

コード例は Python REPL / スクリプト内で実行してください。DuckDB の接続は `duckdb.connect(<path>)` を利用します。

1) 日次 ETL 実行（株価・財務・カレンダーの差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントスコアを取得して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {count}")
```

3) 市場レジーム（bull/neutral/bear）を算出して market_regime に保存
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査用 DuckDB を初期化（監査テーブル作成）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を利用して order/signals/executions を記録できます
```

5) カレンダー更新ジョブ（J-Quants から市場カレンダー差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print(f"保存件数: {saved}")
```

注意:
- OpenAI と J-Quants の API 呼び出しは API キー（環境変数か引数）を必要とします。
- 多くの関数は target_date を明示的に受け取ることでルックアヘッドを防止しています。バックテスト等で利用する際は target_date を適切に指定してください。

---

## ディレクトリ構成

主要なファイル・モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数/設定管理
    - ai/
      - __init__.py
      - news_nlp.py             — ニュースセンチメント（OpenAI）
      - regime_detector.py      — 市場レジーム判定
    - data/
      - __init__.py
      - pipeline.py             — ETL パイプライン & run_daily_etl
      - jquants_client.py       — J-Quants API クライアント + 保存関数
      - news_collector.py       — RSS ニュース収集
      - calendar_management.py  — 市場カレンダー判定・更新ジョブ
      - quality.py              — データ品質チェック
      - audit.py                — 監査ログ初期化・DDL
      - etl.py                  — ETL 結果型の再エクスポート
      - stats.py                — 統計ユーティリティ（zscore 正規化等）
    - research/
      - __init__.py
      - factor_research.py      — モメンタム/バリュー/ボラティリティ計算
      - feature_exploration.py  — 将来リターン・IC・統計サマリ
    - research/*.py
    - その他モジュール

簡易ツリー（例）
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ pipeline.py
│  ├─ jquants_client.py
│  ├─ news_collector.py
│  ├─ calendar_management.py
│  ├─ quality.py
│  └─ audit.py
└─ research/
   ├─ factor_research.py
   └─ feature_exploration.py
```

---

## 注意事項 / 運用上のポイント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml の存在で判定）に依存します。CI やテストで自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは JSON Mode を利用して厳密な JSON を期待する設計です。応答パースで失敗した場合はフェイルセーフでスコア0.0やスキップする挙動があります（ログ参照）。
- J-Quants API にはレート制限とトークン更新が必要です。`JQUANTS_REFRESH_TOKEN` を用意してください。
- DuckDB のスキーマやテーブルはプロジェクト側で期待する構造があります。ETL を初めて実行する前に必要なスキーマ初期化処理を行ってください（別途 schema 初期化関数や SQL がある想定）。
- 本ライブラリは「データ処理 / 研究 / 戦略の基礎コンポーネント」を提供します。実際の発注・運用ロジック（ブローカ接続・ポジション管理など）は別途実装・統合してください。

---

不明点や README に追加してほしい具体的な実行例（例：Docker 化、CI 用スクリプト、schema 初期化手順など）があればお知らせください。追加でサンプル .env.example を作成することも可能です。