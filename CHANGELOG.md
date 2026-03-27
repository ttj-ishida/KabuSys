# CHANGELOG

すべての重要な変更はこのファイルで管理します。本ファイルは「Keep a Changelog」仕様に従っています。  
フォーマット:
- Added: 新機能
- Changed: 変更
- Fixed: 修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

## [Unreleased]
- なし

## [0.1.0] - 2026-03-27
初回リリース。以下の主要機能と設計方針を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。公開モジュール: data, strategy, execution, monitoring。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境設定管理
  - Settings クラスを実装し、環境変数からアプリ設定を取得可能に（src/kabusys/config.py）。
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml で探索）。
  - .env パーサーは export 形式、クォートやエスケープ、コメント処理に対応。自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - 必須環境変数チェック関数を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - デフォルト値: KABUS_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV（development/paper_trading/live）等。

- AI（自然言語処理）モジュール
  - ニュースセンチメント分析: score_news を実装（src/kabusys/ai/news_nlp.py）。
    - 前日15:00 JST〜当日08:30 JST のニュースを対象に銘柄単位で集約し、OpenAI（gpt-4o-mini）へバッチ送信してスコアを生成。
    - バッチサイズ、文字数・記事数上限、JSON mode を使った堅牢なレスポンスバリデーション、スコアクリッピング（±1.0）を実装。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）や指数バックオフを実装。API失敗時は該当チャンクをスキップし処理継続（フェイルセーフ）。
    - DuckDB への書き込みは冪等（DELETE → INSERT）かつ部分失敗時に他コードを保護する実装。
    - テスト容易性のため OpenAI 呼び出し部を差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定: score_regime を実装（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で 'bull'/'neutral'/'bear' を判定・保存。
    - マクロ記事抽出、OpenAI 呼出し、エラーハンドリング（リトライ・5xx判定・フォールバック macro_sentiment=0.0）を実装。
    - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に保存。失敗時は ROLLBACK と例外伝播。

- データプラットフォーム関連
  - ETLパイプラインの公開インターフェース ETLResult を追加（src/kabusys/data/etl.py / pipeline.py）。
    - 差分取得・backfill・品質チェックの結果を集約するデータクラスを提供。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。
  - マーケットカレンダー管理モジュール（src/kabusys/data/calendar_management.py）を追加。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - J-Quants からの差分取得・夜間アップデートジョブ(calendar_update_job) を実装。バックフィル・健全性チェックあり。
    - DB未取得時は曜日ベースでフォールバックする一貫した挙動。

- リサーチ（因子計算）モジュール（src/kabusys/research/*）
  - ファクター計算: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials を参照）。
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR、平均売買代金、出来高比率、PER/ROE 等を含む。
    - データ不足時の None 処理やログ出力を実装。
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank を実装。
    - 将来リターン計算（複数ホライズン）、スピアマンIC（ランク相関）、統計サマリーを提供。
    - pandas等に依存しない純標準ライブラリ実装。

- 共通実装・設計的配慮
  - DuckDB を主な分析データベースとして利用する設計（多くの関数で DuckDB 接続を引数に受ける）。
  - ルックアヘッドバイアス防止: 各部で datetime.today()/date.today() の直接参照を避け、target_date を明示的に受け取る実装。
  - ロギングを各モジュールに導入（情報・警告・デバッグログ）。
  - テストしやすさを考慮し、API呼出し部は差し替え可能に実装。
  - OpenAI 呼び出しは JSON mode とゼロ温度（temperature=0）を使用し、レスポンスの堅牢なパースを実装。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- OpenAI API キーや各種トークンは環境変数で管理する方針を明確化（Settings で必須チェック）。.env 自動読み込み時に既存 OS 環境変数を保護する仕組みを導入。

---

注意事項・移行メモ（利用者向け）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を使う機能を利用する場合は OPENAI_API_KEY（score_news / score_regime の api_key 引数でも指定可）
- .env 自動読み込み:
  - プロジェクトルートは本モジュールファイルから親ディレクトリを遡って .git または pyproject.toml を探して決定します。CIやテストで自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 書き込みの注意:
  - DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、該当箇所では明示的に空チェックを行っています。
- OpenAI 呼び出しの挙動:
  - 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライします。その他のエラーや最終的な失敗時はフェイルセーフとして該当チャンク/評価をスキップし、中立（0.0）やスコア未書き込みで継続します。

この CHANGELOG はコードベースから推測して作成しています。各機能の詳細な使用方法は該当モジュールのドキュメントや docstrings を参照してください。