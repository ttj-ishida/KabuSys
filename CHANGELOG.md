CHANGELOG
=========

全ての重要な変更点をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初版を追加（バージョン 0.1.0）。
  - パッケージ名: kabusys
  - __all__ に data, strategy, execution, monitoring を公開

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
  - .env パーサを独自実装（コメント処理、export プレフィックス、シングル/ダブルクォートのエスケープ処理に対応）
  - OS 環境変数を保護する protected オプションと override ロジックを提供
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを環境変数から取得
    - env（development / paper_trading / live）や log_level の値検証
    - is_live / is_paper / is_dev のユーティリティ

- ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）でセンチメントを評価
  - UTC/JST を考慮したニュース収集ウィンドウ計算（calc_news_window）
  - バッチ処理（最大 20 銘柄 / チャンク）、記事件数・文字数のトリム対応（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
  - JSON Mode を使用した厳格なレスポンス期待（{"results":[{"code":"XXXX","score":0.0}, ...]}）
  - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装
  - レスポンスの厳密なバリデーションとスコアの ±1.0 クリッピング
  - DuckDB への書き込みは冪等性を意識（対象コードのみ DELETE → INSERT、executemany の空リスト回避）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で regime を判定
  - マクロキーワードによる raw_news フィルタリング、最大記事数制限
  - OpenAI 呼び出しは独立実装、リトライ / バックオフ / フェイルセーフ（API 失敗時 macro_sentiment=0.0）
  - レジームスコアのクリップ処理とラベル付け（bull / neutral / bear）
  - DuckDB へ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）

- 研究用ファクター計算（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ/流動性（20 日 ATR、相対 ATR、平均売買代金、出来高比率）
    - バリュー（PER, ROE: raw_financials と prices_daily の結合）
    - データ不足時の None 処理と安全な SQL 実装（DuckDB）
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman ρ）計算、ランク変換ユーティリティ（同順位は平均ランク）
    - factor_summary：count/mean/std/min/max/median の算出（None を除外）
  - z-score 正規化ユーティリティをデータ層から参照可能に公開

- データ管理（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar テーブル）、祝日・半日・SQ判定ロジック
    - DB データ優先、未登録日は曜日ベースでフォールバック（週末除外）
    - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day を提供
    - calendar_update_job: J-Quants から差分取得・バックフィル（直近 _BACKFILL_DAYS を再取得）・健全性チェック
  - pipeline / ETL:
    - ETLResult データクラスを提供（取得件数・保存件数・品質問題・エラー一覧など）
    - 差分更新・バックフィル・品質チェック（quality モジュール連携）の設計を反映
  - etl モジュールは ETLResult を再エクスポート

- 共通設計方針・運用上の配慮
  - ルックアヘッドバイアス防止: 各処理で datetime.today() / date.today() を直接参照しない設計（target_date を明示的に渡す）
  - DuckDB を主要なローカル分析 DB として想定、SQL + Python による計算を優先
  - DB 書き込みは冪等性を意識（DELETE→INSERT や ON CONFLICT を想定）
  - OpenAI 呼び出しに対する安全策（リトライ・バックオフ・非致命的フォールバック）
  - テスト容易性: OpenAI 呼び出し箇所をモック差し替え可能に実装（_call_openai_api を patch で置換）

Changed
- 初版リリースのため該当なし

Fixed
- 初版リリースのため該当なし

Security
- 必須の環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）は Settings 経由で取得。未設定時は ValueError を送出するため、運用時には .env の準備または環境変数設定が必要。

Notes / Known limitations
- strategy / execution / monitoring パッケージ名は __init__ で公開されているが、この変更セット内には関連する実装ファイルが含まれていない（将来の実装予定）。
- DuckDB のバージョン差異による executemany の挙動（空リスト不可等）を考慮した防御的実装を行っている。
- 外部 API（J-Quants, OpenAI）呼び出しの実行には各種 API キーやネットワーク接続が必要。API レスポンスの不整合はログ警告のうえフェイルセーフ挙動にフォールバックするが、想定外ケースではスコア取得失敗が発生する可能性がある。

References
- 実装内コメントや docstring に設計方針・処理フローを詳細に記載しています。必要に応じて各モジュールの docstring を参照してください。