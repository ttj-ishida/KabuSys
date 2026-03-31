# KabuSys

KabuSys は日本株向けのデータ基盤・研究・AI支援・監査ログ・ETL・市場レジーム判定などを含む自動売買システムのライブラリ群です。本リポジトリは以下の要素を Python モジュールとして提供します。

- データ取得・ETL（J-Quants API 経由、DuckDB 保存）
- データ品質チェック
- ニュース収集・ニュース NLP（OpenAI を用いたセンチメント評価）
- 市場レジーム判定（MA とマクロニュースの合成）
- 研究用ファクター計算・特徴量解析
- 監査ログ（注文→約定のトレーサビリティ）用スキーマ初期化
- 設定管理（.env 自動読み込み、環境変数）

以下は本コードベースの概要、セットアップ、使い方、ディレクトリ構成などのドキュメントです。

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータパイプライン、AI ベースニュース解析、リサーチ用のファクター計算、監視・監査機能を modular に提供するライブラリ群です。  
設計上の特徴：

- Look-ahead bias の回避（内部で date.today() を無作為に参照しない設計の関数群）
- DuckDB を中心としたローカル分析データベース
- J-Quants API との安全で堅牢なインターフェース（レートリミット、リトライ、トークン自動リフレッシュ）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（JSON Mode を利用）
- ニュース収集に対する SSRF / XML 攻撃対策（defusedxml、ホスト検証、サイズ制限）

## 機能一覧

主な機能（モジュール単位）

- kabusys.config
  - .env ファイル自動読み込み（プロジェクトルート検出）
  - 環境変数から構成を取得する Settings クラス
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存関数、レート制御、リトライ）
  - pipeline: 日次 ETL（run_daily_etl）や個別 ETL（run_prices_etl 等）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector: RSS 収集と前処理（SSRF 対策、トラッキングURL除去、ID生成）
  - calendar_management: 市場カレンダー管理・営業日ロジック（next/prev/is_trading_day 等）
  - audit: 監査ログ用スキーマの初期化・DB 作成（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄ごとにまとめて OpenAI に送り ai_scores を作成
  - regime_detector.score_regime: ETF（1321）の MA 乖離 + マクロニュース LLM を合成して market_regime を算出
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター算出）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank 等

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai (OpenAI の公式 SDK)
  - defusedxml
  - その他: typing、urllib など標準ライブラリ

例（pip）:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

※実運用では requirements.txt / pyproject.toml を用いて依存管理してください。

## セットアップ手順

1. リポジトリをクローン／展開する。

2. 仮想環境作成（推奨）
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
pip install -U pip
pip install duckdb openai defusedxml
```

3. 環境変数 / .env の準備  
プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと、自動的に読み込まれます（環境変数が優先）。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

推奨される主要な環境変数（.env 例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id

# オプション
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

4. データベース用ディレクトリの作成（必要に応じて）
```bash
mkdir -p data
```

## 使い方（主要ユースケース）

以下は最小限の Python スニペット例です。いずれも duckdb を使って接続した conn を渡して実行します。

- DuckDB 接続の生成（デフォルトパスは設定により変更できます）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（株価 / 財務 / カレンダーの差分 ETL）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア生成（OpenAI API キーは env または引数で指定可能）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すことが推奨（テストや安全性のため）
count = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
print(f"scored {count} codes")
```

- 市場レジーム判定（1321 の MA200 乖離 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
```

- 監査 DB の初期化（監査ログ用の専用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# 返り値は {date, code, mom_1m, mom_3m, mom_6m, ma200_dev} の dict リスト
```

- 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)
```

## 開発・テストのヒント

- .env の自動読み込みはプロジェクトルート（.git / pyproject.toml）を基準に行われます。ユニットテスト中に自動読み込みを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- OpenAI への外部呼び出しやネットワーク I/O は各モジュールで呼び出し関数をラップしており、テスト時は該当関数（例: kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api、kabusys.data.news_collector._urlopen 等）を unittest.mock.patch で差し替えることを想定しています。
- DuckDB の executemany に関する挙動（空リスト不可など）を考慮してコードが書かれています。テストデータを作る際は注意してください。

## ディレクトリ構成

以下は主要なソースツリー（src/kabusys 以下）の抜粋と説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と .env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py         - ニュースを銘柄別に集約して OpenAI でスコアリング（score_news）
    - regime_detector.py  - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   - J-Quants API クライアント（fetch / save 関数）
    - pipeline.py         - ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - quality.py          - データ品質チェック
    - news_collector.py   - RSS 収集と前処理
    - calendar_management.py - 市場カレンダー管理・営業日ロジック
    - audit.py            - 監査ログ用スキーマ定義・初期化（init_audit_db 等）
    - stats.py            - zscore_normalize などの統計ユーティリティ
    - etl.py              - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py  - momentum/value/volatility のファクター計算
    - feature_exploration.py - forward returns, IC, summary 等
  - research/* その他の研究ユーティリティ

各モジュールは DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取り SQL と Python を組み合わせて処理する設計になっています。

## 注意点 / 運用上の留意事項

- 本ライブラリは実際の約定・資金移動を伴う注文送信を含んでいないモジュール（研究・データ基盤寄り）と、実行系（execution）や監視系（monitoring）を分けた構成が想定されています。実売買環境で使用する際は十分な検証とリスク管理を行ってください。
- 環境変数に機密情報（API キーやパスワード）を設定する際は権限管理・シークレット管理ツールの利用を推奨します。
- OpenAI API 呼び出しは外部通信を伴います。料金、レート制限、応答フォーマットの変化に注意してください。
- J-Quants API はレート制限があるため、jquants_client は内部でスロットリング・リトライを実装しています。利用時は API 利用規約を遵守してください。

---

この README はコードの主要点をまとめたものです。より詳細な設計ドキュメント（DataPlatform.md, StrategyModel.md 等）がある前提で実装は作られています。具体的な運用手順や追加の CLI / サービス化は別途スクリプトや orchestration が必要です。必要であれば、README に追加したい実行例やデプロイ手順（systemd / Docker / k8s 等）についても作成します。