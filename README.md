# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント解析）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（注文→約定のトレース）など、運用に必要な主要機能をモジュール化して提供します。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local / OS 環境変数から自動読み込み（優先順: OS > .env.local > .env）
  - 必須設定未指定時は明示的エラー

- データ ETL（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX カレンダーの差分取得
  - レートリミット対応、トークン自動リフレッシュ、リトライ（指数バックオフ）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集
  - RSS フィード収集、前処理、トラッキングパラメータ削除、SSRF 対策
  - raw_news / news_symbols への冪等保存

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（ai_scores へ書込み）
  - レート制限・API エラー時のリトライ、レスポンスバリデーション

- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70% 重み）とマクロニュース LLM センチメント（30%）を合成
  - bull / neutral / bear を日次で算出・保存

- リサーチ（Factor / Feature exploration）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z-score 正規化

- データ品質チェック
  - 欠損、重複、前日比スパイク、日付不整合の検出と QualityIssue レポート

- 監査ログ（Audit）
  - signal → order_request → execution の階層的トレーサビリティ用テーブル群
  - DuckDB に監査用 DB を初期化するユーティリティ

---

## セットアップ手順

※環境やパッケージ管理ツールに応じて読み替えてください。

1. Python バージョン
   - Python 3.10+ を推奨（型注釈で union | None 等を使用）

2. リポジトリをクローン / インストール
   - 開発時（editable install）
     ```
     git clone <repo-url>
     cd <repo>
     pip install -e .
     ```
   - または依存パッケージを直接インストール：
     ```
     pip install duckdb openai defusedxml
     ```
   - （必要に応じて他の依存を追加してください）

3. 環境変数 / .env
   - プロジェクトルート（pyproject.toml または .git のあるフォルダ）に `.env` / `.env.local` を配置できます。
   - 自動読み込みはデフォルトで有効。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な必須環境変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=（J-Quants リフレッシュトークン）
   KABU_API_PASSWORD=（kabuステーション API パスワード）
   SLACK_BOT_TOKEN=（Slack Bot トークン）
   SLACK_CHANNEL_ID=（Slack チャネルID）
   OPENAI_API_KEY=（OpenAI API キー）  # score_news / score_regime 実行時に必要
   ```

   オプション（デフォルトあり）:
   ```
   KABUSYS_ENV=development|paper_trading|live  # default=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb           # settings.duckdb_path によって Path が返る
   SQLITE_PATH=data/monitoring.db
   KABUSYS_DISABLE_AUTO_ENV_LOAD=1            # 自動.envロードを無効化（テスト用）
   ```

4. DuckDB（ローカル DB）
   - `duckdb` パッケージをインストールすればファイル DB を即利用可能です。
   - 監査ログ専用 DB を初期化するには後述の API を使用します。

---

## 使い方（基本的な例）

以下は Python REPL / スクリプト内での利用例です。

- DuckDB 接続の準備
```python
import duckdb
from kabusys.config import settings

# ファイルパスは settings.duckdb_path を利用
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（J-Quants から差分取得→保存→品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date=None で今日が対象
print(result.to_dict())
```

- ニュースのセンチメントスコア付与（前日15:00〜当日08:30 JST のウィンドウ）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み銘柄数が返る
```

- 市場レジームスコア算出
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
# audit_conn は初期化済みの DuckDB 接続
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- デバッグ / テスト用: 自動 .env ロードを無効化
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -m pytest
```

---

## 設定と動作ポリシー（重要メモ）

- Look-ahead バイアス防止
  - 多くのモジュールは内部で `date` / `target_date` を明示的に受け取り、`datetime.today()` を直接参照しない設計です。バックテストでの使用時は必ず適切な target_date を渡してください。

- OpenAI / J-Quants API エラー対策
  - 429、タイムアウト、ネットワークエラー、5xx 等はリトライ（指数バックオフ）で再試行しますが、最終的に失敗した場合は安全側のフォールバック（例: macro_sentiment=0.0）を採ります。API キーは安全に保管してください。

- .env のパース
  - `.env` のパーサはクォート、export プレフィックス、コメント等に対応しています。`.env.local` は `.env` を上書きする目的で使用できます（OS 環境変数は保護されます）。

---

## ディレクトリ構成

プロジェクトの主要なファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                            # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                         # ニュースセンチメント → ai_scores
    - regime_detector.py                  # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                   # J-Quants API クライアント + 保存関数
    - pipeline.py                         # 日次 ETL パイプライン（run_daily_etl 等）
    - etl.py                              # ETLResult 再エクスポート
    - news_collector.py                    # RSS 収集・前処理
    - calendar_management.py              # 市場カレンダー管理 / 営業日判定
    - quality.py                          # データ品質チェック
    - stats.py                            # zscore_normalize 等
    - audit.py                            # 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py                  # Momentum / Value / Volatility 等
    - feature_exploration.py              # forward returns, IC, summary, rank

（上記以外に strategy / execution / monitoring 等のパッケージインターフェースが想定されています。パッケージ __all__ は kabusys/__init__.py で定義）

---

## よくある質問 / トラブルシューティング

- Q: .env が読み込まれない / テストで環境を隔離したい  
  A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます。

- Q: OpenAI の応答が想定 JSON で返ってこない（パースエラー）  
  A: モジュールはパース失敗時に警告ログを出してそのコードをスキップ（またはデフォルト値）します。レスポンスの安定化のため温度を 0 に固定し JSON Mode を使用していますが、LLM の振る舞いに依存するためログを確認してください。

- Q: DuckDB の executemany で空リストエラーが出る  
  A: 一部 DuckDB バージョンでは executemany に空リストが渡せないため、コード内で空チェックを行っています。呼び出し側で空の場合の処理を検討してください。

---

## セキュリティ上の注意

- API キー・トークンは必ず適切に管理してください（CI に平文で置かない、必要があれば Vault 等を使用）。
- news_collector は SSRF 対策やレスポンス上限等を実装していますが、外部フィードの扱いには注意してください。
- 監査ログには取り消せないトレースが残る想定のため、アクセス制御を適切に行ってください。

---

この README はライブラリの概要と基本的な使い方を示したものです。より詳細な設計方針・データスキーマ・運用手順はソース内の docstring（各モジュールの先頭コメント）を参照してください。必要であればサンプルスクリプトや運用ガイド（デプロイ・監視）を別途用意できます。