# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ（KabuSys）

短い概要：
- J-Quants / kabuステーション 等のデータソースからデータを収集・ETL し、DuckDB 上での解析・ファクター計算・AI ベースのニュースセンチメントや市場レジーム判定、監査ログの管理までをカバーする内部ライブラリ群です。
- バックテスト／リサーチ／運用（paper/live）で共通に使えるユーティリティを提供します。

---

## 主な機能 (Features)

- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーなどを差分取得して DuckDB に保存（冪等保存）
  - 差分更新・バックフィル・ページネーション対応・レート制御・トークン自動リフレッシュ
- データ品質チェック
  - 欠損値、スパイク（急騰・急落）、重複、日付不整合（未来日付／非営業日のデータ）検出
- ニュース収集
  - RSS フィードから記事取得、テキスト前処理、SSRF 対策、トラッキングパラメータ除去、raw_news への冪等登録
- AI（LLM）による NLP / レジーム判定
  - ニュースの銘柄別センチメント（gpt-4o-mini + JSON Mode） → ai_scores へ保存
  - マクロニュースとETF（1321）のMA乖離を合わせて日次の市場レジーム（bull/neutral/bear）を判定
  - API リトライ・フォールバック設計（LLM失敗時は中立スコア等で継続）
- 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal → order_request → executions をトレースする監査スキーマと初期化ユーティリティ

---

## 必要条件 / 前提

- Python 3.10 以上（ソースで `|` 型注釈や新しい構文を使用）
- 必要な Python パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAIなど）
- 環境変数／.env に API トークン等を設定

（実際に使用する際はプロジェクトの requirements.txt / pyproject.toml を確認してください）

---

## 環境変数 / .env

主に以下の環境変数を参照します（必須は明示）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン（ETL, jquants_client.get_id_token で使用）
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意) — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite (監視等) のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI 呼び出しで使用（score_news / score_regime に渡す api_key と併用可能）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）で `.env` と `.env.local` を自動的に読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` をオーバーライドします。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 `.env`（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=Cxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （実際のプロジェクトでは requirements.txt / pyproject.toml を用意している想定です:
   pip install -r requirements.txt または pip install -e .）

4. .env を作成（必要な環境変数を設定）
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（前節参照）。

5. 初期 DB ディレクトリを作成（必要なら）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は代表的なユーティリティの使い方例です。実行前に環境変数（OpenAI / J-Quants トークン等）をセットしてください。

- DuckDB 接続と日次 ETL 実行
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）をスコア化して ai_scores に保存
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scored:", count)
```

- 市場レジーム判定（ETF 1321 の MA とマクロ記事の合成）
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DuckDB 初期化（監査専用 DB を作る）
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- 設定（Settings）参照例
```
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点：
- score_news / score_regime は OpenAI API を呼び出します。api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を準備してください。
- ルックアヘッドバイアス回避のため、これらの関数は内部で date.today() を直接参照しない設計です。バックテスト用途でも target_date を明示してください。

---

## ディレクトリ構成

リポジトリ内の主要なファイル群（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（AI）
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL インターフェース再エクスポート
    - calendar_management.py         — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py              — RSS ニュース収集
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログスキーマ初期化
    - (その他: jquants_client の補助関数等)
  - research/
    - __init__.py
    - factor_research.py             — Momentum/Value/Volatility 等
    - feature_exploration.py         — forward returns / IC / summary / rank
  - ai/ (上記)
  - research/ (上記)
  - monitoring, strategy, execution  — パッケージ公開名に含まれるが本 README のサンプルコードには含めていません
- pyproject.toml (プロジェクトルートに存在する想定)
- .env, .env.local (実行環境に置く)

（上記はソース内のファイルヘッダ・モジュール説明を元にした要約です）

---

## 開発・テスト時の注意事項

- 自動 .env ロードを無効にする:
  - テストで環境汚染を避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants の外部呼び出しは、ユニットテストではモック推奨（モジュールでは _call_openai_api 等が差し替え可能に設計されています）。
- DuckDB に対する executemany の空パラメータは一部バージョンでエラーとなるため、コード中で空チェックが行われています。テストデータ作成時に注意してください。

---

## トラブルシューティング

- .env が読み込まれない / 値が反映されない
  - パッケージはプロジェクトルート（.git または pyproject.toml を基準）を自動検出して `.env` を読み込みます。テストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化した上で必要な環境変数を明示的に設定してください。
- OpenAI の呼び出しで 401 が出る
  - OPENAI_API_KEY を確認、あるいは API キーを明示的に関数に渡してください。
- J-Quants の API リクエストに 401 が出る
  - JQUANTS_REFRESH_TOKEN を設定し、jquants_client.get_id_token() が正しく動くか確認してください。

---

必要であれば README に「インストール用の requirements.txt 例」「.env.example」「より細かな API 使用例（ETL の個別実行、quality チェックの実行例）」などを追記できます。どの部分を詳細化したいか教えてください。