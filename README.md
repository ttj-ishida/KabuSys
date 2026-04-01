# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants や各種 RSS、OpenAI（LLM）を利用してデータ収集・品質管理・AI評価・リサーチ・監査ログを提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ」「DuckDB を中心としたローカル分析」です。

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価（OHLCV）・財務・市場カレンダーを差分取得・保存（jquants_client）
  - 日次 ETL パイプライン（run_daily_etl）による一括取得・品質チェック（pipeline）
- データ品質管理
  - 欠損・スパイク・重複・日付不整合などのチェック（quality）
- ニュース収集 / 前処理
  - RSS フィード収集（SSRF 対策・トラッキング除去）と raw_news への冪等保存（news_collector）
- AI 評価
  - ニュースを銘柄単位で LLM に投げてセンチメントを算出（news_nlp）
  - マクロ + 指数移動平均を組合せた市場レジーム判定（regime_detector）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算・IC / 統計サマリー（research.feature_exploration）
  - Zスコア正規化などの共通統計ユーティリティ（data.stats）
- 監査（トレーサビリティ）
  - シグナル → 発注 → 約定まで追跡する監査テーブル初期化・ユーティリティ（data.audit）
- カレンダー管理
  - JPX カレンダーの取得・営業日判定・前後の営業日取得（data.calendar_management）

---

## 動作要件

- Python 3.10 以上（型注釈に | 演算子を使用）
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS）

requirements.txt がある場合はそちらを利用してください。ない場合は最低限以下をインストールしてください:

pip install duckdb openai defusedxml

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または pip install duckdb openai defusedxml

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` から自動ロードされます（デフォルト）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 実行時に必須）
その他（デフォルトあり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

settings オブジェクトでアクセス可能:
from kabusys.config import settings
settings.jquants_refresh_token
settings.duckdb_path
...

---

## 使い方（サンプル）

以下は Python から直接呼び出す代表的な利用例です。

- DuckDB 接続の作成（ファイル DB を使用）
from pathlib import Path
import duckdb
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))

- 日次 ETL を実行する
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースを使って銘柄センチメントをスコアリングする
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数に設定するか、api_key 引数で渡す
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {num_written}")

- 市場レジーム判定（ETF 1321 の MA200 + マクロニュース）
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれます

- 監査 DB を初期化する（監査専用 DuckDB）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算例
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# リスト形式で (date, code, mom_1m, mom_3m, mom_6m, ma200_dev) を返す

注意点:
- 各関数はルックアヘッドバイアスを避ける設計（内部で datetime.today() を参照しない、target_date を明示）。
- OpenAI 呼び出しは API 失敗時にフォールバック（0.0）やリトライを行う設計ですが、API キーは必須です。
- J-Quants API はレート制限を守るよう内部で制御しています。

---

## 実装上のポイント / 動作挙動

- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を探索）から `.env` → `.env.local` を読み込みます。
  - OS 環境変数 > .env.local > .env の優先順位です。
- エラー/フォールバック方針
  - ETL や API 呼び出しは個別に例外を捕捉し、可能な限り他パイプラインは継続します（fail-safe）。
  - OpenAI 呼び出しは指定回数リトライ後にスコアを 0.0 にフォールバックする実装があります。
- 冪等性
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を使用して冪等的に保存します。
  - news_collector は URL 正規化＋ハッシュで記事 ID を生成し重複挿入を防ぎます。
- セキュリティ
  - news_collector は SSRF 対策（スキーム検証、プライベート IP ブロック、リダイレクト検査）や XML 攻撃対策（defusedxml）を実装しています。
  - API キー・トークンは .env や環境変数で管理し、決してコードに埋め込まないでください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                   — ニュースを LLM でスコアリング
  - regime_detector.py            — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント + 保存ロジック
  - pipeline.py                   — ETL パイプライン実装（run_daily_etl 等）
  - etl.py                        — ETLResult のエクスポート
  - calendar_management.py        — 市場カレンダー管理
  - news_collector.py             — RSS 収集・前処理
  - quality.py                    — データ品質チェック
  - stats.py                      — 共通統計ユーティリティ
  - audit.py                      — 監査ログテーブル初期化
- research/
  - __init__.py
  - factor_research.py            — モメンタム/ボラティリティ/バリュー等
  - feature_exploration.py        — 将来リターン・IC・統計サマリー
- research/...（他ユーティリティ）

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取って処理します。

---

## 開発 / テストに関するヒント

- テスト実行時に .env の自動ロードを抑制するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants API 呼び出し部分は内部で呼び出し関数を分離しており、ユニットテストではモックしやすい設計です（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB はインメモリ接続 ":memory:" でテストできます。

---

## 補足 / 注意事項

- 本プロジェクトは証券取引に関わる機能を含むため、本番運用前に十分な検証とリスク管理（注文の冪等性・オフラインでのバックテスト・資金管理）を必ず行ってください。
- KABUSYS_ENV を `live` にすると本番向けの挙動（例: 発注周りの制約等）を有効にする想定です。paper_trading / development を用途に応じて使い分けてください。

---

ご不明点や README に追記してほしい実例（.env.example の推奨内容やより詳しい API 使用例など）があれば教えてください。README をプロジェクト実態に合わせて拡張します。