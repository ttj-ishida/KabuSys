# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群。  
DuckDB をデータレイヤに、J-Quants / kabuステーション / OpenAI を外部データ・AI に使い、ETL、データ品質チェック、ニュース NLP、市場レジーム判定、研究用ファクター計算、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの株価（OHLCV）・財務データ・マーケットカレンダー取得（ページネーション／リトライ／レート制御）
  - 差分更新・バックフィル対応の日次 ETL パイプライン（run_daily_etl）
- データ品質管理
  - 欠損値・スパイク・重複・日付不整合のチェック（quality モジュール）
- ニュース収集・NLP
  - RSS 取得、前処理、raw_news / news_symbols への保存ロジック（SSRF/サイズ制限/トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント集計（ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF 1321 の 200日 MA 乖離 + マクロニュースセンチメントの混合で日次レジーム判定（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム/バリュー/ボラティリティ等のファクター計算（research）
  - 将来リターン、IC、統計サマリ等の探索ツール
- 監査／トレーサビリティ
  - signal → order_request → executions の監査テーブル定義・初期化（data.audit.init_audit_db / init_audit_schema）
- 設定管理
  - .env 自動ロード（プロジェクトルート検出）と Settings API（kabusys.config.settings）

---

## 必要条件（依存ライブラリ）

主要依存（代表例）:
- Python 3.10+
- duckdb
- openai
- defusedxml

実際のプロジェクトでは pyproject.toml / requirements.txt に記載された依存を参照してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （開発・テスト用にその他の依存がある場合は適宜追加）
4. 環境変数を設定
   - プロジェクトルートに `.env` と `.env.local`（任意）を配置できます。
   - 自動ロードはデフォルトで有効。自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu API パスワード（API 利用時）
   - OPENAI_API_KEY: OpenAI を使う機能を実行する場合（score_news / score_regime）
   - そのほかオプション設定:
     - KABUSYS_ENV (development|paper_trading|live)
     - LOG_LEVEL (DEBUG|INFO|...)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等

例: `.env.example`（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（クイックスタート）

以下は Python REPL / スクリプトからライブラリを使う最小例です。DuckDB のパスは settings.duckdb_path を利用できます。

1) DuckDB 接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクトを返します
conn = duckdb.connect(str(settings.duckdb_path))
# 今日の ETL（target_date を指定して過去日を処理することも可能）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュースの NLP スコア（ai_scores）を生成する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 19))  # target_date を指定
print(f"scored {n_written} symbols")
```
- OpenAI API キーを `OPENAI_API_KEY` 環境変数で指定するか、score_news の api_key 引数で渡します。

3) 市場レジームを判定して market_regime に書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 03, 19))  # API キーは環境変数で
```

4) 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# これで監査テーブル(signal_events, order_requests, executions) が作成されます
```

注意:
- OpenAI の呼び出しはリトライ・フォールバックが実装されていますが、実行時のコスト・レート制限に注意してください。
- テスト時は OpenAI 呼び出しをモックする設計（モジュール関数を patch）になっています。

---

## 設定（Settings）について

kabusys.config.Settings によって以下の値へアクセスできます（主なもの）:
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
- settings.line_channel_access_token / settings.line_user_id
- settings.duckdb_path (Path)
- settings.sqlite_path (Path)
- settings.pid_file_path / settings.kill_flag_path
- settings.env / settings.log_level / settings.is_live など

自動で `.env` / `.env.local` をプロジェクトルートから読み込む仕組みがあります。読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 開発上の注意点

- Look-ahead バイアス対策: ai モジュール・ETL・研究モジュールの多くは datetime.today()/date.today() を直接参照せず、target_date を明示的に渡す設計です。バックテスト等では target_date を必ず指定してください。
- DuckDB の executemany に空リストを渡すと例外になるバージョンがあるため処理部で空チェックが入っています。
- J-Quants API 呼び出しは内部でレート制御（120req/min）とリトライ処理を行います。401 受信時は refresh token による再取得を試みます。
- NewsCollector は SSRF 対策／XML パースの安全化（defusedxml）を行っています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings 管理
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP（score_news）
  - regime_detector.py            — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント / 保存関数
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETL 結果型公開
  - quality.py                    — データ品質チェック
  - stats.py                      — 共通統計ユーティリティ（zscore_normalize）
  - news_collector.py             — RSS 取得 / 前処理
  - calendar_management.py        — マーケットカレンダー管理
  - audit.py                      — 監査ログ初期化・DDL
- research/
  - __init__.py
  - factor_research.py            — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py        — 将来リターン / IC / 統計サマリ等

（その他サブパッケージ: strategy / execution / monitoring が __all__ に含まれていますが、ここに示したのは提供されている主要なデータ・AI・研究モジュールです）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - プロジェクトルート判定は .git または pyproject.toml を基準に行います。配布状況によって検出できない場合は環境変数を直接設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で読み込んでください。
- OpenAI 呼び出しが遅い / レート制限に掛かる
  - バッチで大量の銘柄を送る処理やニュースの多い日には時間がかかることがあります。API キーや使用モデル、バッチサイズ（news_nlp の _BATCH_SIZE）を調整してください。
- DuckDB にスキーマがない / テーブルがない
  - ETL 実行前に schema 初期化処理（プロジェクト側で定義されている場合）を行うか、必要なテーブルが存在することを確認してください。audit.init_audit_db は監査スキーマを作成します。

---

必要があれば README に CLI 利用法・コード例の追加や、.env.example の完全サンプル、テスト実行手順、CI / デプロイ手順なども追記します。どの情報を優先して補足しますか？