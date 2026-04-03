# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（発注・約定トレーサビリティ）、リサーチ用ファクター計算などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を含む Python パッケージです。

- J-Quants API を使った株価・財務・カレンダーの差分 ETL（DuckDB へ保存）
- RSS ベースのニュース収集と OpenAI を用いたニュースセンチメントスコアリング
- LLM（OpenAI）と市場指標（ETF 1321 の MA200）を組み合わせた市場レジーム判定
- 研究用のファクター計算・特徴量解析ユーティリティ
- 監査（signal → order_request → execution）用の DB スキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の共通方針として「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API失敗時の継続）」を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（ページネーション・認証・レート制御・リトライ実装）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
  - ニュース収集: fetch_rss / preprocess_text（SSRF 対策・トラッキング除去）
  - データ品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai
  - ニュース NLP スコアリング: score_news（OpenAI を使った銘柄別センチメント）
  - 市場レジーム判定: score_regime（ETF 1321 の MA200 と LLM を合成）
- research
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量解析: calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理
  - 環境変数 / .env 自動ロード（プロジェクトルート検出）および Settings API（kabusys.config.settings）

---

## 前提 / 必要環境

- Python >= 3.10（PEP 604 の union 型などを使用）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- J-Quants リフレッシュトークン（JQUANTS_REFRESH_TOKEN）
- OpenAI API キー（OPENAI_API_KEY） — news_nlp / regime_detector 実行時
- kabu ステーション API パスワード（KABU_API_PASSWORD）等は用途に応じて設定

requirements.txt がある場合はそちらを参照してください。なければ最低限以下を入れてください:

pip install duckdb openai defusedxml

（プロジェクト配布時に正式な requirements を用意してください）

---

## 環境変数 / 設定

Settings は環境変数から値を読み込みます。主要なキー:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携時）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite path（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / その他監視設定
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

自動で .env / .env.local をプロジェクトルートから読み込みます（CWD ではなく __file__ を基準に .git または pyproject.toml を探索）。自動ロードを無効化する場合は:

export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースはシェルライク（export プレフィックス、クォート、コメント対応）です。

---

## セットアップ手順

1. リポジトリをクローン（あるいはパッケージを配置）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存パッケージをインストール
   - pip install -e .    （プロジェクトに setup.cfg / pyproject.toml がある場合）
   - または個別に: pip install duckdb openai defusedxml
4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数をエクスポート
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
5. DuckDB データベース用ディレクトリを作成（自動的に作成することが多いですが確認）
   - mkdir -p data

---

## 使い方（よく使う例）

以下は代表的なユースケースの最小例です。実行前に前述の環境変数を設定してください。

- DuckDB 接続を作る

from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（カレンダー・株価・財務・品質チェックを順に実行）

from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- 個別の ETL ジョブを実行する（例: 株価のみ）

from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
print(f"fetched={fetched}, saved={saved}")

- ニュース NLP スコアリング（OpenAI 必須）

from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None -> 環境変数 OPENAI_API_KEY を使用

- 市場レジーム判定（ETF 1321 の MA200 と LLM を合成）

from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB 初期化（監査専用 DB を用意する場合）

from kabusys.data.audit import init_audit_db
db_conn = init_audit_db("data/audit.duckdb")
# あるいは既存 conn にスキーマ追加:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)

- ファクター計算（研究用）

from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

mom = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

---

## 実装上の注意点 / デザインノート

- ルックアヘッドバイアス防止: モジュール内で datetime.today() / date.today() による自動参照を避け、呼び出し側が target_date を渡す設計になっています（ETL やスコアリング関数は target_date を引数に取ります）。
- 冪等性: J-Quants からの保存は ON CONFLICT DO UPDATE などで冪等保存を行います。
- フェイルセーフ: LLM/API の一時失敗やパースエラー時は例外を投げずにフォールバック（例: スコア 0.0）する箇所が存在します。ログを確認してください。
- テスト容易性: OpenAI 呼び出し部等は内部関数を patch して差し替え可能な設計です（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- .env の自動ロードはプロジェクトルートを .git または pyproject.toml で検出して行います。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / Settings
- ai/
  - __init__.py
  - news_nlp.py                  — ニュース NLP スコアリング
  - regime_detector.py           — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（fetch/save）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETLResult 再エクスポート
  - calendar_management.py       — 市場カレンダー管理
  - news_collector.py            — RSS ニュース収集
  - quality.py                   — データ品質チェック
  - stats.py                     — 統計ユーティリティ（zscore_normalize）
  - audit.py                     — 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py           — モメンタム/バリュー/ボラティリティ
  - feature_exploration.py       — 将来リターン / IC / サマリー
- monitoring/ (未表示: 監視・実行系モジュール等)
- strategy/ (未表示: 戦略実行ロジック等)
- execution/ (未表示: 発注執行ロジック等)

---

## よくある質問 / トラブルシューティング

- OpenAI レスポンスのパースで失敗するケース:
  - モジュールは JSON パース失敗時に安全にフォールバックしますが、出力フォーマットが変わるとスコア取得に失敗します。モデルには SYSTEM PROMPT で厳密な JSON 出力を要求しています（news_nlp / regime_detector の _SYSTEM_PROMPT を参照）。
- J-Quants 認証エラー（401）:
  - jquants_client は 401 受信時にリフレッシュトークンで自動更新して1回リトライします。環境変数 JQUANTS_REFRESH_TOKEN が正しいか確認してください。
- DuckDB の executemany に関する注意:
  - 一部関数で空リストを executemany に渡してはいけない（DuckDB のバージョン依存）。コード内で明示的にチェックしています。

---

## 貢献 / 開発

- 開発用ブランチで機能追加や修正を行い、ユニットテストを追加してください。
- 外部 API 呼び出しのユニットテストではクライアントの呼び出しをモックすることを推奨します（例: OpenAI 呼び出し、urllib リクエスト、_urlopen 等）。

---

必要であれば、README に以下を追記できます:
- インストール用の pyproject.toml / setup.cfg に基づく具体的な pip コマンド
- CI / テストの実行手順（pytest 等）
- サンプル .env.example の内容
- API レート制御やロギング設定の詳細

追記希望があれば教えてください。