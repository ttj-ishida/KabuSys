Keep a Changelog
=================

すべての重要な変更はこのファイルに記載します。
このファイルは「Keep a Changelog」規約に準拠しています。

フォーマット:
- Unreleased: 現在開発中の変更
- バージョン見出しは [version] - YYYY-MM-DD の形式

## [Unreleased]
- 今後の改善予定（コードからの推測）
  - 単体テスト・統合テストの拡充（OpenAI 呼び出しや DuckDB 周りのモック強化）
  - OpenAI クライアントの抽象化・テスト容易性向上
  - ロギング設定の公開（settings 経由での構成反映）
  - API クライアント（J-Quants / kabu）のエラーハンドリング強化と戻り値の型安定化

## [0.1.0] - 2026-03-31
初回リリース。以下の主要機能とモジュールを実装。

Added
- パッケージ基盤
  - パッケージのバージョン定義と公開モジュール一覧を追加（kabusys.__init__）。
- 設定管理（kabusys.config）
  - .env/.env.local を自動ロードする仕組みを実装（プロジェクトルート検出は .git / pyproject.toml に基づく）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサの実装（export プレフィックス、クォート・エスケープ、コメント取り扱いなどに対応）。
  - Settings クラスを提供し、J-Quants・kabu API・Slack トークン・DB パス・環境種別（development/paper_trading/live）・ログレベルの取得と検証を行う。
  - 必須環境変数未設定時に明示的なエラーを投げる _require 実装。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのテキストを生成し、OpenAI（gpt-4o-mini）に対してバッチで JSON Mode を使ったセンチメント評価を実施。
    - バッチサイズ制御、1 銘柄あたりの最大記事数と最大文字数でトークン肥大対策。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密なバリデーション実装（JSON 抽出、results リスト、code/score の検証、スコアのクリップ）。
    - 部分失敗時にも既存スコアを保護するため、取得した銘柄のみ DELETE→INSERT で置換する冪等保存処理を実装。
    - テスト用に内部の OpenAI 呼び出し関数のモック差替えを想定した設計（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、OpenAI 呼び出しは独立実装。API失敗時は macro_sentiment=0.0 とするフェイルセーフ。
    - DB への書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作で実装。
    - リトライ・エラー処理（RateLimit/接続タイムアウト/APIError の扱い）を実装。
- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - market_calendar 未取得時は曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants からの差分取得、バックフィル（直近日数再フェッチ）、健全性チェック、冪等保存フローを実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー一覧を保持）。
    - テーブル存在確認・最大日付取得などのユーティリティ実装。
    - 差分更新・backfill・品質チェック（quality モジュールとの連携）を想定した構成。
  - jquants_client との連携ポイントを想定（fetch/save 関数を利用する設計）。
- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20日 ATR、ATR 比率、平均売買代金、出来高比率）、Value（PER, ROE）の計算関数を実装。
    - DuckDB 上の SQL を多用し、営業日ベースの窓処理・欠損時の None 扱いなど、実務的な欠損耐性を考慮。
    - 出力は (date, code) を含む dict リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、データ存在チェック）、IC 計算（Spearman の ρ によるランク相関）、統計サマリー（count/mean/std/min/max/median）を提供。
    - ランキング関数（rank）で同順位は平均ランクを採用、丸め処理で ties の安定化を実装。
    - pandas など外部依存を使わず標準ライブラリ＋DuckDB で実装。
- 共通実装上の設計方針（コード全体に反映）
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() を直接参照する処理を極力排除し、関数呼び出し側から基準日を受け取る設計。
  - OpenAI 呼び出しにおける堅牢なエラー処理（リトライ、5xx 判定、JSON パース失敗フォールバックなど）。
  - DuckDB のバージョン互換性に配慮した実装（executemany における空リスト回避等）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT など）し、ロールバック処理を組み込み。
  - テストしやすい内部フック（_call_openai_api の patch ポイント等）を用意。

Changed
- 初回公開のため該当なし。

Fixed
- 初回公開のため該当なし。

Security
- 現時点でセキュリティ関連の注記はなし。環境変数・APIキーの取り扱いは Settings 経由で必須化している点に留意。

Notes / Known limitations
- OpenAI の呼び出しは gpt-4o-mini と JSON モードを前提としているが、API 仕様変更やレスポンスのばらつきに対する保護コード（JSON 抽出・バリデーション）は入れているものの、運用中に調整が必要な可能性あり。
- DuckDB のバインド挙動や日付型の取り扱いは実稼働での確認が必要（コードは互換性に配慮している）。
- quality モジュールや jquants_client は外部実装（または別モジュール）を想定しており、実際の ETL 実行にはそれらの実装が必要。

リリースノート作成に使用したソースの根拠
- src 内のモジュール実装（config / ai / data / research 等）から機能の存在・設計方針・注意点を抽出して記載しました。

-----