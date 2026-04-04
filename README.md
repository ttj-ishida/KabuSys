# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。  
DuckDB をデータレイヤに用い、J-Quants / RSS / OpenAI（LLM）など外部ソースを統合して、ETL、品質チェック、ニュース NLP、マーケットレジーム判定、リサーチ用ファクター計算、監査ログなどを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）、財務データ、マーケットカレンダーを差分取得して DuckDB に保存
  - 差分・バックフィルロジック、ページネーション、レート制御、トークン自動リフレッシュ対応

- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付整合性（将来日付や非営業日データ）を検出

- ニュース収集
  - RSS から記事取得、前処理、URL 正規化、SSRF 対策、raw_news / news_symbols への保存（冪等）

- ニュース NLP（LLM）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのセンチメントスコアリング（ai_scores へ保存）
  - マクロニュースの集約と市場センチメント評価

- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離とマクロセンチメントを合成して daily のレジーム（bull/neutral/bear）を判定・保存

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
  - クロスセクション正規化ユーティリティ（Zスコア）

- 監査ログ（Audit）
  - シグナル → 発注 → 約定のトレース用テーブル群（冪等・UTC タイムスタンプ）と初期化ユーティリティ

- 設定管理
  - .env / .env.local / OS 環境変数の自動読み込み（プロジェクトルート検出），自動無効化フラグあり

---

## 必要条件・依存関係

主に以下のパッケージを使用しています（バージョンは例示）:

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ: urllib, json, logging, datetime, pathlib など）

インストール例（最低限）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発時はパッケージを編集可能インストール
pip install -e .
```

プロジェクトに requirements.txt がある場合はそれを使ってください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
```bash
git clone <repo-url>
cd <repo>
```

2. Python 仮想環境を作成・有効化（任意）
```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows
```

3. 依存パッケージをインストール
```bash
pip install duckdb openai defusedxml
pip install -e .
```

4. 環境変数（.env）を準備  
プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

例（.env.example）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI (news NLP / regime detector)
OPENAI_API_KEY=your_openai_api_key

# kabu API (もし使用する場合)
KABU_API_PASSWORD=...

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

# データベースパス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. 必要なディレクトリを作成（デフォルトのデータ保存先が存在しない場合）
```bash
mkdir -p data
```

---

## 使い方（主要 API / 実行例）

以下はライブラリ内の関数を直接呼ぶサンプルです。スクリプト化して Cron / ワーカーで実行する前提です。

- DuckDB 接続を作成して日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # デフォルトパスは settings.duckdb_path
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP（ai スコア）を特定日で実行（OpenAI API キーが必要）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote scores for {written} codes")
```

- 市場レジーム判定を実行:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

- 個別ファクター計算（リサーチ用）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
# records は各銘柄の日付・code をキーとしたファクター辞書のリスト
```

- 設定取得（環境変数）:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- news_nlp / regime_detector は OpenAI を使います。API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- J-Quants 呼び出しには `JQUANTS_REFRESH_TOKEN` が必須です（settings.jquants_refresh_token）。

---

## 自動 .env ロードの挙動

- 自動読み込み順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```
- プロジェクトルートはこのパッケージのファイル位置から親ディレクトリをさかのぼり `.git` または `pyproject.toml` を基準に検出します。見つからない場合は自動ロードをスキップします。

---

## よく使うユーティリティ / 注意点

- ETL は部分的に失敗しても他処理を継続する設計です。戻り値の ETLResult でエラーや品質問題を確認してください。
- DuckDB の executemany は空リストを受け付けないバージョンに注意（コード内で回避済）。
- LLM 呼び出しはリトライ・フォールバックロジックを持ちます。API エラー時はゼロスコアやスキップでフェイルセーフにしています。
- ニュース収集では SSRF 対策、トラッキングパラメータ除去、応答サイズ制限など安全対策を実装しています。
- 監査ログ（audit）テーブルは削除しない前提で設計されています。order_request_id は冪等キーとして二重発注防止に使用されます。

---

## ディレクトリ構成

以下は主要ファイル／ディレクトリの概略です（src 配下）:

src/kabusys/
- __init__.py
- config.py                -- 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py            -- ニュース NLP（銘柄ごとの ai_score）
  - regime_detector.py     -- 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py      -- J-Quants API クライアント（取得・保存）
  - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
  - etl.py                 -- ETLResult の再エクスポート
  - quality.py             -- 品質チェック
  - news_collector.py      -- RSS 収集
  - calendar_management.py -- 市場カレンダー管理（is_trading_day など）
  - stats.py               -- 統計ユーティリティ（zscore_normalize）
  - audit.py               -- 監査ログ初期化・ユーティリティ
- research/
  - __init__.py
  - factor_research.py     -- ファクター計算（momentum/value/volatility）
  - feature_exploration.py -- 将来リターン / IC / サマリー等
- ai、data、research 内部で多くの補助関数と安全設計が実装されています。

プロジェクトルートには（存在する場合）
- .env / .env.local
- pyproject.toml / setup.cfg（Python パッケージ設定）
- README.md（本ファイル）

---

## 開発・運用上のヒント

- ローカルでのテスト実行時に .env を使って API キーを渡すと便利です。自動ロードを無効にしたい単体テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に格納されます。別パスを使う場合は環境変数 `DUCKDB_PATH` で上書きできます。
- OpenAI の呼び出しはコストがかかるため、開発中はモック／スタブやテスト用の置き換えを使ってください（モジュール内の _call_openai_api をテスト用にパッチ可能）。
- J-Quants のレート制限（120 req/min）に合わせた RateLimiter が組み込まれていますが、大量呼び出しのバッチ運用時は注意してください。

---

## ライセンス / 貢献

（この README にはライセンス情報が含まれていません。リポジトリの LICENSE ファイルを参照してください。）

貢献方法:
- Issue / Pull Request を用いてバグ報告や改善提案をお願いします。
- 重大な設計変更は事前に Issue で議論を行ってください。

---

以上が KabuSys の README の概要です。実際の運用スクリプト（cron / systemd / ワーカー）に組み込む際はログ設定、プロセス監視、LINE 通知等を追加してください。必要であれば具体的なデプロイ手順やサンプルスクリプトも提供します。