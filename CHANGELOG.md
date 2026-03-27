Keep a Changelog
=================

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
バージョニングは SemVer に従います。

Unreleased
----------

- 今後の変更予定はここに記載します。

[0.1.0] - 2026-03-27
-------------------

Added
- 初期リリース: kabusys パッケージ (バージョン 0.1.0)
  - パッケージのエントリポイントを定義 (src/kabusys/__init__.py)。
  - 公開サブパッケージ候補: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定/ロード機能 (src/kabusys/config.py)
  - Settings クラスを提供し、アプリケーション設定を環境変数から取得。
  - .env / .env.local の自動読み込みをプロジェクトルート（.git または pyproject.toml）を基準に実施。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサーを実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルール等に対応。
  - 環境変数要求ヘルパー (_require) と入力検証:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須変数チェック。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL（DEBUG/INFO/...）の検証。
  - デフォルトの DB パス (DUCKDB_PATH, SQLITE_PATH) の取り扱い（Path 型で返却）。

- AI（NLP）モジュール (src/kabusys/ai)
  - news_nlp モジュール:
    - raw_news と news_symbols を元に銘柄毎のニュースを集約し、OpenAI (gpt-4o-mini) に JSON mode で一括問い合わせしてセンチメント（ai_score）を算出。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの記事数・文字数上限、リトライ（429/ネットワーク/5xx に対する指数バックオフ）等を実装。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。DuckDB への置換的書き込み（DELETE → INSERT）をトランザクションで実行。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
    - calc_news_window によるタイムウィンドウ計算（JST ベースの前日15:00〜当日08:30 を UTC に変換）。
  - regime_detector モジュール:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算、マクロキーワードフィルタ、OpenAI 呼び出し（gpt-4o-mini、JSON mode）、リトライ/フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。ルックアヘッドを避ける設計（date < target_date 等）。
    - API 呼び出しはモジュール内部で独立実装（モジュール間のプライベート関数共有を避ける）。

- Research（因子・特徴量解析）モジュール (src/kabusys/research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) の計算（DuckDB SQL を活用）。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を算出（EPS が 0 または欠損時は None）。
    - すべて DuckDB の prices_daily / raw_financials のみ参照。外部 API へはアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターン計算。horizons の検証と1クエリでの取得最適化。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。欠損・同順位処理を含む。
    - rank: 同順位は平均ランクにする実装（round による tie 対策）。
    - factor_summary: count/mean/std/min/max/median などの基本統計集約。

- Data（データ管理）モジュール (src/kabusys/data)
  - calendar_management:
    - market_calendar テーブルを利用した営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB データを優先し、未登録日は曜日ベースのフォールバック（週末除外）で一貫した挙動を提供。
    - calendar_update_job: J-Quants クライアント経由でカレンダーを差分取得し、バックフィル（直近数日）・健全性チェック（将来日付の異常検知）・冪等保存を実施。
  - pipeline (ETL):
    - ETLResult dataclass を公開（kabusys.data.etl に再エクスポート）。ETL の取得数/保存数、品質チェック結果、エラー一覧を収集して返却可能。
    - テーブル存在チェック、最大日付取得等のユーティリティを実装。
    - ETL の設計方針として差分更新、部分失敗時の既存データ保護、品質チェックの集約的取り扱いを明示。

- 公開ヘルパー/互換性
  - ETLResult の再エクスポート (src/kabusys/data/etl.py)。
  - DuckDB を前提とした SQL 実装と互換性配慮（executemany の空リスト回避など）を含む。

Fixed / Hardened
- ルックアヘッドバイアス対策: AI スコアリング系（news_nlp, regime_detector）は datetime.today()/date.today() を内部で参照せず、呼び出し側から target_date を受け取る設計。
- OpenAI 呼び出し周りの堅牢化:
  - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ実装。
  - JSON パース失敗や不正レスポンスはロギングしてフォールバック（0.0 やスキップ）することで全体処理の継続を確保。
- DuckDB 相互運用性の考慮（空の executemany を避ける等）とトランザクション保護（BEGIN/COMMIT/ROLLBACK を使用した冪等書き込み）。
- テスト容易性向上:
  - OpenAI 呼び出しを差し替え可能にしてユニットテストでのモックを想定。

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 今後の改善候補（推測）
- strategy / execution / monitoring サブパッケージの具体実装はこのリリースでは含まれていないように見える（__all__ に名前のみ宣言）。これらの実装追加は今後のリリースで予定されると推測される。
- jquants_client の実装や外部 API の認証周り（id_token 注入など）の詳細は実コードの提供に応じて改善可能。
- テストカバレッジ強化（DuckDB を使った統合テスト、OpenAI 呼び出しのフェイルケース）を推奨。

----