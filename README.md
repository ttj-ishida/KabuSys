# KabuSys

日本株向けの自動売買 / データパイプラインライブラリです。本リポジトリはデータ収集（J-Quants）、データ品質チェック、特徴量/ファクター計算、ニュースNLP と LLM を用いたスコアリング、監査ログ（発注トレース）、市場レジーム判定などを含むモジュール群を提供します。

主な用途
- データプラットフォーム（株価・財務・カレンダー）の差分ETL
- ニュース記事の収集・前処理・LLMによるセンチメントスコア化
- 銘柄ファクターの計算（モメンタム、バリュー、ボラティリティ等）
- 市場レジーム判定（MA と マクロニュースの合成）
- 発注→約定の監査ログスキーマ（DuckDB）

---

## 機能一覧

- 環境変数 / .env の読み込み・管理（kabusys.config）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）
- データ ETL（kabusys.data.pipeline）
  - J-Quants から差分取得（prices / financials / market_calendar）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（refresh_token → id_token）・ページネーション・レートリミット・リトライ
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、SSRF/サイズ制限対策
- データ品質チェック（kabusys.data.quality）
- 市場カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後の営業日探索、夜間更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化
- AI（kabusys.ai）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI 呼び出しは gpt-4o-mini を想定、JSON モードでの厳密なパースとリトライ実装
- 研究用モジュール（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 汎用統計ユーティリティ（kabusys.data.stats）

---

## 動作要件（推奨）

- Python 3.10+
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（openai） — AI スコアリングを使う場合
- defusedxml — RSS パース時の安全対策
- （任意）その他標準ライブラリのみで動作する箇所も多いです

例（仮想環境でのインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発環境ならパッケージを編集可能にインストール
pip install -e .
```
（requirements.txt / pyproject.toml がある場合はそれに従ってください）

---

## 環境変数 / 設定

kabusys.config.Settings で使用される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視用など）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト "development"）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト "INFO"）
- OPENAI_API_KEY — OpenAI 呼び出しに使用（news_nlp / regime_detector の引数 api_key を省略する場合に参照）

自動 .env 読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を起点）を探索し、`.env` → `.env.local` の順で自動読み込みします。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url> kabusys
   cd kabusys
   ```

2. 仮想環境の作成と依存パッケージのインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   pip install -e .
   ```

3. 環境変数を用意
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を作成してください。
   - 例（.env.example を参考に）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします（テスト時など）。

4. DuckDB データベースの準備
   - デフォルトでは `data/kabusys.duckdb` を使います。必要に応じて `settings.duckdb_path` を書き換えるか、環境変数 `DUCKDB_PATH` を設定してください。
   - 監査ログ専用 DB を初期化する例は下記「使い方」を参照。

---

## 使い方（主要な例）

以下は Python REPL / スクリプトから呼ぶ最低限のサンプルです。時間やターゲット日付は用途に合わせて指定してください（内部処理は look-ahead バイアスを避ける設計になっています）。

基本準備:
```python
import duckdb
from kabusys.config import settings

# デフォルト DuckDB ファイルに接続
conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL を実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

監査ログスキーマを初期化（監査専用 DB を作る例）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は UTC タイムゾーン設定を行い、DDL を作成します
```

ニュース記事のスコア（AI）を付与:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY から取得されます（api_key 引数で上書き可）
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"Wrote scores for {written} codes")
```

市場レジーム判定（MA200 + マクロニュース）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

# api_key 引数で OpenAI キーを渡すこともできます
score_regime(conn, target_date=date(2026, 3, 20))
```

ファクター計算・研究用ユーティリティ:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
fwd = calc_forward_returns(conn, target)
# IC 例（mom_1m と fwd_1d の関連）
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
```

ニュース RSS を個別にフェッチ（news_collector.fetch_rss）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["title"], a["datetime"])
```

ログレベルや環境は `KABUSYS_ENV` / `LOG_LEVEL` で制御します。

---

## ディレクトリ構成（主要ファイル）

主要なパッケージ構成は以下の通りです（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースの LLM スコアリング、JSON mode + バッチ処理
    - regime_detector.py    — MA200 と マクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult の再エクスポート
    - news_collector.py     — RSS 収集・前処理・保存支援
    - calendar_management.py— 市場カレンダー管理（営業日判定・更新ジョブ）
    - quality.py            — データ品質チェック
    - audit.py              — 監査ログスキーマ初期化
    - stats.py              — 汎用統計ユーティリティ（zscore 正規化等）
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility の計算
    - feature_exploration.py— 将来リターン, IC, 統計サマリ, rank 等

（上記以外に strategy / execution / monitoring 等のトップレベル要素が今後含まれる想定。パッケージ __all__ はこれらを公開しています）

---

## 開発上の注意 / 設計ポリシー（抜粋）

- ルックアヘッドバイアス回避: モジュールの多くは内部で datetime.today()/date.today() を直接参照せず、必ず target_date を外部から与える設計になっています。
- 冪等性: DuckDB への保存は可能な限り ON CONFLICT（UPSERT）で実装されています。
- フェイルセーフ: AI / API 呼び出し失敗時は多くの箇所でフォールバック（例: スコア=0.0）して処理継続を優先します。
- セキュリティ: RSS 取得時の SSRF 対策、XML パースの defusedxml 利用、レスポンスサイズチェック等の防御実装あり。
- リトライ/レート制御: J-Quants クライアントはレートリミット（固定間隔スロットリング）・リトライ・401 の自動リフレッシュ等を実装しています。

---

## トラブルシューティング

- 環境変数が見つからない場合は `kabusys.config.Settings` が ValueError を投げます。`.env` を正しく作成したか、KABUSYS_DISABLE_AUTO_ENV_LOAD を誤って設定していないか確認してください。
- OpenAI 呼び出しで JSON パースエラーが出るとそのチャンクはスキップされ、ログに警告が残ります。API キーやモデル指定を確認してください。
- DuckDB に関するエラーはスキーマ不整合やファイルパーミッションが原因のことが多いです。ログと SQL を確認してください。

---

## ライセンス・貢献

本 README にはライセンス情報が含まれていません。実際の運用や公開の際は LICENSE を追加して運用ルールを明記してください。機能追加やバグ修正は Pull Request を歓迎します。貢献前に issue で計画を相談してください。

---

以上がこのコードベースの概要と使い方のまとめです。実行例や追加のヘルプが必要であれば、どの操作（ETL・ニューススコアリング・監査DB初期化など）について詳しく知りたいか教えてください。