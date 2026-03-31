CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
安定化・改良・仕様はコードベースから推測して記載しています。

Unreleased
----------
- なし（初回リリース: 0.1.0）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース "kabusys" を追加。
  - パッケージメタ情報: __version__ = "0.1.0"、公開モジュール: data, strategy, execution, monitoring。
- 環境設定管理モジュールを追加（kabusys.config）。
  - .env ファイルまたは環境変数から自動的に設定値を読み込む機能を実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーは次の特徴を持つ:
    - 空行・コメント行（#）／export KEY=val 形式の対応。
    - シングル・ダブルクォート内のバックスラッシュエスケープ処理。
    - クォート無し値の行内コメント判定（直前が空白/タブの場合にコメントとみなす）。
  - OS 側の既存環境変数を保護する protected 機構（上書き制御）。
  - 必須環境変数未設定時に ValueError を投げる _require ユーティリティ。
  - Settings クラスで主要設定を公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルトあり)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（Path を返す）
    - KABUSYS_ENV 値検証 (development/paper_trading/live)
    - LOG_LEVEL 値検証（DEBUG/INFO/...）
    - is_live / is_paper / is_dev の便宜プロパティ
- AI 関連モジュールを追加（kabusys.ai）。
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）でバッチセンチメント評価。
    - JST ベースのタイムウィンドウ計算 (前日15:00〜当日08:30 を UTC に変換)。
    - バッチサイズ、1銘柄あたりの最大記事数/文字数トリム、JSON mode による応答処理。
    - 429/ネットワークエラー/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、コード整合性、数値チェック）。
    - スコアは ±1.0 にクリップ。DuckDB への書き込みは部分置換（DELETE→INSERT）で冪等性を確保。
    - テスト容易性のため OpenAI 呼出しを差し替え可能に設計（_call_openai_api を patch 可能）。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）判定。
    - prices_daily と raw_news を参照し、結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しに対するリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0 にフォールバック）。
    - LLM 呼び出しは news_nlp と独立した内部実装でモジュール結合を緩和。
- データプラットフォーム関連モジュールを追加（kabusys.data）。
  - calendar_management:
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバック（週末判定）を行う一貫したロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新する夜間バッチの骨子（バックフィル・健全性チェック備え）。
  - pipeline / ETL:
    - ETLResult データクラスを追加（ETL 実行結果の集約: 取得数・保存数・品質問題・エラー等）。
    - ETL の差分更新、バックフィル、品質チェック設計方針を反映（実装の骨子）。
  - ETL 周りの内部ユーティリティ（テーブル存在チェック、最大日付取得、トレーディング日調整等）。
- 研究用モジュールを追加（kabusys.research）。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務データを取得し PER/ROE を計算。
    - DuckDB SQL を主体にして外部 API には依存しない実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンに対する将来リターンを一度のクエリで取得する汎用実装（horizons の検証あり）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（欠損/非有限値を除外、最小レコード数チェック）。
    - rank: 同順位は平均ランクとするランク付け実装（浮動小数点丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - data.stats の zscore_normalize を再エクスポート（research パッケージ __init__ で公開）。
- DuckDB に関する互換性考慮を実装。
  - executemany に空リストを渡せない（DuckDB 0.10 の制約）ことをハンドリングしたガードを導入。
- ロギングと防御的実装。
  - 各処理で詳細な logger 呼び出しを追加（info/debug/warning/exception）。
  - ルックアヘッドバイアス回避のため date.today()/datetime.today() を直接参照しない設計を明示的に採用（target_date を引数として受け取る）。

Changed
- （初回リリースのため「変更」はなし。上記は新規追加機能の説明。）

Fixed
- （初回リリースのため「修正」はなし。ただし過去の設計上の注意点や、エラー耐性を高める実装（例: API エラーの status_code 取扱い、安全な JSON 抽出、ROLLBACK の二重例外処理など）を反映。）

Security
- 必須の秘密情報（OpenAI APIキー, J-Quants トークン, kabu API パスワード, Slack トークン等）は Settings から取得し、未設定時に例外を発生させることで誤動作を防止。

Notes / Implementation Details
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を想定しているが、万一の余分なテキスト混入に備えて最外の {} を抽出して復元する処理を実装。
- API エラーは 5xx とそれ以外で挙動を分けてリトライ可否を制御。
- 各 AI 関数はテスト容易性を考慮して内部の _call_openai_api を unittest.mock.patch で差し替え可能にしている。
- DB 書き込みは基本的にトランザクション（BEGIN/COMMIT/ROLLBACK）で行い、部分失敗時に他レコードを不必要に上書きしない方式を採用。

今後の予定（推測）
- ETL 実行本体の orchestration（pipeline の上位実装）や jquants_client の具体実装の追加・結合テスト。
- strategy / execution / monitoring モジュールの具現化（現在はパッケージ公開名に含まれるが実体は未掲載）。
- 性能改善（大型 DB クエリの最適化や非同期 API コール）、および詳細なユニットテストの追加。