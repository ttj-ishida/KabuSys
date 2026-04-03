# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP、リサーチ用ファクター計算、監査ログといった機能を含み、戦略・発注層とは分離して実装されています。

主な設計方針は次の通りです。
- ルックアヘッドバイアスを避ける（内部で date.today() を直接参照しない等）
- DuckDB を主なオンディスク DB として使用
- 外部 API 呼び出しは再現性・耐障害性（リトライ・バックオフ等）を考慮
- API キー等は .env / 環境変数で管理（auto load 対応）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API 経由で株価（日次OHLCV）、財務情報、上場銘柄情報、JPXカレンダーを差分取得・保存
  - run_daily_etl による日次ETLパイプライン（カレンダー→株価→財務→品質チェック）
- データ品質チェック
  - 欠損（OHLC）検出、前日比スパイク検出、主キー重複、日付整合性（未来日付・非営業日データ）など
- ニュース収集
  - RSS フィード取得・前処理（URL 正規化、SSRF 対策、本文整形）→ raw_news / news_symbols 保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを LLM（gpt-4o-mini 等）でスコアリングし ai_scores に保存（バッチ・リトライ対応）
  - マクロニュースから市場レジーム（bull/neutral/bear）判定（ETF 1321 の MA200 乖離 と LLMセンチメントの合成）
- 研究用機能
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブルを DuckDB に初期化・管理
- 環境 / 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート自動検出）と Settings クラス経由の設定取得

---

## 必要条件

- 推奨 Python バージョン: 3.10+
  - union 演算子（A | B）や型注釈、list[str] 等を利用しているため Python 3.10 以上を推奨します
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （そのほかユーティリティとして標準ライブラリと urllib 等を利用）

pip で最低限インストールする例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発インストール（パッケージ化されている前提）
pip install -e .
```

（requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化
2. 依存パッケージをインストール（上記参照）
3. プロジェクトルートに .env を作成（自動で読み込まれます）
   - 自動ロードの順序: OS環境変数 > .env.local > .env
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
4. DuckDB ファイルや監視用ファイルを格納するディレクトリを用意（settings のデフォルトは data/ 以下）
5. OpenAI や J-Quants の API キーを .env に設定

例: .env の雛形（.env.example 相当）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション API（発注連携等）
KABU_API_PASSWORD=your_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# DB / モニタリング
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行監視
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
KILL_FLAG_CLEAR_ON_START=1

# 環境 / ログ
KABUSYS_ENV=development   # development / paper_trading / live
LOG_LEVEL=INFO
```

環境変数の読み込みは kabusys.config.Settings クラスを通じて行います。必須のキーが未設定の場合は ValueError が発生します。

---

## 使い方（例）

以下はライブラリを使った代表的な操作例です。実行は適切に仮想環境を有効化した上で行ってください。

- DuckDB 接続を作成して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返します
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニューススコアリング（特定日）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None => env OPENAI_API_KEY を利用
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 以降、conn_audit を使って監査ログの操作が可能
```

- リサーチ用ファクター計算:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- RSS フィード取得（ニュース収集の個別利用例）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

注意点:
- OpenAI 呼び出しには API キー（環境変数 OPENAI_API_KEY）が必要です。
- J-Quants は認証トークン（リフレッシュトークン JQUANTS_REFRESH_TOKEN）を使って id_token を取得します。
- run_daily_etl 等は DB 内の既存状態に依存するため、初回は必要なテーブルスキーマを用意しておくか、ETL スキーマ初期化処理を別途実行してください（本リポジトリに schema 初期化コードが含まれている想定です）。

---

## 環境変数と設定（主なキー）

kabusys.config.Settings で参照される主な環境変数（大文字）:

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (LLM 呼び出しに必要)
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動ロードを無効化します

.env はプロジェクトルート（.git または pyproject.toml を基準に検出）から自動読み込みされます。読み込み順序と挙動:
- OS 環境変数が最優先
- .env.local は .env の上書き（override=True）
- .env は既に設定されている OS 環境変数を上書きしない（override=False）

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメントスコア生成（OpenAI 連携）
    - regime_detector.py    — マクロセンチメント + ETF MA200 で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETL の公開型（ETLResult の再エクスポート）
    - news_collector.py     — RSS 収集・前処理（SSRF 対策等）
    - calendar_management.py— JPX カレンダー管理・営業日ヘルパー
    - stats.py              — 汎用統計（Zスコア正規化 等）
    - quality.py            — 品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py              — 監査ログスキーマ初期化 / audit DB ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py— 将来リターン・IC・統計サマリー等

各モジュールは docstring とログ出力により動作方針・制約が明記されています。ユニットテストや CI はプロジェクトに応じて追加してください。

---

## 運用上の注意

- 本ライブラリは本番発注ロジックや戦略本体とは切り離して設計されています。実際の発注処理や資金管理は別モジュールで慎重に実装してください。
- Live 環境（KABUSYS_ENV=live）では外部 API コールや発注の影響が実際の取引に及ぶため、十分な検証・モニタリングの下で運用してください。
- API レート制限やコストに注意して OpenAI / J-Quants の呼び出しを行ってください（バッチ化・キャッシュ・リトライ方針が各モジュールに実装されています）。
- DuckDB のバージョン差分により executemany の振る舞いや型バインドが異なる場合があるため、環境依存テストを行ってください。

---

## 貢献

バグ報告や機能提案は Issue を立ててください。内部実装の一貫性（例: ルックアヘッドバイアス回避やトランザクション処理）を保つことを意識して PR を送ってください。

---

README はここまでです。必要であれば以下を追加します:
- 詳細な .env.example ファイル
- requirements.txt / pyproject.toml のサンプル
- 初期スキーマ作成スクリプトの使用例
- よくあるエラーと対処法

どれを追加しますか？