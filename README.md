# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由の株価/財務/カレンダー取得）、ニュース収集・NLP（OpenAI 連携）による銘柄センチメント評価、市場レジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

## 主な特徴

- データ取得・ETL
  - J-Quants API から日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分取得／バックフィル／冪等保存（ON CONFLICT）を想定した設計
  - 品質チェック（欠損、スパイク、重複、日付不整合）を実行可能

- ニュース収集・NLP
  - RSS 収集（SSRF 対策、URL 正規化、サイズ上限、XML サニタイズ）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント評価（ai_scores への保存）
  - 市場マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントの合成）

- 研究（Research）モジュール
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- 監査ログ（Audit）
  - signal → order_request → execution までのトレーサビリティを担保する監査テーブル群
  - DuckDB ベースで監査DBの初期化ユーティリティを提供

- 設定管理
  - .env から自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）
  - 必要環境変数の取得ユーティリティ（settings オブジェクト）

---

## 必要環境（推奨）

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml

（パッケージはプロジェクトの requirements.txt / pyproject.toml に合わせて導入してください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## 環境変数 / 設定

このパッケージは環境変数から設定を読み取ります（`kabusys.config.settings` を通じてアクセス可能）。自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには環境変数を設定します:

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 使用時。関数引数で上書き可）

その他（任意 / デフォルトあり）:
- KABUSYS_ENV — (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB のデフォルトパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

.env 例（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=xxxxx
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## セットアップ手順（開発時）

1. リポジトリをクローン
2. Python 仮想環境作成・有効化
3. 必要パッケージをインストール（上記参照）
4. .env を作成（.env.example を参考に）
5. DuckDB の初期スキーマは利用ケースに応じて作成（スキーマ初期化用ユーティリティを用意すること）

---

## 使い方：主要ユースケース例

以下はライブラリを直接インポートして使う簡単な例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- 日次 ETL 実行（データ取得 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント評価を実行（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で渡す）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定を実行
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB（監査ログ）を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。テーブルは作成済み。
```

- 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026,3,20))
# factors: list of dict (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)
```

注意:
- OpenAI 呼び出しは API 呼び出し数やトークンに依存します。api_key を引数で指定することも可能。
- ニュース / レジームの実装はルックアヘッドバイアスを避ける設計（内部で datetime.today() を参照しない等）になっています。バッチやバックテストでの利用に注意。

---

## API の主な公開関数（抜粋）

- kabusys.config.settings — 環境変数アクセス
- kabusys.data.pipeline.run_daily_etl — 日次 ETL のメイン
- kabusys.data.pipeline.ETLResult — ETL 実行結果オブジェクト
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.quality.run_all_checks — 品質チェックの実行
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化
- kabusys.ai.news_nlp.score_news — ニュースセンチメント評価（ai_scores への書込）
- kabusys.ai.regime_detector.score_regime — 市場レジームスコア算出・market_regime 書込
- kabusys.research.* — ファクター計算 / 特徴量解析ユーティリティ

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env 自動読み込み・設定管理
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — マーケットレジーム判定
- data/
  - __init__.py
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py — J-Quants API クライアント（取得 + 保存）
  - calendar_management.py — カレンダー管理（営業日ロジック）
  - news_collector.py — RSS 収集（SSRF 対策あり）
  - quality.py — データ品質チェック
  - stats.py — 統計ユーティリティ（Zスコア）
  - audit.py — 監査ログ（スキーマ初期化）
  - etl.py — ETL インターフェース再エクスポート
- research/
  - __init__.py
  - factor_research.py — ファクター計算
  - feature_exploration.py — 将来リターン / IC / summary

（その他、strategy / execution / monitoring モジュールは __all__ に定義されていますが、今回の抜粋コードには含まれていません）

---

## 実運用上の注意点

- API キーやトークンは厳重に管理してください。特に OpenAI や J-Quants のキーは外部に流出しないように。
- DuckDB ファイルはファイルロックやバックアップに配慮してください（複数プロセスでの同時書き込みは注意）。
- ETL / API 呼び出しにはリトライやレート制御を組込んでいますが、運用環境に合わせてタイムアウト・リトライ回数は調整してください。
- ニュース NLP やレジーム判定は外部 LLM（OpenAI）に依存します。コストやレイテンシ、利用制限に注意してください。
- KABUSYS_ENV を適切に切り替え（development / paper_trading / live）し、live では本番用の安全対策（ステージングでの動作確認・リスク制御）を厳密に行ってください。

---

## ライセンス / 貢献

（ここにはプロジェクトの LICENSE や貢献ガイドライン、連絡先を記載してください）

---

必要であれば、README に含める実行例スクリプトや Docker / CI セットアップ、より詳細なスキーマ定義（テーブル一覧）や運用手順を追加できます。どの情報を補足したいか教えてください。