# CHANGELOG

すべての重要な変更点を記録します。本ドキュメントは「Keep a Changelog」仕様に準拠しています。  
リリース日はコードベースから推測した作成日を使用しています。

全般的な注記
- セマンティックバージョニングに従います（パッケージ版の __version__ は `0.1.0`）。
- DuckDB をデータストアとして想定した設計と、OpenAI（gpt-4o-mini）による JSON Mode を用いた NLP 統合が含まれます。
- 時刻/日付の扱いに関しては「ルックアヘッドバイアス防止」を設計方針に明示しており、内部で datetime.today()/date.today() を直接参照しない実装になっています（テスト・バックテストの信頼性向上）。

Unreleased
- （なし）

[0.1.0] - 2026-03-28
Added
- 初期公開リリース。以下の主要コンポーネントを実装・公開。
  - パッケージ構成
    - kabusys パッケージ（__version__ = 0.1.0）
    - サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ 指定）
  - 環境設定管理（kabusys.config）
    - .env / .env.local の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）
    - export KEY=val 形式やクォート／コメント処理に対応した .env パーサを実装
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応
    - 必須環境変数取得用の _require()、および Settings クラスを提供
    - 主要設定項目: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL
  - AI（自然言語処理）機能（kabusys.ai）
    - news_nlp.score_news
      - raw_news と news_symbols を元に銘柄別に記事を集約し、OpenAI にバッチ送信してセンチメント（-1.0〜1.0）を算出
      - チャンク処理（最大20銘柄/チャンク）、トークン肥大化対策（記事数・文字数の上限）
      - JSON Mode を用いたレスポンスバリデーションと数値クリップ（±1.0）
      - レート制限・ネットワーク断・サーバーエラー（5xx）に対する指数バックオフリトライ
      - 成功した銘柄のみ ai_scores テーブルに DELETE → INSERT で置換（部分失敗時に他銘柄を保護）
    - regime_detector.score_regime
      - ETF 1321（Nikkei 225 連動型）の200日移動平均乖離（重み 70%）と news_nlp を用いたマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定
      - OpenAI 呼び出しに対するリトライ/フォールバック、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）、失敗時の ROLLBACK ハンドリング
      - LLM 呼び出し失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）
    - 共通: OpenAI クライアント呼び出しはモジュール内で抽象化しており、テスト時に差し替え可能
  - データ基盤（kabusys.data）
    - calendar_management
      - market_calendar テーブルによる営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
      - DB 登録値優先、未登録日は曜日ベースのフォールバック（カレンダーデータがまばらな場合でも一貫性を保つ設計）
      - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック
    - pipeline / ETL
      - ETLResult データクラスを公開（ETL 実行結果／品質問題／エラー情報の集約）
      - 差分更新・バックフィル・品質チェック（quality モジュールとの連携を想定した設計方針）
  - リサーチ（kabusys.research）
    - factor_research
      - calc_momentum: 1M/3M/6M リターン、ma200乖離を計算（データ不足時は None）
      - calc_volatility: 20日 ATR（avg true range）、相対ATR、平均売買代金、出来高比率を計算
      - calc_value: raw_financials から最新財務を取得し PER / ROE を算出（EPS が無効な場合は None）
      - DuckDB SQL を活用した効率的な集合演算
    - feature_exploration
      - calc_forward_returns: 将来リターン（任意ホライズン）の一括計算（horizons チェックあり）
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算
      - factor_summary, rank: 統計サマリーとランク付けユーティリティ（外部依存なし）
  - テスト/運用フレンドリーな設計
    - 直接日時を参照しない設計により、バックテストでのルックアヘッド防止
    - 外部API呼び出し箇所は差し替え可能に実装（unittest.mock でモックしやすい）
    - DuckDB の executemany に関する互換性配慮（空リストチェック）

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で提供する必要あり。未設定時は ValueError を送出する箇所あり（score_news, score_regime）。
- 環境変数による機密情報のハンドリングは Settings 経由で行うことを推奨。

互換性・移行メモ
- 必須環境変数（代表例）
  - OPENAI_API_KEY（news_nlp / regime_detector）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabu API）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（監視通知）
- .env 自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / raw_* / prices_daily 等のスキーマが期待されます。ETL・AI処理の前に必要テーブルが存在することを確認してください。
- OpenAI のレスポンス仕様（JSON Mode）に依存しています。モデルや SDK バージョンを変更する際はレスポンスパースの互換性に注意してください。
- calendar_update_job と ETL パイプラインは J-Quants クライアント（kabusys.data.jquants_client）に依存します。実行環境へ適切な認証情報を設定してください。

公開 API（代表的な関数）
- kabusys.config.Settings（settings）
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.research.factor_research.calc_momentum(conn, target_date)
- kabusys.research.factor_research.calc_volatility(conn, target_date)
- kabusys.research.factor_research.calc_value(conn, target_date)
- kabusys.research.feature_exploration.calc_forward_returns(conn, target_date, horizons=None)
- kabusys.research.feature_exploration.calc_ic(factor_records, forward_records, factor_col, return_col)
- kabusys.research.feature_exploration.factor_summary(records, columns)
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
- kabusys.data.pipeline.ETLResult

既知の制約・注意点
- DuckDB のバージョン依存の挙動（executemany の空リスト扱いなど）を考慮したコードになっています。使用する DuckDB のバージョンによっては注意が必要です。
- LLM のレスポンスが想定外の場合は該当チャンクをスキップし、部分的にスコアが書き込まれる可能性があります（設計上のフェイルセーフ）。
- JSON パースや API レスポンスのバリデーションに失敗した場合、例外を投げずに空結果・デフォルト値（例: macro_sentiment=0.0）へフォールバックする箇所があります。ログに警告が出力されます。

今後の予定（想定）
- ai モジュールのモデル/プロンプト改善、より精緻なレスポンスバリデーション
- ETL のさらに細かな品質チェック（quality モジュールとの統合拡張）
- モニタリング・アラート機能（Slack 経由通知など）の実装・強化

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時は変更履歴やコミットログを参照してください。）