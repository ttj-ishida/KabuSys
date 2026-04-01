CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

フォーマットの意味:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: 修正
- Security: セキュリティ関連の修正

[Unreleased]
------------

- —


[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初版リリース。
- 基本パッケージ情報を公開
  - kabusys.__version__ = 0.1.0
  - パッケージトップで data/strategy/execution/monitoring を __all__ に公開。

- 環境変数／設定管理 (kabusys.config)
  - .env / .env.local の自動ロード実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env パーサ実装: export KEY=val 形式、シングル/ダブルクォートとバックスラッシュエスケープ、コメント処理に対応。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。OS 環境変数は保護（上書き回避）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live） / ログレベル等の取得とバリデーションを提供。
  - 必須環境変数未設定時は明確な ValueError を送出。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメントスコアを算出。
  - タイムウィンドウ定義（JST基準）：前日 15:00 ～ 当日 08:30（UTC に変換して DB を参照）。
  - 1銘柄あたり記事件数・文字数の上限（デフォルト: 最大10記事、3000文字）でトークン肥大化を抑制。
  - 1 API 呼び出しで最大 20 銘柄のバッチ処理（_BATCH_SIZE=20）。
  - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対し指数バックオフでリトライ（最大回数設定あり）。
  - レスポンスのバリデーション実装（JSON 抽出、results 配列検証、コード存在チェック、数値検証、±1.0 クリップ）。
  - DuckDB 互換性を考慮し、executemany へ空リストを渡さない防御実装。
  - API 呼び出し箇所はテスト容易性のため _call_openai_api を分離（patch による差し替え容易）。
  - APIキーは引数で注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
  - MA200 乖離算出、raw_news からマクロキーワードフィルタ取得、OpenAI による macro_sentiment 評価（gpt-4o-mini）、スコア合成と閾値判定を実装。
  - LLM 呼び出しでのリトライ、API 失敗時は macro_sentiment = 0.0 のフェイルセーフ。
  - idempotent な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とエラー時の ROLLBACK ロギング。
  - テスト用に _call_openai_api を分離。

- 研究用ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム: 約1ヶ月/3ヶ月/6ヶ月リターン、200日移動平均乖離を計算（データ不足時は None）。
    - ボラティリティ/流動性: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - バリュー: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB を用いた SQL 実装。prices_daily / raw_financials のみ参照し外部 API へはアクセスしない。
  - feature_exploration:
    - 将来リターン計算（デフォルト horizons = [1,5,21]、ホライズン検証あり）。
    - IC（Spearman の ρ）計算（rank による同順位処理、最小サンプル数検査）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
    - 標準ライブラリのみで実装（pandas 等に依存しない）。
  - research パッケージは zscore_normalize 等のユーティリティを再エクスポート。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を基に営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。最大探索日数制限で無限ループ回避。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、保存）。
  - pipeline / etl:
    - ETLResult データクラスを提供（取得件数、保存件数、品質問題、エラー集約）。
    - pipeline モジュールに基づく差分取得、保存（jquants_client の save_* を利用して冪等保存）、品質チェックのフレームワーク設計を反映。
    - ETLResult.to_dict() により品質問題をシリアライズ可能。
  - jquants_client を介したデータ取得・保存を想定（実際のクライアントは別モジュール）。

- 共通設計方針（横断的）
  - ルックアヘッドバイアス対策: 多くの関数は datetime.today()/date.today() を参照せず target_date に依存する設計。
  - API 呼び出しはフェイルセーフに設計（失敗時はスキップまたはデフォルト値で継続し、例外を不要に伝播させない箇所がある）。
  - DuckDB とトランザクション（BEGIN/COMMIT/ROLLBACK）を用いた冪等更新を徹底。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Implementation hints
- OpenAI API を利用する機能は api_key を引数で渡す設計になっており、テストではパッチ差し替えが容易。
- .env パーシングはシェルライクなエスケープやコメントに配慮しており、.env.local の値で .env を上書きする挙動（OS 環境変数は保護）を採用。
- DuckDB の executemany に関する互換性（空リスト渡し不可）を考慮した実装が各所に含まれる。

開発者向け連絡
- 本リリースは初期実装を幅広く含むため、各モジュール（特に外部 API 呼び出し部分）については統合テストと運用時モニタリングを推奨します。各処理はログ出力を行うので、実運用時は LOG_LEVEL を適切に設定してください。