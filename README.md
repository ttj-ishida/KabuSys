# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
データ収集（J-Quants / RSS）、ETL、品質チェック、リサーチ（ファクター計算）、AIベースのニュースセンチメント/市場レジーム判定、監査ログ（オーダー→約定トレース）などを提供します。

---

## 概要

KabuSys は以下の目的を持つ Python パッケージです。

- J-Quants API から株価・財務・カレンダー等を安全に取得して DuckDB に格納する ETL パイプライン
- RSS からニュース収集、前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価と市場レジーム判定
- 研究用途のファクター計算・特徴量探索ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal / order_request / execution）を保持する監査テーブル初期化ユーティリティ

設計上のポイント：
- バックテスト/研究でのルックアヘッドバイアス回避を重視（内部で datetime.today() を直接参照しない等）
- API 呼び出しに対するリトライ/レート制限/フォールバックを組み込み
- DuckDB を中心に軽量にデータを保存・クエリ可能

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存関数・レート制御）
  - ニュース収集（RSS → raw_news）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（missing, duplicates, spike, date_consistency）
  - 監査ログ初期化（init_audit_schema, init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約し LLM でセンチメントを算出して ai_scores に保存
  - regime_detector.score_regime: 1321(ETF) の MA 乖離とマクロニュースセンチメントを合成して market_regime を作成
- research/
  - factor_research: momentum/volatility/value 等のファクター計算関数
  - feature_exploration: 将来リターン計算 / IC（情報係数） / 統計サマリー
- config.py
  - 環境変数の読み込み（.env / .env.local の自動読み込み）と設定オブジェクト（settings）

セキュリティ・堅牢性:
- RSS の SSRF 対策、受信サイズ制限、XML パーサのハードニング
- J-Quants API のレート制御とトークン自動更新
- OpenAI 呼び出しでのリトライ/タイムアウト/パース失敗のフェイルセーフ

---

## セットアップ手順

最低限の手順（例）

1. Python 環境を作成（例: venv）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. パッケージと依存をインストール（プロジェクトに setuptools/poetry の設定がある前提で、ローカル編集用インストール例）:
   ```bash
   pip install -e .   # プロジェクトルートに setup.cfg/pyproject.toml がある場合
   ```

   必要な主要依存（該当バージョンは適宜指定してください）:
   - duckdb
   - openai
   - defusedxml

   直接インストールする場合:
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数・.env ファイルを用意
   - ルートに `.env` または `.env.local` を置くと自動的に読み込まれます（config.py がプロジェクトルートを探索して読み込み）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用 Slack 設定（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: environment (development / paper_trading / live)（デフォルト: development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）

   注意: Settings オブジェクトは .env.example を参照して必要変数を埋めてください。必須変数が未設定の場合は Settings のプロパティで ValueError が発生します。

---

## 使い方（代表例）

以降は簡単な使用例です。適宜ログ設定や例外処理を追加してください。

- DuckDB 接続の取得（設定されたパスを利用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- ETL（日次パイプライン）を実行する
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を None にすると今日（settings.env を踏まえた）を使う
result = run_daily_etl(conn, target_date=None)
print(result.to_dict())
```

- 単体 ETL（株価・財務・カレンダー）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

d = date(2026, 3, 20)
fetched, saved = run_prices_etl(conn, d)
```

- ニュースのセンチメント評価（OpenAI API キーが必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査用独立 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.db")
# これで監査用テーブルとインデックスが作成されます
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

records = calc_momentum(conn, date(2026, 3, 20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- OpenAI 呼び出しは rate-limit や API エラーに対してリトライを行いますが、API キーが必要です。
- AI 関連処理は記事が無い場合や API エラー時に安全に 0 相当で継続するロバストな設計です（例: macro_sentiment=0.0）。

---

## ディレクトリ構成

主要ファイルを抜粋した構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュース NLP スコアリング（score_news）
    - regime_detector.py            # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント（fetch/save）
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - etl.py                        # ETLResult の再エクスポート
    - news_collector.py             # RSS → raw_news 収集
    - calendar_management.py        # 市場カレンダー管理（営業日判定等）
    - quality.py                    # データ品質チェック
    - stats.py                      # 統計ユーティリティ（zscore_normalize）
    - audit.py                      # 監査ログ初期化（init_audit_schema/init_audit_db）
  - research/
    - __init__.py
    - factor_research.py            # Momentum / Volatility / Value
    - feature_exploration.py        # 将来リターン / IC / 統計サマリー

---

## 実運用向けの注意・ヒント

- .env の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml の所在）を探索して `.env` / `.env.local` を自動読み込みします。
  - .env.local は .env を上書きします（OS 環境変数は保護されます）。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。
- Look-ahead バイアス防止:
  - ai/ と data/ の設計は「バックテスト中に未来データを参照しない」ことを重視しています。target_date パラメータに依存する関数は内部で date.today() を直接参照しないようになっています。
- J-Quants と OpenAI の利用:
  - API 利用のためのトークン・課金等の管理は利用者側で行ってください。
  - J-Quants はリクエストレートに注意（ライブラリ内でレート制御あり）。
- DuckDB の互換性:
  - executemany に空リストを渡せないバージョンの対処や、型の扱いに注意した実装上の工夫があります。DuckDB のバージョン依存問題に注意してください。

---

必要があれば以下も提供できます:
- .env.example のテンプレート
- サンプルスクリプト（ETL 定期実行、監視、Slack 通知連携）
- 開発用のテスト実行手順（モックを利用したユニットテストの例）

その他、ご希望の README の拡張（より詳細な API リファレンス、サンプル DB スキーマ、実運用デプロイ手順など）があれば教えてください。