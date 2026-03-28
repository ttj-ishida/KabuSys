# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
市場データの ETL、ニュース収集・NLP（LLM）によるセンチメント評価、ファクター計算、監査ログ（発注→約定トレース）などを含み、バックテストや運用パイプラインの構成要素として利用できます。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）および必須環境変数の検証
- データ取得・ETL（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPXマーケットカレンダーの差分取得・保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue を収集）
- ニュース収集
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存想定
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを LLM に送りセンチメントを ai_scores に保存（バッチ・JSON Mode）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM 評価の合成）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - order_request_id による冪等性を考慮した設計

---

## セットアップ手順

1. Python 環境を準備（推奨: Python 3.10+）
   - 仮想環境の作成例:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最低限）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリや他の HTTP モジュールは既に使用）
   例:
   ```
   pip install duckdb openai defusedxml
   ```

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意してください。

3. 環境変数を設定
   - ルートに `.env` / `.env.local` を置くとパッケージ起動時に自動読み込みされます（CWD に依存しないプロジェクトルート検出）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で .env 自動ロードを無効化
     - DUCKDB_PATH（デフォルト `data/kabusys.duckdb`）
     - SQLITE_PATH（デフォルト `data/monitoring.db`）

4. OpenAI API
   - news_nlp / regime_detector の呼び出しには OpenAI API キーが必要です。
     - 環境変数 `OPENAI_API_KEY` をセットするか、関数呼び出し時に `api_key` を渡してください。

---

## 使い方（主要な呼び出し例）

※ ダミー例。実行には適切な DB スキーマ・テーブル準備や API トークンが必要です。

- DuckDB 接続と ETL の実行例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を実行:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY 環境変数を設定済みであれば api_key=None でOK
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジームスコアの計算:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマ初期化（監査用 DB）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って audit テーブルにアクセス可能
```

- RSS フィード取得（ニュース収集の一部）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

---

## 主要 API / モジュール一覧（抜粋）

- kabusys.config
  - settings: 環境設定アクセス（例: settings.jquants_refresh_token）
- kabusys.data
  - pipeline.run_daily_etl: 日次 ETL のエントリポイント
  - jquants_client: API 呼び出し / 保存関数（fetch_* / save_*）
  - quality: データ品質チェック（run_all_checks 等）
  - news_collector: RSS 取得 / 前処理
  - calendar_management: 営業日判定・calendar_update_job
  - audit: 監査ログ DDL と初期化
  - stats: zscore_normalize
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニューススコア取得・ai_scores 書込
  - regime_detector.score_regime: マクロ + MA200 による市場レジーム判定
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank

---

## ディレクトリ構成

（主なファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py (ETL の公開 API 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
    - ...（ファクター・研究用ユーティリティ）
  - ai/
    - ...（LLM 関連）
  - その他: strategy/, execution/, monitoring/（__all__ に名前は出ていますがコードベースに追加実装される想定）

※ 実際のソースは上記ファイルごとに詳細実装があります（ETL、品質チェック、LLM 呼び出し等）。

---

## 運用上の注意 / 設計方針（抜粋）

- Look-ahead bias 回避: 多くの関数で date の扱いが明確にされ、内部で現在日時を勝手に参照しない設計（引数で target_date を受ける）。
- 冪等性: ETL 保存関数は ON CONFLICT DO UPDATE を利用して再実行可能に設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）呼び出し失敗時は適切にログを残し、可能な範囲で処理を継続する。
- セキュリティ: ニュース収集周りは SSRF 対策・XML インジェクション対策（defusedxml）あり。
- テスト容易性: OpenAI 呼び出しや URL オープン関数はモック差替え可能な実装になっています。

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートはこのパッケージのファイル位置から親ディレクトリに .git または pyproject.toml を探して決定します。ルートが見つからない場合自動読み込みはスキップされます。
  - 自動ロードを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。

- OpenAI 呼び出しで失敗する
  - OPENAI_API_KEY を環境変数で設定するか、score_news / score_regime の api_key 引数で渡してください。
  - rate limit やネットワークエラーは内部リトライロジックで扱われますが、API 側の制限に注意してください。

- DuckDB のスキーマがない・テーブルがない
  - ETL 実行前にスキーマ初期化スクリプト（プロジェクト側で管理）を実行する必要があります。監査ログは kabusys.data.audit.init_audit_schema / init_audit_db で初期化できます。

---

必要に応じて README に追加したい内容（例: 環境変数の .env.example、テストの実行手順、CI の設定、具体的な SQL スキーマ定義やサンプルデータのロード手順等）があれば教えてください。README を拡張して具体例やコマンドを追記します。