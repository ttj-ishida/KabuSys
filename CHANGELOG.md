# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

リリース日付はコードベースの最終更新日（推定）を使用しています。

## [Unreleased]
- ドキュメントや CLI、テストフレームワーク連携などの追加予定事項はここに記載します。

## [0.1.0] - 2026-03-29
初回リリース（コードベースから推測した機能群と実装の概要）。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開モジュール群を追加。
  - __version__ を "0.1.0" として設定。

- 環境設定管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使った自動ロード無効化をサポート。
  - .env パーサを実装:
    - export KEY=val 形式対応、クォート文字（シングル/ダブル）やバックスラッシュエスケープ対応。
    - 行コメントやインラインコメントの処理を細かく制御。
    - ファイル読み込み失敗時の警告出力。
  - 環境変数取得用 Settings クラスを提供（プロパティ経由で設定値アクセスを実現）。
    - 必須変数取得時の _require による ValueError 投出。
    - DU CKDB/SQLite パスのデフォルト、KABUSYS_ENV/LOG_LEVEL の検証ロジックを実装。
    - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントスコアを算出。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を明確に算出する calc_news_window 実装。
    - 1チャンクあたり最大20銘柄のバッチ送信、記事数／文字数トリム、レスポンス検証ロジックを実装。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンスバリデーションとスコアの ±1.0 クリップ処理。
    - DuckDB 互換性のため executemany の空リスト扱いを考慮した DB 書き込み（DELETE→INSERT の置換戦略）。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日移動平均乖離 (ma200_ratio)（重み70%）とニュースマクロセンチメント（重み30%）を合成してレジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出し（gpt-4o-mini）でマクロ記事を評価、API失敗時は安全側として macro_sentiment=0.0 を使用。
    - レジームスコアを clip(-1,1) して label を決定し、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - news_nlp の補助関数を直接共有せず、モジュール間の結合を避ける設計。

- データ処理（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）:
    - ETLResult dataclass を公開し、ETL 実行結果（取得数 / 保存数 / 品質チェック / エラー）を構造化して返却。
    - 差分更新 / backfill / 品質チェックの設計方針を反映。
    - DuckDB 上での最大日付取得ユーティリティ等を実装。
  - カレンダー管理（kabusys.data.calendar_management）:
    - market_calendar を利用した営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - カレンダー未取得時の曜日ベースのフォールバック、DB 値優先の一貫したロジック。
    - calendar_update_job: J-Quants API から差分取得→保存（バックフィル・健全性チェックを含む）。
    - DuckDB 日付変換ユーティリティやテーブル存在チェック等の補助関数を実装。
  - ETL インターフェース再エクスポート（kabusys.data.etl）。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum（1M/3M/6M/ma200乖離）、Volatility（20日ATR, 相対ATR, 平均売買代金, 出来高比率）、Value（PER, ROE）を DuckDB SQL で計算。
    - データ不足時の None 戻し、結果を (date, code) キーの dict リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - forward returns（任意ホライズンの将来リターン）計算。
    - calc_ic（スピアマンランク相関による IC 計算）、rank（同順位を平均ランクで扱う）、factor_summary（count/mean/std/min/max/median）を実装。
  - research パッケージの公開 API をまとめてエクスポート。

### Changed
- 設計方針・安全対策明確化（コード中に多数の設計コメントを反映）
  - ルックアヘッドバイアス防止のため各所で datetime.today()/date.today() を直接参照しない設計を徹底（target_date を外部から注入するスタイル）。
  - OpenAI 呼び出しに対してフェイルセーフ（API障害時はゼロ等で継続）、詳細なログ・警告を出力。
  - DuckDB のバージョン差に起因する制約（executemany の空リストなど）に対する互換性処理を追加。
  - モジュール間の結合を抑えるため、内部的な OpenAI 呼び出し関数を各モジュールで個別実装（テスト時に patch で差し替え可能）。

### Fixed
- レスポンスパース／エッジケース対応
  - news_nlp の JSON パースで前後余計なテキストが混在するケースに対して最外の {} を抽出して復元する耐性を追加。
  - .env パーサのクォート・エスケープ処理やコメント判定を強化し、実運用での .env フォーマット差異に強くした。

### Security
- API キーの取り扱い
  - OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY から取得する設計。未設定時は ValueError を投じ明確化。
  - .env 自動ロードにおいて OS 環境変数を保護するための protected セットを実装（.env.local による上書きを制御可能）。

### Notes / Implementation details
- OpenAI 用 SDK（gpt-4o-mini）を使用する想定。AI 呼び出しは JSON Mode を利用して厳密な JSON 出力を期待するプロンプトを仕様化。
- news_nlp と regime_detector で OpenAI 呼び出しの内部実装を分離しており、ユニットテストで差し替えやすい設計（patch 対応）。
- 多くの DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT 相当）して実装されている。
- カレンダー更新や ETL は J-Quants クライアント（kabusys.data.jquants_client）を利用する設計（実際のクライアント実装は別モジュール想定）。

---

今後の候補（コードから推測）
- 監視・実行周り（monitoring / execution）や Slack 通知の統合（Settings に Slack トークン等の設定があるため）が想定される。  
- テストと CI 用のモックユーティリティ、より詳しいドキュメント（StrategyModel.md / DataPlatform.md 参照先の整備）。

（以上）