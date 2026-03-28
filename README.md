# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、ファクター・リサーチ、マーケットカレンダー管理、監査ログ（トレーサビリティ）、および市場レジーム判定などを含むモジュール群を提供します。

主に DuckDB をデータ格納に使い、OpenAI（gpt-4o-mini 等）をニュースセンチメント解析に利用する構成です。

---

## 特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価（日足）、財務データ、マーケットカレンダーを差分取得して DuckDB に保存
  - 差分更新・バックフィル・ページネーション対応・ID トークン自動リフレッシュ
  - ETL の実行結果を ETLResult として取得

- データ品質チェック
  - 欠損データ、スパイク（急変）、重複、日付不整合（未来日付・非営業日）検出
  - QualityIssue オブジェクトで詳細を返す

- ニュース収集 / 前処理
  - RSS フィード取得（SSRF 対策、レスポンスサイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存処理

- ニュース NLP（OpenAI 経由）
  - 銘柄ごとニュースをまとめて LLM に投げ、銘柄別センチメント（ai_scores）を DuckDB に保存（score_news）
  - バッチ処理・リトライ・レスポンスバリデーションあり

- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離 + マクロニュースセンチメントを合成して market_regime テーブルに判定を記録（score_regime）

- リサーチ / ファクター計算
  - モメンタム、バリュー、ボラティリティ等のファクター計算
  - 将来リターン、IC（Spearman）や統計サマリの計算
  - z-score 正規化ユーティリティ

- マーケットカレンダー管理
  - market_calendar テーブルの更新、営業日判定、前後営業日の取得、期間内営業日リストの取得
  - DB データ優先・未登録日は曜日フォールバック

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査用テーブル定義と初期化関数
  - 監査DBの初期化ユーティリティ（init_audit_db）

- 設定管理
  - 環境変数（.env / .env.local）の自動ロード（プロジェクトルートを検出して取り込む）
  - 必須設定の取得ユーティリティ（Settings）

---

## システム要件（推奨）

- Python 3.10+
- DuckDB
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全対策）
- その他標準ライブラリ

必要な Python パッケージ例:
- duckdb
- openai
- defusedxml

簡単なインストール例:
```
python -m pip install duckdb openai defusedxml
```

プロジェクトを開発環境にインストールする場合（pyproject.toml がある前提）:
```
python -m pip install -e .
```

---

## 環境変数 / 設定

このパッケージは環境変数経由で設定を読み込みます（.env / .env.local 自動ロード機能あり）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news/score_regime を使う場合）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須とされる箇所あり）
- SLACK_CHANNEL_ID: Slack チャネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment ('development' / 'paper_trading' / 'live')（デフォルト: development）
- LOG_LEVEL: 'DEBUG'/'INFO'/...（デフォルト: INFO）

Settings は `kabusys.config.settings` から参照できます。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=passwd
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（ローカル）

1. リポジトリをクローン（既にある場合はスキップ）
2. Python 仮想環境の作成と有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows
   ```
3. 必要パッケージをインストール
   ```
   python -m pip install -U pip
   python -m pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください）
4. 必要な環境変数を設定（.env をプロジェクトルートに作成）
5. DuckDB の初期スキーマは各モジュールの初期化ロジックや管理スクリプトで作成してください（audit の初期化関数等を利用可）。

---

## 使い方（簡単なコード例）

以下はいくつかの典型的な使い方例です。DuckDB 接続には `duckdb.connect(path)` を使用します（path は settings.duckdb_path などで設定）。

- ETL（日次）を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースを LLM でスコア付けして ai_scores に保存する:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None -> OPENAI_API_KEY 使用
print("書き込み件数:", n_written)
```

- 市場レジーム判定（score_regime）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- リサーチ系（モメンタムなど）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の辞書リスト
```

- 監査ログ DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_duckdb.db")
# これで signal_events / order_requests / executions テーブルが作成される
```

- 設定取得例:
```python
from kabusys.config import settings
print(settings.duckdb_path)         # Path オブジェクト
print(settings.env)                 # 'development' / 'paper_trading' / 'live'
```

注意:
- OpenAI を使う機能は `OPENAI_API_KEY` を環境変数でセットするか、関数に api_key を渡してください。
- J-Quants との連携は `JQUANTS_REFRESH_TOKEN` が必須です。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトのルートに README.md、pyproject.toml 等がある想定。以下は src/kabusys 以下の主要モジュール）

- src/kabusys/
  - __init__.py
  - config.py                          # 環境変数 / 設定の読み込み
  - ai/
    - __init__.py
    - news_nlp.py                       # ニュースセンチメント取得（score_news）
    - regime_detector.py                # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py            # 市場カレンダー管理（営業日判定等）
    - etl.py / pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - stats.py                          # 共通統計ユーティリティ（zscore_normalize）
    - quality.py                        # データ品質チェック
    - audit.py                          # 監査ログ初期化（監査スキーマ）
    - jquants_client.py                 # J-Quants API クライアント（fetch/save）
    - news_collector.py                 # RSS ニュース収集・前処理
    - pipeline.py                       # ETLResult の再エクスポート（etl.py から）
  - research/
    - __init__.py
    - factor_research.py                # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py            # 将来リターン / IC / サマリー 等

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り SQL と Python の組合せで処理する設計です。

---

## 運用上の注意 / ベストプラクティス

- Look-ahead バイアス防止
  - 多くの関数は内部で date.today() を直接参照しない設計（target_date を明示する）。
  - バックテストでは、バックテスト対象開始日以前のデータのみを DB に入れてから使用してください。

- API リトライ / フェイルセーフ
  - OpenAI / J-Quants 呼び出しはリトライやフォールバック（失敗時 0.0 スコア等）を行う設計です。
  - ただしネットワークや認証の問題はログに通知されます。運用時はログ監視を推奨します。

- 環境変数の自動ロード
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動で読み込みます。
  - テスト等で自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB 書き込みは冪等化を重視
  - save_* 関数は ON CONFLICT / DO UPDATE を用いて冪等に保存します。
  - ETL の各段階でトランザクション制御を行っていますが、部分失敗時の挙動には注意してください（ログ・ETLResult を確認してください）。

---

## 参考情報 / 追加開発ポイント

- OpenAI のレスポンスは JSON mode を利用して厳密な JSON を期待しますが、補完処理（前後テキストの除去）も実装されています。
- news_collector は SSRF/サイズ制限/トラッキング除去等の堅牢化を施しています。
- 監査ログは監査要件に沿ったテーブル群（UUID ベース、冪等キー）を提供します。
- 実運用時は kabuステーション API 発注モジュールや Slack 通知のラッパーを作成して統合してください（本コードベースではデータ取得・スコアリング・監査の基盤機能を提供）。

---

ご要望があれば、README に含めるサンプルスクリプト、pyproject.toml / requirements.txt の推奨内容、あるいは各モジュールの API ドキュメント（関数一覧・引数説明）を追加で生成します。どの部分を詳しくしたいか教えてください。