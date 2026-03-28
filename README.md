# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、マーケットカレンダー管理、監査ログ（発注／約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価（日足）、財務、マーケットカレンダーを差分取得・保存（ページネーション対応、冪等保存）
  - run_daily_etl を中心とした日次 ETL パイプライン（品質チェック付き）
- データ品質チェック
  - 欠損、重複、日付不整合、株価スパイク検出（quality モジュール）
- ニュース収集・前処理
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、gzip 対応）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - マクロニュース + ETF MA200 乖離を統合した「市場レジーム判定」（score_regime）
  - OpenAI の JSON モード（gpt-4o-mini）を使用、リトライ・フェイルセーフ実装
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算（research パッケージ）
  - 将来リターン、IC（Spearman）、統計サマリー等のユーティリティ
- カレンダー管理
  - JPX カレンダーの差分更新、営業日判定、next/prev_trading_day 等のユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化（冪等）
  - 監査用 DB 初期化ユーティリティ（init_audit_db / init_audit_schema）
- 設定管理
  - .env / 環境変数読み込み（自動ロード、上書きルール、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）

---

## 必要条件

- Python 3.10+
- DuckDB（Python パッケージ）: duckdb
- OpenAI Python SDK（OpenAI を利用する機能を使う場合）: openai
- defusedxml（RSS パースの安全対策）
- （任意）その他ネットワークアクセスが必要（J-Quants API、RSS、OpenAI）

pip 例:
```
pip install duckdb openai defusedxml
```

（実運用では requirements.txt / poetry 等で依存を固定してください）

---

## 環境変数（必須 / 任意）

主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。
- KABU_API_PASSWORD (必須)  
  kabuステーション API を使う場合のパスワード。
- SLACK_BOT_TOKEN (必須)  
  Slack 通知に使うボットトークン。
- SLACK_CHANNEL_ID (必須)  
  Slack のチャンネル ID。
- OPENAI_API_KEY (必須 — news_nlp / regime_detector を利用する場合)  
  OpenAI API キー。score_news / score_regime は引数で明示的にキーを渡すこともできます。
- DUCKDB_PATH (任意)  
  DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)  
  監視用途などの SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意)  
  development / paper_trading / live のいずれか（デフォルト development）
- LOG_LEVEL (任意)  
  DEBUG/INFO/WARNING/ERROR/CRITICAL

自動で .env / .env.local をプロジェクトルートから読み込みます（.git または pyproject.toml を探します）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=yourpassword
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローン
2. 仮想環境を作成して有効化（推奨）
3. 依存ライブラリをインストール
   - 例: pip install -r requirements.txt
   - あるいは最低限: pip install duckdb openai defusedxml
4. プロジェクトルートに `.env` を作成し必要な環境変数を設定
5. DuckDB 用のデータディレクトリを作成（必要に応じて）
   - 例: mkdir -p data

---

## 使い方（主要なユースケース）

以下はライブラリをインポートして利用する基本例です。実行は Python スクリプトや CLI から行ってください。

- DuckDB 接続を作る（例: ETL 実行）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントをスコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY か引数で渡す）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を渡すことも可
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査テーブルに書き込み・照会が可能
```

- ファクター計算／リサーチ例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(factors, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

注意点:
- OpenAI や J-Quants など外部 API 呼び出しには適切な API キーが必要です。
- score_news / score_regime は API エラー時にフォールバックロジックを持ちますが、API 呼び出し回数やコストに注意してください。
- テスト時は各モジュールの内部呼出し（_call_openai_api など）をモックする設計になっています。

---

## 主要なモジュール / ディレクトリ構成

リポジトリの主要な部分（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動ロード、settings オブジェクト（J-Quants トークン等）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント（score_news）
    - regime_detector.py — マクロ + MA200 を用いた市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult の再エクスポート
    - calendar_management.py— マーケットカレンダー管理（営業日判定等）
    - news_collector.py     — RSS 収集ロジック（SSRF 対策、正規化、保存）
    - quality.py            — データ品質チェック
    - stats.py              — zscore_normalize など統計ユーティリティ
    - audit.py              — 監査ログテーブル定義・初期化（init_audit_db 等）
  - research/
    - __init__.py
    - factor_research.py    — momentum / volatility / value 等の計算
    - feature_exploration.py— 将来リターン/IC/統計サマリーなど
  - research/、ai/、data/ は外部 API によらないロジックも多く、バックテストや研究用途に適しています。

---

## テスト・開発メモ

- OpenAI 呼び出し部分（news_nlp._call_openai_api や regime_detector._call_openai_api）はテスト時にモックしやすい設計です。unittest.mock.patch を使って差し替えてください。
- config.py はプロジェクトルート（.git または pyproject.toml）を起点に .env を自動読み込みします。CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードをオフにすることを検討してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で空チェックが入っています（互換性考慮）。

---

## 運用上の注意

- J-Quants の API レート制限 (120 req/min) を尊重してください（jquants_client._RateLimiter が補助します）。
- OpenAI の利用はコストが発生します。バッチサイズ・モデル選択に注意してください（news_nlp は銘柄をチャンクして送信）。
- 監査ログは削除しない前提（トレーサビリティ重要）。スキーマ変更時は注意して運用してください。
- 本ライブラリは Look-ahead Bias を避ける設計方針があり、内部関数は date を引数で受け取るなどの配慮があります。バックテスト用途で利用する場合はこの方針に沿って使用してください。

---

## 参考・補足

- 各関数・モジュールに詳細な docstring（日本語）が付与されています。実装の意図や設計上の注意はそちらを参照してください。
- 追加の運用ツール（CLI、スケジューラ連携、監視）などはプロジェクト側で別途実装してください。README にない運用上の手順が必要な場合は環境・要件に合わせて追記してください。

---

問題や改善提案、特定の利用シナリオ（例えば ETL を Airflow に組み込む方法、OpenAI のプロンプト調整、監査スキーマ拡張など）があれば、用途に合わせて README を拡張します。必要な例や手順があれば教えてください。