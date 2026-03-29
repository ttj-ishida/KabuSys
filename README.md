# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータプラットフォーム・研究・自動売買基盤を構築するための Python ライブラリ群です。  
DuckDB を用いた時系列データ管理、J-Quants API 経由のデータ取得・ETL、ニュースの収集と LLM による NLP スコアリング、ファクター計算・特徴探索、監査ログ（トレーサビリティ）などを含みます。

主な設計方針
- ルックアヘッドバイアスを防ぐ（内部で date.today()/datetime.today() を直接参照しない設計）
- DuckDB を中心としたシンプルで冪等な ETL / 保存処理
- 外部 API 呼び出しはリトライ・レート制御を備えた堅牢な実装
- ニュース集約 → LLM（OpenAI）によるバッチスコアリングの実装（JSON Mode を利用）
- 監査ログ（signal → order_request → execution）による完全なトレーサビリティ

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）および必須環境変数検査
- Data（データプラットフォーム）
  - J-Quants API クライアント（株価、財務、上場情報、カレンダー取得）
  - ETL パイプライン（差分取得・保存・品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day など）
  - ニュース収集（RSS、SSRF対策、前処理、raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 統計ユーティリティ（Zスコア正規化）
  - 監査ログ（signal/order_requests/executions のスキーマ・初期化）
- AI / NLP
  - ニュースセンチメントスコアリング（銘柄ごとの ai_score 生成）
  - 市場レジーム判定（ETF(1321) の MA とマクロニュースの LLM スコアを合成）
- Research（リサーチ用ユーティリティ）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- 付帯機能
  - Slack 通知用設定（トークン／チャンネルID を環境変数で管理）
  - kabuステーション API 用設定

---

## 必要環境・依存

- Python 3.10 以上（PEP 604 の `|` 型ヒント等を使用）
- 主要依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

例: requirements.txt（プロジェクトで管理してください）
```
duckdb
openai
defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）
3. 依存をインストール
   - pip install -r requirements.txt
4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml が存在する場所）に .env を作成すると自動で読み込まれます（ただし自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack ボットトークン（通知を使う場合）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（通知を使う場合）
   - 任意／デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト `INFO`
     - KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

5. DuckDB ファイル（および監査 DB）ディレクトリを作る
   - デフォルトでは data/ 以下に作成されます。必要なら手動で作成してください。

---

## 使い方（代表的な例）

以下は Python REPL / スクリプトからの利用例です。各関数はルックアヘッドを避けるため明示的な target_date を受け取ります。

- 基本設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)   # Path オブジェクト
print(settings.is_live)
```

- DuckDB 接続を開く（ETL / AI / Research に共通で使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（市場カレンダー / 株価 / 財務 / 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日（内部で調整）
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成（OpenAI API キーは env OPENAI_API_KEY、または api_key 引数で指定）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))  # 該当日のニュースウィンドウを処理
print(f"written scores: {n_written}")
```

- 市場レジームを判定して market_regime テーブルに書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 監査ログスキーマの初期化（監査専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を用いて order/signals の永続化処理を行う
```

- OpenAI API キーの指定
  - 環境変数 `OPENAI_API_KEY` を設定するか、score_news / score_regime の api_key 引数で直接渡してください。  
  - LLM 呼び出しは内部でリトライやエラーハンドリングを実施します。API 失敗時はフェイルセーフ（スコア 0.0 など）で継続する設計です。

---

## 重要な注意点 / 動作方針

- ルックアヘッドバイアス防止:
  - モジュールの多くは内部で date.today() を直接参照しません。必ず明示的な target_date を渡すか、run_daily_etl のようなエントリポイントで日付を調整します。
- 環境変数の自動読み込み:
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動で読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト向け）。
- OpenAI や J-Quants API の呼び出しはレート制御・リトライ・トークンリフレッシュ等のロジックが組み込まれていますが、API 利用制限やコストはユーザー側で管理してください。
- DuckDB の executemany は空リストを受け付けない制約を考慮したコードになっています（一部の関数で事前判定あり）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージの主要なファイル構成（src/kabusys）です。

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NPL スコアリング（OpenAI）
    - regime_detector.py  — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得 + 保存）
    - pipeline.py              — ETL パイプライン（run_daily_etl など）
    - etl.py                   — ETLResult 再エクスポート
    - news_collector.py        — RSS 取得・前処理・raw_news 保存（SSRF 対策）
    - calendar_management.py   — 市場カレンダー管理（トレード日判定等）
    - stats.py                 — 統計ユーティリティ（zscore）
    - quality.py               — データ品質チェック
    - audit.py                 — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py       — Momentum / Value / Volatility 等の計算
    - feature_exploration.py   — 将来リターン計算・IC・summary・rank

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートが正しく検出されているか確認してください（.git または pyproject.toml が存在するディレクトリ）。自動ロードを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認。
- OpenAI 呼び出しでパースエラーが出る
  - 本ライブラリは JSON Mode を使い厳密な JSON 応答を期待しますが、LLM 応答の揺らぎにはフォールバックロジックがあります。テスト時は該当モジュールの _call_openai_api をモックしてください。
- J-Quants の認可エラー（401）
  - jquants_client は 401 を検出するとリフレッシュトークンで再取得を試みます。環境変数 JQUANTS_REFRESH_TOKEN を確認してください。

---

## 貢献ガイド（簡易）

- 新機能や修正は feature ブランチを作成して Pull Request を送ってください。
- テストは各モジュールの外部 API 呼び出しをモックして行ってください（モジュール内で差し替え可能なフックが多数用意されています）。
- API キーや本番設定はリポジトリに含めないでください。必ず .env（.env.local）で運用してください。

---

もし README に追加したい具体的な使用例（ETL スケジュール例、Slack 通知のサンプル、kabuステーション発注フローの説明など）があれば、用途に応じたセクションを追記します。必要なサンプルや .env.example の内容を指示してください。