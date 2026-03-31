# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。J-Quants からのデータ取得（ETL）、ニュース収集・NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを一貫して提供します。

主な設計方針は「ルックアヘッドバイアス排除」「冪等性」「フェイルセーフ（API失敗時の安全なフォールバック）」「DuckDB を用いた軽量なオンプレ/クラウド保存」です。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（主なもの）
- 使い方（主要 API / サンプル）
- ディレクトリ構成
- 注意事項 / 実装上のポイント

---

プロジェクト概要
- J-Quants API を用いた市場データの差分 ETL（株価日足・財務・市場カレンダー）
- RSS ベースのニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント算出（銘柄別 ai_score / マクロセンチメント）
- ETF（1321）の MA とマクロセンチメントを合成した市場レジーム判定（bull/neutral/bear）
- 研究用途のファクター計算（モメンタム / ボラティリティ / バリュー 等）、前方リターン計算、IC 計算、Z スコア正規化
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 発注／約定までを追跡する監査ログスキーマ（DuckDB）と初期化ユーティリティ

---

機能一覧
- data.jquants_client: J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ、DuckDB への冪等保存）
- data.pipeline: 日次 ETL パイプライン（run_daily_etl）と個別 ETL ジョブ（prices/financials/calendar）
- data.news_collector: RSS 収集・前処理・保存（SSRF / XML 脆弱性対策、サイズ制限）
- ai.news_nlp: 銘柄別ニュースセンチメントの算出（OpenAI JSON Mode を利用）
- ai.regime_detector: ETF MA とマクロセンチメントを合成した市場レジーム算出
- data.quality: データ品質チェック（QualityIssue の集合を返す）
- data.calendar_management: 営業日判定・前後営業日算出・カレンダー更新ジョブ
- data.audit: 監査ログスキーマ定義と初期化（init_audit_schema / init_audit_db）
- research: ファクター計算・特徴量探索・統計ユーティリティ

---

必要条件
- Python 3.10 以上（typing の | 演算子を使用）
- 主な依存ライブラリ（抜粋）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリを多用し、pandas 等には依存しない設計）
- ネットワークアクセス（J-Quants API、RSS、OpenAI 等）

推奨: 仮想環境（venv / pyenv）で動かしてください。

---

セットアップ手順（開発向け）
1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. パッケージをインストール（開発モード）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（デフォルト）。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - サンプル: .env.example を参照して作成してください（プロジェクトルートに .git または pyproject.toml があると自動検出します）。

---

環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須、data.jquants_client.get_id_token に使用）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp/ai.regime_detector で使用。api_key 引数でも注入可能）
- KABU_API_PASSWORD: kabu ステーション用パスワード（注文実行部分が実装される想定）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

注: 必須のもの（ValueError を出す）は Settings を経由すると明示されます（kabusys.config.settings）。

---

使い方（サンプル）

- DuckDB 接続を作って ETL を実行する（日次）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースのスコアリング（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"書き込み銘柄数: {count}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
mom_z = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

- 監査ログ（Audit DB）初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ作成される
```

- カレンダー・営業日ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py           — 銘柄別ニュースセンチメント算出
    - regime_detector.py    — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch/save）
    - pipeline.py           — ETL パイプライン（run_daily_etl 他）
    - etl.py                — ETLResult export
    - news_collector.py     — RSS 収集、前処理
    - calendar_management.py— マーケットカレンダー管理 / 営業日判定
    - quality.py            — 品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログスキーマと初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    — モメンタム / バリュー / ボラティリティ 等
    - feature_exploration.py— 将来リターン / IC / 統計サマリー 等

（上記は主なモジュール。詳細な内部関数はモジュール内ドキュメントを参照してください。）

---

注意事項 / 実装上のポイント
- ルックアヘッドバイアス防止:
  - 多くの処理は内部で date（引数）ベースになっており、datetime.today()/date.today() を直接参照しないよう設計されています（バックテストでの誤用を防止）。
- 冪等性:
  - J-Quants から取得したデータは DuckDB へ ON CONFLICT DO UPDATE で保存するため再実行しても一貫性が保たれます。
- フェイルセーフ:
  - OpenAI 呼び出しや外部 API の失敗は、スコアを 0.0 にフォールバックする等の安全策が入っています（ただし運用ポリシーに合わせて監視してください）。
- レート制御・リトライ:
  - J-Quants クライアントは固定間隔のレートリミットとエクスポネンシャルバックオフを実装しています。
- セキュリティ:
  - RSS 取得は SSRF 対策、XML パースは defusedxml を利用、レスポンスサイズ上限などの防御が組み込まれています。
- テストの容易性:
  - OpenAI 呼び出し等は内部でラップしてあり、ユニットテスト用にパッチしやすい設計です（例: kabusys.ai.news_nlp._call_openai_api をモック）。

---

問題点・拡張
- kabu ステーションや実際の発注の統合は本リポジトリの別モジュール（execution 等）で扱う想定です。実運用時は発注前の十分な検証・テストを行ってください。
- モデルやプロンプトは将来的に調整が必要になる可能性があります（OpenAI のモデルアップデート等）。

---

お問い合わせ
- ソースコードの個別関数には詳細な docstring を記載しています。実装/運用に関する質問や機能追加は該当モジュールの docstring をまずご参照ください。必要であれば README を適宜更新します。

以上。README の補足や、使い方の具体的なスクリプト例（cron ジョブ/コンテナ実行例等）が必要であれば教えてください。