# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）・ニュース収集・ニュースNLP（OpenAI）・市場レジーム判定・ファクター計算・監査ログなど、バックテスト／運用で必要な基盤機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価（日次OHLCV）・財務データ・市場カレンダーを差分取得・保存（DuckDB）
  - 差分取得・バックフィル・ページネーション対応・レートリミット / リトライ実装
- データ品質チェック
  - 欠損値、スパイク（急騰/急落）、主キー重複、日付不整合などを検出
- ニュース収集
  - RSS フィード取得、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存
- ニュースNLP（OpenAI）
  - gpt-4o-mini を用いた銘柄別ニュースセンチメント（ai_scores へ保存）
  - バッチ処理、JSON Mode、リトライ / フォールバック実装
- 市場レジーム判定
  - ETF(1321) の200日移動平均乖離とマクロニュースLLMセンチメントを組合せて日次でレジーム判定（bull / neutral / bear）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルによる発注〜約定の監査ログ、冪等性・UTC タイムスタンプ管理

---

## 必要な環境変数（概略）

必須（Settings が必ず参照するもの）
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI を使う場合に必要（score_news / score_regime など）

任意（デフォルト値あり）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動読み込みを無効化
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

.env ファイルの自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動読み込みします。
- テスト等で自動ロードを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を用意（推奨: 3.10+）
2. リポジトリをチェックアウトし、パッケージをインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。DuckDB / openai / defusedxml 等の依存が必要です）
3. 必要な環境変数を `.env` に設定（例は下に記載）
4. DuckDB データベースのディレクトリを作る（必要なら）
   ```
   mkdir -p data
   ```

例: .env（最小）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下はインタラクティブやジョブスクリプトでよく使う操作例です。

事前準備:
- DuckDB を使うので `duckdb` パッケージが必要です。
- OpenAI を使う場合は `OPENAI_API_KEY` を設定してください。

1) DuckDB 接続を作成して ETL を実行（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクトを返します
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

2) ニュースセンチメントをスコアリングして ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数で設定されている場合、api_key を省略できます
num_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("書き込み銘柄数:", num_written)
```

3) 市場レジームを判定して market_regime テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

4) 監査ログ DB を初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

5) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# Zスコア正規化の例
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## よくある運用注意点

- Look-ahead バイアス対策が各所に組み込まれています（target_date 未満のデータのみ参照、datetime.today() を直接参照しない等）。バックテスト等で使用する場合は target_date を明示的に与えてください。
- OpenAI や J-Quants API の呼び出しはリトライ・フォールバックを実装していますが、APIキーやレートの設定は適切に管理してください。
- .env 自動読み込みはプロジェクトルートを .git / pyproject.toml から検出します。CI やテストで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、モジュール側で対策が入っていますが、DB バージョンに注意してください。

---

## ディレクトリ構成（主要ファイル）

（パッケージは `src/kabusys` 配下）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM センチメントスコアリング（score_news）
    - regime_detector.py — マクロ + MA200 による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー・営業日判定・カレンダー更新ジョブ
    - etl.py — ETL インターフェース（ETLResult のエクスポート）
    - pipeline.py — 日次 ETL パイプライン（run_daily_etl / run_*_etl）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — 品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
    - jquants_client.py — J-Quants API クライアント（fetch / save 実装、レート制御、リトライ）
    - news_collector.py — RSS 収集・前処理・SSRF 対策
    - pipeline.py (ETL パイプラインの実装)
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - (その他: strategy/ execution/ monitoring 等のサブパッケージは package の __all__ に含まれていますが、ここに示された主要モジュールがコア機能を構成します)

---

## 開発・貢献

- コードは単体テスト可能なようにモック可能箇所（API 呼び出しやネットワーク I/O）を分離しています。テスト時はモジュールのプライベート関数を patch して外部依存を差し替えてください。
- PR の際は、ユニットテストと簡単な統合テストを追加してください。ETL 周りは少量のダミーデータで回せるテストがあると助かります。

---

これで README の概要は終わりです。特定の使い方（例: ETL のスケジューリング、監査ログの運用、strategy 実装例）を追記したい場合は、用途に合わせた章を追加しますので教えてください。