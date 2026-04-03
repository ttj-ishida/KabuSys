# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群（KabuSys）。  
ETL、データ品質チェック、ニュースセンチメント（LLM）評価、マーケットレジーム判定、ファクター計算、監査ログなど、トレーディング・リサーチに必要な主要コンポーネントを提供します。

主な設計方針:
- DuckDB を中心としたオンプレ／ローカル検証向けデータ基盤
- Look-ahead bias を避けるための日付設計（内部で date.today()/datetime.today() を直接参照しない）
- 冪等性（ETL や DB 書き込みは ON CONFLICT / DELETE→INSERT などで安全に）
- 外部 API（J-Quants / OpenAI / kabuステーション 等）への堅牢な呼び出し（レート制御・リトライ・フェイルセーフ）
- モジュール単位でテスト容易性を意識した分離設計

## 機能一覧
- データ ETL
  - J-Quants から株価（日次OHLCV）、財務情報、上場銘柄・マーケットカレンダーの差分取得・保存
  - 差分取得・バックフィル・ページネーション・トークン管理・レートリミット対応
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合（未来日・非営業日データ）検出
- ニュース収集
  - RSS 取得 → 前処理 → raw_news / news_symbols への冪等保存
  - SSRF 防止・サイズ制限・トラッキングパラメータ除去等の安全対策
- ニュース NLP（LLM）
  - 銘柄ごとのニュース統合センチメント（gpt-4o-mini を想定）を ai_scores に書き込む
  - バッチ処理・チャンク化・リトライ・レスポンス検証
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離 と マクロニュースセンチメント を合成して日次レジーム判定（bull/neutral/bear）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（情報係数）や統計サマリ機能、Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査用テーブル定義と初期化ユーティリティ（DuckDB）
  - 発注トレーサビリティのための UUID ベース階層設計
- 設定管理
  - .env/.env.local と環境変数から設定を自動ロード（プロジェクトルート検出）
  - 必須設定の取得ユーティリティ（kabusys.config.settings）

## 前提・依存関係
（実際のパッケージ配布に合わせて適宜調整してください）

- Python 3.10+（typing の union 型などを使用）
- 必要なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib, json 等）

例（開発環境でのインストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# パッケージとしてインストールする場合
pip install -e .
```

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 環境を準備（仮想環境推奨）
3. 依存パッケージをインストール（上記参照）
4. 環境変数の準備
   - プロジェクトルートに `.env`（および開発専用 `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

必須となる主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（実行系で使用）
- OPENAI_API_KEY: OpenAI（news_nlp / regime_detector で使用）

その他（任意／デフォルトあり）:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB など（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / その他監視閾値

例 `.env`（簡易）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
```

## 使い方（主要な操作例）

以下はライブラリ API を使う簡単な例です。実行前に環境変数や DuckDB のスキーマが適切に用意されていることを確認してください。

- DuckDB 接続の作成:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースセンチメント（LLM）で銘柄ごとのスコアを作成:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数で用意しておく（引数で渡すことも可）
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"written: {n_written}")
```

- 市場レジームの判定（ma200 + マクロニュース）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- ファクター計算（例: モメンタム）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# records: list of dict with keys date, code, mom_1m, mom_3m, mom_6m, ma200_dev
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 設定取得:
```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)  # KABUSYS_ENV が 'live' のとき True
```

注意点:
- OpenAI を呼ぶ関数（news_nlp.score_news, regime_detector.score_regime）は API キーを必要とします。環境変数 `OPENAI_API_KEY` または引数 `api_key` を渡してください。
- ETL、ニュース収集、AI 呼出しは外部 API を使用するため、API 利用料やレート制限に注意してください。
- DuckDB のテーブルスキーマは実行するモジュールごとに前提があるため、初期化手順やマイグレーションが必要な場合があります（スキーマ定義は data/audit などのモジュールで生成可能）。

## ディレクトリ構成（主要ファイル）
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースセンチメント（LLM）関連
    - regime_detector.py     -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント + 保存処理
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETL 結果型の再エクスポート
    - news_collector.py      -- RSS 収集
    - calendar_management.py -- JPX カレンダー管理 / 営業日ロジック
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore など）
    - audit.py               -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     -- Momentum / Value / Volatility 等
    - feature_exploration.py -- 将来リターン / IC / summary / rank
  - ai, data, research 以下にそれぞれの実装ファイルが存在します

（上記は主要モジュールの抜粋です。実際のツリーはリポジトリを参照してください。）

## 補足 / 開発時メモ
- 自動 .env ロード
  - パッケージロード時にプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動で読み込みます。
  - 自動ロードを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
- テスト時の差し替え
  - OpenAI 呼出しなどは内部で小さなラッパー関数を使っているため、unit test で差し替え（patch）しやすく設計されています。
- 安全設計
  - news_collector は SSRF 防止、XML パースの安全化（defusedxml）、レスポンスサイズ制限などを行っています。
  - jquants_client はレートリミットを守る RateLimiter、401 時のトークン自動リフレッシュ、リトライロジックを実装しています。

---

上記はこのコードベースの主要な使い方と構成のサマリです。詳細な API の振る舞いや DB スキーマ（テーブル定義）は各モジュール（data/*, ai/*, research/*）のドキュメント／ソース内コメントを参照してください。必要があれば README に追加すべき具体的な使用例や運用手順（cron / systemd / コンテナ化など）について追記します。