# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI によるセンチメント評価）、市場レジーム判定、ファクター算出、データ品質チェック、監査ログ（注文→約定トレース）など、現物/戦略開発・運用に必要な主要機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の明示的取得（例: JQUANTS_REFRESH_TOKEN）
- データ ETL
  - J-Quants API から株価（日足）・財務・マーケットカレンダーを差分取得して DuckDB に保存
  - 差分取得、バックフィル、品質チェックの一括実行（run_daily_etl）
  - レートリミット・再試行・401 自動リフレッシュ対応
- ニュース収集
  - RSS フィード取得、前処理（URL除去・正規化）・raw_news へ冪等保存
  - SSRF 対策、受信サイズ上限、トラッキングパラメータ除去などを実装
- ニュース NLP / レジーム判定（OpenAI）
  - 銘柄ごとのニュースセンチメントを gpt-4o-mini（JSON mode）で評価し ai_scores に保存（score_news）
  - マクロニュースと ETF(1321) の MA200乖離を合成して日次の市場レジームを判定（score_regime）
  - API 再試行・フェイルセーフ（API失敗時は中立扱い）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリューファクター算出
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリー
- データ品質チェック
  - 欠損、重複、スパイク、将来日付・非営業日データ検出（QualityIssue 構造で集約）
- 監査ログ（audit）
  - signal → order_request → execution までトレース可能なテーブル群の初期化・管理
  - DuckDB 用の冪等 DDL とインデックスを提供

---

## 前提（Prerequisites）

- Python 3.10 以上（型注釈に PEP 604 等を使用）
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI へアクセスする場合）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

プロジェクト配布形態により setup / pyproject で依存を明示してください。

---

## 環境変数 / .env について

- 自動ロード: パッケージ内 `kabusys.config` は、.git または pyproject.toml を起点にプロジェクトルートを特定し、`.env` → `.env.local` の順で自動読み込みします（OS 環境変数を保護）。
- 自動ロード無効化: テスト等で無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 主要な環境変数:
  - JQUANTS_REFRESH_TOKEN (必須: J-Quants 用リフレッシュトークン)
  - OPENAI_API_KEY (OpenAI を使うときに必要)
  - KABU_API_PASSWORD (kabu API)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (通知用)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存インストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があれば pip install -e . を推奨）
4. 環境変数設定
   - .env / .env.local をプロジェクトルートに配置するか、OS 環境変数を設定
5. データディレクトリ準備（必要なら）
   - mkdir -p data
   - デフォルトで DuckDB ファイルは data/kabusys.duckdb に作成されます

---

## 使い方（簡単なコード例）

ライブラリはモジュール単位で使います。以下は主要な利用例です。

- DuckDB 接続の作成（監査DB初期化例含む）
```python
import duckdb
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# duckdb に接続
conn = duckdb.connect(str(settings.duckdb_path))

# 監査DBを別ファイルに初期化して接続を得る
audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```

- 日次 ETL 実行（J-Quants トークンは settings から自動取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None -> env OPENAI_API_KEY を参照
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20))
```

- リサーチ関数（ファクター算出）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
```

- 品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意:
- OpenAI を使用する関数は api_key 引数で明示指定可能。指定しない場合は環境変数 OPENAI_API_KEY を参照します。
- ETL / ニュース収集 / OpenAI 呼び出しは外部 API を利用するため、ネットワークと適切な API キーが必要です。

---

## 主要なモジュール / ディレクトリ構成

（src/kabusys 配下の主なファイルと役割を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env ロード、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py          - ニュースセンチメント評価（score_news）
    - regime_detector.py   - マクロ＋MA200 で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    - J-Quants API クライアント（fetch / save）
    - pipeline.py          - ETL パイプライン（run_daily_etl 他）
    - etl.py               - ETL 結果クラス ETLResult を再エクスポート
    - news_collector.py    - RSS ニュース収集・前処理
    - calendar_management.py - 市場カレンダー判定 / 更新ジョブ
    - quality.py           - データ品質チェック
    - stats.py             - 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py             - 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py   - Momentum / Volatility / Value の計算
    - feature_exploration.py - 将来リターン / IC / 統計サマリー 等

（実際のリポジトリにはさらに strategy / execution / monitoring 等のモジュールがある想定です。コード冒頭の __all__ 参照）

---

## 実運用上の注意点

- Look-ahead バイアス回避
  - 多くの関数は date 引数ベースで動作し、datetime.today()/date.today() を直接参照しないよう設計されています。バックテスト等では target_date を明示してください。
- フェイルセーフ方針
  - 外部 API の失敗時は例外で止めずに「中立スコア」や「スキップ」で継続する箇所が多く、運用側でのエラー監視が必要です。
- 環境別挙動
  - settings.env（KABUSYS_ENV）により is_live / is_paper / is_dev で判定できます。発注ロジックを実装する場合は環境に応じた制御を必ず行ってください。
- データベースの互換性
  - DuckDB の executemany に関する挙動や list バインドの挙動はバージョンによって差があるため、コードは互換性に配慮していますが、本番環境での DuckDB バージョン管理を推奨します。

---

## 開発・テスト

- .env 自動読み込みを無効化したいユニットテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants 呼び出しは外部 API を伴うため、ユニットテストでは該当呼び出しをモック（unittest.mock.patch）する設計になっています（モジュール内で API 呼び出しをラップしている箇所があるため差し替えが容易です）。

---

## ライセンス・貢献

- README の末尾にライセンスやコントリビューションに関する文言を追記してください（このテンプレートには記載していません）。

---

必要であれば、各モジュールの API ドキュメント（引数・返り値の詳細、例外の挙動）や、運用手順（定期ジョブの cron/airflow 設定例、監視アラートの例）も作成できます。どの部分を優先して深堀りしますか？