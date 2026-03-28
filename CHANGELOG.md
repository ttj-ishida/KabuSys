# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回リリース。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化 (src/kabusys/__init__.py) とバージョン定義 __version__ = "0.1.0" を追加。
  - 公開サブパッケージ: data, research, ai, その他の基盤モジュール群を整理してエクスポート。

- 環境設定 / config (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする仕組みを実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export プレフィックス、クォート（シングル/ダブル）およびエスケープ、行内コメントの取り扱いに対応。
  - OS 環境変数を保護する protected な上書き処理を実装（.env.local は override=True）。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス等の設定を型付きプロパティとして提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須とする _require() を実装。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを提供。
    - KABUSYS_ENV の検証（development / paper_trading / live）および LOG_LEVEL の検証を実装。
    - is_live / is_paper / is_dev の補助プロパティを追加。

- AI モジュール (src/kabusys/ai)
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算のユーティリティ calc_news_window を提供。
    - バッチサイズ、トークン肥大化対策（記事数・文字数トリム）、最大リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンスバリデーション（JSON 抽出、results リスト・各要素の code/score 検証）と ±1.0 のクリップを実装。
    - テスト容易性のため _call_openai_api の差し替え（unittest.mock.patch）を想定。
    - DB 書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT を行う冪等性設計。DuckDB の executemany の制約を考慮した実装あり。
  - regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime に保存。
    - マクロ記事抽出（マクロキーワード群）、OpenAI 呼び出し（gpt-4o-mini）、JSON レスポンスパース、リトライ/フォールバック（API失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止（target_date 未満のデータのみ使用）を意識した設計。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理を使用し、例外時は ROLLBACK を試行。

- Data モジュール (src/kabusys/data)
  - calendar_management (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定ユーティリティを実装：
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB データ優先、未登録日は曜日ベースのフォールバックという一貫した判定方針。
    - カレンダー夜間バッチ更新 calendar_update_job を実装（J-Quants クライアント呼び出しとバックフィル／健全性チェック）。
    - 最大探索日数やバックフィル日数、先読み日数などの定数を定義。
  - pipeline / etl (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを定義し、ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化して返す。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を想定した ETL パイプライン設計（実装は ETLResult とユーティリティ中心）。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research モジュール (src/kabusys/research)
  - factor_research (src/kabusys/research/factor_research.py)
    - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装：
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None を返す）
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ウィンドウ内データ不足時は None）
      - calc_value: PER / ROE（raw_financials の最新レコードを target_date 以前から取得）
    - DuckDB のウィンドウ関数や LAG/AVG を活用し、高速に計算。
    - Z スコア正規化ユーティリティは kabusys.data.stats から利用可能にする設計（外部参照）。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（柔軟な horizons サポート、入力検証）を実装。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関）を実装。少数データや等分散時の安全処理あり。
    - rank（同順位は平均ランク化）および factor_summary（count/mean/std/min/max/median）を実装。
  - research パッケージ __init__ で主要関数をまとめてエクスポート。

### Security
- 環境変数の自動ロードは OS 環境変数を上書きしないデフォルト動作で、.env.local は明示的な上書き（override）として扱う。
- API キー（OpenAI 等）は明示的に引数で注入可能で、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させ安全側で停止。

### Design / Implementation Notes
- ルックアヘッドバイアス防止を多くの関数（ニュースウィンドウ、MA 計算、regime 判定等）で厳格に実施。date.today()/datetime.today() を直接参照しない設計。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢なパースと検証を行う。5xx/ネットワーク/429 等は再試行（指数バックオフ）、解析エラー/非リトライエラーはフェイルセーフでスコア 0 またはスキップ扱い。
- DuckDB のバージョン差異（executemany への空リストバインドが不可等）を考慮した互換性処理を導入。
- DB 書き込みは可能な限り冪等（DELETE → INSERT、ON CONFLICT 等）かつトランザクション（BEGIN/COMMIT/ROLLBACK）を使用。

### Known issues / Limitations
- OpenAI（gpt-4o-mini）を利用するため、API キーが必須。API コスト・レスポンス時間・利用制限に注意。
- AI スコアリングは LLM の出力品質に依存するため、外部環境変化（モデルアップデート等）で挙動が変わる可能性がある。
- 一部の関数はデータ不足時に None や 0 を返す（ex. ma200_dev が計算不可、記事がない場合の macro_sentiment=0.0 など）。使用側で適切なハンドリングが必要。
- calendar_update_job / ETL の外部 API 呼び出し部分は jquants_client 等の実装に依存するため、本体のみでは完全に動作しない。テストでは外部依存をモックすることを想定。

---

（初回リリースのため Breaking changes / Changed / Fixed の区分はありません）