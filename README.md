# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）→ 品質チェック → 特徴量計算 → AI ニュース判定 → 監査ログ／発注までを想定したモジュール群を提供します。

主な設計方針は以下の通りです。
- ルックアヘッドバイアスを防ぐ（内部で datetime.today() を不用意に参照しない等）
- DuckDB を中心としたローカルデータ管理と冪等的保存
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを組み込む
- テスト可能性を重視した設計（API 呼び出し箇所を差し替え可能）

---

## 機能一覧

- データ取得（J-Quants API）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダー等の差分取得・保存（jquants_client）
  - 固有のレートリミッタ／リトライ／トークンリフレッシュ実装

- ETL パイプライン（data.pipeline）
  - run_daily_etl によりカレンダー → 株価 → 財務 → 品質チェックを一括実行
  - 差分取得、バックフィル、品質チェック（quality）をサポート

- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合などを検出・報告

- ニュース収集（data.news_collector）
  - RSS からの安全なニュース取得（SSRF 対策、サイズ上限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存を想定

- AI 評価（ai.news_nlp / ai.regime_detector）
  - ニュースを LLM（gpt-4o-mini 等）で銘柄ごとにセンチメント付与（score_news）
  - マクロセンチメント + ETF (1321) の MA200 乖離を合成して市場レジーム判定（score_regime）
  - OpenAI 呼び出しは JSON mode を使い、堅牢にパース／リトライする

- 研究用ユーティリティ（research）
  - モメンタム・バリュー・ボラティリティ等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ等

- 監査ログ（data.audit）
  - signal → order_request → execution のトレーサビリティテーブル定義・初期化ユーティリティ
  - init_audit_db / init_audit_schema により DuckDB に監査スキーマを作成

- 汎用統計ユーティリティ（data.stats）
  - Z スコア正規化など

---

## 動作要件 (推奨)

- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- その他: 標準ライブラリを多用（urllib, json, datetime など）

インストールはプロジェクトに requirements.txt がある場合それを使うか、最低限以下を入れてください。
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（実運用では lock ファイルや extras を用意して下さい）

---

## 環境変数（必須 / 任意）

このライブラリは環境変数／.env を読み込んで設定を取得します（プロジェクトルートに `.git` または `pyproject.toml` がある場合、自動で `.env` / `.env.local` を読み込みます）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL の認証に使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）

その他（デフォルトあり）:
- KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）
- KABUS_API_BASE_URL: kabus API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）

.env の読み込み優先度:
- OS 環境変数 > .env.local > .env
（.env.local は .env をオーバーライドします）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（例: pip install -r requirements.txt / または個別インストール）
4. プロジェクトルートに `.env` を作成し必要な環境変数を設定
   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```
5. DuckDB の保存先ディレクトリを作成（例: data/）
6. （任意）監査 DB を初期化:
   ```py
   from kabusys.data.audit import init_audit_db
   from kabusys.config import settings
   conn = init_audit_db(settings.duckdb_path)  # または別パス
   ```

---

## 使い方（基本的な例）

以下はライブラリの代表的な使い方例です。実運用ではエラー処理・ログ設定を行ってください。

- DuckDB に接続して日次 ETL を実行する:
```py
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを生成（score_news）:
```py
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジームをスコアリング（score_regime）:
```py
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算:
```py
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
```

- 監査スキーマ初期化（別 DB に作る場合）:
```py
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

注意:
- AI 関連 API（OpenAI）を利用するためには有効な API キーと利用可能なモデルのアクセス権が必要です。
- J-Quants の API 呼び出しはレート制限に従います。大量リクエスト時は注意してください。

---

## 主要モジュール / ディレクトリ構成

（ソース: src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # ニュースを LLM でスコアリングするロジック
    - regime_detector.py    # マクロセンチメント + MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント（fetch/save）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - etl.py                # ETL 結果型 ETLResult の再公開
    - news_collector.py     # RSS 収集（SSRF 対策・正規化等）
    - quality.py            # データ品質チェック
    - calendar_management.py# 市場カレンダー管理と営業日判定
    - stats.py              # 汎用統計（zscore_normalize 等）
    - audit.py              # 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py    # Momentum/Value/Volatility 計算
    - feature_exploration.py# 将来リターン・IC・統計サマリ
  - research/ (submodules exported accordingly)
  - その他ユーティリティ類

（上記は現行コードベースの主なファイル一覧です）

---

## 設計上の注意点・運用メモ

- ルックアヘッドバイアス回避のため、関数は内部で現在日時を直接参照せず、外部から target_date を渡す設計です。バックテストや再現性の確保に有利です。
- J-Quants / OpenAI 呼び出しにはリトライやバックオフを実装していますが、API コストやレートに注意してください。
- news_collector は RSS の取得時に SSRF・ZIP bomb 等の対策（ホスト検査、サイズ上限、gzip 解凍サイズチェック）を含みます。
- DuckDB の executemany は空リストを受け付けないバージョンの互換性を考慮した実装がなされています（空チェックを行っています）。
- 自動 .env 読み込みは project root（.git または pyproject.toml を探索）を基準に行います。CI やテスト時には環境変数を直接注入するか、`KABUSYS_DISABLE_AUTO_ENV_LOAD` を使って自動ロードを無効化してください。

---

## ライセンス / 貢献

この README はコードベースのドキュメント例です。実際のライセンス情報・貢献ガイドラインはリポジトリの LICENSE / CONTRIBUTING.md を参照してください。

---

不明点や README に追加したい具体的なコマンド例（Docker Compose、systemd ジョブ、CI 設定など）があれば知らせてください。必要に応じて追記します。