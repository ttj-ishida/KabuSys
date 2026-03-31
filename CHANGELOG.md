CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。  

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

Unreleased
----------
（未リリースの変更はここに記載します）

0.1.0 - 2026-03-31
-----------------

Added
- パッケージ初回リリースとして CLI/ライブラリ名 "kabusys" を公開
  - パッケージバージョン: 0.1.0
  - __all__ により主要サブパッケージを公開: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）
  - .env パースの堅牢化:
    - コメント、export プレフィックス、シングル・ダブルクォート、バックスラッシュエスケープ対応
    - 行単位の無効判定（空行・コメント等）
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを提供し、各種必須設定をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック
    - KABU_API_BASE_URL のデフォルト
    - データベースパスのデフォルト（DUCKDB_PATH, SQLITE_PATH）
    - KABUSYS_ENV の検証（development, paper_trading, live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の判定ユーティリティ

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp.score_news)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを ai_scores テーブルへ保存
    - 一銘柄あたりの最大記事数・文字数制限、チャンク処理（最大 20 銘柄/コール）
    - JSON Mode 応答の堅牢なバリデーション（レスポンスのパースと検証）
    - レート制限/ネットワーク断/タイムアウト/5xx に対する指数バックオフとリトライ
    - フェイルセーフ設計: API 失敗時は当該チャンクをスキップして他の銘柄処理を継続
    - 書き込みは部分失敗耐性あり（成功したコードのみ DELETE→INSERT で置換）
    - calc_news_window ユーティリティにより JST のニュースウィンドウ（前日15:00〜当日08:30）を UTC naive datetime で計算
  - 市場レジーム判定 (kabusys.ai.regime_detector.score_regime)
    - ETF (code=1321) の 200 日移動平均乖離を用いたテクニカルスコアと、マクロニュースの LLM センチメントを重み付けしてレジーム（bull/neutral/bear）を算出
    - OpenAI 呼び出しを専用関数で実装し、news_nlp と結合しない設計（モジュール分離）
    - API リトライ/フォールバック: LLM 呼び出し失敗時は macro_sentiment を 0.0 として継続
    - レジーム結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）

- データプラットフォーム関連 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーを扱うユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB の market_calendar を優先し、未登録日は曜日ベースでフォールバック（週末除外）
    - calendar_update_job: J-Quants API から差分取得 → market_calendar へ冪等保存。バックフィルと健全性チェックを実装
  - ETL パイプライン (kabusys.data.pipeline と kabusys.data.etl)
    - ETLResult dataclass を公開（ETL の取得/保存件数、品質問題、エラーを集約）
    - 差分更新、バックフィル、品質チェックの設計方針を実装（jquants_client 経由での取得・save_* による冪等保存）
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得 等
    - デフォルトのバックフィル/先読み設定を導入（例: calendar lookahead/backfill）
  - jquants_client を想定した API 連携ポイントを用意（fetch/save の呼び出しに対応）

- Research（研究）モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m/3m/6m、ma200_dev（200 日 MA 乖離）等を DuckDB の prices_daily から計算
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新財務レコードを target_date 以前から取得）
    - ファクター計算はデータ不足時に None を返す設計
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（欠損・同値・最小サンプル数の扱いを明確化）
    - rank: 同順位は平均ランクで扱う（丸めで ties 判定の安定化）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
  - 研究用ユーティリティ群を __init__ で再エクスポート（zscore_normalize を含む）

- 実装方針・品質面での配慮（全体）
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を内部で直接参照しない設計（すべて target_date を引数で指定）
  - DuckDB を主要なローカル分析 DB として利用
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 等想定）
  - OpenAI API 呼び出しは JSON モードを利用し、パースとバリデーションを堅牢に実装
  - エラーはできる限り局所的に処理（部分失敗を許容）し、上位で判断できるよう ETLResult 等で集約

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Security
- 環境変数に API キー（OPENAI_API_KEY 等）を想定。AI 関連関数は API キー未設定時に ValueError を送出し、誤った挙動を防止。

Notes / Migration
- AI 機能を使用する場合は環境変数 OPENAI_API_KEY を設定するか、各関数に api_key を明示的に渡してください。
- 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用途）。
- DuckDB のテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime 等）が期待されます。スキーマ不一致や未作成時の挙動は各モジュール内のチェック／フォールバックに従います。
- ETL/カレンダー取得は jquants_client との統合を前提としています。テスト時は該当クライアントをモックしてください。

今後の予定（例）
- strategy / execution モジュールの実装・ドキュメント化
- AI モデル挙動の追加検証と性能チューニング
- DuckDB スキーマ定義とマイグレーション管理の提供

--- 

（本 CHANGELOG はコードベースの実装内容から推測して作成しています。実際の変更履歴運用ではコミット履歴やリリースノートに基づいて更新してください。）