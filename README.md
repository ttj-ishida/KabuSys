# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

主な目的:
- J-Quants からのデータ取得と DuckDB への永続化（冪等保存）
- RSS ニュース収集と LLM を使った銘柄センチメント算出
- 市場レジーム判定（テクニカル + マクロニュース）
- 研究用ファクター計算・特徴量解析
- 発注フロー追跡のための監査ログスキーマ

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出、`.env.local` の優先度が高い）
  - 必須設定をラップする Settings クラス（`kabusys.config.settings`）

- データ（kabusys.data）
  - J-Quants クライアント（取得・保存・リトライ・レートリミット）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - マーケットカレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS → raw_news、SSRF 対策、トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ（signal_events / order_requests / executions）の初期化ユーティリティ

- AI / NLP（kabusys.ai）
  - ニュースから銘柄別センチメント算出（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を JSON Mode で呼び出す実装（リトライ・フェイルセーフ設計）

- 研究（kabusys.research）
  - Momentum / Volatility / Value のファクター算出
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化

- 汎用ユーティリティ
  - 統計ユーティリティ（zscore_normalize 等）
  - DuckDB 用の idempotent 保存ロジック

---

## 動作環境・依存関係（想定）

- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib 等）

インストール例:
```
python -m pip install duckdb openai defusedxml
# または
pip install -e .
```
（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

---

## 環境変数（必須・主要）

自動読み込み: パッケージ読み込み時にプロジェクトルート（`.git` または `pyproject.toml`）を探し `.env` と `.env.local` を読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（Settings で _require_ されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注周りで使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — environment: "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト `data/monitoring.db`）
- OPENAI_API_KEY — OpenAI を使う機能（score_news / score_regime）で参照

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン / プロジェクトディレクトリへ移動
2. Python 仮想環境作成 & 有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
   またはプロジェクト提供のパッケージ設定を利用:
   ```
   pip install -e .
   ```
4. 環境変数を準備（`.env` / `.env.local` をプロジェクトルートに置く）
5. DuckDB ファイルの配置先ディレクトリを作成（例: data/）
   ```
   mkdir -p data
   ```
6. （必要に応じて）監査用 DB 初期化（例は下記）

---

## 使い方（代表的な例）

※ すべて Python API 経由で呼び出します。CLI は付属していないため自分でスクリプトを作成してください。

- DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントをスコアリングする（OpenAI API キー必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

- 市場レジームを評価して保存する（OpenAI API キー必要）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- 研究用ファクターを計算する
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
```

---

## 注意点・設計上の留意事項

- Look-ahead バイアス対策:
  - module 内で datetime.today() / date.today() を直接参照しない関数設計になっている（target_date 引数を必ず受け取る）。
  - J-Quants データ取得時は fetched_at を UTC で記録する等、「いつそのデータが利用可能になったか」を明確化。

- OpenAI 呼び出し:
  - gpt-4o-mini を想定し JSON Mode で結果を取得（レスポンスのバリデーション処理あり）。
  - API エラー時は安全側にフォールバック（スコア=0 等）して処理を継続するフェイルセーフ設計。

- .env 自動読み込み:
  - プロジェクトルートを __file__ の親から探索して判定するため、カレントワーキングディレクトリに依存しません。
  - テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして自動ロードを無効化可能。

- DuckDB executemany の制約など実運用での互換性を考慮した実装（空リストバインドの回避など）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                            — 環境変数 / Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                         — ニュース NLP / score_news
    - regime_detector.py                  — マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                   — J-Quants API クライアント（取得・保存）
    - pipeline.py                         — ETL パイプライン（run_daily_etl 等）
    - etl.py                              — ETL ユーティリティ公開（ETLResult）
    - calendar_management.py              — 市場カレンダー管理
    - news_collector.py                   — RSS ニュース収集
    - quality.py                          — データ品質チェック
    - stats.py                            — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                            — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py                  — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py              — 将来リターン / IC / rank / factor_summary
  - research/...                           — 研究用ユーティリティ群
  - その他（strategy / execution / monitoring 等のエントリポイントは __all__ に準備）

---

## テスト・モックについて

- OpenAI やネットワーク呼び出し周りは内部で関数分離されているため、ユニットテストでは該当関数（例: kabusys.ai.news_nlp._call_openai_api）を patch / mock して挙動を検証できます。
- RSS フェッチは _urlopen をモック可能（SSRF 保護を含む）。

---

## 最後に

この README はコードベースからの抜粋に基づく概要ドキュメントです。より詳細な設計意図（DataPlatform.md / StrategyModel.md 等）が別途ある前提で作られています。運用前に必須環境変数・DB スキーマ・監査ポリシーを確認してください。

不明点があれば具体的なユースケース（ETL 実行、AI スコアリング実行、監査 DB 初期化 等）を教えてください。設定例やスクリプトサンプルを補足で提供します。