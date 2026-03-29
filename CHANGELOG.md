CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- 既知のバージョンは semver に準拠します。  
- 日付はリリース日を表します。

[Unreleased]
------------

- なし

0.1.0 - 2026-03-29
------------------

Added
- 初回リリース: kabusys パッケージの基本機能を公開
  - パッケージメタ:
    - __version__ = "0.1.0"
    - パッケージトップで data, strategy, execution, monitoring を __all__ で公開

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化可能（テスト向け）
    - OS 側に既に存在する環境変数は保護（protected）して上書きを防止
  - .env パーサを実装
    - "export KEY=val" 形式対応
    - シングル/ダブルクォート内のエスケープ処理対応
    - コメントの扱い（クォート有無での取り扱い差）
  - Settings クラスでアプリ設定をプロパティ化
    - J-Quants / kabuステーション / Slack / DB パス等を取得
    - env（development / paper_trading / live）と log_level のバリデーション
    - is_live / is_paper / is_dev のユーティリティプロパティ

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄毎のニュースを集約し OpenAI （gpt-4o-mini）でセンチメント評価
  - 主な仕様:
    - JST の前日15:00〜当日08:30 相当のウィンドウ計算（calc_news_window）
    - 1銘柄あたり最大記事数・文字数を制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - 1 API コールで最大 20 銘柄単位のバッチ処理（_BATCH_SIZE）
    - JSON Mode を利用し厳密な JSON 出力を期待
    - レート制限・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列チェック、コード/スコアの型チェック）
    - スコアは ±1.0 にクリップ
    - 書き込みは部分失敗に備えて該当コードのみ DELETE → INSERT（冪等保存）
    - API キーは引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次で regime を判定
  - 主な仕様:
    - ma200_ratio を DuckDB の prices_daily から計算（ルックアヘッド防止のため target_date 未満のみ使用）
    - マクロキーワードで raw_news をフィルタしてタイトルを LLM に渡して macro_sentiment を算出
    - LLM 呼び出しは gpt-4o-mini、JSON mode 利用、再試行/バックオフ実装
    - API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ
    - 合成スコアをクリップし閾値で 'bull'/'neutral'/'bear' を決定
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）と ROLLBACK 処理

- データ関連（kabusys.data）
  - calendar_management
    - JPX カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ロジックを提供
    - DB に calendar データがない場合は曜日ベース（土日除外）でフォールバック
    - calendar_update_job: J-Quants API から差分取得 → market_calendar に冪等保存、バックフィルと健全性チェックを実装
  - pipeline / etl
    - ETLResult データクラス（kabusys.data.pipeline.ETLResult）を公開（kabusys.data.etl で再エクスポート）
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）のインターフェース設計
    - DuckDB テーブル存在チェック・最大日付取得等のユーティリティ実装

- Research（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時は None）
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（データ不足時は None）
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS 無効時は None）
    - 各関数とも DuckDB の prices_daily / raw_financials のみ参照し、外部発注等の副作用なし
  - feature_exploration
    - calc_forward_returns: 将来リターン計算（horizons の入力検証、まとめて1クエリ取得）
    - calc_ic: スピアマンのランク相関（ties は平均ランク処理）
    - rank: 値をランクに変換（round(...,12) による数値丸めで ties の安定化）
    - factor_summary: 各カラムの基本統計量（count/mean/std/min/max/median）を計算

- パッケージ公開・再エクスポート
  - kabusys.ai.__init__ で score_news をエクスポート
  - kabusys.research.__init__ で主要計算関数と zscore_normalize を公開
  - kabusys.data.etl で ETLResult を再エクスポート

Changed
- 設計上の多くの決定を明文化（ドキュメンテーション的な実装注釈）
  - ルックアヘッドバイアス回避のため date.today() 等を参照しない設計を採用
  - DuckDB のバインド/ executemany の挙動に配慮した実装（空リストの扱い回避）
  - OpenAI 呼び出し関数はモジュール毎に独立実装してテスト時に差し替えやすく設計

Fixed
- フェイルセーフ / ロバスト性強化
  - OpenAI API の失敗時に例外で停止させず、適切にフォールバック値（例: macro_sentiment=0.0）を使用するように実装
  - JSON レスポンスの前後ノイズに対応するため最外の {} を抽出してパースする復元ロジックを導入
  - DB 書き込みでエラー発生時に ROLLBACK を試み、さらに ROLLBACK 失敗をログ出力

Security
- なし（このリリースで報告されたセキュリティ修正はありません）

Deprecated
- なし

Removed
- なし

Notes / その他
- OpenAI SDK のエラー型やフィールド名の変化に備えて getattr(..., default) を用いる等、将来 SDK の変更に対する寛容性を持たせている箇所があります。
- 一部実装（例: _adjust_to_trading_day の続き等）がファイル末尾で途切れている箇所があります。リリース時点では主要機能の API（関数群）は定義済みですが、未実装箇所は今後のパッチで補完予定です。

もし詳しいリリース日付の調整や、追加で「既知の問題」や「今後の予定（Roadmap）」をCHANGELOGに付記したい場合は指示してください。