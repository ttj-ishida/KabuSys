# KabuSys

日本株向けのデータパイプライン・リサーチ・監査・AI支援を備えた自動売買／研究基盤ライブラリです。  
DuckDB をデータストアとして使用し、J-Quants API / RSS / OpenAI（LLM）などと連携するモジュール群を提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で date.today() を直接参照しない）
- DuckDB を中心とした冪等的な ETL / 保存処理
- API 呼び出しはレート制御・リトライ・フェイルセーフを備える
- テスト容易性（API キー注入や内部関数のモック化を想定）

---

## 機能一覧
- データ収集 / ETL
  - J-Quants から株価（日足）、財務データ、JPX カレンダーを差分取得・保存（jquants_client, data.pipeline）
  - RSS からニュース収集（news_collector）
  - market_calendar の夜間更新ジョブ（calendar_update_job）
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク、日付不整合などの検出
- 研究・ファクター計算（research）
  - Momentum / Value / Volatility 等の計算（factor_research）
  - 将来リターン計算、IC（情報係数）、統計サマリー（feature_exploration）
  - Z-score 正規化ユーティリティ（data.stats）
- AI ベースの NLP スコアリング（ai）
  - ニュースの銘柄別センチメントスコアリング（news_nlp.score_news）
  - マクロニュースと ETF MA 乖離を組み合わせた市場レジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を JSON Mode で使用、リトライとフェイルセーフ実装
- 監査ログ（data.audit）
  - signal → order_request → execution のトレーサビリティを確保する監査スキーマ初期化・専用DB初期化

---

## 必要条件 / 推奨環境
- Python 3.10 以上（型注釈に | を使用しているため）
- 主な依存ライブラリ（プロジェクトの setup にて管理する想定）
  - duckdb
  - openai（OpenAI Python SDK）
  - defusedxml
  - その他標準ライブラリ（urllib 等）
- J-Quants API アクセス用のリフレッシュトークンや OpenAI API キーなど外部サービスの資格情報

---

## セットアップ手順（開発環境）
1. リポジトリをチェックアウト
2. 仮想環境の作成・有効化（例: python -m venv .venv && source .venv/bin/activate）
3. 依存インストール
   - pip install -e .   （あるいは requirements.txt がある場合は pip install -r requirements.txt）
4. 環境変数設定
   - プロジェクトルートに `.env`（と任意で `.env.local`）を作成します。
   - 自動で .env を読み込む仕組みが組み込まれています（CWD ではなくパッケージ位置を基準に探索）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API 利用時のパスワード（必須）

推奨 / 任意（デフォルトあり）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用（空文字可）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE : Paper Trading の fill 模式（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- KABUSYS_ENV : 環境 (development|paper_trading|live)、デフォルト development
- LOG_LEVEL : ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）

例 .env（例示）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## 使い方（主要 API の例）
以下は Python REPL / スクリプト内での利用例です。DuckDB 接続（duckdb.connect）を渡すことで各処理を実行します。

1) 日次 ETL 実行（run_daily_etl）
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースセンチメントのスコアリング（score_news）
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か api_key 引数で指定
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")

3) 市場レジーム判定（score_regime）
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))

4) 監査ログ DB 初期化（専用 DB を作る）
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn は初期化済みの DuckDB 接続

5) 研究用ファクター計算（例: calc_momentum）
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# レコードは [{ "date": ..., "code": "XXXX", "mom_1m": ..., ... }, ...]

注意点:
- OpenAI を使う関数は api_key を引数で注入可能（テスト容易性）。
- LLM 呼び出しはリトライやエラーで安全にフォールバックします（失敗時は 0 や空で継続）。
- ETL や保存処理は冪等性を考慮しており、再実行が安全になるよう設計されています。

---

## 開発・運用上の注意
- DuckDB のバージョン差異（executemany の空リスト受け入れなど）を考慮した実装が各所にあります。ライブラリの互換性に注意してください。
- J-Quants API のレート制限（120 req/min）に従うためクライアント側で間引き/スロットリングを行っています。大量取得時の設定や運用は考慮してください。
- ニュース収集では SSRF 対策や XML パースの安全（defusedxml）を実装しています。外部フィードの追加時にもこの制約を尊重してください。
- 本ライブラリはバックテスト・実運用でのルックアヘッドバイアスを避ける設計を重視しています。ターゲット日より前のデータのみを参照することを徹底しています。

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数 / 設定の集中管理（自動 .env ロード機能含む）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの銘柄別センチメント計算（score_news）
  - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存）
  - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl, ...）
  - calendar_management.py — JPX カレンダー管理（is_trading_day 等）
  - news_collector.py — RSS フィード収集
  - audit.py — 監査ログスキーマ / DB 初期化
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - etl.py — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等
  - feature_exploration.py — forward returns, IC, factor_summary, rank
  - その他リサーチ補助モジュール
- ai, monitoring, strategy, execution など（パッケージ初期化で __all__ に含めているモジュール群）

（README 用に抜粋しています。実際のコードベースは上記以外にも補助モジュールが含まれます）

---

## よくある質問 / トラブルシューティング
- .env が自動で読み込まれない
  - パッケージは __file__ を基点にプロジェクトルート（.git または pyproject.toml）を探索して .env を読み込みます。テストなどで自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI キーが見つからない旨のエラー
  - score_news / score_regime は api_key 引数または環境変数 `OPENAI_API_KEY` を期待します。いずれも未設定だと ValueError を投げます。
- J-Quants の 401 エラー
  - jquants_client は 401 受信時に自動でリフレッシュトークンから id_token を取得してリトライするロジックがあります。設定が正しいか（JQUANTS_REFRESH_TOKEN）を確認してください。

---

必要であれば README 内に .env.example のテンプレートやより詳細な使用例（ETL スケジューリング、Paper Trading の設定、Line 通知のサンプルなど）を追加できます。追加希望の項目を教えてください。